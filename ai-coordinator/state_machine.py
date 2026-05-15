"""
状态机模块 - 事件驱动的状态管理
实现事件 → 状态 → 动作的流转
"""
import logging
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class SystemState(str, Enum):
    """系统状态枚举"""
    NORMAL = "normal"              # 正常
    VIGILANT = "vigilant"          # 警戒（单项告警）
    WARNING = "warning"            # 警告（多项告警）
    CRITICAL = "critical"          # 严重（需紧急处理）
    EMERGENCY = "emergency"        # 紧急（全量响应）
    RECOVERING = "recovering"       # 恢复中


class EventType(str, Enum):
    """事件类型"""
    # 传感器事件
    SENSOR_ANOMALY = "sensor_anomaly"
    SENSOR_CRITICAL = "sensor_critical"
    
    # 视觉事件
    VISION_DETECTION = "vision_detection"
    VISION_CRITICAL = "vision_critical"
    
    # 语音事件
    VOICE_ALERT = "voice_alert"
    VOICE_COMMAND = "voice_command"
    
    # 系统事件
    MANUAL_ALERT = "manual_alert"
    SYSTEM_ERROR = "system_error"
    TIMEOUT = "timeout"


@dataclass
class Event:
    """事件对象"""
    type: EventType
    source: str                          # 来源：sensor/vision/voice/manual
    data: Dict[str, Any]
    timestamp: str
    level: Optional[str] = None          # P0/P1/P2
    confidence: float = 1.0


@dataclass
class StateTransition:
    """状态转换记录"""
    from_state: SystemState
    to_state: SystemState
    trigger_event: EventType
    timestamp: str
    reason: str


class StateMachine:
    """状态机实现"""

    # 状态转换规则
    # 格式：(当前状态, 事件类型, 目标状态)
    TRANSITIONS: List[tuple] = [
        # 正常状态
        (SystemState.NORMAL, EventType.SENSOR_ANOMALY, SystemState.VIGILANT),
        (SystemState.NORMAL, EventType.VISION_DETECTION, SystemState.VIGILANT),
        (SystemState.NORMAL, EventType.VOICE_ALERT, SystemState.WARNING),
        (SystemState.NORMAL, EventType.SENSOR_CRITICAL, SystemState.CRITICAL),
        (SystemState.NORMAL, EventType.VISION_CRITICAL, SystemState.CRITICAL),
        (SystemState.NORMAL, EventType.MANUAL_ALERT, SystemState.CRITICAL),
        (SystemState.NORMAL, EventType.SYSTEM_ERROR, SystemState.WARNING),
        
        # 警戒状态
        (SystemState.VIGILANT, EventType.SENSOR_ANOMALY, SystemState.WARNING),
        (SystemState.VIGILANT, EventType.VISION_DETECTION, SystemState.WARNING),
        (SystemState.VIGILANT, EventType.VOICE_ALERT, SystemState.CRITICAL),
        (SystemState.VIGILANT, EventType.SENSOR_CRITICAL, SystemState.CRITICAL),
        (SystemState.VIGILANT, EventType.VISION_CRITICAL, SystemState.CRITICAL),
        (SystemState.VIGILANT, EventType.MANUAL_ALERT, SystemState.EMERGENCY),
        
        # 警告状态
        (SystemState.WARNING, EventType.SENSOR_CRITICAL, SystemState.CRITICAL),
        (SystemState.WARNING, EventType.VISION_CRITICAL, SystemState.CRITICAL),
        (SystemState.WARNING, EventType.VOICE_ALERT, SystemState.CRITICAL),
        (SystemState.WARNING, EventType.MANUAL_ALERT, SystemState.EMERGENCY),
        (SystemState.WARNING, EventType.SENSOR_ANOMALY, SystemState.WARNING),
        (SystemState.WARNING, EventType.VISION_DETECTION, SystemState.WARNING),
        
        # 严重状态
        (SystemState.CRITICAL, EventType.VOICE_ALERT, SystemState.EMERGENCY),
        (SystemState.CRITICAL, EventType.MANUAL_ALERT, SystemState.EMERGENCY),
        
        # 紧急状态（只能恢复到严重）
        (SystemState.EMERGENCY, EventType.SYSTEM_ERROR, SystemState.RECOVERING),
        
        # 恢复路径
        (SystemState.VIGILANT, EventType.TIMEOUT, SystemState.NORMAL),
        (SystemState.WARNING, EventType.TIMEOUT, SystemState.VIGILANT),
        (SystemState.CRITICAL, EventType.TIMEOUT, SystemState.WARNING),
        (SystemState.RECOVERING, EventType.TIMEOUT, SystemState.NORMAL),
    ]

    def __init__(self, initial_state: SystemState = SystemState.NORMAL):
        self.current_state = initial_state
        self.history: List[StateTransition] = []
        self._action_handlers: Dict[SystemState, List[Callable]] = {
            state: [] for state in SystemState
        }
        self._timeout_handlers: Dict[SystemState, Callable] = {}
        logger.info(f"StateMachine initialized with state: {initial_state.value}")

    def register_action(self, state: SystemState, handler: Callable[[Event], None]):
        """注册状态进入时的动作"""
        self._action_handlers[state].append(handler)

    def register_timeout(self, state: SystemState, handler: Callable[[], None], timeout_seconds: int):
        """注册超时自动恢复"""
        self._timeout_handlers[state] = handler
        # 这里简化处理，实际应该用 asyncio 或定时器

    def process_event(self, event: Event) -> SystemState:
        """
        处理事件，返回目标状态
        
        Args:
            event: 输入事件
            
        Returns:
            目标状态（可能与当前状态相同）
        """
        old_state = self.current_state
        
        # 查找转换规则
        target_state = self._find_transition(self.current_state, event.type)
        
        if target_state and target_state != self.current_state:
            self._transition_to(target_state, event)
            return target_state
        
        # 无转换规则，检查是否执行当前状态的动作
        self._execute_actions(self.current_state, event)
        return self.current_state

    def _find_transition(self, current: SystemState, event_type: EventType) -> Optional[SystemState]:
        """查找状态转换"""
        for from_state, evt_type, to_state in self.TRANSITIONS:
            if from_state == current and evt_type == event_type:
                return to_state
        return None

    def _transition_to(self, target_state: SystemState, event: Event):
        """执行状态转换"""
        transition = StateTransition(
            from_state=self.current_state,
            to_state=target_state,
            trigger_event=event.type,
            timestamp=datetime.utcnow().isoformat() + "Z",
            reason=f"Event: {event.type.value}, Level: {event.level or 'N/A'}",
        )
        self.history.append(transition)
        
        logger.warning(
            f"State transition: {self.current_state.value} → {target_state.value} "
            f"(trigger: {event.type.value})"
        )
        
        self.current_state = target_state
        
        # 执行动作
        self._execute_actions(target_state, event)

    def _execute_actions(self, state: SystemState, event: Event):
        """执行状态对应的动作"""
        for handler in self._action_handlers[state]:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Action handler error: {e}")

    def get_state(self) -> SystemState:
        """获取当前状态"""
        return self.current_state

    def get_state_level(self) -> int:
        """获取状态的紧急程度等级（1-5）"""
        levels = {
            SystemState.NORMAL: 1,
            SystemState.VIGILANT: 2,
            SystemState.WARNING: 3,
            SystemState.CRITICAL: 4,
            SystemState.EMERGENCY: 5,
            SystemState.RECOVERING: 2,
        }
        return levels.get(self.current_state, 1)

    def force_state(self, state: SystemState, reason: str = ""):
        """强制设置状态（用于恢复）"""
        old_state = self.current_state
        self.current_state = state
        logger.info(f"Force state: {old_state.value} → {state.value} ({reason})")


# 全局状态机实例
_state_machine: Optional[StateMachine] = None


def get_state_machine() -> StateMachine:
    """获取全局状态机"""
    global _state_machine
    if _state_machine is None:
        _state_machine = StateMachine()
    return _state_machine
