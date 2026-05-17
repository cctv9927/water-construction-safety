from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


# ============ 通用 ============
class BaseResponse(BaseModel):
    success: bool = True
    message: str = "操作成功"


# ============ 用户/认证 ============
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    role: str = "viewer"


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# ============ 告警 ============
class AlertLevelEnum(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class AlertStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    VERIFIED = "verified"
    CLOSED = "closed"


class AlertBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    level: AlertLevelEnum = AlertLevelEnum.P2
    location: Optional[str] = Field(default=None, max_length=200)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90, description="纬度: -90~90")
    longitude: Optional[float] = Field(default=None, ge=-180, le=180, description="经度: -180~180")
    sensor_id: Optional[int] = Field(default=None, gt=0)
    evidence_images: List[str] = Field(default_factory=list, max_length=20)
    metadata: dict = Field(default_factory=dict)


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    status: Optional[AlertStatusEnum] = None
    level: Optional[AlertLevelEnum] = None
    title: Optional[str] = None
    description: Optional[str] = None
    evidence_images: Optional[List[str]] = None
    metadata: Optional[dict] = None


class AlertAssignmentCreate(BaseModel):
    user_id: int


class AlertResponse(AlertBase):
    id: int
    status: AlertStatusEnum
    creator_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    resolved_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AlertResponse]


class AlertFilter(BaseModel):
    level: Optional[AlertLevelEnum] = None
    status: Optional[AlertStatusEnum] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    sensor_id: Optional[int] = None
    search: Optional[str] = None


# ============ 传感器 ============
class SensorTypeEnum(str, Enum):
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    VIBRATION = "vibration"
    DISPLACEMENT = "displacement"
    FLOW = "flow"
    WIND_SPEED = "wind_speed"
    RAINFALL = "rainfall"
    HUMIDITY = "humidity"
    WATER_LEVEL = "water_level"


class SensorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: SensorTypeEnum
    location: Optional[str] = Field(default=None, max_length=200)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    device_id: Optional[str] = Field(default=None, max_length=100, pattern="^[A-Za-z0-9_-]+$")
    unit: Optional[str] = Field(default=None, max_length=20)
    min_value: Optional[float] = Field(default=None, ge=-1e9, le=1e9)
    max_value: Optional[float] = Field(default=None, ge=-1e9, le=1e9)

    @field_validator("max_value")
    @classmethod
    def validate_range(cls, v, info):
        """确保 max_value >= min_value"""
        min_val = info.data.get("min_value")
        if v is not None and min_val is not None and v < min_val:
            raise ValueError("max_value must be greater than or equal to min_value")
        return v


class SensorCreate(SensorBase):
    pass


class SensorResponse(SensorBase):
    id: int
    is_active: bool
    last_seen: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class SensorDataPoint(BaseModel):
    timestamp: datetime
    value: float = Field(..., ge=-1e9, le=1e9)
    quality: str = Field(default="good", pattern="^(good|bad|uncertain)$")


class SensorDataResponse(BaseModel):
    sensor_id: int
    sensor_name: str
    sensor_type: str
    unit: Optional[str]
    data: List[SensorDataPoint]
    stats: Optional[dict] = None  # 统计信息


# ============ AI 视觉 ============
class DetectionBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    category: str


class DetectionRequest(BaseModel):
    image_url: Optional[str] = None
    image_data: Optional[str] = None  # Base64 encoded


class DetectionResponse(BaseModel):
    detections: List[DetectionBox]
    image_url: str
    processing_time_ms: float
    model_version: str = "yolov8n-1.0"


# ============ 电子沙盘 ============
class SandboxModelResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    model_type: str
    file_path: str
    bounds: Optional[dict]
    center_point: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class VideoClipResponse(BaseModel):
    id: int
    title: Optional[str]
    camera_id: str
    location: Optional[str]
    file_path: str
    thumbnail_path: Optional[str]
    duration: Optional[float]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    detection_results: List[dict] = []

    class Config:
        from_attributes = True


# ============ 专家系统 ============
class ExpertQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    context: Optional[dict] = None


class ExpertQueryResponse(BaseModel):
    answer: str
    sources: List[dict] = []
    confidence: float


class FormGenerateRequest(BaseModel):
    form_type: str = Field(..., description="表格类型: inspection/check/rectification/acceptance")
    project_name: str
    date: Optional[str] = None
    location: Optional[str] = None
    inspector: Optional[str] = None
    data: Optional[dict] = None


class FormGenerateResponse(BaseModel):
    form_id: str
    form_type: str
    title: str
    content: dict
    generated_at: datetime
