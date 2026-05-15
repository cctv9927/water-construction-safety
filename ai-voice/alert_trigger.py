"""
告警触发模块
- 基于意图识别结果触发告警
- 支持多种告警级别和播报
"""
import asyncio
import logging
from typing import Optional, Dict, Any, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .intent import IntentType, IntentResult
from .tts import announce_alert, get_tts_engine

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """告警级别"""
    P0 = "P0"   # 紧急：立即响应
    P1 = "P1"   # 重要：快速响应
    P2 = "P2"   # 一般：正常处理


@dataclass
class Alert:
    """告警信息"""
    level: AlertLevel
    intent_type: IntentType
    message: str
    source: str  # 来源：voice/video/sensor
    timestamp: str
    confidence: float
    raw_data: Dict[str, Any]


class AlertTrigger:
    """告警触发器"""

    # 意图到告警级别的映射
    INTENT_LEVEL_MAP = {
        IntentType.ALERT_HELP: AlertLevel.P0,
        IntentType.ALERT_FIRE: AlertLevel.P0,
        IntentType.ALERT_INJURY: AlertLevel.P0,
        IntentType.COMMAND_EVACUATE: AlertLevel.P0,
        IntentType.ALERT_ENV: AlertLevel.P1,
        IntentType.COMMAND_STOP: AlertLevel.P1,
        IntentType.COMMAND_START: AlertLevel.P2,
        IntentType.STATUS_QUERY: AlertLevel.P2,
    }

    def __init__(self, announce: bool = True, min_confidence: float = 0.5):
        """
        初始化告警触发器
        
        Args:
            announce: 是否自动播报
            min_confidence: 最低置信度阈值
        """
        self.announce_enabled = announce
        self.min_confidence = min_confidence
        self._alert_callbacks: list[Callable[[Alert], Awaitable[None]]] = []

    def register_callback(self, callback: Callable[[Alert], Awaitable[None]]):
        """注册告警回调"""
        self._alert_callbacks.append(callback)

    def trigger_from_intent(self, intent_result: IntentResult, source: str = "voice") -> Optional[Alert]:
        """
        从意图结果触发告警
        
        Args:
            intent_result: 意图识别结果
            source: 数据来源
            
        Returns:
            Alert 对象或 None（不满足触发条件）
        """
        # 置信度检查
        if intent_result.confidence < self.min_confidence:
            logger.debug(f"Confidence {intent_result.confidence} below threshold")
            return None
        
        # 未知意图不触发
        if intent_result.intent == IntentType.UNKNOWN:
            return None
        
        # 获取告警级别
        level = self.INTENT_LEVEL_MAP.get(
            intent_result.intent,
            AlertLevel.P2
        )
        
        # 构建告警消息
        message = self._build_message(intent_result)
        
        alert = Alert(
            level=level,
            intent_type=intent_result.intent,
            message=message,
            source=source,
            timestamp=datetime.utcnow().isoformat() + "Z",
            confidence=intent_result.confidence,
            raw_data={
                "raw_text": intent_result.raw_text,
                "entities": intent_result.entities,
                "keywords_matched": intent_result.keywords_matched,
            },
        )
        
        logger.warning(f"Alert triggered: {level.value} - {message}")
        return alert

    async def process_alert(self, alert: Alert):
        """
        处理告警（触发回调和播报）
        
        Args:
            alert: 告警对象
        """
        # 自动播报
        if self.announce_enabled:
            asyncio.create_task(self._announce(alert))
        
        # 触发回调
        for callback in self._alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

    async def _announce(self, alert: Alert):
        """播报告警"""
        try:
            await announce_alert(alert.message, alert.level.value)
            logger.info(f"Alert announced: {alert.message}")
        except Exception as e:
            logger.error(f"TTS announce failed: {e}")

    def _build_message(self, intent_result: IntentResult) -> str:
        """构建告警消息"""
        intent_messages = {
            IntentType.ALERT_HELP: "检测到紧急求助信号，请立即响应",
            IntentType.ALERT_FIRE: "检测到火灾报警，请立即确认",
            IntentType.ALERT_INJURY: "检测到人员伤亡报警，请立即响应",
            IntentType.ALERT_ENV: "检测到环境异常，请检查确认",
            IntentType.COMMAND_START: "接收到启动指令",
            IntentType.COMMAND_STOP: "接收到停止指令",
            IntentType.COMMAND_EVACUATE: "紧急疏散指令，请立即撤离",
            IntentType.STATUS_QUERY: "收到状态查询请求",
            IntentType.UNKNOWN: "语音指令未识别",
        }
        
        base_msg = intent_messages.get(intent_result.intent, "未知告警")
        
        # 添加位置信息
        location = intent_result.entities.get("location", "")
        if location:
            base_msg += f"，位置：{location}"
        
        return base_msg


# 全局告警触发器
_trigger: Optional[AlertTrigger] = None


def get_trigger() -> AlertTrigger:
    """获取全局告警触发器"""
    global _trigger
    if _trigger is None:
        _trigger = AlertTrigger(announce=True)
    return _trigger


def create_alert_from_intent(intent_result: IntentResult, source: str = "voice") -> Optional[Alert]:
    """便捷函数：从意图创建告警"""
    return get_trigger().trigger_from_intent(intent_result, source)
