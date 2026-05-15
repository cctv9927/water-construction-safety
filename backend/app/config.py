from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "水利建设工地质量安全监管系统"
    DEBUG: bool = True
    API_PREFIX: str = "/api"
    
    # 数据库配置
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/water_safety"
    
    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT 配置
    JWT_SECRET: str = "change-me-in-production-water-safety-2024"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24小时
    
    # 文件上传配置
    UPLOAD_DIR: str = "/tmp/water-safety/uploads"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # AI 模型配置
    VISION_MODEL_PATH: str = "/models/yolov8n.onnx"
    EMBEDDING_MODEL_PATH: str = "/models/bge-base-zh.onnx"
    
    # 传感器配置
    SENSOR_DATA_RETENTION_DAYS: int = 90
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
