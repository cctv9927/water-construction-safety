"""
传感器 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.db.database import get_db
from app.models.models import Sensor, SensorData
from app.schemas.schemas import (
    SensorResponse, SensorCreate,
    SensorDataResponse, SensorDataPoint
)

router = APIRouter()


@router.get("/", response_model=list[SensorResponse])
async def list_sensors(
    type: Optional[str] = None,
    is_active: Optional[bool] = True,
    db: Session = next(get_db())
):
    """获取传感器列表"""
    query = db.query(Sensor)
    
    if type:
        query = query.filter(Sensor.type == type)
    if is_active is not None:
        query = query.filter(Sensor.is_active == is_active)
    
    sensors = query.order_by(desc(Sensor.created_at)).all()
    return sensors


@router.get("/{sensor_id}", response_model=SensorResponse)
async def get_sensor(sensor_id: int, db: Session = next(get_db())):
    """获取传感器详情"""
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="传感器不存在")
    return sensor


@router.post("/", response_model=SensorResponse)
async def create_sensor(sensor: SensorCreate, db: Session = next(get_db())):
    """创建传感器"""
    db_sensor = Sensor(**sensor.model_dump())
    db.add(db_sensor)
    db.commit()
    db.refresh(db_sensor)
    return db_sensor


@router.get("/{sensor_id}/data", response_model=SensorDataResponse)
async def get_sensor_data(
    sensor_id: int,
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(100, ge=1, le=10000),
    db: Session = next(get_db())
):
    """获取传感器数据"""
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="传感器不存在")
    
    # 默认查询最近24小时
    if not end_time:
        end_time = datetime.now()
    if not start_time:
        start_time = end_time - timedelta(hours=24)
    
    query = db.query(SensorData).filter(
        SensorData.sensor_id == sensor_id,
        SensorData.timestamp >= start_time,
        SensorData.timestamp <= end_time
    )
    
    data_points = query.order_by(desc(SensorData.timestamp)).limit(limit).all()
    
    # 计算统计信息
    values = [dp.value for dp in data_points]
    stats = {}
    if values:
        stats = {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "count": len(values)
        }
    
    return SensorDataResponse(
        sensor_id=sensor.id,
        sensor_name=sensor.name,
        sensor_type=sensor.type.value if hasattr(sensor.type, 'value') else sensor.type,
        unit=sensor.unit,
        data=[
            SensorDataPoint(timestamp=dp.timestamp, value=dp.value, quality=dp.quality)
            for dp in data_points
        ],
        stats=stats
    )


@router.post("/{sensor_id}/data")
async def add_sensor_data(
    sensor_id: int,
    value: float,
    timestamp: Optional[datetime] = None,
    quality: str = "good",
    db: Session = next(get_db())
):
    """添加传感器数据点"""
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="传感器不存在")
    
    if not timestamp:
        timestamp = datetime.now()
    
    data_point = SensorData(
        sensor_id=sensor_id,
        value=value,
        timestamp=timestamp,
        quality=quality
    )
    db.add(data_point)
    
    # 更新传感器最后活跃时间
    sensor.last_seen = timestamp
    db.commit()
    
    return {"success": True, "data_point_id": data_point.id}
