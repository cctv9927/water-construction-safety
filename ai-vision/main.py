"""
AI Vision Module - YOLOv8 ONNX 推理服务
FastAPI 图像识别服务，端口 8082
支持静态图片检测（URL/Base64/文件上传）+ RTSP 视频流实时检测
"""
import os
import time
import base64
import logging
import json
import asyncio
from pathlib import Path
from typing import Optional, List
from uuid import uuid4

import numpy as np
import httpx
from PIL import Image
from io import BytesIO

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from model import YOLOv8ONNX
from schemas import (
    DetectRequest, DetectResponse, ModelInfo,
    RTSPCameraConfig, RTSPDetectionResult,
    RTSPBatchAddRequest, RTSPStreamEventRequest, RTSPSourcesResponse,
)
from rtsp_stream import RTSPStreamManager, StreamConfig, DetectionResult

# ─── 日志配置 ───────────────────────────────────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("ai-vision")

# ─── 配置 ───────────────────────────────────────────────
MODEL_PATH = os.getenv("MODEL_PATH", "models/yolov8n.onnx")
DEFAULT_CONFIDENCE = float(os.getenv("DEFAULT_CONFIDENCE", "0.5"))
MAX_DETECTIONS = int(os.getenv("MAX_DETECTIONS", "100"))
COORDINATOR_URL = os.getenv("COORDINATOR_URL", "http://localhost:8084")

# ─── 全局模型和流管理器 ──────────────────────────────────
model: Optional[YOLOv8ONNX] = None
stream_manager: Optional[RTSPStreamManager] = None


# ─── FastAPI 应用 ────────────────────────────────────────
app = FastAPI(
    title="Water-Safety AI Vision",
    version="1.3.0",
    description="水利建设工地图像识别服务 - YOLOv8 ONNX 推理 + RTSP 视频流检测",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    global model, stream_manager
    logger.info("正在加载 YOLOv8 ONNX 模型...")
    model = YOLOv8ONNX(
        model_path=MODEL_PATH,
        conf_threshold=DEFAULT_CONFIDENCE,
        max_detections=MAX_DETECTIONS,
    )
    stream_manager = RTSPStreamManager(model)
    logger.info(f"模型加载完成，类别数: {model.num_classes}")


@app.on_event("shutdown")
async def shutdown():
    logger.info("AI Vision 服务关闭，停止所有 RTSP 流...")
    if stream_manager:
        stream_manager.stop_all()


# ─── 辅助函数 ────────────────────────────────────────────
async def fetch_image(url: str) -> np.ndarray:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGB")
        return np.array(img)


def decode_base64_image(b64_str: str) -> np.ndarray:
    data = base64.b64decode(b64_str)
    img = Image.open(BytesIO(data)).convert("RGB")
    return np.array(img)


async def _report_to_coordinator(detection_result: DetectionResult):
    """将检测结果上报给 AI Coordinator"""
    if not detection_result.detections:
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{COORDINATOR_URL}/event/vision",
                json={
                    "camera_id": detection_result.camera_id,
                    "detection_type": detection_result.detections[0]["class_name"],
                    "confidence": detection_result.detections[0]["confidence"],
                    "location": detection_result.camera_id,
                }
            )
            logger.debug(f"已上报给 Coordinator: {detection_result.camera_id}")
    except Exception as e:
        logger.warning(f"上报 Coordinator 失败: {e}")


def _build_detection_response(img: np.ndarray, results: list, elapsed_ms: float):
    """构建检测响应数据（URL/Base64/文件上传共用）"""
    from schemas import Detection, BBox
    detections_out = [
        Detection(
            class_id=r["class_id"],
            class_name=r["class_name"],
            confidence=round(float(r["confidence"]), 4),
            bbox=BBox(
                x1=int(r["bbox"][0]), y1=int(r["bbox"][1]),
                x2=int(r["bbox"][2]), y2=int(r["bbox"][3]),
            ),
        )
        for r in results
    ]
    return DetectResponse(
        code=0, message="success",
        data={
            "width": int(img.shape[1]),
            "height": int(img.shape[0]),
            "detections": detections_out,
            "count": len(detections_out),
            "inference_time_ms": round(elapsed_ms, 2),
        },
    )


# ─── 文件上传图片检测 API ────────────────────────────────

@app.post("/detect/upload")
async def detect_upload(
    file: UploadFile = File(...),
    confidence: float = 0.5,
    max_detections: int = 100,
):
    """图片目标检测（文件上传 multipart/form-data），返回 JSON 检测结果"""
    global model
    if model is None:
        raise HTTPException(status_code=503, detail="模型未加载")

    # 保存上传文件到临时目录
    os.makedirs("/tmp/ai-vision-uploads", exist_ok=True)
    suffix = Path(file.filename).suffix if file.filename else ".jpg"
    filepath = f"/tmp/ai-vision-uploads/{uuid4().hex}{suffix}"

    try:
        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"文件保存失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    try:
        img = Image.open(filepath).convert("RGB")
        img_array = np.array(img)

        start = time.perf_counter()
        results = model.detect(
            img_array,
            conf_threshold=confidence,
            max_detections=max_detections,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        return {
            "code": 0,
            "message": "success",
            "data": {
                "width": int(img_array.shape[1]),
                "height": int(img_array.shape[0]),
                "filename": file.filename,
                "detections": [
                    {
                        "class_id": r["class_id"],
                        "class_name": r["class_name"],
                        "confidence": round(float(r["confidence"]), 4),
                        "bbox": {
                            "x1": int(r["bbox"][0]),
                            "y1": int(r["bbox"][1]),
                            "x2": int(r["bbox"][2]),
                            "y2": int(r["bbox"][3]),
                        },
                    }
                    for r in results
                ],
                "count": len(results),
                "inference_time_ms": round(elapsed_ms, 2),
            },
        }
    except Exception as e:
        logger.error(f"推理失败: {e}")
        raise HTTPException(status_code=500, detail=f"推理失败: {str(e)}")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


# ─── 静态图片检测 API ────────────────────────────────────

@app.post("/detect", response_model=DetectResponse)
async def detect(request: DetectRequest):
    """图片目标检测（静态图片 URL 或 Base64）"""
    global model
    if model is None:
        raise HTTPException(status_code=503, detail="模型未加载")

    try:
        if request.image:
            img = await fetch_image(request.image)
        elif request.image_base64:
            img = decode_base64_image(request.image_base64)
        else:
            raise HTTPException(status_code=400, detail="必须提供 image 或 image_base64")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图片加载失败: {e}")
        raise HTTPException(status_code=400, detail=f"图片加载失败: {str(e)}")

    start = time.perf_counter()
    try:
        results = model.detect(
            img,
            conf_threshold=request.confidence,
            max_detections=request.max_detections,
        )
    except Exception as e:
        logger.error(f"推理失败: {e}")
        raise HTTPException(status_code=500, detail=f"推理失败: {str(e)}")

    elapsed_ms = (time.perf_counter() - start) * 1000
    return _build_detection_response(img, results, elapsed_ms)


# ─── RTSP 视频流管理 API ─────────────────────────────────

@app.post("/rtsp/add")
async def rtsp_add_camera(request: RTSPCameraConfig):
    """添加一路 RTSP 摄像头流"""
    global stream_manager
    if stream_manager is None:
        raise HTTPException(status_code=503, detail="服务未初始化")

    config = StreamConfig(
        rtsp_url=request.rtsp_url,
        name=request.camera_id,
        interval_seconds=request.interval_seconds,
        confidence=request.confidence,
        max_detections=MAX_DETECTIONS,
    )

    stream_manager.add_stream(config)

    if request.enabled:
        stream_manager.start_stream(request.camera_id)

    return {"code": 0, "message": f"摄像头 {request.camera_id} 已添加", "running": request.enabled}


@app.post("/rtsp/batch-add")
async def rtsp_batch_add(request: RTSPBatchAddRequest):
    """批量添加 RTSP 摄像头流"""
    global stream_manager
    if stream_manager is None:
        raise HTTPException(status_code=503, detail="服务未初始化")

    results = []
    for cam in request.cameras:
        config = StreamConfig(
            rtsp_url=cam.rtsp_url,
            name=cam.camera_id,
            interval_seconds=cam.interval_seconds,
            confidence=cam.confidence,
            max_detections=MAX_DETECTIONS,
        )
        stream_manager.add_stream(config)
        if cam.enabled:
            stream_manager.start_stream(cam.camera_id)
        results.append({"camera_id": cam.camera_id, "enabled": cam.enabled})

    return {"code": 0, "message": f"已添加 {len(results)} 路摄像头", "cameras": results}


@app.post("/rtsp/{camera_id}/start")
async def rtsp_start(camera_id: str):
    """启动指定摄像头"""
    global stream_manager
    if stream_manager is None or camera_id not in stream_manager.streams:
        raise HTTPException(status_code=404, detail=f"摄像头不存在: {camera_id}")
    stream_manager.start_stream(camera_id)
    return {"code": 0, "message": f"{camera_id} 已启动"}


@app.post("/rtsp/{camera_id}/stop")
async def rtsp_stop(camera_id: str):
    """停止指定摄像头"""
    global stream_manager
    if stream_manager is None or camera_id not in stream_manager.streams:
        raise HTTPException(status_code=404, detail=f"摄像头不存在: {camera_id}")
    stream_manager.stop_stream(camera_id)
    return {"code": 0, "message": f"{camera_id} 已停止"}


@app.get("/rtsp/sources", response_model=RTSPSourcesResponse)
async def rtsp_sources():
    """查看所有 RTSP 流状态"""
    global stream_manager
    if stream_manager is None:
        return RTSPSourcesResponse(streams=[], total=0)
    statuses = stream_manager.get_all_status()
    return RTSPSourcesResponse(
        streams=[{"camera_id": s["name"], "status": s["status"],
                  "total_frames": s["total_frames"], "error_count": s["error_count"]}
                 for s in statuses],
        total=len(statuses),
    )


@app.delete("/rtsp/{camera_id}")
async def rtsp_delete(camera_id: str):
    """删除摄像头流"""
    global stream_manager
    if stream_manager is None or camera_id not in stream_manager.streams:
        raise HTTPException(status_code=404, detail=f"摄像头不存在: {camera_id}")
    stream_manager.remove_stream(camera_id)
    return {"code": 0, "message": f"{camera_id} 已删除"}


# ─── 健康检查和模型信息 ─────────────────────────────────

@app.get("/health")
async def health():
    global stream_manager
    rtsp_count = len(stream_manager.streams) if stream_manager else 0
    running = sum(1 for s in (stream_manager.get_all_status() if stream_manager else [])
                  if s.get("running", False))
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "rtsp_total": rtsp_count,
        "rtsp_running": running,
    }


@app.get("/model/info", response_model=ModelInfo)
async def model_info():
    if model is None:
        raise HTTPException(status_code=503, detail="模型未加载")
    return ModelInfo(
        model_path=model.model_path,
        num_classes=model.num_classes,
        input_size=model.input_size,
        class_names=model.class_names,
    )


# ─── 入口 ────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs("models", exist_ok=True)
    if not Path(MODEL_PATH).exists():
        logger.warning(f"模型文件不存在: {MODEL_PATH}，将尝试自动下载...")
        try:
            from ultralytics import YOLO
            YOLO("yolov8n.pt")
            logger.info("YOLOv8n 模型下载完成")
        except Exception as e:
            logger.error(f"模型下载失败: {e}")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8082,
        workers=1,
        log_level="info",
    )
