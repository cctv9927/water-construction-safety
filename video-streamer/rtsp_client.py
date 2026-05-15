"""RTSP 客户端模块 - 使用 ffmpeg-python 拉取视频流"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Awaitable

import ffmpeg

logger = logging.getLogger(__name__)


class StreamStatus(Enum):
    """流状态枚举"""
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"
    STOPPED = "stopped"


@dataclass
class StreamInfo:
    """流信息"""
    stream_id: str
    url: str
    status: StreamStatus = StreamStatus.IDLE
    fps: float = 0.0
    width: int = 0
    height: int = 0
    error_count: int = 0
    last_frame_time: Optional[float] = None


class RTSPClient:
    """RTSP 流客户端"""

    def __init__(
        self,
        stream_id: str,
        rtsp_url: str,
        timeout: int = 30,
        retry_interval: int = 5,
        max_retries: int = 3,
    ):
        self.stream_id = stream_id
        self.rtsp_url = rtsp_url
        self.timeout = timeout
        self.retry_interval = retry_interval
        self.max_retries = max_retries

        self._process: Optional[subprocess.Popen] = None
        self._status = StreamStatus.IDLE
        self._frame_callback: Optional[Callable[[bytes], Awaitable[None]]] = None
        self._running = False
        self._info = StreamInfo(stream_id=stream_id, url=rtsp_url)

    @property
    def status(self) -> StreamStatus:
        return self._status

    @property
    def info(self) -> StreamInfo:
        return self._info

    async def connect(
        self,
        frame_callback: Callable[[bytes], Awaitable[None]]
    ) -> bool:
        """连接到 RTSP 流并开始接收帧"""
        self._frame_callback = frame_callback
        self._running = True
        self._info.status = StreamStatus.CONNECTING

        return await self._do_connect()

    async def _do_connect(self) -> bool:
        """执行连接逻辑"""
        for attempt in range(self.max_retries + 1):
            if not self._running:
                return False

            try:
                self._status = StreamStatus.CONNECTING
                self._info.status = StreamStatus.CONNECTING
                logger.info(f"[RTSP-{self.stream_id}] 正在连接... (尝试 {attempt + 1}/{self.max_retries + 1})")

                # 使用 ffmpeg-python 构建拉流命令
                # 输出为原始帧数据 (rawvideo) 通过管道传输
                self._process = (
                    ffmpeg
                    .input(self.rtsp_url, 
                           rtsp_transport='tcp',
                           timeout=self.timeout * 1000000)  # ffmpeg-python 用微秒
                    .output('pipe:', 
                            format='rawvideo', 
                            pix_fmt='rgb24',
                            vcodec='copy')
                    .run_async(pipe_stdout=True, pipe_stderr=True)
                )

                # 验证进程启动成功
                if self._process.poll() is not None:
                    stderr = self._process.stderr.read().decode() if self._process.stderr else ""
                    raise RuntimeError(f"ffmpeg 进程启动失败: {stderr}")

                self._status = StreamStatus.CONNECTED
                self._info.status = StreamStatus.CONNECTED
                logger.info(f"[RTSP-{self.stream_id}] 连接成功")
                return True

            except Exception as e:
                logger.warning(f"[RTSP-{self.stream_id}] 连接失败: {e}")
                self._info.error_count += 1
                self._status = StreamStatus.ERROR
                self._info.status = StreamStatus.ERROR

                if attempt < self.max_retries:
                    logger.info(f"[RTSP-{self.stream_id}] {self.retry_interval}秒后重连...")
                    await asyncio.sleep(self.retry_interval)
                else:
                    logger.error(f"[RTSP-{self.stream_id}] 达到最大重试次数，放弃连接")
                    return False

        return False

    async def _read_frames_loop(self):
        """异步读取帧循环"""
        import struct

        # 假设常见分辨率 1920x1080 RGB24
        frame_size = 1920 * 1080 * 3

        while self._running and self._process and self._process.poll() is None:
            try:
                # 读取帧数据
                raw_frame = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self._process.stdout.read(frame_size)
                    ),
                    timeout=5.0
                )

                if not raw_frame:
                    logger.warning(f"[RTSP-{self.stream_id}] 流结束")
                    break

                # 更新帧率
                import time
                self._info.last_frame_time = time.time()

                # 回调处理帧
                if self._frame_callback:
                    await self._frame_callback(raw_frame)

            except asyncio.TimeoutError:
                logger.warning(f"[RTSP-{self.stream_id}] 读取帧超时")
                continue
            except Exception as e:
                logger.error(f"[RTSP-{self.stream_id}] 读取帧错误: {e}")
                break

        # 连接断开，尝试重连
        if self._running and self._info.error_count < self.max_retries:
            self._status = StreamStatus.RECONNECTING
            self._info.status = StreamStatus.RECONNECTING
            await self._do_connect()

    async def start_reading(self):
        """启动帧读取"""
        await self._read_frames_loop()

    def stop(self):
        """停止拉流"""
        self._running = False
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None

        self._status = StreamStatus.STOPPED
        self._info.status = StreamStatus.STOPPED
        logger.info(f"[RTSP-{self.stream_id}] 流已停止")


class RTSPManager:
    """RTSP 流管理器 - 管理多路并发流"""

    def __init__(self):
        self._streams: dict[str, RTSPClient] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    def add_stream(self, client: RTSPClient):
        """添加一个流"""
        self._streams[client.stream_id] = client
        logger.info(f"[Manager] 添加流 {client.stream_id}: {client.rtsp_url}")

    def remove_stream(self, stream_id: str):
        """移除一个流"""
        if stream_id in self._streams:
            self._streams[stream_id].stop()
            del self._streams[stream_id]
            if stream_id in self._tasks:
                self._tasks[stream_id].cancel()
                del self._tasks[stream_id]
            logger.info(f"[Manager] 移除流 {stream_id}")

    async def start_all(
        self,
        frame_callback: Callable[[str, bytes], Awaitable[None]]
    ) -> dict[str, bool]:
        """启动所有流，返回每个流的连接状态"""
        results = {}

        async def wrapped_callback(stream_id: str, frame: bytes):
            await frame_callback(stream_id, frame)

        for stream_id, client in self._streams.items():
            async def connect_stream(sid: str, c: RTSPClient):
                success = await c.connect(
                    lambda fid=sid, frame=None: wrapped_callback(fid, frame)
                )
                results[sid] = success
                if success:
                    self._tasks[sid] = asyncio.create_task(c.start_reading())

            await connect_stream(stream_id, client)

        return results

    async def start_stream(
        self,
        stream_id: str,
        frame_callback: Callable[[bytes], Awaitable[None]]
    ) -> bool:
        """启动单个流"""
        if stream_id not in self._streams:
            logger.error(f"[Manager] 流 {stream_id} 不存在")
            return False

        client = self._streams[stream_id]
        success = await client.connect(frame_callback)
        if success:
            self._tasks[stream_id] = asyncio.create_task(client.start_reading())
        return success

    def stop_stream(self, stream_id: str):
        """停止单个流"""
        self.remove_stream(stream_id)

    def stop_all(self):
        """停止所有流"""
        for stream_id in list(self._streams.keys()):
            self.remove_stream(stream_id)

    def get_stream_info(self, stream_id: str) -> Optional[StreamInfo]:
        """获取流信息"""
        return self._streams.get(stream_id, None)

    def list_streams(self) -> list[StreamInfo]:
        """列出所有流"""
        return [client.info for client in self._streams.values()]
