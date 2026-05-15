"""
FastAPI 主服务 - 多智能体调度模块
端口：8084
集成飞书机器人 Webhook 告警推送
"""
import asyncio
import logging
import os
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from .state_machine import SystemState, EventType, Event, get_state_machine
from .alert_grader import AlertLevel, Alert, get_grader
from .event_router import EventRouter, EventConverter, get_router
from .fusion import FusionEngine, get_fusion_engine
from .redis_client import RedisStreamClient, get_redis_client, STREAMS
from .feishu_notifier import get_notifier, set_feishu_webhook, FeishuNotifier, AlertPayload

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============== 数据模型 ==============

class SensorEventRequest(BaseModel):
    sensor_id: str
    sensor_type: str
    value: float
    location: Optional[str] = None
    timestamp: Optional[str] = None
    confidence: float = 1.0


class VisionEventRequest(BaseModel):
    camera_id: str
    detection_type: str
    confidence: float
    location: Optional[str] = None
    bbox: Optional[Dict[str, int]] = None
    timestamp: Optional[str] = None


class VoiceEventRequest(BaseModel):
    intent_type: str
    raw_text: str
    confidence: float
    location: Optional[str] = None
    timestamp: Optional[str] = None


class ManualAlertRequest(BaseModel):
    message: str
    level: str = "P1"
    location: Optional[str] = None


class EventResponse(BaseModel):
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


class FeishuWebhookRequest(BaseModel):
    """配置飞书 Webhook URL"""
    webhook_url: str = Field(..., description="飞书机器人 Webhook URL")


class FeishuTestRequest(BaseModel):
    """测试飞书通知"""
    webhook_url: Optional[str] = None  # 不传则使用已配置的 URL


# ============== 生命周期管理 ==============

redis_client: Optional[RedisStreamClient] = None
fusion_engine: Optional[FusionEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, fusion_engine

    logger.info("Starting AI Coordinator Service...")

    # 初始化 Redis
    redis_client = get_redis_client()
    fusion_engine = get_fusion_engine()

    try:
        await redis_client.connect()
    except Exception as e:
        logger.warning(f"Redis connection failed: {e} (continuing without Redis)")

    # 从环境变量加载飞书 Webhook
    feishu_url = os.environ.get("FEISHU_WEBHOOK_URL")
    if feishu_url:
        set_feishu_webhook(feishu_url)
        logger.info("Feishu webhook loaded from environment variable")

    yield

    logger.info("Shutting down AI Coordinator Service...")
    if redis_client:
        await redis_client.disconnect()


app = FastAPI(
    title="AI Coordinator Service",
    description="水利工地安全监管系统 - 多智能体调度模块（含飞书告警推送）",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== 辅助函数 ==============

async def _notify_feishu(alert_data: Dict[str, Any], source: str):
    """发送飞书告警通知"""
    notifier = get_notifier()
    if not notifier.enabled:
        logger.debug("Feishu notifier disabled, skipping notification")
        return

    payload = notifier.format_alert_from_event(
        level=alert_data.get("level", "P2"),
        source=source,
        message=alert_data.get("message", alert_data.get("raw_text", "")),
        title=alert_data.get("title", f"{source.upper()} 告警"),
        location=alert_data.get("location"),
        sensor_type=alert_data.get("sensor_type"),
        sensor_value=alert_data.get("sensor_value"),
        detection_type=alert_data.get("detection_type"),
        confidence=alert_data.get("confidence"),
        raw_text=alert_data.get("raw_text"),
    )

    await notifier.send_alert(payload)


# ============== API 路由 ==============

@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "ai-coordinator",
        "port": 8084,
        "version": "1.1.0",
    }


@app.get("/health")
async def health_check():
    state_machine = get_state_machine()
    notifier = get_notifier()
    return {
        "status": "healthy",
        "current_state": state_machine.get_state().value,
        "state_level": state_machine.get_state_level(),
        "redis": "connected" if redis_client and redis_client._client else "disconnected",
        "feishu": "enabled" if notifier.enabled else "disabled",
    }


@app.get("/state")
async def get_state():
    state_machine = get_state_machine()
    return {
        "state": state_machine.get_state().value,
        "level": state_machine.get_state_level(),
        "history_count": len(state_machine.history),
        "last_transition": state_machine.history[-1].__dict__ if state_machine.history else None,
    }


@app.post("/state/reset")
async def reset_state():
    state_machine = get_state_machine()
    state_machine.force_state(SystemState.NORMAL, "Manual reset")
    return {"code": 0, "message": "State reset to NORMAL"}


# ============== 事件处理 ==============

@app.post("/event/sensor", response_model=EventResponse)
async def handle_sensor_event(request: SensorEventRequest):
    try:
        data = request.model_dump()
        event = EventConverter.from_sensor(data)

        state_machine = get_state_machine()
        new_state = state_machine.process_event(event)

        location = request.location or "default"
        fusion_engine.add_sensor_alert(
            location, request.sensor_type, request.value, request.confidence,
        )
        fused_alert = fusion_engine.fuse(location)

        # 构建告警数据
        alert_data = {
            "level": event.level,
            "message": f"[{request.sensor_type}] 传感器告警：{request.value}（置信度 {request.confidence:.0%}）",
            "title": f"传感器 {request.sensor_type} 告警",
            "source": "sensor",
            "location": location,
            "sensor_type": request.sensor_type,
            "sensor_value": request.value,
            "confidence": request.confidence,
        }

        # 异步发送飞书通知（P0/P1 必发，P2 仅融合后发送）
        if event.level in ["P0", "P1"] or (fused_alert and fused_alert.level.value in ["P0", "P1"]):
            asyncio.create_task(_notify_feishu(alert_data, "sensor"))

        if redis_client and redis_client._client:
            await redis_client.xadd(
                STREAMS["SENSOR_ALERTS"],
                {
                    "event_type": event.type.value,
                    "level": event.level,
                    "sensor_type": request.sensor_type,
                    "value": str(request.value),
                    "state": new_state.value,
                }
            )

        return EventResponse(
            code=0,
            message="Sensor event processed",
            data={
                "event_type": event.type.value,
                "level": event.level,
                "current_state": new_state.value,
                "fused_alert": fused_alert.model_dump() if fused_alert else None,
                "feishu_notified": event.level in ["P0", "P1"],
            }
        )

    except Exception as e:
        logger.error(f"Sensor event error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/event/vision", response_model=EventResponse)
async def handle_vision_event(request: VisionEventRequest):
    try:
        data = request.model_dump()
        event = EventConverter.from_vision(data)

        state_machine = get_state_machine()
        new_state = state_machine.process_event(event)

        location = request.location or "default"
        fusion_engine.add_vision_alert(
            location, request.detection_type, request.confidence, request.camera_id,
        )
        fused_alert = fusion_engine.fuse(location)

        alert_data = {
            "level": event.level,
            "message": f"AI检测到 [{request.detection_type}]，置信度 {request.confidence:.0%}",
            "title": f"视觉检测 {request.detection_type} 告警",
            "source": "vision",
            "location": location,
            "detection_type": request.detection_type,
            "confidence": request.confidence,
        }

        if event.level in ["P0", "P1"] or (fused_alert and fused_alert.level.value in ["P0", "P1"]):
            asyncio.create_task(_notify_feishu(alert_data, "vision"))

        if redis_client and redis_client._client:
            await redis_client.xadd(
                STREAMS["VISION_ALERTS"],
                {
                    "event_type": event.type.value,
                    "level": event.level,
                    "detection_type": request.detection_type,
                    "confidence": str(request.confidence),
                    "state": new_state.value,
                }
            )

        return EventResponse(
            code=0,
            message="Vision event processed",
            data={
                "event_type": event.type.value,
                "level": event.level,
                "current_state": new_state.value,
                "fused_alert": fused_alert.model_dump() if fused_alert else None,
                "feishu_notified": event.level in ["P0", "P1"],
            }
        )

    except Exception as e:
        logger.error(f"Vision event error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/event/voice", response_model=EventResponse)
async def handle_voice_event(request: VoiceEventRequest):
    try:
        data = request.model_dump()
        event = EventConverter.from_voice(data)

        state_machine = get_state_machine()
        new_state = state_machine.process_event(event)

        location = request.location or "default"
        fusion_engine.add_voice_alert(
            location, request.intent_type, request.confidence, request.raw_text,
        )
        fused_alert = fusion_engine.fuse(location)

        alert_data = {
            "level": event.level,
            "message": f"语音告警：{request.raw_text}",
            "title": f"语音识别 {request.intent_type} 告警",
            "source": "voice",
            "location": location,
            "confidence": request.confidence,
            "raw_text": request.raw_text,
        }

        if event.level in ["P0", "P1"] or (fused_alert and fused_alert.level.value in ["P0", "P1"]):
            asyncio.create_task(_notify_feishu(alert_data, "voice"))

        if redis_client and redis_client._client:
            await redis_client.xadd(
                STREAMS["VOICE_ALERTS"],
                {
                    "event_type": event.type.value,
                    "level": event.level,
                    "intent_type": request.intent_type,
                    "raw_text": request.raw_text,
                    "state": new_state.value,
                }
            )

        return EventResponse(
            code=0,
            message="Voice event processed",
            data={
                "event_type": event.type.value,
                "level": event.level,
                "current_state": new_state.value,
                "fused_alert": fused_alert.model_dump() if fused_alert else None,
                "feishu_notified": event.level in ["P0", "P1"],
            }
        )

    except Exception as e:
        logger.error(f"Voice event error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/event/manual", response_model=EventResponse)
async def handle_manual_alert(request: ManualAlertRequest):
    try:
        event = EventConverter.from_manual(
            {"message": request.message},
            request.level,
        )

        state_machine = get_state_machine()
        new_state = state_machine.process_event(event)

        # 手动告警默认发送飞书通知
        alert_data = {
            "level": request.level,
            "message": request.message,
            "title": "手动告警",
            "source": "manual",
            "location": request.location,
        }
        asyncio.create_task(_notify_feishu(alert_data, "manual"))

        if redis_client and redis_client._client:
            await redis_client.xadd(
                STREAMS["COORDINATOR"],
                {
                    "event_type": event.type.value,
                    "level": request.level,
                    "message": request.message,
                    "state": new_state.value,
                }
            )

        return EventResponse(
            code=0,
            message="Manual alert processed",
            data={
                "event_type": event.type.value,
                "level": request.level,
                "current_state": new_state.value,
                "feishu_notified": True,
            }
        )

    except Exception as e:
        logger.error(f"Manual alert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== 飞书 Webhook 管理 ==============

@app.post("/feishu/config")
async def config_feishu(request: FeishuWebhookRequest):
    """配置飞书 Webhook URL（运行时生效）"""
    set_feishu_webhook(request.webhook_url)
    # 测试发送
    notifier = get_notifier()
    test_payload = notifier.format_alert_from_event(
        level="P2",
        source="system",
        message="飞书 Webhook 配置成功，系统已就绪",
        title="Webhook 配置测试",
    )
    success = await notifier.send_alert(test_payload)

    return {
        "code": 0,
        "message": "Feishu webhook configured",
        "test_sent": success,
    }


@app.post("/feishu/test")
async def test_feishu(request: FeishuTestRequest = None):
    """测试飞书通知"""
    notifier = get_notifier()
    if request and request.webhook_url:
        notifier.set_webhook(request.webhook_url)

    if not notifier.enabled:
        return {"code": 1, "message": "Feishu webhook not configured"}

    # 发送各级别测试消息
    results = {}
    for level in ["P0", "P1", "P2"]:
        payload = notifier.format_alert_from_event(
            level=level,
            source="test",
            message=f"这是一条{level}级测试告警，用于验证飞书机器人连通性",
            title="飞书通知测试",
            location="测试区域A",
        )
        results[level] = await notifier.send_alert(payload)

    return {
        "code": 0,
        "message": "Feishu test completed",
        "results": results,
    }


@app.get("/feishu/status")
async def feishu_status():
    """查看飞书通知状态"""
    notifier = get_notifier()
    return {
        "enabled": notifier.enabled,
        "webhook_configured": bool(notifier.webhook_url),
        # 脱敏显示 URL
        "webhook_hint": f"***" + notifier.webhook_url[-20:] if notifier.webhook_url else None,
    }


# ============== 融合查询 ==============

@app.get("/fusion/alerts")
async def get_fused_alerts():
    alerts = fusion_engine.get_fused_alerts()
    return {
        "code": 0,
        "data": {
            "alerts": {loc: alert.model_dump() for loc, alert in alerts.items()},
            "count": len(alerts),
        }
    }


@app.get("/fusion/cross-location")
async def get_cross_location_fused():
    fused = fusion_engine.get_multi_location_fused()
    return {
        "code": 0,
        "data": fused.model_dump() if fused else None,
    }


# ============== 启动服务 ==============

def main():
    logger.info("Starting AI Coordinator Service on port 8084...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8084,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
