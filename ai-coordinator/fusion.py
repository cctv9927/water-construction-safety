"""
多模态融合判断模块
- 综合视频、传感器、语音等多种数据源
- 基于时序和空间关联进行融合分析
"""
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

from .alert_grader import Alert, AlertLevel, AlertType, get_grader
from .state_machine import Event, SystemState

logger = logging.getLogger(__name__)


@dataclass
class FusionContext:
    """融合上下文"""
    alerts: List[Alert] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)
    location: Optional[str] = None
    time_window: float = 60.0  # 时间窗口（秒）
    last_update: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class FusionEngine:
    """多模态融合引擎"""

    def __init__(self, time_window_seconds: float = 60.0):
        """
        初始化融合引擎
        
        Args:
            time_window_seconds: 时间窗口大小
        """
        self.time_window = timedelta(seconds=time_window_seconds)
        self.contexts: Dict[str, FusionContext] = defaultdict(lambda: FusionContext(time_window=self.time_window.total_seconds()))
        self.grader = get_grader()

    def add_sensor_alert(self, location: str, sensor_type: str, value: float, confidence: float = 1.0):
        """添加传感器告警"""
        alert = self.grader.grade_sensor_alert(sensor_type, value, confidence)
        self._add_alert(location, alert)

    def add_vision_alert(self, location: str, detection_type: str, confidence: float, location_info: Optional[str] = None):
        """添加视觉告警"""
        alert = self.grader.grade_vision_alert(detection_type, confidence, location_info)
        self._add_alert(location, alert)

    def add_voice_alert(self, location: str, intent_type: str, confidence: float, raw_text: str = ""):
        """添加语音告警"""
        alert = self.grader.grade_voice_alert(intent_type, confidence, raw_text)
        self._add_alert(location, alert)

    def _add_alert(self, location: str, alert: Alert):
        """添加告警到上下文"""
        ctx = self.contexts[location]
        ctx.alerts.append(alert)
        ctx.last_update = datetime.utcnow().isoformat() + "Z"
        
        # 清理过期告警
        self._cleanup_expired(location)
        
        logger.info(f"Added alert to {location}: {alert.level.value} - {alert.message}")

    def _cleanup_expired(self, location: str):
        """清理过期告警"""
        ctx = self.contexts[location]
        now = datetime.utcnow()
        cutoff = now - self.time_window
        
        valid_alerts = []
        for alert in ctx.alerts:
            alert_time = datetime.fromisoformat(alert.timestamp.replace("Z", "+00:00"))
            if alert_time > cutoff:
                valid_alerts.append(alert)
        
        ctx.alerts = valid_alerts

    def fuse(self, location: str) -> Optional[Alert]:
        """
        融合指定位置的告警
        
        Args:
            location: 位置标识
            
        Returns:
            融合后的告警
        """
        ctx = self.contexts.get(location)
        if not ctx or not ctx.alerts:
            return None
        
        # 清理过期
        self._cleanup_expired(location)
        
        if not ctx.alerts:
            return None
        
        # 单源告警直接返回
        if len(ctx.alerts) == 1:
            return ctx.alerts[0]
        
        # 多源融合
        return self.grader.fuse_alerts(ctx.alerts)

    def get_fused_alerts(self) -> Dict[str, Alert]:
        """
        获取所有位置的融合告警
        
        Returns:
            位置 -> 告警 的字典
        """
        results = {}
        for location in list(self.contexts.keys()):
            fused = self.fuse(location)
            if fused:
                results[location] = fused
        return results

    def get_multi_location_fused(self) -> Optional[Alert]:
        """
        跨位置融合
        
        当多个位置同时告警时，生成全局告警
        
        Returns:
            跨位置融合告警
        """
        # 统计各位置告警
        location_alerts = self.get_fused_alerts()
        
        if not location_alerts:
            return None
        
        # 只有一个位置有告警
        if len(location_alerts) == 1:
            return list(location_alerts.values())[0]
        
        # 多位置告警：计算最高级别
        levels = [a.level for a in location_alerts.values()]
        if AlertLevel.P0 in levels:
            final_level = AlertLevel.P0
        elif AlertLevel.P1 in levels:
            final_level = AlertLevel.P1
        else:
            final_level = AlertLevel.P2
        
        # 构建跨位置告警
        locations = list(location_alerts.keys())
        message = f"多区域告警：{', '.join(locations)}"
        
        fused = Alert(
            level=final_level,
            type=AlertType.MULTI_SOURCE_ALERT,
            message=message,
            source="fusion",
            timestamp=datetime.utcnow().isoformat() + "Z",
            confidence=max(a.confidence for a in location_alerts.values()),
            tags=["multi_location"],
        )
        
        return fused

    def correlate_events(self, sensor_event: Event, vision_event: Event) -> Dict[str, Any]:
        """
        关联传感器和视觉事件
        
        用于判断传感器异常是否与视觉检测结果相关
        
        Args:
            sensor_event: 传感器事件
            vision_event: 视觉事件
            
        Returns:
            关联分析结果
        """
        result = {
            "correlated": False,
            "confidence": 0.0,
            "reason": "",
        }
        
        # 时间相关性
        sensor_time = datetime.fromisoformat(sensor_event.timestamp.replace("Z", "+00:00"))
        vision_time = datetime.fromisoformat(vision_event.timestamp.replace("Z", "+00:00"))
        time_diff = abs((sensor_time - vision_time).total_seconds())
        
        if time_diff > 30:  # 30秒内
            result["reason"] = f"时间差过大: {time_diff:.1f}秒"
            return result
        
        # 数据相关性（简化版）
        sensor_type = sensor_event.data.get("sensor_type", "")
        vision_type = vision_event.data.get("detection_type", "")
        
        # 相关性规则
        correlation_rules = {
            ("temperature", "fire"): 0.9,
            ("vibration", "collapse"): 0.8,
            ("displacement", "intrusion"): 0.7,
            ("wind_speed", "crowd"): 0.6,
        }
        
        correlation = correlation_rules.get((sensor_type, vision_type), 0.3)
        
        result["correlated"] = correlation >= 0.6
        result["confidence"] = correlation * (1 - time_diff / 30)
        result["reason"] = f"传感器{sensor_type}与视觉{vision_type}相关"
        
        return result


# 全局融合引擎
_fusion_engine: Optional[FusionEngine] = None


def get_fusion_engine() -> FusionEngine:
    """获取全局融合引擎"""
    global _fusion_engine
    if _fusion_engine is None:
        _fusion_engine = FusionEngine(time_window_seconds=60.0)
    return _fusion_engine
