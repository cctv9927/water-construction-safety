"""视频流处理模块 - FastAPI 服务"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import VideoStreamerConfig, StreamSource, RTSPConfig, DiagnosticsConfig
from rtsp_client import RTSPManager, StreamStatus
from frame_capture import FrameCapture, CaptureConfig, FrameData, CaptureTrigger
from diagnostics import VideoDiagnostics, DiagnosticConfig, DiagnosticResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# FastAPI 应用
app = FastAPI(title="视频流处理服务", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局状态
rtsp_manager: Optional[RTSPManager] = None
frame_capture: Optional[FrameCapture] = None
diagnostics: Optional[VideoDiagnostics] = None
config: Optional[VideoStreamerConfig] = None

# WebSocket 连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, stream_id: str):
        await websocket.accept()
        if stream_id not in self.active_connections:
            self.active_connections[stream_id] = []
        self.active_connections[stream_id].append(websocket)

    def disconnect(self, websocket: WebSocket, stream_id: str):
        if stream_id in self.active_connections:
            if websocket in self.active_connections[stream_id]:
                self.active_connections[stream_id].remove(websocket)
            if not self.active_connections[stream_id]:
                del self.active_connections[stream_id]

    async def broadcast(self, stream_id: str, message: dict):
        if stream_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[stream_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            for conn in disconnected:
                self.disconnect(conn, stream_id)


ws_manager = ConnectionManager()

# 帧存储（临时）
_latest_frames: dict[str, bytes] = {}
_frame_lock = asyncio.Lock()


async def on_diagnostic_alert(result: DiagnosticResult):
    """诊断告警回调"""
    alert_msg = {
        "type": "diagnostic_alert",
        "data": {
            "stream_id": result.stream_id,
            "diagnostic_type": result.diagnostic_type.value,
            "severity": result.severity,
            "message": result.message,
            "timestamp": result.timestamp,
            "value": result.value,
        }
    }
    await ws_manager.broadcast(result.stream_id, alert_msg)
    logger.warning(f"[Alert] {result.stream_id}: {result.message}")


async def on_frame_received(stream_id: str, raw_frame: bytes):
    """帧接收回调"""
    global diagnostics

    # 存储最新帧
    async with _frame_lock:
        _latest_frames[stream_id] = raw_frame

    # 触发诊断分析
    if diagnostics:
        try:
            await diagnostics.analyze_frame(stream_id, raw_frame)
        except Exception as e:
            logger.error(f"诊断分析失败: {e}")

    # 广播帧信息到 WebSocket
    await ws_manager.broadcast(stream_id, {
        "type": "frame_update",
        "stream_id": stream_id,
        "timestamp": datetime.now().isoformat(),
    })


# ============ API 模型 ============

class CaptureRequest(BaseModel):
    stream_id: str
    trigger: str = "manual"
    event_type: Optional[str] = None
    format: str = "jpeg"


class StreamStatusResponse(BaseModel):
    stream_id: str
    status: str
    fps: float = 0.0
    width: int = 0
    height: int = 0
    error_count: int = 0


class DiagnosticStatusResponse(BaseModel):
    stream_id: str
    width: int
    height: int
    last_brightness: Optional[float]
    consecutive_black: int
    consecutive_occlusion: int
    freeze_count: int
    is_alerting: bool


# ============ API 路由 ============

@app.get("/")
async def root():
    return {"service": "video-streamer", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/streams")
async def add_stream(source: StreamSource):
    """添加视频流"""
    global rtsp_manager

    if rtsp_manager is None:
        raise HTTPException(status_code=500, detail="服务未初始化")

    from rtsp_client import RTSPClient
    client = RTSPClient(
        stream_id=source.stream_id,
        rtsp_url=source.rtsp_url,
        timeout=config.rtsp.timeout if config else 30,
        retry_interval=config.rtsp.retry_interval if config else 5,
        max_retries=config.rtsp.max_retries if config else 3,
    )
    rtsp_manager.add_stream(client)
    return {"stream_id": source.stream_id, "status": "added"}


@app.delete("/streams/{stream_id}")
async def remove_stream(stream_id: str):
    """移除视频流"""
    global rtsp_manager

    if rtsp_manager is None:
        raise HTTPException(status_code=500, detail="服务未初始化")

    rtsp_manager.stop_stream(stream_id)
    return {"stream_id": stream_id, "status": "removed"}


@app.post("/streams/{stream_id}/start")
async def start_stream(stream_id: str):
    """启动视频流"""
    global rtsp_manager

    if rtsp_manager is None:
        raise HTTPException(status_code=500, detail="服务未初始化")

    success = await rtsp_manager.start_stream(stream_id, on_frame_received)
    if not success:
        raise HTTPException(status_code=500, detail=f"启动流 {stream_id} 失败")
    return {"stream_id": stream_id, "status": "started"}


@app.post("/streams/{stream_id}/stop")
async def stop_stream(stream_id: str):
    """停止视频流"""
    global rtsp_manager

    if rtsp_manager is None:
        raise HTTPException(status_code=500, detail="服务未初始化")

    rtsp_manager.stop_stream(stream_id)
    return {"stream_id": stream_id, "status": "stopped"}


@app.get("/streams/{stream_id}/status", response_model=StreamStatusResponse)
async def get_stream_status(stream_id: str):
    """获取流状态"""
    global rtsp_manager

    if rtsp_manager is None:
        raise HTTPException(status_code=500, detail="服务未初始化")

    info = rtsp_manager.get_stream_info(stream_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"流 {stream_id} 不存在")

    return StreamStatusResponse(
        stream_id=info.stream_id,
        status=info.status.value,
        fps=info.fps,
        width=info.width,
        height=info.height,
        error_count=info.error_count,
    )


@app.get("/streams")
async def list_streams():
    """列出所有流"""
    global rtsp_manager

    if rtsp_manager is None:
        raise HTTPException(status_code=500, detail="服务未初始化")

    streams = rtsp_manager.list_streams()
    return {
        "streams": [
            {
                "stream_id": s.stream_id,
                "url": s.url,
                "status": s.status.value,
                "fps": s.fps,
                "width": s.width,
                "height": s.height,
            }
            for s in streams
        ]
    }


@app.post("/capture")
async def capture_frame(request: CaptureRequest):
    """手动截帧"""
    global frame_capture

    if frame_capture is None:
        raise HTTPException(status_code=500, detail="截帧服务未初始化")

    async with _frame_lock:
        raw_data = _latest_frames.get(request.stream_id)

    if not raw_data:
        raise HTTPException(status_code=404, detail=f"流 {request.stream_id} 无可用帧")

    frame = FrameData(
        stream_id=request.stream_id,
        raw_data=raw_data,
        width=1920,
        height=1080,
    )

    trigger = CaptureTrigger(request.trigger)
    record = await frame_capture.capture_frame(
        frame,
        trigger=trigger,
        format=request.format,
        event_type=request.event_type,
    )

    return {
        "capture_id": record.capture_id,
        "file_path": record.file_path,
        "success": record.success,
        "error": record.error_message,
    }


@app.post("/capture/scheduled")
async def start_scheduled_capture(
    stream_id: str = Query(...),
    interval: float = Query(60.0, description="截帧间隔(秒)")
):
    """启动定时截帧"""
    global frame_capture

    if frame_capture is None:
        raise HTTPException(status_code=500, detail="截帧服务未初始化")

    async def frame_callback():
        async with _frame_lock:
            raw_data = _latest_frames.get(stream_id)
        if raw_data:
            return FrameData(stream_id=stream_id, raw_data=raw_data, width=1920, height=1080)
        raise ValueError(f"No frame for {stream_id}")

    task_id = frame_capture.start_scheduled(stream_id, interval, frame_callback)
    return {"task_id": task_id, "stream_id": stream_id, "interval": interval}


@app.delete("/capture/scheduled/{stream_id}")
async def stop_scheduled_capture(stream_id: str):
    """停止定时截帧"""
    global frame_capture

    if frame_capture is None:
        raise HTTPException(status_code=500, detail="截帧服务未初始化")

    frame_capture.stop_scheduled(stream_id)
    return {"stream_id": stream_id, "status": "stopped"}


@app.get("/capture/stats")
async def get_capture_stats():
    """获取截帧统计"""
    global frame_capture

    if frame_capture is None:
        raise HTTPException(status_code=500, detail="截帧服务未初始化")

    return frame_capture.get_capture_stats()


@app.get("/diagnostics/{stream_id}/status", response_model=DiagnosticStatusResponse)
async def get_diagnostic_status(stream_id: str):
    """获取诊断状态"""
    global diagnostics

    if diagnostics is None:
        raise HTTPException(status_code=500, detail="诊断服务未初始化")

    status = diagnostics.get_stream_status(stream_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"流 {stream_id} 不存在")

    return DiagnosticStatusResponse(**status)


@app.get("/diagnostics/status")
async def list_diagnostic_status():
    """列出所有诊断状态"""
    global diagnostics

    if diagnostics is None:
        raise HTTPException(status_code=500, detail="诊断服务未初始化")

    return {"streams": diagnostics.list_stream_status()}


# ============ WebSocket 路由 ============

@app.websocket("/ws/{stream_id}")
async def websocket_endpoint(websocket: WebSocket, stream_id: str):
    """WebSocket 实时视频流"""
    await ws_manager.connect(websocket, stream_id)
    logger.info(f"[WS] Client connected: {stream_id}")

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                # 处理客户端命令
                if msg.get("type") == "capture":
                    # 触发截帧
                    await capture_frame(CaptureRequest(
                        stream_id=stream_id,
                        trigger="manual"
                    ))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, stream_id)
        logger.info(f"[WS] Client disconnected: {stream_id}")


# ============ 初始化与启动 ============

def init_services(cfg: VideoStreamerConfig):
    """初始化服务"""
    global rtsp_manager, frame_capture, diagnostics, config

    config = cfg

    # RTSP 管理器
    rtsp_manager = RTSPManager()

    # 截帧服务
    frame_capture_config = CaptureConfig(
        output_dir=cfg.frame_capture.output_dir,
        jpeg_quality=cfg.frame_capture.jpeg_quality,
        png_compress=cfg.frame_capture.png_compress,
        max_storage_days=cfg.frame_capture.max_storage_days,
    )
    frame_capture = FrameCapture(frame_capture_config)

    # 诊断服务
    diag_config = DiagnosticConfig(
        brightness_threshold=cfg.diagnostics.brightness_threshold,
        occlusion_ratio=cfg.diagnostics.occlusion_ratio,
        check_interval=cfg.diagnostics.check_interval,
    )
    diagnostics = VideoDiagnostics(diag_config, alert_callback=on_diagnostic_alert)

    # 添加配置的流
    for source in cfg.streams:
        from rtsp_client import RTSPClient
        client = RTSPClient(
            stream_id=source.stream_id,
            rtsp_url=source.rtsp_url,
            timeout=cfg.rtsp.timeout,
            retry_interval=cfg.rtsp.retry_interval,
            max_retries=cfg.rtsp.max_retries,
        )
        rtsp_manager.add_stream(client)

    logger.info(f"[Init] 初始化完成: {len(cfg.streams)} 个流")


def load_config(config_path: str = "config.yaml") -> VideoStreamerConfig:
    """加载配置"""
    import yaml
    path = Path(config_path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return VideoStreamerConfig(**raw)
    else:
        # 默认配置
        return VideoStreamerConfig()


async def startup():
    """启动服务"""
    global rtsp_manager

    # 加载配置
    cfg = load_config()
    init_services(cfg)

    # 启动所有流
    if rtsp_manager and cfg.streams:
        await rtsp_manager.start_all(on_frame_received)
        logger.info(f"[Startup] 已启动 {len(cfg.streams)} 个视频流")

    logger.info("=" * 50)
    logger.info("视频流处理服务启动完成")
    logger.info(f"端口: {cfg.websocket.port}")
    logger.info("=" * 50)


async def shutdown():
    """关闭服务"""
    global rtsp_manager, frame_capture, diagnostics

    logger.info("正在关闭视频流处理服务...")

    if rtsp_manager:
        rtsp_manager.stop_all()

    if frame_capture:
        frame_capture.stop_all_scheduled()
        frame_capture.cleanup_old_files()

    if diagnostics:
        diagnostics.stop_monitoring()

    logger.info("视频流处理服务已关闭")


@app.on_event("startup")
async def startup_event():
    await startup()


@app.on_event("shutdown")
async def shutdown_event():
    await shutdown()


if __name__ == "__main__":
    import yaml

    # 默认配置
    default_config = {
        "rtsp": {"timeout": 30, "retry_interval": 5, "max_retries": 3},
        "frame_capture": {"output_dir": "/tmp/frames", "jpeg_quality": 85, "max_storage_days": 7},
        "diagnostics": {"brightness_threshold": 20.0, "occlusion_ratio": 0.8},
        "websocket": {"host": "0.0.0.0", "port": 8081},
        "streams": [],
    }

    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    if not Path(config_path).exists():
        with open(config_path, "w") as f:
            yaml.dump(default_config, f)
        logger.info(f"已生成默认配置: {config_path}")

    cfg = load_config(config_path)
    uvicorn.run(
        app,
        host=cfg.websocket.host,
        port=cfg.websocket.port,
        log_level="info",
    )
