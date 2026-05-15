"""
视觉检测 API 路由
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Optional
import base64
import time
import httpx

from app.schemas.schemas import DetectionRequest, DetectionResponse, DetectionBox

router = APIRouter()

# AI Vision 服务地址
VISION_SERVICE_URL = "http://localhost:8001"


@router.post("/detect", response_model=DetectionResponse)
async def detect_objects(request: DetectionRequest):
    """
    图像目标检测
    - 支持 URL 或 Base64 编码的图片
    """
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{VISION_SERVICE_URL}/detect",
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            result = response.json()
            
            processing_time = (time.time() - start_time) * 1000
            
            return DetectionResponse(
                detections=[
                    DetectionBox(**d) for d in result.get("detections", [])
                ],
                image_url=result.get("image_url", ""),
                processing_time_ms=processing_time,
                model_version=result.get("model_version", "yolov8n-1.0")
            )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"AI Vision 服务不可用: {str(e)}")


@router.post("/detect/file")
async def detect_from_file(
    file: UploadFile = File(...),
    confidence_threshold: float = 0.5
):
    """从上传文件进行检测"""
    contents = await file.read()
    image_base64 = base64.b64encode(contents).decode()
    
    request = DetectionRequest(image_data=image_base64)
    return await detect_objects(request)


@router.get("/health")
async def vision_health():
    """检查 AI Vision 服务状态"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{VISION_SERVICE_URL}/health")
            return response.json()
    except:
        return {"status": "unavailable", "service": "ai-vision"}
