from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    VIEWER = "viewer"


class AlertLevel(str, enum.Enum):
    P0 = "P0"  # 立即处理
    P1 = "P1"  # 当天处理
    P2 = "P2"  # 计划处理


class AlertStatus(str, enum.Enum):
    PENDING = "pending"      # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    VERIFIED = "verified"    # 已复核
    CLOSED = "closed"        # 已关闭


class SensorType(str, enum.Enum):
    TEMPERATURE = "temperature"      # 温度
    PRESSURE = "pressure"            # 压力
    VIBRATION = "vibration"          # 震动
    DISPLACEMENT = "displacement"    # 位移
    FLOW = "flow"                    # 流量
    WIND_SPEED = "wind_speed"        # 风速
    RAINFALL = "rainfall"            # 降雨量
    HUMIDITY = "humidity"            # 湿度
    WATER_LEVEL = "water_level"      # 水位


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(Enum(UserRole), default=UserRole.VIEWER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联
    alerts = relationship("Alert", back_populates="creator")
    alert_assignments = relationship("AlertAssignment", back_populates="user")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    level = Column(Enum(AlertLevel), default=AlertLevel.P2)
    status = Column(Enum(AlertStatus), default=AlertStatus.PENDING)
    
    # 位置信息
    location = Column(String(200))  # 位置描述
    latitude = Column(Float)
    longitude = Column(Float)
    
    # 关联数据
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=True)
    video_clip_id = Column(Integer, ForeignKey("video_clips.id"), nullable=True)
    
    # 图片证据
    evidence_images = Column(JSON, default=list)  # 图片URL列表
    
    # 元数据
    metadata = Column(JSON, default=dict)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # 创建者
    creator_id = Column(Integer, ForeignKey("users.id"))
    
    # 关联
    creator = relationship("User", back_populates="alerts")
    sensor = relationship("Sensor", back_populates="alerts")
    assignments = relationship("AlertAssignment", back_populates="alert")
    workflow_steps = relationship("WorkflowStep", back_populates="alert")


class AlertAssignment(Base):
    __tablename__ = "alert_assignments"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text)
    
    alert = relationship("Alert", back_populates="assignments")
    user = relationship("User", back_populates="alert_assignments")


class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(Enum(SensorType), nullable=False)
    location = Column(String(200))
    latitude = Column(Float)
    longitude = Column(Float)
    
    # 设备信息
    device_id = Column(String(100), unique=True, index=True)
    unit = Column(String(20))  # 单位
    min_value = Column(Float)
    max_value = Column(Float)
    
    # 状态
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联
    alerts = relationship("Alert", back_populates="sensor")
    data_points = relationship("SensorData", back_populates="sensor")


class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # 附加信息
    quality = Column(String(20), default="good")  # good, bad, uncertain
    metadata = Column(JSON, default=dict)
    
    sensor = relationship("Sensor", back_populates="data_points")


class VideoClip(Base):
    __tablename__ = "video_clips"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    camera_id = Column(String(100), index=True)
    location = Column(String(200))
    
    # 文件信息
    file_path = Column(String(500))
    thumbnail_path = Column(String(500))
    duration = Column(Float)  # 秒
    file_size = Column(Integer)  # 字节
    
    # 时间范围
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    
    # AI 检测结果
    detection_results = Column(JSON, default=list)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SandboxModel(Base):
    __tablename__ = "sandbox_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    model_type = Column(String(50))  # gltf, glb, 3dtiles
    file_path = Column(String(500))
    
    # 元数据
    bounds = Column(JSON)  # 边界框
    center_point = Column(JSON)  # 中心点
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    step_name = Column(String(100), nullable=False)
    step_order = Column(Integer, default=0)
    
    # 执行信息
    executor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    result = Column(Text)
    
    # 状态
    is_completed = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    alert = relationship("Alert", back_populates="workflow_steps")
