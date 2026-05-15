"""
FastAPI 主服务 - 多智能体调度模块
端口：8084
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============== 数据模型 ==============

class SensorEventRequest(BaseModel):
    """传感器事件请求"""
    sensor_id: str
    sensor_type: str
    value: float
    location: Optional[str] = None
    timestamp: Optional[str] = None
    confidence: float = 1.0


class VisionEventRequest(BaseModel):
    """视觉事件请求"""
    camera_id: str
    detection_type: str
    confidence: float
    location: Optional[str] = None
    bbox: Optional[Dict[str, int]] = None
    timestamp: Optional[str] = None


class VoiceEventRequest(BaseModel):
    """语音事件请求"""
    intent_type: str
    raw_text: str
    confidence: float
    location: Optional[str] = None
    timestamp: Optional[str] = None


class ManualAlertRequest(BaseModel):
    """手动告警请求"""
    message: str
    level: str = "P1"
    location: Optional[str] = None


class EventResponse(BaseModel):
    """事件响应"""
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


# ============== 生命周期管理 ==============

redis_client: Optional[RedisStreamClient] = None
fusion_engine: Optional[FusionEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    global redis_client, fusion_engine
    
    # 启动
    logger.info("Starting AI Coordinator Service...")
    redis_client = get_redis_client()
    fusion_engine = get_fusion_engine()
    
    try:
        await redis_client.connect()
    except Exception as e:
        logger.warning(f"Redis connection failed: {e} (continuing without Redis)")
    
    yield
    
    # 关闭
    logger.info("Shutting down AI Coordinator Service...")
    if redis_client:
        await redis_client.disconnect()


# 创建 FastAPI 应用
app = FastAPI(
    title="AI Coordinator Service",
    description="水利工地安全监管系统 - 多智能体调度模块",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== API 路由 ==============

@app.get("/")
async def root():
    """服务健康检查"""
    return {
        "status": "ok",
        "service": "ai-coordinator",
        "port": 8084,
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    state_machine = get_state_machine()
    return {
        "status": "healthy",
        "current_state": state_machine.get_state().value,
        "state_level": state_machine.get_state_level(),
        "redis": "connected" if redis_client and redis_client._client else "disconnected",
    }


@app.get("/state")
async def get_state():
    """获取当前系统状态"""
    state_machine = get_state_machine()
    return {
        "state": state_machine.get_state().value,
        "level": state_machine.get_state_level(),
        "history_count": len(state_machine.history),
        "last_transition": state_machine.history[-1].__dict__ if state_machine.history else None,
    }


@app.post("/state/reset")
async def reset_state():
    """重置系统状态"""
    state_machine = get_state_machine()
    state_machine.force_state(SystemState.NORMAL, "Manual reset")
    return {"code": 0, "message": "State reset to NORMAL"}


# ============== 事件处理 ==============

@app.post("/event/sensor", response_model=EventResponse)
async def handle_sensor_event(request: SensorEventRequest):
    """处理传感器事件"""
    try:
        # 转换事件
        data = request.model_dump()
        event = EventConverter.from_sensor(data)
        
        # 状态机处理
        state_machine = get_state_machine()
        new_state = state_machine.process_event(event)
        
        # 融合引擎处理
        location = request.location or "default"
        fusion_engine.add_sensor_alert(
            location,
            request.sensor_type,
            request.value,
            request.confidence,
        )
        
        # 获取融合结果
        fused_alert = fusion_engine.fuse(location)
        
        # 发布到 Redis
        if redis_client and redis_client._client:
            await redis_client.xadd(
                STREAMS["SENSOR_ALERTS"],
                {
                    "event_type": event.type.value,
                    "level": event.level,
                    "sensor_type": request.sensor_type,
                    "value": request.value,
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
            }
        )
        
    except Exception as e:
        logger.error(f"Sensor event error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/event/vision", response_model=EventResponse)
async def handle_vision_event(request: VisionEventRequest):
    """处理视觉事件"""
    try:
        # 转换事件
        data = request.model_dump()
        event = EventConverter.from_vision(data)
        
        # 状态机处理
        state_machine = get_state_machine()
        new_state = state_machine.process_event(event)
        
        # 融合引擎处理
        location = request.location or "default"
        fusion_engine.add_vision_alert(
            location,
            request.detection_type,
            request.confidence,
            request.camera_id,
        )
        
        # 获取融合结果
        fused_alert = fusion_engine.fuse(location)
        
        # 发布到 Redis
        if redis_client and redis_client._client:
            await redis_client.xadd(
                STREAMS["VISION_ALERTS"],
                {
                    "event_type": event.type.value,
                    "level": event.level,
                    "detection_type": request.detection_type,
                    "confidence": request.confidence,
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
            }
        )
        
    except Exception as e:
        logger.error(f"Vision event error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/event/voice", response_model=EventResponse)
async def handle_voice_event(request: VoiceEventRequest):
    """处理语音事件"""
    try:
        # 转换事件
        data = request.model_dump()
        event = EventConverter.from_voice(data)
        
        # 状态机处理
        state_machine = get_state_machine()
        new_state = state_machine.process_event(event)
        
        # 融合引擎处理
        location = request.location or "default"
        fusion_engine.add_voice_alert(
            location,
            request.intent_type,
            request.confidence,
            request.raw_text,
        )
        
        # 获取融合结果
        fused_alert = fusion_engine.fuse(location)
        
        # 发布到 Redis
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
            }
        )
        
    except Exception as e:
        logger.error(f"Voice event error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/event/manual", response_model=EventResponse)
async def handle_manual_alert(request: ManualAlertRequest):
    """处理手动告警"""
    try:
        # 创建事件
        event = EventConverter.from_manual(
            {"message": request.message},
            request.level,
        )
        
        # 状态机处理
        state_machine = get_state_machine()
        new_state = state_machine.process_event(event)
        
        # 发布到 Redis
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
            }
        )
        
    except Exception as e:
        logger.error(f"Manual alert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== 融合查询 ==============

@app.get("/fusion/alerts")
async def get_fused_alerts():
    """获取所有融合告警"""
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
    """获取跨位置融合告警"""
    fused = fusion_engine.get_multi_location_fused()
    return {
        "code": 0,
        "data": fused.model_dump() if fused else None,
    }


# ============== 启动服务 ==============

def main():
    """启动服务"""
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
