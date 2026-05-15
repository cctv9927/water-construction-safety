"""传感器数据采集模块的 Pydantic 数据模型"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class SensorType(str, Enum):
    """传感器类型枚举"""
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    VIBRATION = "vibration"
    DISPLACEMENT = "displacement"
    FLOW = "flow"
    WIND_SPEED = "wind_speed"
    RAINFALL = "rainfall"
    UNKNOWN = "unknown"


class Location(BaseModel):
    """传感器位置信息"""
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    altitude: Optional[float] = None


class RawSensorData(BaseModel):
    """MQTT 接收到的原始传感器数据"""
    sensor_id: str
    sensor_type: str
    site_id: str
    value: float
    unit: str = ""
    timestamp: Optional[str] = None
    location: Optional[Location] = None

    @field_validator("sensor_type", mode="before")
    @classmethod
    def normalize_sensor_type(cls, v: str) -> str:
        return v.strip().lower()


class FormattedSensorData(BaseModel):
    """格式化后的传感器数据（上报格式）"""
    site_id: str
    sensor_id: str
    sensor_type: str
    value: float
    unit: str
    timestamp: str
    location: Optional[dict] = None
    quality: str = "good"          # good | bad | uncertain
    raw_value: float
    collected_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")


class ConfigModel(BaseModel):
    """配置文件模型"""
    class MQTTConfig(BaseModel):
        broker: str
        client_id: str
        topics: list[str]
        qos: int = 1
        keepalive: int = 60
        reconnect_delay: int = 5

    class IoTHubConfig(BaseModel):
        base_url: str
        timeout: int = 10
        retry: int = 3

    class CollectorConfig(BaseModel):
        report_interval: int = 5
        batch_size: int = 100
        log_level: str = "INFO"

    mqtt: MQTTConfig
    iot_hub: IoTHubConfig
    collector: CollectorConfig
