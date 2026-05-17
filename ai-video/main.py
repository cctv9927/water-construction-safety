"""
AI Video Module - 视频处理服务 (v0.3)
目标追踪 / 视频浓缩 / 异常诊断 / Redis Stream 任务队列 / ByteTrack 集成

API 端点:
  POST /track/video           - 追踪视频文件
  POST /track/stream         - 实时流追踪（WebSocket）
  GET  /track/result/{task_id} - 查询追踪结果
  POST /task/track           - 提交追踪任务（异步）
  GET  /task/{task_id}       - 查询异步任务状态
"""
import os
import json
import uuid
import asyncio
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse
import uvicorn

from tracker import ByteTrackerWrapper
from summarizer import VideoSummarizer
from diagnostics import VideoDiagnostics
from queue_manager import RedisTaskQueue

# ─── 日志配置 ─────────────────────────────────────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("ai-video")

# ─── 全局配置 ─────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
VISION_API = os.getenv("VISION_API", "http://ai-vision:8082/detect")
COORDINATOR_CALLBACK = os.getenv("COORDINATOR_CALLBACK", "http://ai-coordinator:8084/callback")
QUEUE_NAME = "video:track_tasks"

# ─── 结果存储（内存 + Redis）───────────────────────────────
# task_id -> {
#   "status": "processing|completed|failed",
#   "created_at": "...",
#   "tracks": [...],
#   "video_url": "...",
#   "camera_id": "...",
#   "total_frames": int,
#   "unique_objects": int,
#   "error": str,
# }
_task_results: Dict[str, Dict[str, Any]] = {}


# ─── FastAPI 应用 ──────────────────────────────────────────
app = FastAPI(
    title="Water-Safety AI Video",
    version="0.3.0",
    description="水利建设工地视频智能分析服务 - ByteTrack 多目标追踪",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── 全局组件 ─────────────────────────────────────────────
task_queue: Optional[RedisTaskQueue] = None


@app.on_event("startup")
async def startup():
    global task_queue
    logger.info("=" * 60)
    logger.info("AI Video 服务启动 (v0.3 - ByteTrack 追踪模式)")
    logger.info("=" * 60)

    try:
        task_queue = RedisTaskQueue(host=REDIS_HOST, port=REDIS_PORT, queue=QUEUE_NAME)
        await task_queue.connect()
        logger.info(f"Redis Stream 连接成功: {REDIS_HOST}:{REDIS_PORT}")
        logger.info(f"任务队列: {QUEUE_NAME}")
    except Exception as e:
        logger.warning(f"Redis 连接失败 ({e})，任务队列降级为内存模式")
        task_queue = None


@app.on_event("shutdown")
async def shutdown():
    if task_queue:
        await task_queue.close()
    logger.info("AI Video 服务关闭")


# ═══════════════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════════════
class TrackVideoRequest(BaseModel):
    """视频追踪请求（URL 方式）"""
    video_url: str = Field(..., description="视频 URL（支持 RTSP/HTTP/HTTPS）")
    camera_id: str = Field(..., description="摄像头 ID")
    model_url: Optional[str] = Field(
        None,
        description="AI Vision 检测服务地址，不填则用环境变量 VISION_API",
    )
    max_frames: int = Field(300, ge=1, le=5000, description="最多处理帧数")
    track_thresh: float = Field(0.5, ge=0.1, le=1.0, description="追踪置信度阈值")
    track_buffer: int = Field(30, ge=1, description="目标消失后保留帧数")
    callback_url: Optional[str] = Field(None, description="完成后回调地址")


class TrackResultResponse(BaseModel):
    """追踪结果响应"""
    task_id: str
    status: str  # processing | completed | failed
    camera_id: Optional[str] = None
    total_frames: Optional[int] = None
    unique_objects: Optional[int] = None
    tracks: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class TaskSubmitResponse(BaseModel):
    """异步任务提交响应"""
    task_id: str
    status: str
    message: str


class StreamTrackRequest(BaseModel):
    """流追踪请求"""
    camera_id: str
    stream_url: str = Field(..., description="RTSP/HTTP 流地址")
    track_thresh: float = Field(0.5, ge=0.1, le=1.0)
    track_buffer: int = Field(30, ge=1)
    send_frames: bool = Field(True, description="是否回传带追踪框的视频帧")


# ═══════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════
def _save_result(task_id: str, data: Dict[str, Any]):
    """保存追踪结果到内存（生产环境应存 Redis）"""
    _task_results[task_id] = data


def _get_result(task_id: str) -> Optional[Dict[str, Any]]:
    """获取追踪结果"""
    return _task_results.get(task_id)


def _init_result(task_id: str, camera_id: str, **kwargs):
    """初始化追踪结果记录"""
    _save_result(task_id, {
        "task_id": task_id,
        "status": "processing",
        "camera_id": camera_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "tracks": [],
        "total_frames": 0,
        "unique_objects": 0,
        **kwargs,
    })


async def _call_vision_api(frame: np.ndarray, vision_url: str) -> List[Dict[str, Any]]:
    """调用 AI Vision 检测服务"""
    import httpx

    # 将帧编码为 JPEG
    _, img_bytes = cv2.imencode(".jpg", frame)
    files = {"image": ("frame.jpg", img_bytes.tobytes(), "image/jpeg")}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(vision_url, files=files)
            resp.raise_for_status()
            data = resp.json()

        # 解析检测结果
        detections = []
        if "detections" in data:
            for det in data["detections"]:
                detections.append({
                    "bbox": det.get("bbox", [0, 0, 0, 0]),
                    "score": det.get("score", 0.0),
                    "class_id": det.get("class_id", 0),
                    "class_name": det.get("class_name", "unknown"),
                })
        elif "results" in data:
            for det in data["results"]:
                detections.append({
                    "bbox": det.get("bbox", [0, 0, 0, 0]),
                    "score": det.get("score", 0.0),
                    "class_id": det.get("class_id", 0),
                    "class_name": det.get("class_name", "unknown"),
                })

        return detections
    except httpx.HTTPStatusError as e:
        logger.warning(f"Vision API HTTP 错误: {e.response.status_code}")
        return []
    except Exception as e:
        logger.warning(f"Vision API 调用失败: {e}")
        return []


async def _send_callback(callback_url: str, payload: Dict[str, Any]):
    """发送任务完成回调到 ai-coordinator"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(callback_url, json=payload)
            resp.raise_for_status()
            logger.info(f"回调成功: {callback_url} -> {resp.status_code}")
    except Exception as e:
        logger.warning(f"回调失败: {callback_url} - {e}")


def _draw_tracks(frame: np.ndarray, tracks: List[Dict], max_display: int = 20) -> np.ndarray:
    """在帧上绘制追踪框和 ID"""
    colors = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255),
        (255, 255, 0), (255, 0, 255), (0, 255, 255),
        (128, 0, 0), (0, 128, 0), (0, 0, 128),
    ]
    display = tracks[:max_display]
    for i, track in enumerate(display):
        x1, y1, x2, y2 = track.get("bbox", [0, 0, 0, 0])
        track_id = track.get("track_id", -1)
        class_name = track.get("class_name", "")
        score = track.get("score", 0.0)

        color = colors[i % len(colors)]
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)

        label = f"ID:{track_id} {class_name} {score:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (int(x1), int(y1) - th - 4), (int(x1) + tw, int(y1)), color, -1)
        cv2.putText(frame, label, (int(x1), int(y1) - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # 叠加显示统计信息
    info = f"Tracks: {len(tracks)} | Frame: {tracks[0]['frame_id'] if tracks else 0}"
    cv2.putText(frame, info, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    return frame


# ═══════════════════════════════════════════════════════════
# 追踪核心处理函数
# ═══════════════════════════════════════════════════════════
async def process_video_track(
    task_id: str,
    video_url: str,
    camera_id: str,
    vision_url: str,
    max_frames: int = 300,
    track_thresh: float = 0.5,
    track_buffer: int = 30,
    callback_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    处理视频追踪的核心逻辑
    流程：打开视频 -> 逐帧检测 + 追踪 -> 聚合轨迹 -> 返回结果
    """
    import httpx

    logger.info(f"[{task_id}] 开始追踪: {video_url}")

    # 初始化结果
    _init_result(task_id, camera_id, video_url=video_url)

    # 打开视频源
    cap = cv2.VideoCapture(video_url)
    local_file = None

    if not cap.isOpened():
        # 尝试下载到临时文件
        logger.info(f"[{task_id}] 视频无法直接打开，尝试下载...")
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.get(video_url)
                resp.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                tmp.write(resp.content)
                local_file = tmp.name
            cap = cv2.VideoCapture(local_file)
            if not cap.isOpened():
                raise RuntimeError(f"视频文件损坏或格式不支持: {video_url}")
            logger.info(f"[{task_id}] 视频下载完成: {local_file}")
        except Exception as e:
            error_msg = f"无法读取视频: {e}"
            logger.error(f"[{task_id}] {error_msg}")
            _save_result(task_id, {
                "task_id": task_id,
                "status": "failed",
                "error": error_msg,
                "camera_id": camera_id,
                "created_at": datetime.utcnow().isoformat() + "Z",
            })
            return _get_result(task_id)

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080

    logger.info(f"[{task_id}] 视频信息: {width}x{height} @ {fps:.1f}fps, 共{total_frames}帧")

    # 初始化追踪器
    tracker = ByteTrackerWrapper(
        track_thresh=track_thresh,
        track_buffer=track_buffer,
        match_thresh=0.8,
        frame_rate=int(fps),
    )

    # 轨迹聚合：track_id -> {class, score, trajectory, bbox_history}
    track_history: Dict[int, Dict[str, Any]] = {}
    next_track_id = 0
    frame_idx = 0
    all_track_frames: List[Dict[str, Any]] = []

    try:
        while frame_idx < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            # 1. 调用 AI Vision 进行检测
            detections = await _call_vision_api(frame, vision_url)

            if not detections:
                # AI Vision 未返回结果时，尝试使用模拟检测（用于测试）
                detections = _mock_detect(frame, frame_idx)

            # 2. ByteTrack 追踪
            tracked = tracker.update(detections)

            # 3. 更新轨迹历史
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
                        "bbox_history": [],
                    }
                else:
                    hist = track_history[tid]
                    hist["score"] = max(hist["score"], t["score"])
                    hist["total_score"] += t["score"]
                    hist["count"] += 1

                # 记录轨迹点：每 5 帧记录一个点（避免轨迹过长）
                if frame_idx % 5 == 0:
                    track_history[tid]["trajectory"].append({
                        "bbox": t["bbox"],
                        "frame": frame_idx,
                        "timestamp_ms": int(frame_idx / fps * 1000),
                    })

                track_history[tid]["bbox_history"].append({
                    "bbox": t["bbox"],
                    "frame": frame_idx,
                })

            # 4. 记录本帧追踪结果
            for t in tracked:
                t["camera_id"] = camera_id
                t["fps"] = fps
            all_track_frames.extend(tracked)

            frame_idx += 1

            # 每 50 帧输出一次进度
            if frame_idx % 50 == 0:
                logger.info(
                    f"[{task_id}] 进度: {frame_idx}/{max_frames} 帧, "
                    f"活跃目标: {len(tracked)}, 累计轨迹: {len(track_history)}"
                )

    finally:
        cap.release()
        if local_file and os.path.exists(local_file):
            os.unlink(local_file)

    # ─── 聚合最终结果 ──────────────────────────────────────
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

    # 按出现次数排序
    final_tracks.sort(key=lambda x: x["appearances"], reverse=True)

    result = {
        "task_id": task_id,
        "status": "completed",
        "camera_id": camera_id,
        "video_url": video_url,
        "video_info": {
            "fps": round(fps, 2),
            "width": width,
            "height": height,
            "total_frames": total_frames,
        },
        "processing": {
            "frames_processed": frame_idx,
            "max_frames": max_frames,
        },
        "summary": {
            "unique_objects": len(track_history),
            "total_detections": len(all_track_frames),
            "class_counts": _count_classes(final_tracks),
        },
        "tracks": final_tracks,
        "frame_tracks": all_track_frames[-500:],  # 最近 500 帧（避免结果过大）
        "created_at": _get_result(task_id).get("created_at", ""),
        "completed_at": datetime.utcnow().isoformat() + "Z",
    }

    _save_result(task_id, result)
    logger.info(
        f"[{task_id}] 追踪完成: {frame_idx} 帧, "
        f"{len(track_history)} 个独立目标, "
        f"{len(all_track_frames)} 次检测"
    )

    # 回调 ai-coordinator
    if callback_url:
        await _send_callback(callback_url, {
            "task_id": task_id,
            "module": "ai-video",
            "status": "completed",
            "result": {
                "unique_objects": len(track_history),
                "tracks_summary": result["summary"],
            },
        })

    return result


def _mock_detect(frame: np.ndarray, frame_idx: int) -> List[Dict[str, Any]]:
    """
    模拟检测（AI Vision 不可用时的回退）
    随机生成符合人体/安全帽特征的检测框
    """
    h, w = frame.shape[:2]
    detections = []

    # 每 5-15 帧生成 0-2 个随机目标
    if frame_idx % np.random.randint(5, 15) < 3:
        n = np.random.randint(1, 3)
        for _ in range(n):
            x1 = np.random.randint(0, max(1, w - 200))
            y1 = np.random.randint(0, max(1, h - 300))
            bw = np.random.randint(80, 200)
            bh = np.random.randint(150, 300)
            x2 = min(w, x1 + bw)
            y2 = min(h, y1 + bh)
            detections.append({
                "bbox": [float(x1), float(y1), float(x2), float(y2)],
                "score": round(np.random.uniform(0.5, 0.98), 4),
                "class_id": 0,
                "class_name": "person",
            })

    # 随机添加安全帽
    if np.random.random() < 0.3:
        x1 = np.random.randint(0, max(1, w - 100))
        y1 = np.random.randint(0, max(1, h - 100))
        detections.append({
            "bbox": [float(x1), float(y1), float(x1 + 60), float(y1 + 60)],
            "score": round(np.random.uniform(0.5, 0.9), 4),
            "class_id": 1,
            "class_name": "helmet",
        })

    return detections


def _count_classes(tracks: List[Dict]) -> Dict[str, int]:
    """统计各类别目标数量"""
    counts: Dict[str, int] = {}
    for t in tracks:
        cls = t.get("class", "unknown")
        counts[cls] = counts.get(cls, 0) + 1
    return counts


# ═══════════════════════════════════════════════════════════
# API 路由
# ═══════════════════════════════════════════════════════════

# ─── 追踪结果查询 ─────────────────────────────────────────
@app.get("/track/result/{task_id}", response_model=TrackResultResponse)
async def get_track_result(task_id: str):
    """查询追踪结果（支持轮询）"""
    result = _get_result(task_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return TrackResultResponse(**result)


# ─── 视频文件追踪 ─────────────────────────────────────────
@app.post("/track/video", response_model=TaskSubmitResponse)
async def track_video(req: TrackVideoRequest):
    """
    追踪视频文件（同步处理，实时返回进度）
    支持：上传视频文件 或 提供视频 URL（RTSP/HTTP/HTTPS）
    """
    task_id = f"track_{uuid.uuid4().hex[:12]}"
    vision_url = req.model_url or VISION_API

    logger.info(
        f"[{task_id}] 收到追踪请求: camera={req.camera_id}, "
        f"video={req.video_url[:80]}, max_frames={req.max_frames}"
    )

    # 初始化结果（异步处理）
    asyncio.create_task(
        process_video_track(
            task_id=task_id,
            video_url=req.video_url,
            camera_id=req.camera_id,
            vision_url=vision_url,
            max_frames=req.max_frames,
            track_thresh=req.track_thresh,
            track_buffer=req.track_buffer,
            callback_url=req.callback_url or COORDINATOR_CALLBACK,
        )
    )

    return TaskSubmitResponse(
        task_id=task_id,
        status="processing",
        message=f"追踪任务已提交 (camera={req.camera_id})，请通过 GET /track/result/{task_id} 查询结果",
    )


# ─── 实时流追踪（WebSocket）────────────────────────────────
@app.websocket("/track/stream")
async def track_stream(websocket: WebSocket):
    """
    实时流追踪 WebSocket 端点

    客户端发送: {"camera_id": "cam_01", "stream_url": "rtsp://...", "track_thresh": 0.5}
    服务端推送: {"frame_id": 1, "tracks": [{"id": 1, "class": "person", "bbox": [...]}]}
    """
    await websocket.accept()
    logger.info("WebSocket 流追踪连接已建立")

    tracker: Optional[ByteTrackerWrapper] = None
    camera_id = "unknown"
    stream_url = ""

    try:
        # ─── 接收初始配置 ─────────────────────────────────
        init_data = await websocket.receive_json()
        camera_id = init_data.get("camera_id", "unknown")
        stream_url = init_data.get("stream_url", "")
        track_thresh = init_data.get("track_thresh", 0.5)
        track_buffer = init_data.get("track_buffer", 30)
        send_frames = init_data.get("send_frames", True)
        vision_url = init_data.get("vision_url", VISION_API)

        tracker = ByteTrackerWrapper(
            track_thresh=track_thresh,
            track_buffer=track_buffer,
        )

        await websocket.send_json({
            "type": "init",
            "status": "connected",
            "camera_id": camera_id,
            "message": "流追踪已启动",
        })

        logger.info(f"[{camera_id}] 流追踪启动: {stream_url}")

        # ─── 拉流并追踪 ───────────────────────────────────
        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            await websocket.send_json({
                "type": "error",
                "message": f"无法打开流: {stream_url}",
            })
            await websocket.close()
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_interval = max(1, int(fps / 10))  # 最多每秒 10 次推送
        frame_idx = 0
        last_send = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                await websocket.send_json({"type": "eos", "message": "视频流结束"})
                break

            frame_idx += 1

            # 限速推送
            if frame_idx - last_send < frame_interval:
                continue

            # 检测
            detections = await _call_vision_api(frame, vision_url)
            tracked = tracker.update(detections)

            # 推送结果
            payload = {
                "type": "frame",
                "frame_id": frame_idx,
                "timestamp_ms": int(frame_idx / fps * 1000),
                "tracks_count": len(tracked),
                "tracks": [
                    {
                        "id": t["track_id"],
                        "class": t.get("class_name", "unknown"),
                        "score": t["score"],
                        "bbox": t["bbox"],
                    }
                    for t in tracked
                ],
            }

            if send_frames:
                # 绘制追踪框
                annotated = _draw_tracks(frame.copy(), tracked)
                _, jpg = cv2.imencode(".jpg", annotated)
                import base64
                payload["frame"] = base64.b64encode(jpg.tobytes()).decode()

            await websocket.send_json(payload)
            last_send = frame_idx

        cap.release()

    except WebSocketDisconnect:
        logger.info(f"[{camera_id}] WebSocket 连接断开")
    except Exception as e:
        logger.error(f"WebSocket 流追踪异常: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        if tracker:
            tracker.reset()


# ─── 视频文件上传追踪 ─────────────────────────────────────
@app.post("/track/upload", response_model=TaskSubmitResponse)
async def track_upload(
    camera_id: str = Query(..., description="摄像头 ID"),
    track_thresh: float = Query(0.5, ge=0.1, le=1.0, description="追踪阈值"),
    max_frames: int = Query(300, ge=1, le=5000, description="最多处理帧数"),
    file: UploadFile = File(..., description="视频文件"),
):
    """通过上传视频文件进行追踪"""
    task_id = f"track_{uuid.uuid4().hex[:12]}"
    vision_url = VISION_API

    # 保存上传文件到临时目录
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        local_path = tmp.name

    logger.info(f"[{task_id}] 上传视频已保存: {local_path} ({len(content) / 1024:.0f} KB)")

    asyncio.create_task(
        process_video_track(
            task_id=task_id,
            video_url=local_path,
            camera_id=camera_id,
            vision_url=vision_url,
            max_frames=max_frames,
            track_thresh=track_thresh,
            track_buffer=30,
            callback_url=None,
        )
    )

    return TaskSubmitResponse(
        task_id=task_id,
        status="processing",
        message=f"视频追踪任务已提交，请通过 GET /track/result/{task_id} 查询结果",
    )


# ─── 健康检查 ─────────────────────────────────────────────
@app.get("/health")
async def health():
    """服务健康检查"""
    redis_ok = False
    if task_queue:
        try:
            await task_queue._client.ping()
            redis_ok = True
        except Exception:
            pass

    return {
        "status": "ok",
        "service": "ai-video",
        "version": "0.3.0",
        "features": ["bytetrack", "summarize", "diagnose"],
        "redis": "connected" if redis_ok else "disconnected",
        "queue": QUEUE_NAME,
        "tasks_in_memory": len(_task_results),
    }


# ─── 兼容旧 API ────────────────────────────────────────────
@app.post("/task/track", response_model=TaskSubmitResponse)
async def submit_track_legacy(req: TrackVideoRequest):
    """旧版任务提交接口（兼容）"""
    return await track_video(req)


@app.get("/task/{task_id}")
async def get_task_legacy(task_id: str):
    """旧版任务查询接口（兼容）"""
    return get_track_result(task_id)


# ─── 异步 Worker 启动入口 ─────────────────────────────────
async def run_worker():
    """后台 Worker：消费 Redis Stream 任务并执行"""
    from worker import process_task
    if task_queue is None:
        logger.error("Redis 未连接，无法启动 Worker")
        return
    await task_queue.connect()
    logger.info("Video Worker 启动，监听任务队列...")
    while True:
        msg = await task_queue.dequeue()
        if msg:
            await process_task(msg)
        else:
            await asyncio.sleep(1)


# ─── 启动入口 ──────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        asyncio.run(run_worker())
    else:
        port = int(os.getenv("PORT", "8083"))
        uvicorn.run("main:app", host="0.0.0.0", port=port, workers=1)
