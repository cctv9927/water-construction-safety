"""
电子沙盘 API 路由
"""
from fastapi import APIRouter, HTTPException
from typing import List
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import SandboxModel, VideoClip
from app.schemas.schemas import SandboxModelResponse, VideoClipResponse

router = APIRouter()


@router.get("/models", response_model=List[SandboxModelResponse])
async def list_models(db: Session = next(get_db())):
    """获取沙盘模型列表"""
    models = db.query(SandboxModel).all()
    return models


@router.get("/models/{model_id}", response_model=SandboxModelResponse)
async def get_model(model_id: int, db: Session = next(get_db())):
    """获取沙盘模型详情"""
    model = db.query(SandboxModel).filter(SandboxModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    return model


@router.get("/videos", response_model=List[VideoClipResponse])
async def list_videos(
    camera_id: str = None,
    limit: int = 50,
    db: Session = next(get_db())
):
    """获取视频片段列表"""
    query = db.query(VideoClip)
    if camera_id:
        query = query.filter(VideoClip.camera_id == camera_id)
    
    videos = query.order_by(VideoClip.created_at.desc()).limit(limit).all()
    return videos


@router.get("/videos/{video_id}", response_model=VideoClipResponse)
async def get_video(video_id: int, db: Session = next(get_db())):
    """获取视频片段详情"""
    video = db.query(VideoClip).filter(VideoClip.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    return video


@router.get("/cameras")
async def list_cameras(db: Session = next(get_db())):
    """获取摄像头列表"""
    cameras = db.query(VideoClip.camera_id, VideoClip.location).distinct().all()
    return [
        {"camera_id": c.camera_id, "location": c.location}
        for c in cameras if c.camera_id
    ]


@router.get("/stats")
async def get_sandbox_stats(db: Session = next(get_db())):
    """获取沙盘统计数据"""
    total_models = db.query(SandboxModel).count()
    total_videos = db.query(VideoClip).count()
    
    cameras = db.query(VideoClip.camera_id).distinct().count()
    
    return {
        "total_models": total_models,
        "total_videos": total_videos,
        "total_cameras": cameras
    }
