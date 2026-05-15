"""
Pydantic 数据模型
"""
from typing import Optional, List, Union, Dict, Any
from pydantic import BaseModel, Field


class BBox(BaseModel):
    x1: int = Field(description="左上角 X 坐标")
    y1: int = Field(description="左上角 Y 坐标")
    x2: int = Field(description="右下角 X 坐标")
    y2: int = Field(description="右下角 Y 坐标")


class Detection(BaseModel):
    class_id: int = Field(description="类别 ID")
    class_name: str = Field(description="类别名称")
    confidence: float = Field(description="置信度 0-1")
    bbox: BBox = Field(description="检测框坐标")


class DetectRequest(BaseModel):
    image: Optional[str] = Field(
        None,
        description="图片 URL（与 image_base64 二选一）",
        examples=["https://example.com/camera1.jpg"],
    )
    image_base64: Optional[str] = Field(
        None,
        description="Base64 编码图片（需包含 data:image/...;base64, 前缀或纯 base64 字符串）",
    )
    confidence: float = Field(0.5, ge=0.0, le=1.0, description="置信度阈值")
    max_detections: int = Field(50, ge=1, le=300, description="最大检测数量")


class DetectData(BaseModel):
    width: int
    height: int
    detections: List[Detection]
    count: int
    inference_time_ms: float


class DetectResponse(BaseModel):
    code: int = Field(description="状态码，0=成功")
    message: str = Field(description="状态信息")
    data: Optional[DetectData] = Field(None, description="检测结果数据")


class ModelInfo(BaseModel):
    model_path: str
    num_classes: int
    input_size: int
    class_names: List[str]


# ============== RTSP 流相关模型 ==============

class RTSPCameraConfig(BaseModel):
    """RTSP 摄像头配置"""
    camera_id: str = Field(..., description="摄像头 ID/名称，唯一标识")
    rtsp_url: str = Field(..., description="RTSP 流地址")
    interval_seconds: float = Field(1.0, ge=0.1, le=60.0, description="检测间隔（秒）")
    confidence: float = Field(0.5, ge=0.0, le=1.0, description="置信度阈值")
    enabled: bool = Field(True, description="是否启用")


class RTSPDetectionResult(BaseModel):
    """RTSP 流检测结果"""
    camera_id: str
    timestamp: str
    inference_time_ms: float
    detections: List[Detection]
    count: int
    status: str
    error: Optional[str] = None


class StreamStatusInfo(BaseModel):
    """流状态信息"""
    camera_id: str
    status: str  # idle / connecting / running / error / stopped
    total_frames: int
    error_count: int


# ============== 批量 RTSP 请求/响应 ==============

class RTSPBatchAddRequest(BaseModel):
    """批量添加 RTSP 流"""
    cameras: List[RTSPCameraConfig]


class RTSPStreamEventRequest(BaseModel):
    """RTSP 检测事件回调配置"""
    # 回调地址：检测到目标时自动 POST 到此地址
    callback_url: Optional[str] = Field(None, description="回调 Webhook 地址")
    # 是否向 ai-coordinator 报告（代替 callback_url）
    report_to_coordinator: bool = Field(False, description="是否上报给 AI Coordinator")
    coordinator_url: str = Field("http://localhost:8084", description="Coordinator 地址")


class RTSPSourcesResponse(BaseModel):
    """RTSP 流信息"""
    streams: List[StreamStatusInfo]
    total: int
