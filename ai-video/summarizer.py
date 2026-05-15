"""
视频浓缩模块
从长视频中提取关键片段，生成浓缩摘要
"""
import logging
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("ai-video.summarizer")


class VideoSummarizer:
    """
    视频浓缩器
    策略：
    1. 帧差法检测场景变化（动静检测）
    2. 安全事件帧提取（AI Vision 检测到的风险帧优先保留）
    3. 时间均匀采样 + 事件加权
    4. 输出关键片段时间戳
    """

    def __init__(
        self,
        min_segments: int = 5,
        max_segments: int = 20,
        motion_threshold: float = 0.05,
        frame_sample_rate: int = 5,
    ):
        self.min_segments = min_segments
        self.max_segments = max_segments
        self.motion_threshold = motion_threshold  # 帧差阈值（画面变化程度）
        self.frame_sample_rate = frame_sample_rate  # 每隔 N 帧分析一次

    def summarize(
        self,
        video_path: str,
        event_frames: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        主入口：视频浓缩
        video_path: 视频文件路径或 URL
        event_frames: 安全事件帧列表 [{timestamp_ms, severity, description}]
        返回：{segments: [{start_ms, end_ms, reason}], summary_video: str}
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_ms = int(total_frames / fps * 1000)

        logger.info(f"视频信息: {fps}fps, {total_frames}帧, {duration_ms}ms")

        motion_scores: List[Tuple[int, float]] = []  # (frame_idx, motion_score)
        prev_gray = None

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % self.frame_sample_rate == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)

                if prev_gray is not None:
                    diff = cv2.absdiff(prev_gray, gray)
                    score = np.mean(diff) / 255.0
                    motion_scores.append((frame_idx, score))

                prev_gray = gray

            frame_idx += 1

        cap.release()

        # 合并事件帧与动态帧
        segments = self._extract_segments(motion_scores, event_frames, fps)

        logger.info(f"视频浓缩完成: {len(segments)} 个关键片段")
        return {
            "segments": segments,
            "total_frames": total_frames,
            "duration_ms": duration_ms,
            "fps": fps,
        }

    def _extract_segments(
        self,
        motion_scores: List[Tuple[int, float]],
        event_frames: Optional[List[Dict]],
        fps: float,
    ) -> List[Dict[str, Any]]:
        """提取关键片段"""
        # 1. 找运动剧烈帧（高于阈值）
        threshold = self.motion_threshold
        active_frames = [f for f, s in motion_scores if s > threshold]

        # 2. 按时间分桶（每段 10 秒）
        bucket_size_frames = int(10 * fps / self.frame_sample_rate)
        buckets: List[List[int]] = []
        current = []
        last_bucket_idx = -1

        for fidx in active_frames:
            bucket_idx = fidx // bucket_size_frames
            if bucket_idx != last_bucket_idx:
                if current:
                    buckets.append(current)
                current = [fidx]
                last_bucket_idx = bucket_idx
            else:
                current.append(fidx)

        if current:
            buckets.append(current)

        # 3. 每桶取最具代表性的帧
        segments = []
        for bucket in buckets:
            if not bucket:
                continue
            # 取分数最高的帧为代表
            best = max(bucket, key=lambda f: next((s for fi, s in motion_scores if fi == f), 0))
            # 转换为时间戳（ms）
            start_ms = int((best - self.frame_sample_rate * 2) / fps * 1000)
            end_ms = int((best + self.frame_sample_rate * 2) / fps * 1000)
            start_ms = max(0, start_ms)
            segments.append({
                "start_ms": start_ms,
                "end_ms": end_ms,
                "frame_idx": best,
                "reason": "motion_detected",
                "severity": "P1",
            })

        # 4. 事件帧加权（高优先级）
        if event_frames:
            for ev in event_frames:
                ts = ev.get("timestamp_ms", 0)
                severity = ev.get("severity", "P1")
                # 合并或新增
                merged = False
                for seg in segments:
                    if abs(seg["start_ms"] - ts) < 3000:
                        seg["reason"] = ev.get("description", "safety_event")
                        seg["severity"] = severity
                        merged = True
                        break
                if not merged:
                    segments.append({
                        "start_ms": ts,
                        "end_ms": ts + 5000,
                        "frame_idx": 0,
                        "reason": ev.get("description", "safety_event"),
                        "severity": severity,
                    })

        # 5. 按时间排序
        segments.sort(key=lambda x: x["start_ms"])

        # 6. 截断/补足
        segments = segments[:self.max_segments]
        while len(segments) < self.min_segments and segments:
            last = segments[-1]
            segments.append({
                "start_ms": last["end_ms"],
                "end_ms": last["end_ms"] + 5000,
                "frame_idx": 0,
                "reason": "coverage_fill",
                "severity": "P2",
            })

        return segments
