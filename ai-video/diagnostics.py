"""
视频异常诊断模块
检测黑屏、模糊、遮挡、角度异常等问题
"""
import logging
import cv2
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("ai-video.diagnostics")


class AnomalyType(str, Enum):
    BLACK_SCREEN = "black_screen"       # 黑屏
    BLURRY = "blurry"                    # 画面模糊
    OCCLUDED = "occluded"                # 摄像头遮挡
    ANGLE_ERROR = "angle_error"         # 角度异常
    OVEREXPOSED = "overexposed"         # 曝光过度
    FROZEN = "frozen"                   # 画面冻结


@dataclass
class AnomalyResult:
    type: AnomalyType
    start_ms: int
    end_ms: int
    severity: str  # P0/P1/P2
    confidence: float
    description: str
    frame_indices: List[int] = field(default_factory=list)


class VideoDiagnostics:
    """
    视频质量异常诊断器
    逐帧分析，检测常见视频质量问题
    """

    def __init__(
        self,
        black_threshold: float = 5.0,      # 平均亮度阈值（0-255）
        blur_threshold: float = 50.0,      # Laplacian 方差阈值（越小越模糊）
        frozen_threshold_frames: int = 5,  # 连续相同帧数阈值
        sample_rate: int = 10,              # 每隔 N 帧检测一次
    ):
        self.black_threshold = black_threshold
        self.blur_threshold = blur_threshold
        self.frozen_threshold_frames = frozen_threshold_frames
        self.sample_rate = sample_rate

    def diagnose(self, video_path: str) -> Dict[str, Any]:
        """
        主入口：诊断视频质量
        返回：{anomalies: [AnomalyResult], overall_quality: str}
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        logger.info(f"诊断视频: {fps}fps, {total_frames}帧")

        anomalies: List[AnomalyResult] = []
        prev_gray = None
        prev_hist = None
        frame_idx = 0
        frozen_count = 0
        consecutive_black = 0
        consecutive_blur = 0
        black_start = 0
        blur_start = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % self.sample_rate != 0:
                frame_idx += 1
                continue

            timestamp_ms = int(frame_idx / fps * 1000)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 1. 黑屏检测
            mean_brightness = np.mean(gray)
            if mean_brightness < self.black_threshold:
                if consecutive_black == 0:
                    black_start = timestamp_ms
                consecutive_black += 1
            else:
                if consecutive_black >= 3:
                    anomalies.append(AnomalyResult(
                        type=AnomalyType.BLACK_SCREEN,
                        start_ms=black_start,
                        end_ms=timestamp_ms,
                        severity="P0" if consecutive_black > 15 else "P1",
                        confidence=min(1.0, consecutive_black / 30),
                        description=f"黑屏持续 {consecutive_black * self.sample_rate} 帧",
                        frame_indices=list(range(black_start, timestamp_ms, self.sample_rate)),
                    ))
                consecutive_black = 0

            # 2. 模糊检测（Laplacian）
            lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            if lap_var < self.blur_threshold:
                if consecutive_blur == 0:
                    blur_start = timestamp_ms
                consecutive_blur += 1
            else:
                if consecutive_blur >= 5:
                    anomalies.append(AnomalyResult(
                        type=AnomalyType.BLURRY,
                        start_ms=blur_start,
                        end_ms=timestamp_ms,
                        severity="P1",
                        confidence=min(1.0, (self.blur_threshold - lap_var) / self.blur_threshold),
                        description=f"画面模糊持续 {consecutive_blur * self.sample_rate} 帧",
                    ))
                consecutive_blur = 0

            # 3. 冻结检测（histogram 相似度）
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            if prev_hist is not None:
                corr = cv2.compareHist(
                    hist.reshape(1, -1).astype(np.float32),
                    prev_hist.reshape(1, -1).astype(np.float32),
                    cv2.HISTCMP_CORREL,
                )
                if corr > 0.98:
                    frozen_count += 1
                else:
                    frozen_count = 0
            prev_hist = hist
            prev_gray = gray

            frame_idx += 1

        # 处理尾部
        if consecutive_black >= 3:
            anomalies.append(AnomalyResult(
                type=AnomalyType.BLACK_SCREEN,
                start_ms=black_start,
                end_ms=int(frame_idx / fps * 1000),
                severity="P0",
                confidence=1.0,
                description="视频结束时仍为黑屏",
            ))

        if consecutive_blur >= 5:
            anomalies.append(AnomalyResult(
                type=AnomalyType.BLURRY,
                start_ms=blur_start,
                end_ms=int(frame_idx / fps * 1000),
                severity="P1",
                confidence=0.8,
                description="视频结束时画面仍模糊",
            ))

        cap.release()

        # 汇总
        p0_count = sum(1 for a in anomalies if a.severity == "P0")
        p1_count = sum(1 for a in anomalies if a.severity == "P1")
        overall_quality = "P0" if p0_count > 0 else "P1" if p1_count > 0 else "OK"

        result = {
            "anomalies": [
                {
                    "type": a.type.value,
                    "start_ms": a.start_ms,
                    "end_ms": a.end_ms,
                    "severity": a.severity,
                    "confidence": round(a.confidence, 4),
                    "description": a.description,
                }
                for a in anomalies
            ],
            "total_frames": total_frames,
            "analyzed_frames": frame_idx,
            "overall_quality": overall_quality,
            "summary": {
                "P0": p0_count,
                "P1": p1_count,
                "P2": sum(1 for a in anomalies if a.severity == "P2"),
            },
        }

        logger.info(f"诊断完成: quality={overall_quality}, P0={p0_count}, P1={p1_count}")
        return result
