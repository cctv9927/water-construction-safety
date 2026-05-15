"""
ByteTrack 目标追踪封装
支持 YOLOv8 检测结果到 Track 关联
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger("ai-video.tracker")

# ByteTrack 安装：pip install ByteTrack
# 注意：ByteTrack 依赖 torch，需要先安装 PyTorch
try:
    from ByteTrack.yolox.tracker.byte_tracker import BYTETracker
    BYTETRACK_AVAILABLE = True
except ImportError:
    BYTETRACK_AVAILABLE = False
    logger.warning("ByteTrack 未安装，将使用简化追踪逻辑（安装: pip install ByteTrack）")


class ByteTrackerWrapper:
    """
    目标追踪器封装
    输入：每帧检测结果 [{bbox, score, class_id}]
    输出：带 Track ID 的检测结果 [{bbox, score, class_id, track_id}]
    """

    def __init__(
        self,
        track_thresh: float = 0.5,
        track_buffer: int = 30,
        match_thresh: float = 0.8,
        frame_rate: int = 30,
    ):
        self.track_thresh = track_thresh
        self.track_buffer = track_buffer
        self.match_thresh = match_thresh
        self.frame_rate = frame_rate
        self.frame_id = 0

        if BYTETRACK_AVAILABLE:
            self.tracker = BYTETracker(
                track_thresh=track_thresh,
                track_buffer=track_buffer,
                match_thresh=match_thresh,
                frame_rate=frame_rate,
            )
            logger.info("ByteTrack 追踪器初始化完成（真实模式）")
        else:
            self.tracker = None
            logger.info("ByteTrack 追踪器初始化完成（简化模式）")
            self._simple_id_counter = 0
            self._simple_tracks: Dict[int, Dict] = {}

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        更新追踪器
        detections: [{bbox: [x1,y1,x2,y2], score: float, class_id: int, class_name: str}]
        返回：[{..., track_id: int}]
        """
        self.frame_id += 1

        if self.tracker is not None:
            return self._update_bytetrack(detections)
        else:
            return self._update_simple(detections)

    def _update_bytetrack(self, detections: List[Dict]) -> List[Dict]:
        """ByteTrack 真实追踪"""
        # 转换为 ByteTrack 格式：N x [x1,y1,x2,y2,score,class]
        if not detections:
            return []

        dets = np.array([
            [d["bbox"][0], d["bbox"][1], d["bbox"][2], d["bbox"][3],
             d["score"], d.get("class_id", 0)]
            for d in detections
        ], dtype=np.float64)

        online_targets = self.tracker.update(dets, (1080, 1920), (1080, 1920))

        results = []
        for t in online_targets:
            x1, y1, x2, y2 = t.tlbr
            results.append({
                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                "score": float(t.score),
                "class_id": int(t.cls),
                "class_name": detections[0].get("class_name", "unknown") if detections else "unknown",
                "track_id": int(t.track_id),
                "frame_id": self.frame_id,
                "timestamp_ms": int(self.frame_id / self.frame_rate * 1000),
            })
        return results

    def _update_simple(self, detections: List[Dict]) -> List[Dict]:
        """简化追踪：基于 IOU 匹配（无 ByteTrack 时使用）"""
        if not detections:
            return []

        results = []
        matched_ids = set()

        for det in detections:
            best_iou = 0
            best_id = None
            for tid, prev in self._simple_tracks.items():
                if tid in matched_ids:
                    continue
                iou = self._compute_iou(det["bbox"], prev["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_id = tid

            if best_id is not None and best_iou > 0.3:
                track_id = best_id
                matched_ids.add(best_id)
            else:
                track_id = self._simple_id_counter
                self._simple_id_counter += 1

            entry = {
                "bbox": det["bbox"],
                "score": det["score"],
                "class_id": det["class_id"],
                "class_name": det.get("class_name", "unknown"),
                "track_id": track_id,
                "frame_id": self.frame_id,
                "timestamp_ms": int(self.frame_id / self.frame_rate * 1000),
            }
            results.append(entry)
            self._simple_tracks[track_id] = entry

        # 清理过期轨迹（超过 90 帧无更新）
        active_ids = {r["track_id"] for r in results}
        self._simple_tracks = {
            k: v for k, v in self._simple_tracks.items()
            if k in active_ids or v.get("frame_id", 0) >= self.frame_id - 90
        }

        return results

    @staticmethod
    def _compute_iou(a: List, b: List) -> float:
        x1 = max(a[0], b[0])
        y1 = max(a[1], b[1])
        x2 = min(a[2], b[2])
        y2 = min(a[3], b[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area_a = (a[2] - a[0]) * (a[3] - a[1])
        area_b = (b[2] - b[0]) * (b[3] - b[1])
        return inter / (area_a + area_b - inter + 1e-6)

    def reset(self):
        self.frame_id = 0
        self._simple_tracks = {}
        self._simple_id_counter = 0
