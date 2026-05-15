"""传感器数据格式化模块"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .models import RawSensorData, FormattedSensorData
from .validator import normalize_timestamp, SensorValidator


class SensorFormatter:
    """传感器数据格式化器"""

    def __init__(self):
        self.validator = SensorValidator()

    def format(self, raw: RawSensorData) -> FormattedSensorData:
        """
        将原始传感器数据格式化为统一的上报格式。
        """
        # 标准化时间戳
        timestamp = normalize_timestamp(raw.timestamp)

        # 评估数据质量
        is_valid, _ = self.validator.validate(raw)
        quality = self.validator.assess_quality(raw, is_valid)

        # 提取 location
        location_dict = None
        if raw.location:
            loc = raw.location
            location_dict = {
                "lat": round(loc.lat, 6),
                "lng": round(loc.lng, 6),
            }
            if loc.altitude is not None:
                location_dict["altitude"] = round(loc.altitude, 2)

        # 单位标准化
        unit = self._normalize_unit(raw.sensor_type, raw.unit)

        # 数值精度处理
        value = round(raw.value, self._get_precision(raw.sensor_type))

        return FormattedSensorData(
            site_id=raw.site_id.strip(),
            sensor_id=raw.sensor_id.strip(),
            sensor_type=raw.sensor_type.lower(),
            value=value,
            unit=unit,
            timestamp=timestamp,
            location=location_dict,
            quality=quality,
            raw_value=raw.value,
        )

    def format_batch(self, raw_list: list[RawSensorData]) -> list[FormattedSensorData]:
        """批量格式化"""
        return [self.format(r) for r in raw_list]

    def _normalize_unit(self, sensor_type: str, unit: str) -> str:
        """标准化单位字符串"""
        unit_map = {
            SensorType.TEMPERATURE.value: {"c": "℃", "f": "℉", "k": "K", "℃": "℃", "°C": "℃"},
            SensorType.PRESSURE.value: {"kpa": "kPa", "mpa": "MPa", "pa": "Pa", "kpa": "kPa"},
            SensorType.VIND_SPEED.value: {"ms": "m/s", "kmh": "km/h", "mph": "mph", "m/s": "m/s"},
            SensorType.FLOW.value: {"m3h": "m³/h", "m³/h": "m³/h", "lmin": "L/min"},
        }
        sensor_type = sensor_type.lower()
        if sensor_type in unit_map and unit.lower() in unit_map[sensor_type]:
            return unit_map[sensor_type][unit.lower()]
        return unit or ""

    def _get_precision(self, sensor_type: str) -> int:
        """根据传感器类型确定小数精度"""
        precision_map = {
            SensorType.TEMPERATURE.value: 2,
            SensorType.PRESSURE.value: 1,
            SensorType.VIBRATION.value: 3,
            SensorType.DISPLACEMENT.value: 2,
            SensorType.FLOW.value: 2,
            SensorType.WIND_SPEED.value: 2,
            SensorType.RAINFALL.value: 1,
        }
        return precision_map.get(sensor_type.lower(), 2)
