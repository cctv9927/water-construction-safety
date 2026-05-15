"""
AI Vision Module - YOLOv8 ONNX 推理服务
FastAPI 图像识别服务，端口 8082
"""
import os
import time
import base64
import logging
import json
from pathlib import Path
from typing import Optional, List

import cv2
import numpy as np
import httpx
from PIL import Image
from io import BytesIO

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import uvicorn

from model import YOLOv8ONNX
from schemas import DetectRequest, DetectResponse, BBox, Detection, ModelInfo

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
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# ─── 全局模型实例 ────────────────────────────────────────
model: Optional[YOLOv8ONNX] = None

# ─── FastAPI 应用 ────────────────────────────────────────
app = FastAPI(
    title="Water-Safety AI Vision",
    version="1.0.0",
    description="水利建设工地图像识别服务 - YOLOv8 ONNX 推理",
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
    global model
    logger.info("正在加载 YOLOv8 ONNX 模型...")
    model = YOLOv8ONNX(
        model_path=MODEL_PATH,
        conf_threshold=DEFAULT_CONFIDENCE,
        max_detections=MAX_DETECTIONS,
    )
    logger.info(f"模型加载完成，类别数: {model.num_classes}")


@app.on_event("shutdown")
async def shutdown():
    logger.info("AI Vision 服务关闭")


# ─── 辅助函数 ────────────────────────────────────────────
async def fetch_image(url: str) -> np.ndarray:
    """从 URL 下载图片"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGB")
        return np.array(img)


def decode_base64_image(b64_str: str) -> np.ndarray:
    """Base64 解码为图片"""
    data = base64.b64decode(b64_str)
    img = Image.open(BytesIO(data)).convert("RGB")
    return np.array(img)


# ─── API 路由 ────────────────────────────────────────────
@app.post("/detect", response_model=DetectResponse)
async def detect(request: DetectRequest):
    """
    图片目标检测
    支持 image_url（优先）或 image_base64
    """
    global model
    if model is None:
        raise HTTPException(status_code=503, detail="模型未加载")

    # 解析图片
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

    # 推理
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

    # 序列化结果
    detections_out: List[Detection] = []
    for r in results:
        detections_out.append(Detection(
            class_id=r["class_id"],
            class_name=r["class_name"],
            confidence=round(float(r["confidence"]), 4),
            bbox=BBox(
                x1=int(r["bbox"][0]),
                y1=int(r["bbox"][1]),
                x2=int(r["bbox"][2]),
                y2=int(r["bbox"][3]),
            ),
        ))

    return DetectResponse(
        code=0,
        message="success",
        data={
            "width": int(img.shape[1]),
            "height": int(img.shape[0]),
            "detections": detections_out,
            "count": len(detections_out),
            "inference_time_ms": round(elapsed_ms, 2),
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": model is not None}


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
    # 确保模型存在
    os.makedirs("models", exist_ok=True)
    if not Path(MODEL_PATH).exists():
        logger.warning(f"模型文件不存在: {MODEL_PATH}，将尝试自动下载...")
        try:
            from ultralytics import YOLO
            yolo = YOLO("yolov8n.pt")
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
