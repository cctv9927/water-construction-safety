from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "水利建设工地质量安全监管系统"
    DEBUG: bool = True
    API_PREFIX: str = "/api"

    # CORS 配置
    # 生产环境必须设置为具体域名，禁止 "*"！
    # 多个域名用逗号分隔，例如：https://example.com,https://app.example.com
    ALLOWED_ORIGINS: str = ""  # 默认为空，强制要求配置

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
        self._validate_cors()

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

    def _validate_cors(self):
        """验证 CORS 配置安全性"""
        if not self.DEBUG and (not self.ALLOWED_ORIGINS or self.ALLOWED_ORIGINS == "*"):
            raise ValueError(
                "CORS 配置不安全！生产环境必须设置具体的 ALLOWED_ORIGINS 域名，"
                "禁止使用 * 通配符。"
            )
        if self.ALLOWED_ORIGINS == "*":
            import warnings
            warnings.warn(
                "[警告] CORS 配置使用通配符 *，生产环境请设置为具体域名。",
                UserWarning
            )


settings = Settings()
