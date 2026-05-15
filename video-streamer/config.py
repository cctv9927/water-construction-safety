"""视频流处理模块配置"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class RTSPConfig(BaseModel):
    """RTSP 连接配置"""
    timeout: int = Field(default=30, description="连接超时(秒)")
    retry_interval: int = Field(default=5, description="重连间隔(秒)")
    max_retries: int = Field(default=3, description="最大重试次数")


class FrameCaptureConfig(BaseModel):
    """截帧配置"""
    output_dir: str = Field(default="/tmp/frames", description="帧图片输出目录")
    jpeg_quality: int = Field(default=85, description="JPEG质量(1-100)")
    png_compress: int = Field(default=6, description="PNG压缩级别(0-9)")
    max_storage_days: int = Field(default=7, description="存储天数")


class DiagnosticsConfig(BaseModel):
    """视频诊断配置"""
    brightness_threshold: float = Field(default=20.0, description="黑屏亮度阈值(0-255)")
    occlusion_ratio: float = Field(default=0.8, description="遮挡比例阈值")
    check_interval: float = Field(default=5.0, description="诊断间隔(秒)")


class WebSocketConfig(BaseModel):
    """WebSocket配置"""
    host: str = Field(default="0.0.0.0", description="监听地址")
    port: int = Field(default=8081, description="监听端口")
    heartbeat_interval: int = Field(default=30, description="心跳间隔(秒)")
    max_frame_size: int = Field(default=10 * 1024 * 1024, description="最大帧大小(10MB)")


class StreamSource(BaseModel):
    """流媒体源配置"""
    stream_id: str = Field(description="流ID")
    rtsp_url: str = Field(description="RTSP URL")
    name: str = Field(default="", description="流名称")
    location: str = Field(default="", description="安装位置")
    enabled: bool = Field(default=True, description="是否启用")


class VideoStreamerConfig(BaseModel):
    """视频流处理总配置"""
    rtsp: RTSPConfig = Field(default_factory=RTSPConfig)
    frame_capture: FrameCaptureConfig = Field(default_factory=FrameCaptureConfig)
    diagnostics: DiagnosticsConfig = Field(default_factory=DiagnosticsConfig)
    websocket: WebSocketConfig = Field(default_factory=WebSocketConfig)
    streams: list[StreamSource] = Field(default_factory=list)
    iot_hub_base_url: str = Field(default="http://localhost:8000", description="IoT Hub地址")
