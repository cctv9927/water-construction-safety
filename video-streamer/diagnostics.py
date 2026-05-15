"""视频质量诊断模块 - 黑屏检测、遮挡检测"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, Awaitable

import numpy as np

logger = logging.getLogger(__name__)


class DiagnosticType(Enum):
    """诊断类型"""
    BLACK_SCREEN = "black_screen"      # 黑屏
    FULL_OBFUSCATION = "full_obfuscation"  # 完全遮挡
    PARTIAL_OBFUSCATION = "partial_obfuscation"  # 部分遮挡
    LOW_BRIGHTNESS = "low_brightness"  # 低亮度
    NOISE = "noise"                    # 噪点过多
    FREEZE = "freeze"                 # 画面冻结


@dataclass
class DiagnosticResult:
    """诊断结果"""
    stream_id: str
    diagnostic_type: DiagnosticType
    timestamp: float
    severity: str  # "info", "warning", "critical"
    value: float
    threshold: float
    message: str
    frame_avg_brightness: Optional[float] = None


@dataclass
class DiagnosticConfig:
    """诊断配置"""
    brightness_threshold: float = 20.0      # 黑屏亮度阈值 (0-255)
    occlusion_ratio: float = 0.8            # 遮挡比例阈值
    check_interval: float = 5.0             # 诊断间隔(秒)
    consecutive_count: int = 3               # 连续异常次数才报警
    freeze_threshold: float = 2.0           # 冻结阈值(秒)


class FrameAnalyzer:
    """帧分析器"""

    @staticmethod
    def calculate_brightness(raw_data: bytes, width: int, height: int) -> float:
        """计算帧平均亮度 (0-255)"""
        try:
            arr = np.frombuffer(raw_data, dtype=np.uint8)
            arr = arr.reshape((height, width, 3))
            # RGB转灰度: Y = 0.299*R + 0.587*G + 0.114*B
            gray = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
            return float(np.mean(gray))
        except Exception as e:
            logger.error(f"计算亮度失败: {e}")
            return 0.0

    @staticmethod
    def detect_occlusion(raw_data: bytes, width: int, height: int) -> float:
        """检测画面遮挡比例"""
        try:
            arr = np.frombuffer(raw_data, dtype=np.uint8)
            arr = arr.reshape((height, width, 3))

            # 简化的遮挡检测：检测大面积纯色区域
            # 计算每个像素与均值的差异
            mean_color = np.mean(arr, axis=(0, 1))
            diff = np.abs(arr - mean_color)
            max_diff = np.max(diff, axis=2)

            # 差异小于阈值的区域认为是纯色（可能是遮挡物）
            occlusion_threshold = 10
            occlusion_pixels = np.sum(max_diff < occlusion_threshold)
            total_pixels = width * height

            return occlusion_pixels / total_pixels
        except Exception as e:
            logger.error(f"检测遮挡失败: {e}")
            return 0.0

    @staticmethod
    def detect_noise(raw_data: bytes, width: int, height: int) -> float:
        """检测噪点比例"""
        try:
            arr = np.frombuffer(raw_data, dtype=np.uint8)
            arr = arr.reshape((height, width, 3))

            # 简化的噪点检测：计算局部方差
            # 使用简单的梯度检测
            gy = np.abs(np.diff(arr, axis=0))
            gx = np.abs(np.diff(arr, axis=1))

            # 高频成分多表示噪点多
            noise_score = np.mean(gy) + np.mean(gx)
            # 归一化到 0-1
            return min(noise_score / 50.0, 1.0)
        except Exception as e:
            logger.error(f"检测噪点失败: {e}")
            return 0.0


class VideoDiagnostics:
    """视频诊断服务"""

    def __init__(
        self,
        config: Optional[DiagnosticConfig] = None,
        alert_callback: Optional[Callable[[DiagnosticResult], Awaitable[None]]] = None
    ):
        self.config = config or DiagnosticConfig()
        self.alert_callback = alert_callback
        self.analyzer = FrameAnalyzer()

        # 流状态追踪
        self._stream_states: dict[str, dict] = {}
        self._running = False
        self._check_task: Optional[asyncio.Task] = None

    def init_stream(self, stream_id: str, width: int = 1920, height: int = 1080):
        """初始化流诊断状态"""
        self._stream_states[stream_id] = {
            "width": width,
            "height": height,
            "last_frame_time": time.time(),
            "last_brightness": None,
            "consecutive_black": 0,
            "consecutive_occlusion": 0,
            "last_frame_hash": None,
            "freeze_count": 0,
        }
        logger.info(f"[Diagnostics] 初始化流 {stream_id}: {width}x{height}")

    async def analyze_frame(
        self,
        stream_id: str,
        raw_data: bytes,
        width: int = 1920,
        height: int = 1080
    ) -> list[DiagnosticResult]:
        """分析帧并返回诊断结果"""
        if stream_id not in self._stream_states:
            self.init_stream(stream_id, width, height)

        state = self._stream_states[stream_id]
        current_time = time.time()
        results = []

        # 更新宽高
        state["width"] = width
        state["height"] = height

        # 1. 黑屏检测
        brightness = self.analyzer.calculate_brightness(raw_data, width, height)
        state["last_brightness"] = brightness

        if brightness < self.config.brightness_threshold:
            state["consecutive_black"] += 1
            if state["consecutive_black"] >= self.config.consecutive_count:
                result = DiagnosticResult(
                    stream_id=stream_id,
                    diagnostic_type=DiagnosticType.BLACK_SCREEN,
                    timestamp=current_time,
                    severity="critical" if brightness < 5 else "warning",
                    value=brightness,
                    threshold=self.config.brightness_threshold,
                    message=f"检测到黑屏/画面过暗 (亮度: {brightness:.1f})",
                    frame_avg_brightness=brightness
                )
                results.append(result)
                logger.warning(f"[{stream_id}] 黑屏告警: 亮度={brightness:.1f}")
        else:
            state["consecutive_black"] = 0

        # 2. 遮挡检测
        occlusion_ratio = self.analyzer.detect_occlusion(raw_data, width, height)
        if occlusion_ratio > self.config.occlusion_ratio:
            state["consecutive_occlusion"] += 1
            if state["consecutive_occlusion"] >= self.config.consecutive_count:
                diag_type = DiagnosticType.FULL_OBFUSCATION if occlusion_ratio > 0.95 else DiagnosticType.PARTIAL_OBFUSCATION
                result = DiagnosticResult(
                    stream_id=stream_id,
                    diagnostic_type=diag_type,
                    timestamp=current_time,
                    severity="critical" if occlusion_ratio > 0.9 else "warning",
                    value=occlusion_ratio,
                    threshold=self.config.occlusion_ratio,
                    message=f"检测到画面遮挡 (遮挡比例: {occlusion_ratio:.1%})",
                    frame_avg_brightness=brightness
                )
                results.append(result)
                logger.warning(f"[{stream_id}] 遮挡告警: 遮挡={occlusion_ratio:.1%}")
        else:
            state["consecutive_occlusion"] = 0

        # 3. 冻结检测（基于帧哈希/时间）
        if state["last_frame_time"]:
            frame_delta = current_time - state["last_frame_time"]
            if frame_delta > self.config.freeze_threshold:
                state["freeze_count"] += 1
                if state["freeze_count"] >= self.config.consecutive_count:
                    result = DiagnosticResult(
                        stream_id=stream_id,
                        diagnostic_type=DiagnosticType.FREEZE,
                        timestamp=current_time,
                        severity="warning",
                        value=frame_delta,
                        threshold=self.config.freeze_threshold,
                        message=f"检测到画面冻结 (持续时间: {frame_delta:.1f}s)",
                        frame_avg_brightness=brightness
                    )
                    results.append(result)
                    logger.warning(f"[{stream_id}] 画面冻结: {frame_delta:.1f}s")
        else:
            state["freeze_count"] = 0

        state["last_frame_time"] = current_time

        # 发送告警
        if results and self.alert_callback:
            for result in results:
                try:
                    await self.alert_callback(result)
                except Exception as e:
                    logger.error(f"发送告警失败: {e}")

        return results

    def get_stream_status(self, stream_id: str) -> Optional[dict]:
        """获取流诊断状态"""
        if stream_id not in self._stream_states:
            return None

        state = self._stream_states[stream_id]
        return {
            "stream_id": stream_id,
            "width": state["width"],
            "height": state["height"],
            "last_brightness": state["last_brightness"],
            "consecutive_black": state["consecutive_black"],
            "consecutive_occlusion": state["consecutive_occlusion"],
            "freeze_count": state["freeze_count"],
            "is_alerting": (
                state["consecutive_black"] >= self.config.consecutive_count or
                state["consecutive_occlusion"] >= self.config.consecutive_count or
                state["freeze_count"] >= self.config.consecutive_count
            )
        }

    def list_stream_status(self) -> list[dict]:
        """列出所有流状态"""
        return [self.get_stream_status(sid) for sid in self._stream_states.keys()]

    async def start_monitoring(
        self,
        frame_provider: Callable[[str], tuple[bytes, int, int]]
    ):
        """启动周期性监控"""
        self._running = True
        logger.info("[Diagnostics] 启动视频质量监控")

        while self._running:
            await asyncio.sleep(self.config.check_interval)

            for stream_id in list(self._stream_states.keys()):
                try:
                    frame_data, width, height = frame_provider(stream_id)
                    if frame_data:
                        await self.analyze_frame(stream_id, frame_data, width, height)
                except Exception as e:
                    logger.debug(f"监控帧获取失败 {stream_id}: {e}")

    def stop_monitoring(self):
        """停止监控"""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
        logger.info("[Diagnostics] 已停止视频质量监控")
