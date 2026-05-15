"""传感器数据校验与清洗模块"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from .models import RawSensorData, SensorType

logger = logging.getLogger(__name__)


class SensorValidator:
    """传感器数据校验器"""

    # 各类型传感器的合理范围阈值（min, max）
    VALID_RANGES: dict[str, tuple[float, float]] = {
        SensorType.TEMPERATURE.value: (-50.0, 80.0),      # ℃
        SensorType.PRESSURE.value: (0.0, 2000.0),        # kPa
        SensorType.VIBRATION.value: (0.0, 500.0),        # mm/s
        SensorType.DISPLACEMENT.value: (-1000.0, 1000.0),  # mm
        SensorType.FLOW.value: (0.0, 10000.0),           # m³/h
        SensorType.WIND_SPEED.value: (0.0, 100.0),       # m/s
        SensorType.RAINFALL.value: (0.0, 500.0),         # mm/h
    }

    def __init__(self, strict: bool = False):
        self.strict = strict

    def validate(self, data: RawSensorData) -> tuple[bool, Optional[str]]:
        """
        校验单条传感器数据。
        Returns: (is_valid, error_message)
        """
        # 必填字段检查
        if not data.sensor_id or not data.sensor_id.strip():
            return False, "sensor_id is empty"
        if not data.site_id or not data.site_id.strip():
            return False, "site_id is empty"

        # 值域范围检查
        sensor_type = data.sensor_type.lower()
        if sensor_type in self.VALID_RANGES:
            low, high = self.VALID_RANGES[sensor_type]
            if not (low <= data.value <= high):
                msg = f"value {data.value} out of range [{low}, {high}] for {sensor_type}"
                if self.strict:
                    return False, msg
                logger.warning(f"[Validator] %s", msg)
                return False, msg

        # 位置信息检查
        if data.location:
            if not (-90 <= data.location.lat <= 90):
                return False, f"invalid latitude: {data.location.lat}"
            if not (-180 <= data.location.lng <= 180):
                return False, f"invalid longitude: {data.location.lng}"

        return True, None

    def assess_quality(self, data: RawSensorData, validation_passed: bool) -> str:
        """
        评估数据质量等级。
        Returns: 'good' | 'uncertain' | 'bad'
        """
        if not validation_passed:
            return "bad"

        sensor_type = data.sensor_type.lower()
        if sensor_type not in self.VALID_RANGES:
            return "uncertain"

        low, high = self.VALID_RANGES[sensor_type]
        margin = (high - low) * 0.1  # 10% margin
        if (low + margin) <= data.value <= (high - margin):
            return "good"
        return "uncertain"


def normalize_timestamp(ts: Optional[str]) -> str:
    """将各种格式的时间戳标准化为 ISO 8601 格式"""
    if not ts:
        return datetime.utcnow().isoformat() + "Z"

    # 已经是 ISO 格式
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.isoformat().replace("+00:00", "Z")
    except ValueError:
        pass

    # 尝试解析为 Unix 时间戳（毫秒）
    try:
        import time
        ts_float = float(ts)
        if ts_float > 1e12:  # 毫秒级
            ts_float /= 1000
        dt = datetime.utcfromtimestamp(ts_float)
        return dt.isoformat() + "Z"
    except (ValueError, OSError):
        pass

    logger.warning(f"[Validator] Cannot parse timestamp '%s', using current time", ts)
    return datetime.utcnow().isoformat() + "Z"
