from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "水利建设工地质量安全监管系统"
    DEBUG: bool = True
    API_PREFIX: str = "/api"
    
    # CORS 配置
    ALLOWED_ORIGINS: str = "*"  # 生产环境设置为具体域名，多个用逗号分隔
    
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
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_jwt_secret()
    
    def _validate_jwt_secret(self):
        """验证 JWT 密钥安全性"""
        weak_secrets = [
            "change-me-in-production",
            "change-me",
            "secret",
            "password",
            "your-secret-key",
        ]
        secret_lower = self.JWT_SECRET.lower()
        
        # 检查是否为弱密钥
        is_weak = any(weak in secret_lower for weak in weak_secrets)
        is_short = len(self.JWT_SECRET) < 32
        
        if is_weak or is_short:
            if not self.DEBUG:
                # 生产环境必须使用强密钥
                raise ValueError(
                    f"JWT_SECRET 过于简单或长度不足！"
                    f"生产环境请设置至少32字符的强随机密钥。"
                    f"当前密钥长度: {len(self.JWT_SECRET)}"
                )
            else:
                # 开发环境仅打印警告
                import warnings
                warnings.warn(
                    f"[开发模式] 使用弱 JWT_SECRET: {self.JWT_SECRET[:10]}..."
                    f"生产环境请设置至少32字符的强随机密钥。",
                    UserWarning
                )


settings = Settings()
