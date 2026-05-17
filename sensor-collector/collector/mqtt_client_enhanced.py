"""
增强版 MQTT 异步订阅客户端
优化点：
1. QoS 2 支持（可靠消息投递）
2. 离线缓冲（断网不丢数据）
3. 自动重连 + 指数退避
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Callable, Optional, List
from dataclasses import dataclass, asdict
from threading import Lock
import aiomqtt

from .models import RawSensorData, ConfigModel

logger = logging.getLogger(__name__)


@dataclass
class BufferedMessage:
    """缓冲消息结构"""
    topic: str
    payload: str
    qos: int
    timestamp: float
    
    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "payload": self.payload,
            "qos": self.qos,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BufferedMessage":
        return cls(
            topic=data["topic"],
            payload=data["payload"],
            qos=data["qos"],
            timestamp=data["timestamp"],
        )


class OfflineBuffer:
    """
    离线缓冲区 - 断网时缓存消息，恢复后自动重传
    使用文件存储，进程重启后数据不丢失
    """
    
    def __init__(self, buffer_dir: str = "/tmp/sensor_buffer", max_size: int = 10000):
        self.buffer_dir = Path(buffer_dir)
        self.buffer_dir.mkdir(parents=True, exist_ok=True)
        self.buffer_file = self.buffer_dir / "offline_buffer.jsonl"
        self.max_size = max_size
        self._lock = Lock()
        self._count = 0
        
        # 初始化时加载已有缓冲
        self._load_count()
    
    def _load_count(self):
        """加载缓冲消息数量"""
        if self.buffer_file.exists():
            with open(self.buffer_file, "r") as f:
                self._count = sum(1 for _ in f)
    
    def push(self, message: BufferedMessage) -> bool:
        """添加消息到缓冲区"""
        if self._count >= self.max_size:
            logger.warning("[Buffer] 缓冲区已满，丢弃最旧的消息")
            self._remove_oldest()
        
        with self._lock:
            try:
                with open(self.buffer_file, "a") as f:
                    f.write(json.dumps(message.to_dict()) + "\n")
                self._count += 1
                return True
            except Exception as e:
                logger.error("[Buffer] 写入缓冲失败: %s", e)
                return False
    
    def pop_all(self) -> List[BufferedMessage]:
        """取出所有缓冲消息"""
        messages = []
        with self._lock:
            if not self.buffer_file.exists():
                return messages
            
            try:
                with open(self.buffer_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                messages.append(BufferedMessage.from_dict(json.loads(line)))
                            except json.JSONDecodeError:
                                pass
                
                # 清空缓冲区
                self.buffer_file.unlink(missing_ok=True)
                self._count = 0
                
            except Exception as e:
                logger.error("[Buffer] 读取缓冲失败: %s", e)
        
        return messages
    
    def _remove_oldest(self):
        """删除最旧的消息"""
        if not self.buffer_file.exists():
            return
        
        try:
            with open(self.buffer_file, "r") as f:
                lines = f.readlines()
            
            if len(lines) > 1:
                with open(self.buffer_file, "w") as f:
                    f.writelines(lines[1:])
                self._count -= 1
        except Exception as e:
            logger.error("[Buffer] 删除最旧消息失败: %s", e)
    
    def size(self) -> int:
        """获取缓冲区大小"""
        return self._count


class MQTTSubscriber:
    """
    增强版 MQTT 异步订阅客户端
    
    优化特性：
    - QoS 2 支持（ Exactly-Once 投递）
    - 离线缓冲（断网数据不丢失）
    - 指数退避重连
    - 连接状态监控
    """
    
    def __init__(self, config: ConfigModel.MQTTConfig):
        self.broker = config.broker
        self.client_id = config.client_id
        self.topics = config.topics
        self.qos = config.qos  # 可配置 QoS 0/1/2
        self.keepalive = config.keepalive
        self.reconnect_delay = config.reconnect_delay
        self._client: Optional[aiomqtt.Client] = None
        self._running = False
        self._offline_buffer: Optional[OfflineBuffer] = None
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        
        # 初始化离线缓冲
        self._init_offline_buffer(config)
    
    def _init_offline_buffer(self, config: ConfigModel.MQTTConfig):
        """初始化离线缓冲"""
        # 从 config 中读取缓冲配置（需要扩展 ConfigModel）
        buffer_enabled = getattr(config, 'offline_buffer', True)
        if buffer_enabled:
            self._offline_buffer = OfflineBuffer(
                buffer_dir="/tmp/sensor_buffer",
                max_size=getattr(config, 'max_buffer_size', 10000)
            )
            logger.info("[MQTT] 离线缓冲已启用，路径: /tmp/sensor_buffer")
    
    @property
    def is_connected(self) -> bool:
        """获取连接状态"""
        return self._connected
    
    async def subscribe(
        self,
        on_message: Callable[[RawSensorData], None],
    ) -> None:
        """
        订阅 MQTT 主题并将消息回调给 on_message。
        on_message 应为 async 函数。
        """
        self._running = True
        self._reconnect_attempts = 0
        
        while self._running:
            try:
                async with aiomqtt.Client(
                    identifier=self.client_id,
                    keepalive=self.keepalive,
                    # 启用清理会话=否，保持订阅
                    clean_session=False,
                ) as client:
                    self._client = client
                    self._connected = True
                    self._reconnect_attempts = 0
                    
                    # 订阅所有主题
                    for topic in self.topics:
                        await client.subscribe(topic, qos=self.qos)
                        logger.info("[MQTT] 订阅成功: topic=%s qos=%d", topic, self.qos)
                    
                    logger.info("[MQTT] 已连接到 broker: %s", self.broker)
                    
                    # 连接成功时，先发送离线缓冲区的消息
                    if self._offline_buffer and self._offline_buffer.size() > 0:
                        asyncio.create_task(self._flush_offline_buffer(client))
                    
                    # 消息循环
                    async for message in client.messages:
                        if not self._running:
                            break
                        
                        try:
                            payload = json.loads(message.payload.decode("utf-8"))
                            data = RawSensorData(**payload)
                            await on_message(data)
                        except json.JSONDecodeError:
                            logger.warning("[MQTT] JSON 解析失败 topic=%s", message.topic)
                        except Exception as e:
                            logger.error("[MQTT] 消息处理异常: %s", e)

            except aiomqtt.MqttError as exc:
                self._connected = False
                self._reconnect_attempts += 1
                
                # 指数退避计算
                delay = min(
                    self.reconnect_delay * (2 ** self._reconnect_attempts),
                    300  # 最大 5 分钟
                )
                
                if self._reconnect_attempts > self._max_reconnect_attempts:
                    logger.error(
                        "[MQTT] 重连次数超限 (%d/%d)，切换到离线缓冲模式",
                        self._reconnect_attempts, self._max_reconnect_attempts
                    )
                    # 继续尝试但降低频率
                    delay = 300
                
                logger.warning(
                    "[MQTT] 连接异常: %s, %.1f秒后重连 (attempt %d)...",
                    exc, delay, self._reconnect_attempts
                )
                await asyncio.sleep(delay)
                
            except Exception as exc:
                self._connected = False
                logger.error("[MQTT] 未知异常: %s", exc)
                await asyncio.sleep(self.reconnect_delay)
    
    async def _flush_offline_buffer(self, client: aiomqtt.Client):
        """发送离线缓冲区中的消息"""
        if not self._offline_buffer:
            return
        
        messages = self._offline_buffer.pop_all()
        if not messages:
            return
        
        logger.info("[MQTT] 开始发送离线缓冲消息，数量: %d", len(messages))
        
        success_count = 0
        fail_count = 0
        
        for msg in messages:
            try:
                client.publish(msg.topic, msg.payload.encode(), qos=msg.qos)
                success_count += 1
            except Exception as e:
                logger.error("[MQTT] 重发离线消息失败: %s", e)
                # 重新加入缓冲区
                self._offline_buffer.push(msg)
                fail_count += 1
        
        logger.info(
            "[MQTT] 离线缓冲发送完成: success=%d fail=%d",
            success_count, fail_count
        )
    
    def buffer_message(self, topic: str, payload: str, qos: int = 2):
        """
        将消息加入离线缓冲区（供外部调用）
        用于在离线时缓存需要发送的消息
        """
        if self._offline_buffer:
            message = BufferedMessage(
                topic=topic,
                payload=payload,
                qos=qos,
                timestamp=time.time(),
            )
            self._offline_buffer.push(message)
            logger.debug("[MQTT] 消息已加入离线缓冲: topic=%s", topic)
    
    def stop(self):
        """停止订阅"""
        self._running = False
        logger.info("[MQTT] 订阅已停止")
        
        # 记录最终缓冲状态
        if self._offline_buffer:
            logger.info(
                "[MQTT] 停止时缓冲区剩余消息: %d",
                self._offline_buffer.size()
            )
