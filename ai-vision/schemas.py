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
        description="Base64 编码图片（与 image 二选一，需包含 data:image/...;base64, 前缀或纯 base64 字符串）",
    )
    confidence: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="置信度阈值（默认 0.5）",
    )
    max_detections: int = Field(
        50,
        ge=1,
        le=300,
        description="最大检测数量（默认 50）",
    )


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
