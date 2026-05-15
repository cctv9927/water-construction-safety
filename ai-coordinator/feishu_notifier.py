"""
飞书通知服务 - 多智能体调度模块
集成飞书机器人 Webhook，实现告警实时推送
"""
import logging
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """告警级别（与 alert_grader.py 保持一致）"""
    P0 = "P0"   # 紧急 - 红色
    P1 = "P1"   # 重要 - 橙色
    P2 = "P2"   # 一般 - 黄色


# 告警级别对应的飞书颜色
LEVEL_COLOR = {
    AlertLevel.P0: "red",
    AlertLevel.P1: "orange",
    AlertLevel.P2: "yellow",
}

# 告警级别对应 emoji
LEVEL_EMOJI = {
    AlertLevel.P0: "🔴",
    AlertLevel.P1: "🟠",
    AlertLevel.P2: "🟡",
}


@dataclass
class AlertPayload:
    """告警消息体"""
    level: AlertLevel
    title: str
    message: str
    source: str                          # sensor / vision / voice / fusion / manual
    location: Optional[str] = None        # 告警位置
    sensor_type: Optional[str] = None    # 传感器类型
    sensor_value: Optional[float] = None # 传感器值
    detection_type: Optional[str] = None # 检测类型
    confidence: Optional[float] = None  # AI 置信度
    raw_text: Optional[str] = None       # 语音原始文本
    timestamp: Optional[str] = None


class FeishuNotifier:
    """飞书机器人通知器"""

    def __init__(self, webhook_url: Optional[str] = None):
        """
        初始化飞书通知器

        Args:
            webhook_url: 飞书机器人 Webhook URL，留空则不发送
        """
        self.webhook_url = webhook_url
        self.enabled = bool(webhook_url)
        if not self.enabled:
            logger.warning("Feishu webhook not configured, notifications disabled")
        else:
            logger.info("Feishu notifier initialized")

    def set_webhook(self, webhook_url: str):
        """运行时设置 Webhook URL"""
        self.webhook_url = webhook_url
        self.enabled = bool(webhook_url)
        logger.info(f"Feishu webhook updated: {'enabled' if self.enabled else 'disabled'}")

    def _build_feishu_card(self, payload: AlertPayload) -> Dict[str, Any]:
        """
        构建飞书卡片消息格式

        飞书卡片消息，支持：
        - 标题（带 emoji 标识级别）
        - 正文（告警详情）
        - 颜色标识（红/橙/黄）
        - 按钮操作（查看详情）
        """
        emoji = LEVEL_EMOJI.get(payload.level, "⚠️")
        color = LEVEL_COLOR.get(payload.level, "red")

        # 构建正文内容
        elements = []

        # 告警消息
        elements.append({
            "tag": "markdown",
            "content": f"**{payload.message}**"
        })

        # 详情表格
        fields = []
        fields.append({"is_short": True, "text": f"**告警级别**\n{emoji} {payload.level.value}"})
        fields.append({"is_short": True, "text": f"**告警来源**\n{payload.source}"})
        if payload.location:
            fields.append({"is_short": True, "text": f"**告警位置**\n{payload.location}"})
        if payload.sensor_type:
            unit = self._get_sensor_unit(payload.sensor_type)
            fields.append({
                "is_short": True,
                "text": f"**传感器类型**\n{payload.sensor_type} = {payload.sensor_value}{unit}"
            })
        if payload.detection_type:
            conf = f"{payload.confidence:.0%}" if payload.confidence else "N/A"
            fields.append({"is_short": True, "text": f"**检测类型**\n{payload.detection_type} (置信度 {conf})"})
        if payload.raw_text:
            fields.append({"is_short": False, "text": f"**语音内容**\n> {payload.raw_text}"})
        fields.append({"is_short": True, "text": f"**时间**\n{payload.timestamp or datetime.now().isoformat()}"})

        elements.append({
            "tag": "cell",
            "fields": fields
        })

        # 底部提示
        level_hint = {
            AlertLevel.P0: "⚠️ 请立即处理，持续告警将自动升级",
            AlertLevel.P1: "📋 请尽快处理，当日内完成",
            AlertLevel.P2: "📝 记录在案，计划处理",
        }
        elements.append({
            "tag": "markdown",
            "content": level_hint.get(payload.level, "")
        })

        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"{emoji} 【{payload.level.value}级告警】{payload.title}"
                    },
                    "template": color
                },
                "elements": elements
            }
        }
        return card

    def _build_simple_message(self, payload: AlertPayload) -> Dict[str, Any]:
        """构建飞书文本消息格式（简单版）"""
        emoji = LEVEL_EMOJI.get(payload.level, "⚠️")
        time_str = payload.timestamp or datetime.now().isoformat()

        text = (
            f"{emoji} **{payload.level.value}级告警**\n\n"
            f"**{payload.title}**\n\n"
            f"{payload.message}\n\n"
            f"📍 来源: {payload.source}"
        )

        if payload.location:
            text += f"\n📍 位置: {payload.location}"
        if payload.sensor_value is not None and payload.sensor_type:
            unit = self._get_sensor_unit(payload.sensor_type)
            text += f"\n📊 数据: {payload.sensor_type} = {payload.sensor_value}{unit}"
        if payload.confidence:
            text += f"\n🤖 置信度: {payload.confidence:.0%}"
        if payload.raw_text:
            text += f"\n🎤 语音: {payload.raw_text}"

        text += f"\n⏰ {time_str}"

        return {"msg_type": "text", "content": {"text": text}}

    def _get_sensor_unit(self, sensor_type: str) -> str:
        """获取传感器单位"""
        units = {
            "temperature": "°C",
            "vibration": "mm/s",
            "displacement": "mm",
            "wind_speed": "m/s",
            "rainfall": "mm/h",
            "pressure": "kPa",
            "flow": "m³/h",
        }
        return units.get(sensor_type, "")

    async def send_alert(self, payload: AlertPayload) -> bool:
        """
        发送告警通知

        Args:
            payload: 告警消息体

        Returns:
            发送是否成功
        """
        if not self.enabled:
            logger.debug(f"Alert skipped (Feishu disabled): [{payload.level.value}] {payload.title}")
            return False

        # 默认时间
        if not payload.timestamp:
            payload.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 构建消息（优先用卡片格式）
        try:
            card_payload = self._build_feishu_card(payload)
        except Exception:
            card_payload = self._build_simple_message(payload)

        # 发送请求
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.webhook_url,
                    json=card_payload,
                )
                result = response.json()

                if response.status_code == 200 and result.get("code") == 0:
                    logger.info(
                        f"Feishu alert sent: [{payload.level.value}] {payload.title} "
                        f"from {payload.source} at {payload.location or 'unknown'}"
                    )
                    return True
                else:
                    logger.error(f"Feishu API error: {result}")
                    return False

        except httpx.TimeoutException:
            logger.error("Feishu webhook timeout")
            return False
        except Exception as e:
            logger.error(f"Feishu send failed: {e}")
            return False

    async def send_batch_alerts(self, alerts: List[AlertPayload]) -> Dict[str, bool]:
        """
        批量发送告警

        Args:
            alerts: 告警列表

        Returns:
            每个告警的发送结果
        """
        results = {}
        for i, alert in enumerate(alerts):
            results[f"alert_{i}"] = await self.send_alert(alert)
        return results

    def send_alert_sync(self, payload: AlertPayload) -> bool:
        """同步发送告警（用于非 async 上下文）"""
        if not self.enabled:
            return False

        if not payload.timestamp:
            payload.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            card_payload = self._build_feishu_card(payload)
        except Exception:
            card_payload = self._build_simple_message(payload)

        try:
            import requests
            response = requests.post(self.webhook_url, json=card_payload, timeout=10)
            result = response.json()
            return response.status_code == 200 and result.get("code") == 0
        except Exception as e:
            logger.error(f"Feishu sync send failed: {e}")
            return False

    def format_alert_from_event(
        self,
        level: str,
        source: str,
        message: str,
        title: Optional[str] = None,
        location: Optional[str] = None,
        sensor_type: Optional[str] = None,
        sensor_value: Optional[float] = None,
        detection_type: Optional[str] = None,
        confidence: Optional[float] = None,
        raw_text: Optional[str] = None,
    ) -> AlertPayload:
        """从事件数据构建告警消息"""
        # 转换 level 字符串到枚举
        try:
            level_enum = AlertLevel(level)
        except ValueError:
            level_enum = AlertLevel.P2

        return AlertPayload(
            level=level_enum,
            title=title or f"{source.upper()} 告警",
            message=message,
            source=source,
            location=location,
            sensor_type=sensor_type,
            sensor_value=sensor_value,
            detection_type=detection_type,
            confidence=confidence,
            raw_text=raw_text,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )


# 全局通知器实例
_notifier: Optional[FeishuNotifier] = None


def get_notifier() -> FeishuNotifier:
    """获取全局飞书通知器"""
    global _notifier
    if _notifier is None:
        import os
        webhook = os.environ.get("FEISHU_WEBHOOK_URL")
        _notifier = FeishuNotifier(webhook_url=webhook)
    return _notifier


def set_feishu_webhook(webhook_url: str):
    """设置飞书 Webhook URL（运行时）"""
    get_notifier().set_webhook(webhook_url)
