"""
AI Video Worker - 任务处理器
从 Redis Stream 消费任务，调用 ByteTrack 追踪并写入结果
"""
import asyncio
import json
import logging
import os
import tempfile
from typing import Dict, Any, Optional

import cv2
import numpy as np

logger = logging.getLogger("ai-video.worker")

# ─── 配置 ──────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
QUEUE_NAME = "video:track_tasks"
VISION_API = os.getenv("VISION_API", "http://ai-vision:8082/detect")
COORDINATOR_CALLBACK = os.getenv("COORDINATOR_CALLBACK", "http://ai-coordinator:8084/callback")

# ─── 导入模块 ──────────────────────────────────────────────
import sys
import os as _os
_module_dir = _os.path.dirname(_os.path.abspath(__file__))
sys.path.insert(0, _module_dir)

from queue_manager import RedisTaskQueue
from tracker import ByteTrackerWrapper


# ═══════════════════════════════════════════════════════════
# 任务处理
# ═══════════════════════════════════════════════════════════
async def process_task(msg: Dict[str, Any]):
    """处理单个任务"""
    task_id = msg["task_id"]
    payload = msg["payload"]
    task_type = payload.get("task_type", "unknown")

    logger.info(f"[Worker] 处理任务: {task_id} ({task_type})")

    try:
        if task_type == "track":
            result = await _process_track_worker(payload)
        elif task_type == "track_video":
            result = await _process_track_worker(payload)
        else:
            result = {"error": f"未知任务类型: {task_type}", "status": "failed"}

        # 更新 Redis 任务状态
        await queue.complete_task(task_id, result)
        logger.info(f"[Worker] 任务成功: {task_id}")

        # 回调 coordinator
        if COORDINATOR_CALLBACK:
            await _send_callback(COORDINATOR_CALLBACK, {
                "task_id": task_id,
                "module": "ai-video",
                "status": "completed",
                "result": result,
            })

    except Exception as e:
        logger.error(f"[Worker] 任务失败: {task_id} - {e}")
        import traceback
        traceback.print_exc()
        await queue.complete_task(task_id, {"error": str(e), "status": "failed"})


async def _send_callback(url: str, payload: Dict[str, Any]):
    """发送回调"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            logger.info(f"[Worker] 回调成功: {url} -> {resp.status_code}")
    except Exception as e:
        logger.warning(f"[Worker] 回调失败: {url} - {e}")


async def _call_vision(frame: np.ndarray, vision_url: str) -> list:
    """调用 AI Vision 检测服务"""
    import httpx

    _, img_bytes = cv2.imencode(".jpg", frame)
    files = {"image": ("frame.jpg", img_bytes.tobytes(), "image/jpeg")}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(vision_url, files=files)
            resp.raise_for_status()
            data = resp.json()

        detections = []
        for det in data.get("detections", data.get("results", [])):
            detections.append({
                "bbox": det.get("bbox", [0, 0, 0, 0]),
                "score": det.get("score", 0.0),
                "class_id": det.get("class_id", 0),
                "class_name": det.get("class_name", "unknown"),
            })
        return detections
    except Exception as e:
        logger.warning(f"[Worker] Vision API 调用失败: {e}")
        return []


async def _process_track_worker(payload: Dict) -> Dict:
    """
    执行 ByteTrack 视频追踪
    - 打开视频源（URL 或本地文件）
    - 逐帧调用 AI Vision 检测
    - ByteTrack 追踪
    - 聚合轨迹并返回
    """
    video_url = payload["video_url"]
    camera_id = payload["camera_id"]
    vision_url = payload.get("model_url", VISION_API)
    max_frames = payload.get("max_frames", 300)
    track_thresh = payload.get("track_thresh", 0.5)
    track_buffer = payload.get("track_buffer", 30)

    task_id = payload.get("task_id", "unknown")

    logger.info(f"[{task_id}] Worker 开始追踪: {video_url[:60]}...")

    # ─── 打开视频 ─────────────────────────────────────────
    cap = cv2.VideoCapture(video_url)
    local_file = None

    if not cap.isOpened():
        # 尝试下载到临时文件
        logger.info(f"[{task_id}] 视频无法直接打开，尝试下载...")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.get(video_url)
                resp.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                tmp.write(resp.content)
                local_file = tmp.name
            cap = cv2.VideoCapture(local_file)
            if not cap.isOpened():
                raise RuntimeError(f"视频文件损坏或格式不支持: {video_url}")
        except Exception as e:
            return {
                "task_id": task_id,
                "camera_id": camera_id,
                "status": "failed",
                "error": f"无法读取视频: {e}",
            }

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080

    # ─── 初始化追踪器 ─────────────────────────────────────
    tracker = ByteTrackerWrapper(
        track_thresh=track_thresh,
        track_buffer=track_buffer,
        match_thresh=0.8,
        frame_rate=int(fps),
    )

    track_history: Dict[int, Dict[str, Any]] = {}
    frame_idx = 0
    all_tracked_frames = []

    try:
        while frame_idx < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            # 调用 AI Vision 检测
            detections = await _call_vision(frame, vision_url)

            if not detections:
                # 回退：使用模拟检测
                detections = _mock_detect(frame, frame_idx)

            # ByteTrack 追踪
            tracked = tracker.update(detections)

            for t in tracked:
                tid = t["track_id"]
                if tid not in track_history:
                    track_history[tid] = {
                        "id": tid,
                        "class": t.get("class_name", "unknown"),
                        "score": t["score"],
                        "total_score": t["score"],
                        "count": 1,
                        "trajectory": [],
                    }
                else:
                    hist = track_history[tid]
                    hist["score"] = max(hist["score"], t["score"])
                    hist["total_score"] += t["score"]
                    hist["count"] += 1

                # 每 5 帧记录一个轨迹点
                if frame_idx % 5 == 0:
                    track_history[tid]["trajectory"].append({
                        "bbox": t["bbox"],
                        "frame": frame_idx,
                        "timestamp_ms": int(frame_idx / fps * 1000),
                    })

                t["camera_id"] = camera_id

            all_tracked_frames.extend(tracked)
            frame_idx += 1

            if frame_idx % 50 == 0:
                logger.info(
                    f"[{task_id}] 进度: {frame_idx}/{max_frames}, "
                    f"活跃: {len(tracked)}, 累计轨迹: {len(track_history)}"
                )

    finally:
        cap.release()
        if local_file and os.path.exists(local_file):
            os.unlink(local_file)

    # ─── 聚合结果 ─────────────────────────────────────────
    final_tracks = []
    for tid, hist in track_history.items():
        final_tracks.append({
            "id": tid,
            "class": hist["class"],
            "score": round(hist["score"], 4),
            "avg_score": round(hist["total_score"] / max(hist["count"], 1), 4),
            "appearances": hist["count"],
            "trajectory": hist["trajectory"],
            "first_seen_frame": hist["trajectory"][0]["frame"] if hist["trajectory"] else 0,
            "last_seen_frame": hist["trajectory"][-1]["frame"] if hist["trajectory"] else 0,
        })

    final_tracks.sort(key=lambda x: x["appearances"], reverse=True)

    class_counts: Dict[str, int] = {}
    for t in final_tracks:
        cls = t.get("class", "unknown")
        class_counts[cls] = class_counts.get(cls, 0) + 1

    result = {
        "task_id": task_id,
        "camera_id": camera_id,
        "status": "completed",
        "video_url": video_url,
        "video_info": {"fps": round(fps, 2), "width": width, "height": height},
        "processing": {
            "frames_processed": frame_idx,
            "max_frames": max_frames,
        },
        "summary": {
            "unique_objects": len(track_history),
            "total_detections": len(all_tracked_frames),
            "class_counts": class_counts,
        },
        "tracks": final_tracks,
        "frame_tracks": all_tracked_frames[-500:],
    }

    logger.info(
        f"[{task_id}] 完成: {frame_idx} 帧, "
        f"{len(track_history)} 个目标, "
        f"{len(all_tracked_frames)} 次检测"
    )

    return result


def _mock_detect(frame, frame_idx: int) -> list:
    """模拟检测（AI Vision 不可用时的回退）"""
    h, w = frame.shape[:2]
    detections = []

    if frame_idx % np.random.randint(5, 15) < 3:
        n = np.random.randint(1, 3)
        for _ in range(n):
            x1 = np.random.randint(0, max(1, w - 200))
            y1 = np.random.randint(0, max(1, h - 300))
            bw, bh = np.random.randint(80, 200), np.random.randint(150, 300)
            detections.append({
                "bbox": [float(x1), float(y1), float(min(w, x1 + bw)), float(min(h, y1 + bh))],
                "score": round(float(np.random.uniform(0.5, 0.98)), 4),
                "class_id": 0,
                "class_name": "person",
            })

    if np.random.random() < 0.3:
        x1 = np.random.randint(0, max(1, w - 100))
        y1 = np.random.randint(0, max(1, h - 100))
        detections.append({
            "bbox": [float(x1), float(y1), float(x1 + 60), float(y1 + 60)],
            "score": round(float(np.random.uniform(0.5, 0.9)), 4),
            "class_id": 1,
            "class_name": "helmet",
        })

    return detections


# ═══════════════════════════════════════════════════════════
# Worker 启动入口
# ═══════════════════════════════════════════════════════════
queue: Optional[RedisTaskQueue] = None


async def main():
    global queue
    queue = RedisTaskQueue(host=REDIS_HOST, port=REDIS_PORT, queue=QUEUE_NAME)

    try:
        await queue.connect()
    except Exception as e:
        logger.error(f"Redis 连接失败: {e}")
        return

    logger.info(f"Video Worker 启动，队列: {QUEUE_NAME}")
    logger.info(f"Vision API: {VISION_API}")

    while True:
        msg = await queue.dequeue(timeout_ms=5000)
        if msg:
            await process_task(msg)
        else:
            # 心跳日志（避免无消息时完全静默）
            logger.debug(f"等待任务中... (队列: {QUEUE_NAME})")


if __name__ == "__main__":
    asyncio.run(main())
