"""
告警分级模块
- 基于传感器阈值和 AI 置信度进行告警分级
- P0/P1/P2 三级告警
"""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """告警级别"""
    P0 = "P0"   # 紧急
    P1 = "P1"   # 重要
    P2 = "P2"   # 一般


class AlertType(str, Enum):
    """告警类型"""
    # 传感器类
    TEMPERATURE_HIGH = "temperature_high"
    TEMPERATURE_CRITICAL = "temperature_critical"
    VIBRATION_ANOMALY = "vibration_anomaly"
    DISPLACEMENT_EXCEED = "displacement_exceed"
    WIND_SPEED_EXCEED = "wind_speed_exceed"
    RAINFALL_HEAVY = "rainfall_heavy"
    
    # 视觉类
    PERSON_UNAUTHORIZED = "person_unauthorized"
    HELMET_MISSING = "helmet_missing"
    DANGER_ZONE_INTRUSION = "danger_zone_intrusion"
    FIRE_DETECTED = "fire_detected"
    CROWD_GATHERING = "crowd_gathering"
    
    # 语音类
    VOICE_EMERGENCY = "voice_emergency"
    VOICE_WARNING = "voice_warning"
    
    # 综合类
    MULTI_SOURCE_ALERT = "multi_source_alert"
    TIMEOUT_ALERT = "timeout_alert"


@dataclass
class Alert:
    """告警数据"""
    level: AlertLevel
    type: AlertType
    message: str
    source: str                      # 告警来源
    timestamp: str
    confidence: float = 1.0          # AI 置信度
    sensor_data: Optional[Dict[str, Any]] = None
    vision_data: Optional[Dict[str, Any]] = None
    voice_data: Optional[Dict[str, Any]] = None
    tags: List[str] = None          # 标签

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class AlertGrader:
    """告警分级器"""

    # 传感器阈值配置
    SENSOR_THRESHOLDS = {
        "temperature": {
            "normal": 35.0,
            "warning": 40.0,
            "critical": 45.0,
        },
        "vibration": {
            "normal": 2.0,
            "warning": 5.0,
            "critical": 8.0,
        },
        "displacement": {
            "normal": 10.0,
            "warning": 20.0,
            "critical": 30.0,
        },
        "wind_speed": {
            "normal": 10.0,
            "warning": 15.0,
            "critical": 20.0,
        },
        "rainfall": {
            "normal": 50.0,
            "warning": 100.0,
            "critical": 150.0,
        },
    }

    # 告警级别权重（用于多源融合）
    SOURCE_WEIGHTS = {
        "sensor": 0.3,
        "vision": 0.4,
        "voice": 0.3,
    }

    def __init__(self):
        self.thresholds = self.SENSOR_THRESHOLDS
        self.weights = self.SOURCE_WEIGHTS

    def grade_sensor_alert(
        self,
        sensor_type: str,
        value: float,
        confidence: float = 1.0
    ) -> Alert:
        """
        传感器告警分级
        
        Args:
            sensor_type: 传感器类型
            value: 测量值
            confidence: AI 置信度
            
        Returns:
            Alert 对象
        """
        threshold = self.thresholds.get(sensor_type, {})
        if not threshold:
            return self._create_alert(
                AlertLevel.P2,
                AlertType.TEMPERATURE_HIGH,  # 默认类型
                f"未知传感器类型 {sensor_type}: {value}",
                "sensor",
                {"sensor_type": sensor_type, "value": value},
                confidence,
            )
        
        # 判断级别
        if value >= threshold.get("critical", float("inf")):
            level = AlertLevel.P0
            alert_type = self._get_critical_type(sensor_type)
        elif value >= threshold.get("warning", float("inf")):
            level = AlertLevel.P1
            alert_type = self._get_warning_type(sensor_type)
        else:
            level = AlertLevel.P2
            alert_type = self._get_warning_type(sensor_type)
        
        message = self._build_sensor_message(sensor_type, value, level)
        
        return self._create_alert(
            level,
            alert_type,
            message,
            "sensor",
            {"sensor_type": sensor_type, "value": value, "unit": self._get_unit(sensor_type)},
            confidence,
        )

    def grade_vision_alert(
        self,
        detection_type: str,
        confidence: float,
        location: Optional[str] = None
    ) -> Alert:
        """
        视觉检测告警分级
        
        Args:
            detection_type: 检测类型（helmet/fire/person/danger_zone等）
            confidence: 置信度
            location: 位置信息
            
        Returns:
            Alert 对象
        """
        # 高置信度优先
        if confidence >= 0.9:
            if detection_type in ["fire", "intrusion", "crowd"]:
                level = AlertLevel.P0
                alert_type = AlertType.FIRE_DETECTED if detection_type == "fire" else AlertType.DANGER_ZONE_INTRUSION
            elif detection_type in ["helmet", "person"]:
                level = AlertLevel.P1
                alert_type = AlertType.HELMET_MISSING if detection_type == "helmet" else AlertType.PERSON_UNAUTHORIZED
            else:
                level = AlertLevel.P2
                alert_type = AlertType.VISION_DETECTION
        elif confidence >= 0.7:
            level = AlertLevel.P1 if detection_type in ["fire", "helmet", "person", "intrusion"] else AlertLevel.P2
            alert_type = AlertType.VISION_DETECTION
        else:
            level = AlertLevel.P2
            alert_type = AlertType.VISION_DETECTION
        
        message = self._build_vision_message(detection_type, confidence, location)
        
        return self._create_alert(
            level,
            alert_type,
            message,
            "vision",
            {"detection_type": detection_type, "location": location},
            confidence,
        )

    def grade_voice_alert(
        self,
        intent_type: str,
        confidence: float,
        raw_text: str = ""
    ) -> Alert:
        """
        语音告警分级
        
        Args:
            intent_type: 意图类型
            confidence: 置信度
            raw_text: 原始文本
            
        Returns:
            Alert 对象
        """
        # 紧急意图
        if intent_type in ["alert_help", "alert_fire", "alert_injury", "command_evacuate"]:
            level = AlertLevel.P0
            alert_type = AlertType.VOICE_EMERGENCY
        elif intent_type in ["alert_env", "command_stop"]:
            level = AlertLevel.P1
            alert_type = AlertType.VOICE_WARNING
        else:
            level = AlertLevel.P2
            alert_type = AlertType.VOICE_WARNING
        
        message = f"语音告警：{raw_text or intent_type}"
        
        return self._create_alert(
            level,
            alert_type,
            message,
            "voice",
            {"intent_type": intent_type, "raw_text": raw_text},
            confidence,
        )

    def fuse_alerts(
        self,
        alerts: List[Alert],
        time_window_seconds: float = 60.0
    ) -> Alert:
        """
        多源告警融合
        
        当多个来源同时告警时，综合判断最终告警级别
        
        Args:
            alerts: 告警列表
            time_window_seconds: 时间窗口（秒）
            
        Returns:
            融合后的告警
        """
        if not alerts:
            raise ValueError("No alerts to fuse")
        
        if len(alerts) == 1:
            return alerts[0]
        
        # 计算加权告警分数
        scores = []
        for alert in alerts:
            # 级别分数：P0=100, P1=50, P2=10
            level_score = {"P0": 100, "P1": 50, "P2": 10}.get(alert.level.value, 10)
            # 置信度加权
            weighted_score = level_score * alert.confidence * self.weights.get(alert.source, 0.3)
            scores.append(weighted_score)
        
        total_score = sum(scores)
        
        # 综合分数阈值判断
        if total_score >= 80:
            final_level = AlertLevel.P0
        elif total_score >= 40:
            final_level = AlertLevel.P1
        else:
            final_level = AlertLevel.P2
        
        # 构建消息
        sources = [a.source for a in alerts]
        messages = [a.message for a in alerts[:3]]  # 最多3条
        final_message = f"多源告警[{','.join(sources)}]: {messages[0]}"
        
        fused_alert = self._create_alert(
            final_level,
            AlertType.MULTI_SOURCE_ALERT,
            final_message,
            "fusion",
            {"alerts": [a.model_dump() for a in alerts], "score": total_score},
            max(a.confidence for a in alerts),
        )
        fused_alert.tags = ["fused", "multi_source"]
        
        logger.info(f"Alerts fused: {len(alerts)} sources, final level: {final_level.value}, score: {total_score:.1f}")
        return fused_alert

    def _create_alert(
        self,
        level: AlertLevel,
        alert_type: AlertType,
        message: str,
        source: str,
        data: Dict[str, Any],
        confidence: float,
    ) -> Alert:
        """创建告警对象"""
        from datetime import datetime
        alert = Alert(
            level=level,
            type=alert_type,
            message=message,
            source=source,
            timestamp=datetime.utcnow().isoformat() + "Z",
            confidence=confidence,
        )
        
        # 根据来源填充数据
        if source == "sensor":
            alert.sensor_data = data
        elif source == "vision":
            alert.vision_data = data
        elif source == "voice":
            alert.voice_data = data
        elif source == "fusion":
            alert.tags = ["fused"]
        
        return alert

    def _get_critical_type(self, sensor_type: str) -> AlertType:
        """获取传感器严重告警类型"""
        mapping = {
            "temperature": AlertType.TEMPERATURE_CRITICAL,
            "vibration": AlertType.VIBRATION_ANOMALY,
            "displacement": AlertType.DISPLACEMENT_EXCEED,
            "wind_speed": AlertType.WIND_SPEED_EXCEED,
            "rainfall": AlertType.RAINFALL_HEAVY,
        }
        return mapping.get(sensor_type, AlertType.TEMPERATURE_CRITICAL)

    def _get_warning_type(self, sensor_type: str) -> AlertType:
        """获取传感器警告告警类型"""
        return AlertType.TEMPERATURE_HIGH

    def _get_unit(self, sensor_type: str) -> str:
        """获取传感器单位"""
        units = {
            "temperature": "°C",
            "vibration": "mm/s",
            "displacement": "mm",
            "wind_speed": "m/s",
            "rainfall": "mm/h",
        }
        return units.get(sensor_type, "")

    def _build_sensor_message(self, sensor_type: str, value: float, level: AlertLevel) -> str:
        """构建传感器告警消息"""
        type_names = {
            "temperature": "温度",
            "vibration": "振动",
            "displacement": "位移",
            "wind_speed": "风速",
            "rainfall": "降雨量",
        }
        type_name = type_names.get(sensor_type, sensor_type)
        unit = self._get_unit(sensor_type)
        level_text = {"P0": "严重超限", "P1": "超过警戒", "P2": "轻度异常"}.get(level.value, "")
        return f"{type_name}告警：当前{value}{unit}，{level_text}"

    def _build_vision_message(self, detection_type: str, confidence: float, location: Optional[str]) -> str:
        """构建视觉告警消息"""
        type_names = {
            "fire": "火焰",
            "helmet": "安全帽",
            "person": "人员",
            "intrusion": "危险区域入侵",
            "crowd": "人群聚集",
        }
        type_name = type_names.get(detection_type, detection_type)
        loc_text = f"，位置：{location}" if location else ""
        return f"AI检测到{type_name}，置信度{confidence:.0%}{loc_text}"


# 全局分级器
_grader: Optional[AlertGrader] = None


def get_grader() -> AlertGrader:
    """获取全局告警分级器"""
    global _grader
    if _grader is None:
        _grader = AlertGrader()
    return _grader
