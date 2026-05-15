"""
事件路由模块
- 将不同来源的事件路由到对应的处理 Agent
- 支持视频、传感器、语音事件
"""
import logging
from typing import Dict, Callable, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .state_machine import Event, EventType, SystemState
from .alert_grader import Alert, AlertLevel, get_grader

logger = logging.getLogger(__name__)


@dataclass
class RouteTarget:
    """路由目标"""
    agent_name: str
    endpoint: str
    priority: int = 0


class EventRouter:
    """事件路由器"""

    def __init__(self):
        self._routes: Dict[EventType, List[RouteTarget]] = {}
        self._handlers: Dict[str, Callable] = {}
        self._grader = get_grader()
        self._setup_default_routes()

    def _setup_default_routes(self):
        """设置默认路由"""
        # 传感器事件
        self.register_route(EventType.SENSOR_ANOMALY, RouteTarget("sensor-collector", "http://localhost:8081/anomaly"))
        self.register_route(EventType.SENSOR_CRITICAL, RouteTarget("sensor-collector", "http://localhost:8081/critical"))
        
        # 视觉事件
        self.register_route(EventType.VISION_DETECTION, RouteTarget("ai-vision", "http://localhost:8082/detection"))
        self.register_route(EventType.VISION_CRITICAL, RouteTarget("ai-vision", "http://localhost:8082/critical"))
        
        # 语音事件
        self.register_route(EventType.VOICE_ALERT, RouteTarget("ai-voice", "http://localhost:8083/alert"))
        self.register_route(EventType.VOICE_COMMAND, RouteTarget("ai-voice", "http://localhost:8083/command"))
        
        # 系统事件
        self.register_route(EventType.MANUAL_ALERT, RouteTarget("backend", "http://localhost:8000/api/alerts"))
        self.register_route(EventType.SYSTEM_ERROR, RouteTarget("backend", "http://localhost:8000/api/errors"))

    def register_route(self, event_type: EventType, target: RouteTarget):
        """注册路由"""
        if event_type not in self._routes:
            self._routes[event_type] = []
        self._routes[event_type].append(target)
        self._routes[event_type].sort(key=lambda x: x.priority, reverse=True)
        logger.info(f"Registered route: {event_type.value} -> {target.agent_name}")

    def register_handler(self, agent_name: str, handler: Callable):
        """注册处理函数"""
        self._handlers[agent_name] = handler
        logger.info(f"Registered handler: {agent_name}")

    def route(self, event: Event) -> List[RouteTarget]:
        """
        路由事件，返回目标列表
        
        Args:
            event: 事件对象
            
        Returns:
            路由目标列表
        """
        targets = self._routes.get(event.type, [])
        
        if not targets:
            logger.warning(f"No routes for event type: {event.type.value}")
            return []
        
        # 根据告警级别调整优先级
        if event.level:
            targets = self._adjust_priority(targets, event.level)
        
        logger.info(f"Routed event {event.type.value} to {[t.agent_name for t in targets]}")
        return targets

    def _adjust_priority(self, targets: List[RouteTarget], level: str) -> List[RouteTarget]:
        """根据告警级别调整优先级"""
        if level == "P0":
            # P0 告警：确保所有相关 Agent 都收到
            return targets
        elif level == "P1":
            # P1 告警：优先级不变
            return targets
        else:
            # P2 告警：只通知主要 Agent
            return targets[:1] if targets else targets

    def dispatch(self, event: Event) -> Dict[str, Any]:
        """
        分发事件到对应 Handler
        
        Args:
            event: 事件对象
            
        Returns:
            分发结果
        """
        targets = self.route(event)
        results = {}
        
        for target in targets:
            handler = self._handlers.get(target.agent_name)
            if handler:
                try:
                    result = handler(event)
                    results[target.agent_name] = {"success": True, "result": result}
                except Exception as e:
                    logger.error(f"Handler {target.agent_name} error: {e}")
                    results[target.agent_name] = {"success": False, "error": str(e)}
            else:
                results[target.agent_name] = {"success": False, "error": "No handler registered"}
        
        return results


class EventConverter:
    """事件格式转换器"""

    @staticmethod
    def from_sensor(data: Dict[str, Any]) -> Event:
        """传感器数据转事件"""
        sensor_type = data.get("sensor_type", "")
        value = data.get("value", 0)
        confidence = data.get("confidence", 1.0)
        
        grader = get_grader()
        alert = grader.grade_sensor_alert(sensor_type, value, confidence)
        
        # 判断事件类型
        if alert.level == AlertLevel.P0:
            event_type = EventType.SENSOR_CRITICAL
        else:
            event_type = EventType.SENSOR_ANOMALY
        
        return Event(
            type=event_type,
            source="sensor",
            data=data,
            timestamp=data.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            level=alert.level.value,
            confidence=confidence,
        )

    @staticmethod
    def from_vision(data: Dict[str, Any]) -> Event:
        """视觉检测数据转事件"""
        detection_type = data.get("detection_type", "")
        confidence = data.get("confidence", 0.5)
        location = data.get("location")
        
        grader = get_grader()
        alert = grader.grade_vision_alert(detection_type, confidence, location)
        
        # 判断事件类型
        if alert.level == AlertLevel.P0:
            event_type = EventType.VISION_CRITICAL
        else:
            event_type = EventType.VISION_DETECTION
        
        return Event(
            type=event_type,
            source="vision",
            data=data,
            timestamp=data.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            level=alert.level.value,
            confidence=confidence,
        )

    @staticmethod
    def from_voice(data: Dict[str, Any]) -> Event:
        """语音数据转事件"""
        intent_type = data.get("intent_type", "unknown")
        confidence = data.get("confidence", 0.5)
        raw_text = data.get("raw_text", "")
        
        grader = get_grader()
        alert = grader.grade_voice_alert(intent_type, confidence, raw_text)
        
        # 判断事件类型
        if alert.level == AlertLevel.P0:
            event_type = EventType.VOICE_ALERT
        else:
            event_type = EventType.VOICE_COMMAND
        
        return Event(
            type=event_type,
            source="voice",
            data=data,
            timestamp=data.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            level=alert.level.value,
            confidence=confidence,
        )

    @staticmethod
    def from_manual(data: Dict[str, Any], level: str = "P1") -> Event:
        """手动告警转事件"""
        return Event(
            type=EventType.MANUAL_ALERT,
            source="manual",
            data=data,
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=level,
            confidence=1.0,
        )


# 全局路由器
_router: Optional[EventRouter] = None


def get_router() -> EventRouter:
    """获取全局路由器"""
    global _router
    if _router is None:
        _router = EventRouter()
    return _router
