"""
Redis Stream 订阅客户端
- 订阅各 Agent 的事件流
- 提供可靠的消息消费
"""
import asyncio
import json
import logging
from typing import Callable, Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class StreamMessage:
    """Stream 消息"""
    stream: str
    message_id: str
    data: Dict[str, Any]


class RedisStreamClient:
    """Redis Stream 客户端"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
    ):
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self._client: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._consumers: Dict[str, asyncio.Task] = {}
        self._running = False

    async def connect(self):
        """建立连接"""
        if self._client:
            return
        
        self._client = redis.Redis(
            host=self.host,
            port=self.port,
            password=self.password,
            db=self.db,
            decode_responses=True,
        )
        
        # 测试连接
        await self._client.ping()
        logger.info(f"Connected to Redis at {self.host}:{self.port}")

    async def disconnect(self):
        """断开连接"""
        self._running = False
        
        # 取消所有消费者
        for task in self._consumers.values():
            task.cancel()
        
        if self._pubsub:
            await self._pubsub.close()
        
        if self._client:
            await self._client.close()
        
        logger.info("Disconnected from Redis")

    async def xread(
        self,
        streams: List[str],
        group: Optional[str] = None,
        consumer: Optional[str] = None,
        count: int = 10,
        block: int = 5000,
    ) -> List[StreamMessage]:
        """
        读取 Stream 消息
        
        Args:
            streams: Stream 名称列表
            group: 消费者组（用于消息组模式）
            consumer: 消费者名称
            count: 每次读取的最大消息数
            block: 阻塞超时（毫秒）
            
        Returns:
            消息列表
        """
        if not self._client:
            await self.connect()
        
        messages = []
        
        try:
            if group and consumer:
                # 消费者组模式
                result = await self._client.xreadgroup(
                    groupname=group,
                    consumername=consumer,
                    streams={s: ">" for s in streams},
                    count=count,
                    block=block,
                )
            else:
                # 普通模式
                result = await self._client.xread(
                    streams={s: "0" for s in streams},
                    count=count,
                    block=block,
                )
            
            for stream_name, stream_messages in result:
                for message_id, data in stream_messages:
                    messages.append(StreamMessage(
                        stream=stream_name,
                        message_id=message_id,
                        data=data,
                    ))
        
        except redis.ResponseError as e:
            if "NOGROUP" in str(e) and group:
                # 消费者组不存在，创建
                for stream in streams:
                    try:
                        await self._client.xgroup_create(stream, group, id="0", mkstream=True)
                        logger.info(f"Created consumer group '{group}' for stream '{stream}'")
                    except redis.ResponseError:
                        pass
        
        return messages

    async def xadd(self, stream: str, data: Dict[str, Any], maxlen: int = 1000) -> str:
        """
        添加消息到 Stream
        
        Args:
            stream: Stream 名称
            data: 消息数据
            maxlen: 最大长度
            
        Returns:
            消息 ID
        """
        if not self._client:
            await self.connect()
        
        # 序列化数据
        serialized = {k: json.dumps(v) if not isinstance(v, str) else v for k, v in data.items()}
        
        message_id = await self._client.xadd(
            stream,
            serialized,
            maxlen=maxlen,
            approximate=True,
        )
        
        return message_id

    async def xack(self, stream: str, group: str, *message_ids: str) -> int:
        """
        确认消息
        
        Args:
            stream: Stream 名称
            group: 消费者组
            message_ids: 消息 ID 列表
            
        Returns:
            确认的消息数
        """
        if not self._client:
            await self.connect()
        
        return await self._client.xack(stream, group, *message_ids)

    async def start_consumer(
        self,
        stream: str,
        group: str,
        consumer: str,
        handler: Callable[[StreamMessage], Any],
        count: int = 10,
    ):
        """
        启动消费者
        
        Args:
            stream: Stream 名称
            group: 消费者组
            consumer: 消费者名称
            handler: 消息处理函数
            count: 每次处理的消息数
        """
        consumer_key = f"{stream}:{group}:{consumer}"
        
        if consumer_key in self._consumers:
            logger.warning(f"Consumer {consumer_key} already running")
            return
        
        self._running = True
        self._consumers[consumer_key] = asyncio.create_task(
            self._consume_loop(stream, group, consumer, handler, count)
        )
        logger.info(f"Started consumer: {consumer_key}")

    async def _consume_loop(
        self,
        stream: str,
        group: str,
        consumer: str,
        handler: Callable[[StreamMessage], Any],
        count: int,
    ):
        """消费循环"""
        while self._running:
            try:
                messages = await self.xread(
                    streams=[stream],
                    group=group,
                    consumer=consumer,
                    count=count,
                )
                
                for msg in messages:
                    try:
                        # 处理消息
                        result = handler(msg)
                        if asyncio.iscoroutine(result):
                            await result
                        
                        # 确认消息
                        await self.xack(stream, group, msg.message_id)
                        
                    except Exception as e:
                        logger.error(f"Handler error for {msg.message_id}: {e}")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Consumer loop error: {e}")
                await asyncio.sleep(1)

    async def stop_consumer(self, consumer_key: str):
        """停止消费者"""
        if consumer_key in self._consumers:
            self._consumers[consumer_key].cancel()
            await self._consumers[consumer_key]
            del self._consumers[consumer_key]
            logger.info(f"Stopped consumer: {consumer_key}")


# 全局 Redis 客户端
_redis_client: Optional[RedisStreamClient] = None


def get_redis_client() -> RedisStreamClient:
    """获取全局 Redis 客户端"""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisStreamClient()
    return _redis_client


# 预定义的 Stream 名称
STREAMS = {
    "SENSOR_ALERTS": "water:alerts:sensor",
    "VISION_ALERTS": "water:alerts:vision",
    "VOICE_ALERTS": "water:alerts:voice",
    "COORDINATOR": "water:coordinator:events",
    "ACTIONS": "water:actions",
}

# 消费者组
GROUPS = {
    "COORDINATOR_GROUP": "coordinator-group",
}
