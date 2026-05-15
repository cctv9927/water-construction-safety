"""截帧服务模块"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, Callable, Awaitable

from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class CaptureTrigger(Enum):
    """截帧触发类型"""
    MANUAL = "manual"           # 手动触发
    SCHEDULED = "scheduled"     # 定时触发
    EVENT = "event"             # 事件触发（如检测到异常）
    MOTION = "motion"           # 运动检测触发


@dataclass
class FrameData:
    """帧数据"""
    stream_id: str
    raw_data: bytes
    width: int = 1920
    height: int = 1080
    timestamp: float = field(default_factory=time.time)


@dataclass
class CaptureRecord:
    """截帧记录"""
    capture_id: str
    stream_id: str
    trigger: CaptureTrigger
    file_path: str
    timestamp: float
    success: bool
    error_message: Optional[str] = None


@dataclass
class CaptureConfig:
    """截帧配置"""
    output_dir: str = "/tmp/frames"
    jpeg_quality: int = 85
    png_compress: int = 6
    max_storage_days: int = 7
    default_width: int = 1920
    default_height: int = 1080


class FrameCapture:
    """帧截取服务"""

    def __init__(self, config: Optional[CaptureConfig] = None):
        self.config = config or CaptureConfig()
        self._output_dir = Path(self.config.output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # 定时任务
        self._scheduled_tasks: dict[str, asyncio.Task] = {}
        self._capture_count = 0

    def _generate_capture_id(self) -> str:
        """生成截帧ID"""
        self._capture_count += 1
        return f"cap_{int(time.time() * 1000)}_{self._capture_count:04d}"

    def _raw_to_image(self, raw_data: bytes, width: int, height: int) -> Image.Image:
        """将原始RGB数据转换为PIL Image"""
        try:
            arr = np.frombuffer(raw_data, dtype=np.uint8)
            arr = arr.reshape((height, width, 3))
            return Image.fromarray(arr, mode='RGB')
        except Exception as e:
            logger.error(f"转换帧数据失败: {e}")
            raise

    async def capture_frame(
        self,
        frame: FrameData,
        trigger: CaptureTrigger = CaptureTrigger.MANUAL,
        format: str = "jpeg",
        event_type: Optional[str] = None
    ) -> CaptureRecord:
        """截取单帧"""
        capture_id = self._generate_capture_id()
        ts = datetime.fromtimestamp(frame.timestamp)

        # 构建文件名
        date_str = ts.strftime("%Y%m%d")
        time_str = ts.strftime("%H%M%S_%f")[:-3]
        ext = "jpg" if format == "jpeg" else "png"

        # 目录结构: output_dir/stream_id/date/
        sub_dir = self._output_dir / frame.stream_id / date_str
        sub_dir.mkdir(parents=True, exist_ok=True)

        # 文件名格式: stream_id_time_trigger_event.jpg
        event_suffix = f"_{event_type}" if event_type else ""
        filename = f"{frame.stream_id}_{time_str}_{trigger.value}{event_suffix}.{ext}"
        file_path = sub_dir / filename

        try:
            # 转换原始数据为图片
            img = self._raw_to_image(
                frame.raw_data,
                frame.width or self.config.default_width,
                frame.height or self.config.default_height
            )

            # 保存图片
            if format == "jpeg":
                img.save(file_path, "JPEG", quality=self.config.jpeg_quality)
            else:
                img.save(file_path, "PNG", compress_level=self.config.png_compress)

            record = CaptureRecord(
                capture_id=capture_id,
                stream_id=frame.stream_id,
                trigger=trigger,
                file_path=str(file_path),
                timestamp=frame.timestamp,
                success=True
            )

            logger.info(
                f"[Capture] {capture_id} 截帧成功: {file_path} "
                f"(触发:{trigger.value}, 大小:{img.size})"
            )
            return record

        except Exception as e:
            logger.error(f"[Capture] {capture_id} 截帧失败: {e}")
            return CaptureRecord(
                capture_id=capture_id,
                stream_id=frame.stream_id,
                trigger=trigger,
                file_path="",
                timestamp=frame.timestamp,
                success=False,
                error_message=str(e)
            )

    async def capture_scheduled(
        self,
        stream_id: str,
        interval_seconds: float,
        frame_callback: Callable[[], Awaitable[FrameData]],
        format: str = "jpeg"
    ):
        """定时截帧任务"""
        task_id = f"scheduled_{stream_id}"
        logger.info(f"[Scheduler] 启动定时截帧: {task_id}, 间隔={interval_seconds}s")

        while True:
            try:
                frame = await frame_callback()
                await self.capture_frame(frame, CaptureTrigger.SCHEDULED, format)
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                logger.info(f"[Scheduler] 停止定时截帧: {task_id}")
                break
            except Exception as e:
                logger.error(f"[Scheduler] 定时截帧异常: {e}")
                await asyncio.sleep(interval_seconds)

    def start_scheduled(
        self,
        stream_id: str,
        interval_seconds: float,
        frame_callback: Callable[[], Awaitable[FrameData]],
        format: str = "jpeg"
    ):
        """启动定时截帧任务"""
        task_id = f"scheduled_{stream_id}"
        if task_id in self._scheduled_tasks:
            logger.warning(f"[Scheduler] 任务 {task_id} 已存在，先停止")
            self._scheduled_tasks[task_id].cancel()

        task = asyncio.create_task(
            self.capture_scheduled(stream_id, interval_seconds, frame_callback, format)
        )
        self._scheduled_tasks[task_id] = task
        return task_id

    def stop_scheduled(self, stream_id: str):
        """停止定时截帧任务"""
        task_id = f"scheduled_{stream_id}"
        if task_id in self._scheduled_tasks:
            self._scheduled_tasks[task_id].cancel()
            del self._scheduled_tasks[task_id]
            logger.info(f"[Scheduler] 已停止定时截帧: {task_id}")

    def stop_all_scheduled(self):
        """停止所有定时截帧任务"""
        for task_id, task in list(self._scheduled_tasks.items()):
            task.cancel()
        self._scheduled_tasks.clear()
        logger.info("[Scheduler] 已停止所有定时截帧任务")

    def cleanup_old_files(self) -> int:
        """清理过期文件"""
        max_age = timedelta(days=self.config.max_storage_days)
        cutoff = datetime.now() - max_age
        removed = 0

        for file in self._output_dir.rglob("*"):
            if file.is_file():
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                if mtime < cutoff:
                    file.unlink()
                    removed += 1
                    logger.debug(f"[Cleanup] 删除过期文件: {file}")

        if removed > 0:
            logger.info(f"[Cleanup] 清理完成: 删除 {removed} 个过期文件")
        return removed

    def get_capture_stats(self) -> dict:
        """获取截帧统计"""
        total_files = sum(1 for _ in self._output_dir.rglob("*.jpg")) + \
                      sum(1 for _ in self._output_dir.rglob("*.png"))

        return {
            "output_dir": str(self._output_dir),
            "total_files": total_files,
            "scheduled_tasks": len(self._scheduled_tasks),
            "capture_count": self._capture_count,
        }
