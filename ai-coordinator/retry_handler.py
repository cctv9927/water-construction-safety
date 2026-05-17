"""
增强版 AI Coordinator - 死信队列与重试机制
优化点：
1. 死信队列（处理失败消息的存储与分析）
2. 智能重试机制（指数退避）
3. 任务状态持久化
4. 告警历史追溯
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict
import httpx

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass
class TaskConfig:
    """任务处理配置"""
    max_retries: int = 3                    # 最大重试次数
    retry_base_delay: float = 1.0           # 重试基础延迟（秒）
    retry_max_delay: float = 60.0          # 最大延迟（秒）
    dead_letter_after_retries: bool = True  # 重试耗尽后是否进入死信队列
    dead_letter_ttl: int = 604800          # 死信保留时间（7天）


@dataclass
class Task:
    """任务结构"""
    task_id: str
    task_type: str                          # sensor / vision / voice / manual
    payload: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    error_message: Optional[str] = None
    result: Optional[Dict] = None
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
            "result": self.result,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            task_id=data["task_id"],
            task_type=data["task_type"],
            payload=data["payload"],
            status=TaskStatus(data["status"]),
            retry_count=data.get("retry_count", 0),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            completed_at=data.get("completed_at"),
            error_message=data.get("error_message"),
            result=data.get("result"),
        )


@dataclass
class DeadLetterEntry:
    """死信条目"""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    error_message: str
    retry_count: int
    created_at: float
    last_retry_at: float
    source_event: str                       # 原始事件类型
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
            "last_retry_at": self.last_retry_at,
            "source_event": self.source_event,
        }


class DeadLetterQueue:
    """
    死信队列
    
    存储处理失败的任务，支持：
    - 持久化存储
    - 定时清理
    - 重新入队
    - 统计分析
    """
    
    def __init__(
        self,
        storage_dir: str = "/tmp/dead_letters",
        max_size: int = 10000,
        ttl_seconds: int = 604800,
    ):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.queue_file = self.storage_dir / "dead_letters.jsonl"
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()
        
        # 内存索引
        self._entries: Dict[str, DeadLetterEntry] = {}
        self._load_from_disk()
    
    def _load_from_disk(self):
        """从磁盘加载死信队列"""
        if not self.queue_file.exists():
            return
        
        try:
            with open(self.queue_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = DeadLetterEntry(**json.loads(line))
                        self._entries[entry.task_id] = entry
            logger.info("[DLQ] 从磁盘加载 %d 条死信", len(self._entries))
        except Exception as e:
            logger.error("[DLQ] 加载死信失败: %s", e)
    
    async def add(
        self,
        task: Task,
        error_message: str,
        source_event: str,
    ) -> bool:
        """添加死信"""
        async with self._lock:
            # 检查是否已存在
            if task.task_id in self._entries:
                logger.warning("[DLQ] 任务 %s 已存在死信记录", task.task_id)
                return False
            
            # 清理过期条目
            await self._cleanup_expired()
            
            # 检查容量
            if len(self._entries) >= self.max_size:
                await self._remove_oldest()
            
            entry = DeadLetterEntry(
                task_id=task.task_id,
                task_type=task.task_type,
                payload=task.payload,
                error_message=error_message,
                retry_count=task.retry_count,
                created_at=task.created_at,
                last_retry_at=task.updated_at,
                source_event=source_event,
            )
            
            self._entries[task.task_id] = entry
            await self._persist_entry(entry)
            
            logger.warning(
                "[DLQ] 任务 %s 进入死信队列: %s (retry=%d)",
                task.task_id, error_message, task.retry_count
            )
            return True
    
    async def _persist_entry(self, entry: DeadLetterEntry):
        """持久化单条死信"""
        try:
            with open(self.queue_file, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception as e:
            logger.error("[DLQ] 持久化死信失败: %s", e)
    
    async def _cleanup_expired(self):
        """清理过期死信"""
        now = time.time()
        expired = [
            task_id for task_id, entry in self._entries.items()
            if now - entry.last_retry_at > self.ttl_seconds
        ]
        
        for task_id in expired:
            del self._entries[task_id]
        
        if expired:
            logger.info("[DLQ] 清理 %d 条过期死信", len(expired))
            await self._rewrite_disk()
    
    async def _remove_oldest(self):
        """删除最旧的死信"""
        if not self._entries:
            return
        
        oldest_task_id = min(
            self._entries.keys(),
            key=lambda k: self._entries[k].last_retry_at
        )
        del self._entries[oldest_task_id]
        await self._rewrite_disk()
    
    async def _rewrite_disk(self):
        """重写磁盘文件"""
        try:
            with open(self.queue_file, "w") as f:
                for entry in self._entries.values():
                    f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception as e:
            logger.error("[DLQ] 重写死信文件失败: %s", e)
    
    async def get(self, task_id: str) -> Optional[DeadLetterEntry]:
        """获取死信"""
        return self._entries.get(task_id)
    
    async def get_all(self) -> List[DeadLetterEntry]:
        """获取所有死信"""
        return list(self._entries.values())
    
    async def retry(self, task_id: str) -> Optional[Task]:
        """将死信重新转为任务"""
        entry = self._entries.get(task_id)
        if not entry:
            return None
        
        task = Task(
            task_id=entry.task_id,
            task_type=entry.task_type,
            payload=entry.payload,
            status=TaskStatus.PENDING,
            retry_count=0,  # 重置重试计数
            created_at=entry.created_at,
        )
        
        del self._entries[task_id]
        await self._rewrite_disk()
        
        logger.info("[DLQ] 死信 %s 重新入队", task_id)
        return task
    
    def get_stats(self) -> Dict:
        """获取死信统计"""
        by_type = defaultdict(int)
        for entry in self._entries.values():
            by_type[entry.task_type] += 1
        
        return {
            "total": len(self._entries),
            "by_type": dict(by_type),
            "oldest": min(
                (e.last_retry_at for e in self._entries.values()),
                default=time.time()
            ),
            "newest": max(
                (e.last_retry_at for e in self._entries.values()),
                default=time.time()
            ),
        }


class RetryHandler:
    """
    智能重试处理器
    
    特性：
    - 指数退避
    - 任务类型区分
    - 最大重试限制
    """
    
    def __init__(self, config: TaskConfig):
        self.config = config
        self._retry_delays: Dict[str, List[float]] = defaultdict(list)
    
    def calculate_delay(self, task_id: str, retry_count: int) -> float:
        """计算重试延迟（指数退避 + 抖动）"""
        import random
        
        # 指数退避
        delay = min(
            self.config.retry_base_delay * (2 ** retry_count),
            self.config.retry_max_delay
        )
        
        # 添加随机抖动（±25%）
        jitter = delay * 0.25 * (random.random() * 2 - 1)
        actual_delay = delay + jitter
        
        self._retry_delays[task_id].append(actual_delay)
        return actual_delay
    
    async def execute_with_retry(
        self,
        task: Task,
        handler_func,  # async function to execute
    ) -> tuple[bool, Any]:
        """
        执行任务，支持重试
        Returns: (success, result_or_error)
        """
        while task.retry_count < self.config.max_retries:
            try:
                result = await handler_func(task)
                
                # 成功
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = time.time()
                return True, result
            
            except Exception as e:
                task.retry_count += 1
                task.updated_at = time.time()
                task.error_message = str(e)
                
                if task.retry_count >= self.config.max_retries:
                    # 重试耗尽
                    if self.config.dead_letter_after_retries:
                        task.status = TaskStatus.DEAD_LETTER
                    else:
                        task.status = TaskStatus.FAILED
                    return False, str(e)
                
                # 计算延迟并等待
                delay = self.calculate_delay(task.task_id, task.retry_count)
                logger.warning(
                    "[Retry] 任务 %s 重试 %d/%d，%.1f秒后重试: %s",
                    task.task_id, task.retry_count, self.config.max_retries,
                    delay, str(e)
                )
                await asyncio.sleep(delay)
        
        return False, "重试次数耗尽"


class EnhancedEventProcessor:
    """
    增强版事件处理器
    
    整合：
    - 死信队列
    - 智能重试
    - 任务追踪
    """
    
    def __init__(
        self,
        task_config: Optional[TaskConfig] = None,
        dead_letter_queue: Optional[DeadLetterQueue] = None,
    ):
        self.task_config = task_config or TaskConfig()
        self.dlq = dead_letter_queue or DeadLetterQueue()
        self.retry_handler = RetryHandler(self.task_config)
        
        # 任务存储
        self._tasks: Dict[str, Task] = {}
        self._lock = asyncio.Lock()
        
        # 事件处理器映射
        self._handlers: Dict[str, callable] = {}
    
    def register_handler(self, event_type: str, handler: callable):
        """注册事件处理器"""
        self._handlers[event_type] = handler
        logger.info("[Processor] 注册事件处理器: %s", event_type)
    
    async def submit(
        self,
        task_type: str,
        payload: Dict[str, Any],
        task_id: Optional[str] = None,
    ) -> Task:
        """提交任务"""
        if not task_id:
            task_id = f"{task_type}_{int(time.time() * 1000)}"
        
        task = Task(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
        )
        
        async with self._lock:
            self._tasks[task_id] = task
        
        # 异步处理
        asyncio.create_task(self._process_task(task))
        
        return task
    
    async def _process_task(self, task: Task):
        """处理单个任务"""
        handler = self._handlers.get(task.task_type)
        if not handler:
            task.status = TaskStatus.FAILED
            task.error_message = f"未找到处理器: {task.task_type}"
            return
        
        async def execute():
            return await handler(task.payload)
        
        success, result = await self.retry_handler.execute_with_retry(
            task, execute
        )
        
        if success:
            task.status = TaskStatus.COMPLETED
            task.result = result
            logger.info("[Processor] 任务 %s 完成", task.task_id)
        else:
            if self.task_config.dead_letter_after_retries:
                task.status = TaskStatus.DEAD_LETTER
                await self.dlq.add(
                    task=task,
                    error_message=result,
                    source_event=task.task_type,
                )
            else:
                task.status = TaskStatus.FAILED
                task.error_message = result
            logger.error("[Processor] 任务 %s 失败: %s", task.task_id, result)
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    async def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        task = self._tasks.get(task_id)
        if not task:
            return None
        return task.to_dict()
    
    async def retry_dead_letter(self, task_id: str) -> bool:
        """重试死信任务"""
        task = await self.dlq.retry(task_id)
        if not task:
            return False
        
        async with self._lock:
            self._tasks[task.task_id] = task
        
        asyncio.create_task(self._process_task(task))
        return True
    
    def get_stats(self) -> Dict:
        """获取统计"""
        status_counts = defaultdict(int)
        for task in self._tasks.values():
            status_counts[task.status.value] += 1
        
        return {
            "tasks": dict(status_counts),
            "dead_letters": self.dlq.get_stats(),
        }
