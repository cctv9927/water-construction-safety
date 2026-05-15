"""统一接入网关配置"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class JWTConfig(BaseModel):
    """JWT 配置"""
    secret_key: str = Field(default="your-secret-key-change-in-production", description="密钥")
    algorithm: str = Field(default="HS256", description="算法")
    access_token_expire_minutes: int = Field(default=30, description="访问令牌过期时间(分钟)")
    refresh_token_expire_days: int = Field(default=7, description="刷新令牌过期时间(天)")


class RateLimitConfig(BaseModel):
    """限流配置"""
    enabled: bool = Field(default=True, description="是否启用限流")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    default_limit: int = Field(default=100, description="默认请求限制(次/分钟)")
    default_window: int = Field(default=60, description="时间窗口(秒)")
    burst_multiplier: float = Field(default=1.5, description="突发倍数")


class LogConfig(BaseModel):
    """日志配置"""
    level: str = Field(default="INFO", description="日志级别")
    format: str = Field(default="json", description="格式: json/text")
    output: str = Field(default="stdout", description="输出: stdout/file")
    file_path: Optional[str] = Field(default=None, description="日志文件路径")


class ServiceConfig(BaseModel):
    """服务配置"""
    name: str = Field(default="water-safety-gateway", description="服务名称")
    host: str = Field(default="0.0.0.0", description="监听地址")
    port: int = Field(default=8000, description="监听端口")
    workers: int = Field(default=4, description="工作进程数")
    reload: bool = Field(default=False, description="开发模式热重载")
    cors_origins: list[str] = Field(default=["*"], description="CORS 允许的源")


class BackendConfig(BaseModel):
    """后端服务配置"""
    sensor_collector: str = Field(default="http://localhost:8001", description="传感器采集服务")
    video_streamer: str = Field(default="http://localhost:8081", description="视频流服务")
    drone_integration: str = Field(default="http://localhost:8082", description="无人机服务")
    ai_coordinator: str = Field(default="http://localhost:8002", description="AI 协调服务")


class GatewayConfig(BaseModel):
    """网关总配置"""
    jwt: JWTConfig = Field(default_factory=JWTConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    log: LogConfig = Field(default_factory=LogConfig)
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    backend: BackendConfig = Field(default_factory=BackendConfig)
