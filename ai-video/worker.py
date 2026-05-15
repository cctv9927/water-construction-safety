"""
AI Video Worker - 任务处理器
从 Redis Stream 消费任务，执行后写入结果
"""
import asyncio
import logging
import json
from typing import Dict, Any

logger = logging.getLogger("ai-video.worker")

# 导入需要各模块
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from queue_manager import RedisTaskQueue
from tracker import ByteTrackerWrapper
from summarizer import VideoSummarizer
from diagnostics import VideoDiagnostics

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
QUEUE_NAME = "video:tasks"


async def process_task(msg: Dict[str, Any]):
    """处理单个任务"""
    task_id = msg["task_id"]
    payload = msg["payload"]
    task_type = payload.get("task_type", "unknown")
    logger.info(f"处理任务: {task_id} ({task_type})")

    try:
        result = None
        if task_type == "track":
            result = await _process_track(payload)
        elif task_type == "summarize":
            result = await _process_summarize(payload)
        elif task_type == "diagnose":
            result = await _process_diagnose(payload)
        else:
            result = {"error": f"未知任务类型: {task_type}"}

        # 更新任务状态
        await queue.complete_task(task_id, result)
        logger.info(f"任务成功: {task_id}")

    except Exception as e:
        logger.error(f"任务失败: {task_id} - {e}")
        import time
        await queue._client.hset(
            f"task:info:{task_id}",
            mapping={
                "status": "failed",
                "error": str(e),
                "updated_at": str(int(time.time())),
            },
        )


async def _process_track(payload: Dict) -> Dict:
    """执行目标追踪"""
    video_url = payload["video_url"]
    camera_id = payload["camera_id"]

    tracker = ByteTrackerWrapper()

    # 下载视频帧（这里简化处理，实际应该拉流）
    # 真实场景：使用 OpenCV VideoCapture 拉 RTSP 流
    import cv2
    cap = cv2.VideoCapture(video_url)
    if not cap.isOpened():
        # 尝试下载到本地
        import tempfile, httpx, os as _os
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.get(video_url)
            resp.raise_for_status()
            tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            tmp.write(resp.content)
            tmp_path = tmp.name
        cap = cv2.VideoCapture(tmp_path)

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_idx = 0
    tracked_results = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 简化：直接送入追踪器（实际应先调用 AI Vision）
        detections = _simple_detect(frame)  # 模拟检测
        tracked = tracker.update(detections)
        for t in tracked:
            t["camera_id"] = camera_id
            t["fps"] = fps
        tracked_results.extend(tracked)
        frame_idx += 1

        if frame_idx > 300:  # 最多处理前 300 帧
            break

    cap.release()
    return {
        "task_id": payload["task_id"],
        "camera_id": camera_id,
        "total_frames_processed": frame_idx,
        "tracks": tracked_results,
    }


def _simple_detect(frame) -> list:
    """简化检测（实际应调用 AI Vision 服务）"""
    # 返回空列表，由 tracker 自行处理
    return []


async def _process_summarize(payload: Dict) -> Dict:
    """执行视频浓缩"""
    summarizer = VideoSummarizer(
        min_segments=payload.get("min_segments", 5),
        max_segments=payload.get("max_segments", 20),
    )
    result = summarizer.summarize(payload["video_url"])
    result["task_id"] = payload["task_id"]
    result["camera_id"] = payload["camera_id"]
    return result


async def _process_diagnose(payload: Dict) -> Dict:
    """执行异常诊断"""
    diagnostics = VideoDiagnostics()
    result = diagnostics.diagnose(payload["video_url"])
    result["task_id"] = payload["task_id"]
    result["camera_id"] = payload["camera_id"]
    return result


# ─── Worker 入口 ──────────────────────────────────────────
queue: RedisTaskQueue


async def main():
    global queue
    queue = RedisTaskQueue(host=REDIS_HOST, port=REDIS_PORT, queue=QUEUE_NAME)
    await queue.connect()
    logger.info(f"Video Worker 启动，监听队列: {QUEUE_NAME}")

    while True:
        msg = await queue.dequeue(timeout_ms=3000)
        if msg:
            await process_task(msg)


if __name__ == "__main__":
    asyncio.run(main())
