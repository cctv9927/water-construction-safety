"""
Redis Stream 异步任务队列封装
"""
import json
import logging
from typing import Optional, Dict, Any
import redis.asyncio as redis

logger = logging.getLogger("ai-video.queue")


class RedisTaskQueue:
    """
    Redis Stream 异步任务队列
    - enqueue: 提交任务
    - dequeue: 消费任务（阻塞）
    - get_task_info: 查询任务状态
    """

    def __init__(self, host: str = "localhost", port: int = 6379, queue: str = "video:tasks"):
        self.host = host
        self.port = port
        self.queue = queue
        self._client: Optional[redis.Redis] = None
        self._consumer_group = f"{queue}:workers"
        self._consumer_name = f"worker-{id(self)}"

    async def connect(self):
        self._client = redis.Redis(host=self.host, port=self.port, decode_responses=True)
        try:
            await self._client.ping()
            logger.info(f"Redis 连接成功: {self.host}:{self.port}")
            # 创建消费者组
            try:
                await self._client.xgroup_create(self.queue, self._consumer_group, id="0", mkstream=True)
                logger.info(f"消费者组已创建: {self._consumer_group}")
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
                logger.debug(f"消费者组已存在: {self._consumer_group}")
        except Exception as e:
            logger.error(f"Redis 连接失败: {e}")
            raise

    async def close(self):
        if self._client:
            await self._client.close()

    def enqueue(self, task_id: str, payload: Dict[str, Any]) -> str:
        """提交任务到 Stream"""
        data = json.dumps(payload, ensure_ascii=False)
        msg_id = self._client.xadd(self.queue, {"task_id": task_id, "payload": data})
        logger.debug(f"任务入队: {task_id} -> msg_id={msg_id}")
        return task_id

    async def dequeue(self, timeout_ms: int = 5000) -> Optional[Dict[str, Any]]:
        """
        从 Stream 消费任务（XREADGROUP）
        返回: {task_id, payload, msg_id} 或 None
        """
        try:
            results = await self._client.xreadgroup(
                self._consumer_group,
                self._consumer_name,
                {self.queue: ">"},
                count=1,
                block=timeout_ms,
            )
            if not results:
                return None

            stream_name, messages = results[0]
            if not messages:
                return None

            msg_id, fields = messages[0]
            task_id = fields["task_id"]
            payload = json.loads(fields["payload"])

            # 记录处理中
            await self._client.hset(
                f"task:info:{task_id}",
                mapping={
                    "status": "processing",
                    "msg_id": msg_id,
                    "updated_at": str(int(__import__("time").time())),
                },
            )

            return {"task_id": task_id, "payload": payload, "msg_id": msg_id}
        except Exception as e:
            logger.error(f"dequeue 失败: {e}")
            return None

    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """查询任务信息（从 Hash）"""
        try:
            info = self._client.hgetall(f"task:info:{task_id}")
            if not info:
                return None
            return info
        except Exception:
            return None

    async def complete_task(self, task_id: str, result: Any):
        """标记任务完成"""
        import time
        await self._client.hset(
            f"task:info:{task_id}",
            mapping={
                "status": "completed",
                "result": json.dumps(result, ensure_ascii=False, default=str),
                "updated_at": str(int(time.time())),
            },
        )
        logger.info(f"任务完成: {task_id}")
