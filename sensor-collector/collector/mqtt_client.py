"""MQTT 异步订阅客户端"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable, Optional

import aiomqtt

from .models import RawSensorData, ConfigModel

logger = logging.getLogger(__name__)


class MQTTSubscriber:
    """MQTT 异步订阅客户端"""

    def __init__(self, config: ConfigModel.MQTTConfig):
        self.broker = config.broker
        self.client_id = config.client_id
        self.topics = config.topics
        self.qos = config.qos
        self.keepalive = config.keepalive
        self.reconnect_delay = config.reconnect_delay
        self._client: Optional[aiomqtt.Client] = None
        self._running = False

    async def subscribe(
        self,
        on_message: Callable[[RawSensorData], None],
    ) -> None:
        """
        订阅 MQTT 主题并将消息回调给 on_message。
        on_message 应为 async 函数。
        """
        self._running = True
        while self._running:
            try:
                async with aiomqtt.Client(
                    identifier=self.client_id,
                    keepalive=self.keepalive,
                ) as client:
                    self._client = client
                    # 订阅所有主题
                    for topic in self.topics:
                        await client.subscribe(topic, qos=self.qos)
                        logger.info("[MQTT] 订阅成功: topic=%s qos=%d", topic, self.qos)

                    logger.info("[MQTT] 已连接到 broker: %s", self.broker)

                    # 消息循环
                    async for message in client.messages:
                        if not self._running:
                            break
                        await self._handle_message(message, on_message)

            except aiomqtt.MqttError as exc:
                logger.error("[MQTT] 连接异常: %s, %.1f秒后重连...", exc, self.reconnect_delay)
                await asyncio.sleep(self.reconnect_delay)
            except Exception as exc:
                logger.error("[MQTT] 未知异常: %s, %.1f秒后重连...", exc, self.reconnect_delay)
                await asyncio.sleep(self.reconnect_delay)

    async def _handle_message(
        self,
        message: aiomqtt.Message,
        on_message: Callable[[RawSensorData], None],
    ) -> None:
        """处理单条 MQTT 消息"""
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            data = RawSensorData(**payload)
            await on_message(data)
        except json.JSONDecodeError:
            logger.warning("[MQTT] JSON 解析失败 topic=%s payload=%s",
                           message.topic, message.payload[:100])
        except Exception as exc:
            logger.error("[MQTT] 消息处理异常 topic=%s error=%s", message.topic, exc)

    def stop(self):
        """停止订阅"""
        self._running = False
        logger.info("[MQTT] 订阅已停止")
