"""
AI Video Module - 视频处理服务
目标追踪 / 视频浓缩 / 异常诊断 / Redis Stream 任务队列
"""
import os
import json
import uuid
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from tracker import ByteTrackerWrapper
from summarizer import VideoSummarizer
from diagnostics import VideoDiagnostics
from queue_manager import RedisTaskQueue

# ─── 日志 ────────────────────────────────────────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("ai-video")

# ─── 配置 ────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
VISION_API = os.getenv("VISION_API", "http://localhost:8082/detect")
QUEUE_NAME = "video:tasks"

# ─── FastAPI ──────────────────────────────────────────────
app = FastAPI(
    title="Water-Safety AI Video",
    version="1.0.0",
    description="水利建设工地视频智能分析服务",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ─── 全局组件 ─────────────────────────────────────────────
task_queue: Optional[RedisTaskQueue] = None


@app.on_event("startup")
async def startup():
    global task_queue
    logger.info("AI Video 服务启动")
    task_queue = RedisTaskQueue(host=REDIS_HOST, port=REDIS_PORT, queue=QUEUE_NAME)
    await task_queue.connect()
    logger.info("Redis Stream 连接成功")


@app.on_event("shutdown")
async def shutdown():
    if task_queue:
        await task_queue.close()
    logger.info("AI Video 服务关闭")


# ─── Pydantic Models ──────────────────────────────────────
class TrackRequest(BaseModel):
    video_url: str = Field(description="视频 URL（支持 RTSP/HTTP）")
    camera_id: str = Field(description="摄像头 ID")
    model_url: Optional[str] = Field(None, description="AI Vision 服务地址")


class SummarizeRequest(BaseModel):
    video_url: str
    camera_id: str
    min_segments: int = Field(5, ge=1)
    max_segments: int = Field(20, ge=1)


class DiagnoseRequest(BaseModel):
    video_url: str
    camera_id: str


class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str
    message: str


# ─── 辅助 ─────────────────────────────────────────────────
def _submit_task(task_type: str, payload: dict) -> str:
    task_id = f"{task_type}_{uuid.uuid4().hex[:12]}"
    payload["task_id"] = task_id
    payload["task_type"] = task_type
    payload["created_at"] = datetime.utcnow().isoformat()
    task_queue.enqueue(task_id, payload)
    logger.info(f"任务已提交: {task_id} ({task_type})")
    return task_id


# ─── API 路由 ─────────────────────────────────────────────
@app.post("/task/track", response_model=TaskSubmitResponse)
async def submit_track(req: TrackRequest):
    task_id = _submit_task("track", {
        "video_url": req.video_url,
        "camera_id": req.camera_id,
        "model_url": req.model_url or VISION_API,
    })
    return TaskSubmitResponse(task_id=task_id, status="queued", message="目标追踪任务已提交")


@app.post("/task/summarize", response_model=TaskSubmitResponse)
async def submit_summarize(req: SummarizeRequest):
    task_id = _submit_task("summarize", {
        "video_url": req.video_url,
        "camera_id": req.camera_id,
        "min_segments": req.min_segments,
        "max_segments": req.max_segments,
    })
    return TaskSubmitResponse(task_id=task_id, status="queued", message="视频浓缩任务已提交")


@app.post("/task/diagnose", response_model=TaskSubmitResponse)
async def submit_diagnose(req: DiagnoseRequest):
    task_id = _submit_task("diagnose", {
        "video_url": req.video_url,
        "camera_id": req.camera_id,
    })
    return TaskSubmitResponse(task_id=task_id, status="queued", message="异常诊断任务已提交")


@app.get("/task/{task_id}")
async def get_task(task_id: str):
    info = task_queue.get_task_info(task_id)
    if not info:
        raise HTTPException(status_code=404, detail="任务不存在")
    return info


@app.get("/health")
async def health():
    return {"status": "ok", "queue": QUEUE_NAME}


# ─── 异步 Worker（可独立进程运行）────────────────────────
async def run_worker():
    """后台 Worker：消费 Redis Stream 任务并执行"""
    from worker import process_task
    await task_queue.connect()
    logger.info("Video Worker 启动，监听任务队列...")
    while True:
        msg = await task_queue.dequeue()
        if msg:
            await process_task(msg)
        else:
            await asyncio.sleep(1)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        asyncio.run(run_worker())
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=8083, workers=1)
