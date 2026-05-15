"""
告警 API 路由
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.database import get_db
from app.models.models import Alert, AlertAssignment, User
from app.schemas.schemas import (
    AlertCreate, AlertUpdate, AlertResponse, AlertListResponse, AlertFilter,
    AlertAssignmentCreate, BaseResponse
)
from app.auth import get_current_user
from app.main import broadcast_alert

router = APIRouter()


@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    level: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sensor_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = next(get_db())
):
    """获取告警列表"""
    query = db.query(Alert)
    
    if level:
        query = query.filter(Alert.level == level)
    if status:
        query = query.filter(Alert.status == status)
    if start_date:
        query = query.filter(Alert.created_at >= start_date)
    if end_date:
        query = query.filter(Alert.created_at <= end_date)
    if sensor_id:
        query = query.filter(Alert.sensor_id == sensor_id)
    if search:
        query = query.filter(
            Alert.title.ilike(f"%{search}%") |
            Alert.description.ilike(f"%{search}%")
        )
    
    total = query.count()
    alerts = query.order_by(desc(Alert.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    return AlertListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=alerts
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: int, db: Session = next(get_db())):
    """获取告警详情"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    return alert


@router.post("/", response_model=AlertResponse)
async def create_alert(
    alert_data: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: Session = next(get_db())
):
    """创建告警"""
    alert = Alert(
        **alert_data.model_dump(),
        creator_id=current_user.id
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    # 广播告警
    await broadcast_alert(alert, "created")
    
    return alert


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    alert_data: AlertUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = next(get_db())
):
    """更新告警"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    update_data = alert_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)
    
    # 如果状态变为完成，记录时间
    if alert_data.status and alert_data.status.value == "completed" and not alert.resolved_at:
        alert.resolved_at = datetime.now()
    
    db.commit()
    db.refresh(alert)
    
    # 广播告警更新
    await broadcast_alert(alert, "updated")
    
    return alert


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = next(get_db())
):
    """删除告警"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    db.delete(alert)
    db.commit()
    
    return {"success": True, "message": "告警已删除"}


@router.post("/{alert_id}/assign")
async def assign_alert(
    alert_id: int,
    assignment: AlertAssignmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = next(get_db())
):
    """分配告警"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    # 验证用户存在
    user = db.query(User).filter(User.id == assignment.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    alert_assignment = AlertAssignment(
        alert_id=alert_id,
        user_id=assignment.user_id
    )
    db.add(alert_assignment)
    
    # 更新告警状态为处理中
    alert.status = "processing"
    
    db.commit()
    
    return {"success": True, "message": f"已分配给 {user.full_name or user.username}"}


@router.get("/{alert_id}/history")
async def get_alert_history(
    alert_id: int,
    db: Session = next(get_db())
):
    """获取告警处理历史"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    # 获取分配历史
    assignments = db.query(AlertAssignment).filter(
        AlertAssignment.alert_id == alert_id
    ).all()
    
    return {
        "alert_id": alert_id,
        "current_status": alert.status.value if hasattr(alert.status, 'value') else alert.status,
        "assignments": [
            {
                "user_id": a.user_id,
                "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                "notes": a.notes
            }
            for a in assignments
        ],
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
    }
