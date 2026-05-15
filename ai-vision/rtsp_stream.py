"""
RTSP 视频流推理模块
支持摄像头 RTSP 流实时目标检测，替代静态图片检测
"""
import asyncio
import logging
import time
import threading
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

import cv2
import numpy as np

logger = logging.getLogger("rtsp-detector")


class StreamStatus(str, Enum):
    """流状态"""
    IDLE = "idle"
    CONNECTING = "connecting"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class StreamConfig:
    """流配置"""
    rtsp_url: str
    name: str = "camera"
    interval_seconds: float = 1.0  # 检测间隔
    confidence: float = 0.5
    max_detections: int = 50
    reconnect_attempts: int = 5
    reconnect_delay: float = 3.0


@dataclass
class DetectionResult:
    """检测结果"""
    camera_id: str
    timestamp: str
    frame_time_ms: float
    inference_time_ms: float
    detections: List[Dict[str, Any]]
    count: int
    status: str
    error: Optional[str] = None


class RTSPStream:
    """
    单路 RTSP 流处理器

    使用方式：
    1. 创建实例：stream = RTSPStream(config)
    2. 注册回调：stream.on_detection(callback_func)
    3. 启动：stream.start()
    4. 停止：stream.stop()
    """

    def __init__(
        self,
        config: StreamConfig,
        detector: Any,  # YOLOv8ONNX 实例
    ):
        self.config = config
        self.detector = detector
        self.status = StreamStatus.IDLE
        self.cap: Optional[cv2.VideoCapture] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.callbacks: List[Callable] = []
        self.last_detection_time = 0.0
        self.total_frames = 0
        self.error_count = 0

    def on_detection(self, callback: Callable[[DetectionResult], None]):
        """注册检测结果回调"""
        self.callbacks.append(callback)

    def _notify(self, result: DetectionResult):
        for cb in self.callbacks:
            try:
                cb(result)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def _connect(self) -> bool:
        """建立 RTSP 连接"""
        self.cap = cv2.VideoCapture(self.config.rtsp_url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 低延迟
        if not self.cap.isOpened():
            self.status = StreamStatus.ERROR
            logger.error(f"[{self.config.name}] RTSP 连接失败: {self.config.rtsp_url}")
            return False
        logger.info(f"[{self.config.name}] RTSP 连接成功: {self.config.rtsp_url}")
        self.status = StreamStatus.RUNNING
        return True

    def _disconnect(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    def _grab_frame(self) -> Optional[np.ndarray]:
        """从 RTSP 流抓取一帧"""
        if not self.cap or not self.cap.isOpened():
            return None
        ret, frame = self.cap.read()
        if not ret:
            self.error_count += 1
            logger.warning(f"[{self.config.name}] 帧读取失败 (累计 {self.error_count} 次)")
            return None
        self.error_count = 0
        self.total_frames += 1
        return frame

    def _detection_loop(self):
        """检测主循环（在独立线程中运行）"""
        logger.info(f"[{self.config.name}] 检测线程启动，间隔 {self.config.interval_seconds}s")

        consecutive_errors = 0

        while self.running:
            # 读取帧
            frame = self._grab_frame()

            if frame is None:
                consecutive_errors += 1
                if consecutive_errors >= self.config.reconnect_attempts:
                    logger.warning(f"[{self.config.name}] 连续{consecutive_errors}次失败，尝试重连...")
                    self._disconnect()
                    time.sleep(self.config.reconnect_delay)
                    if not self._connect():
                        logger.error(f"[{self.config.name}] 重连失败，停止")
                        self.status = StreamStatus.ERROR
                        break
                    consecutive_errors = 0
                continue

            consecutive_errors = 0

            # 节流控制
            now = time.time()
            if now - self.last_detection_time < self.config.interval_seconds:
                continue

            # 执行检测
            try:
                frame_read_start = time.perf_counter()
                results = self.detector.detect(
                    frame,
                    conf_threshold=self.config.confidence,
                    max_detections=self.config.max_detections,
                )
                inference_ms = (time.perf_counter() - frame_read_start) * 1000

                # 过滤低置信度
                filtered = [
                    {
                        "class_id": r["class_id"],
                        "class_name": r["class_name"],
                        "confidence": round(float(r["confidence"]), 4),
                        "bbox": [int(x) for x in r["bbox"]],
                    }
                    for r in results
                ]

                result = DetectionResult(
                    camera_id=self.config.name,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    frame_time_ms=0.0,
                    inference_time_ms=round(inference_ms, 2),
                    detections=filtered,
                    count=len(filtered),
                    status="success",
                )

                self._notify(result)
                self.last_detection_time = now

                if filtered:
                    logger.info(
                        f"[{self.config.name}] 检测: {len(filtered)} 个目标 "
                        f"(推理 {inference_ms:.1f}ms)"
                    )

            except Exception as e:
                logger.error(f"[{self.config.name}] 检测异常: {e}")
                self._notify(DetectionResult(
                    camera_id=self.config.name,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    frame_time_ms=0.0,
                    inference_time_ms=0.0,
                    detections=[],
                    count=0,
                    status="error",
                    error=str(e),
                ))

        self.status = StreamStatus.STOPPED
        self._disconnect()
        logger.info(f"[{self.config.name}] 检测线程退出")

    def start(self):
        """启动流处理"""
        if self.running:
            logger.warning(f"[{self.config.name}] 流已在运行")
            return

        if not self._connect():
            return

        self.running = True
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()
        self.status = StreamStatus.RUNNING

    def stop(self):
        """停止流处理"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        self._disconnect()
        self.status = StreamStatus.STOPPED

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.config.name,
            "status": self.status.value,
            "rtsp_url": self.config.rtsp_url,
            "total_frames": self.total_frames,
            "error_count": self.error_count,
            "running": self.running,
        }


class RTSPStreamManager:
    """
    RTSP 流管理器
    管理多路摄像头同时检测
    """

    def __init__(self, detector: Any):
        self.detector = detector
        self.streams: Dict[str, RTSPStream] = {}

    def add_stream(self, config: StreamConfig) -> str:
        """
        添加一路 RTSP 流

        Args:
            config: 流配置

        Returns:
            流名称（camera_id）
        """
        if config.name in self.streams:
            logger.warning(f"流 {config.name} 已存在，先停止再添加")
            self.streams[config.name].stop()

        stream = RTSPStream(config, self.detector)
        self.streams[config.name] = stream
        logger.info(f"流已添加: {config.name} -> {config.rtsp_url}")
        return config.name

    def start_stream(self, name: str):
        """启动指定流"""
        if name not in self.streams:
            raise ValueError(f"流不存在: {name}")
        self.streams[name].start()

    def start_all(self):
        """启动所有流"""
        for stream in self.streams.values():
            stream.start()

    def stop_stream(self, name: str):
        """停止指定流"""
        if name in self.streams:
            self.streams[name].stop()

    def stop_all(self):
        """停止所有流"""
        for stream in self.streams.values():
            stream.stop()

    def get_all_status(self) -> List[Dict[str, Any]]:
        return [s.get_status() for s in self.streams.values()]

    def remove_stream(self, name: str):
        """移除并停止流"""
        if name in self.streams:
            self.streams[name].stop()
            del self.streams[name]

    def __len__(self):
        return len(self.streams)
