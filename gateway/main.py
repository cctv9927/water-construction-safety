"""统一接入网关 - FastAPI 主入口"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import httpx
import uvicorn
import yaml
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import GatewayConfig, BackendConfig
from .auth import AuthService, TokenResponse, TokenPayload, get_current_user
from .rate_limiter import RateLimiter
from .middleware import setup_middleware
from .logger import get_logger, LogConfig


# 创建 FastAPI 应用
app = FastAPI(
    title="水利工地安全监管系统 - 统一接入网关",
    version="1.0.0",
    description="所有感知层服务的统一入口"
)

# 全局状态
config: Optional[GatewayConfig] = None
auth_service: Optional[AuthService] = None
rate_limiter: Optional[RateLimiter] = None
logger = get_logger()


# ============ 配置加载 ============

def load_config(config_path: str = "config.yaml") -> GatewayConfig:
    """加载配置"""
    path = Path(config_path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return GatewayConfig(**raw)
    else:
        return GatewayConfig()


# ============ API 模型 ============

class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ProxyRequest(BaseModel):
    path: str
    method: str = "GET"
    body: Optional[dict] = None
    params: Optional[dict] = None


# ============ 认证接口 ============

@app.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """用户登录"""
    global auth_service

    # TODO: 实际应查询数据库验证用户
    # 这里简化为示例
    if request.username == "admin" and request.password == "admin123":
        return auth_service.create_tokens(
            user_id="user_001",
            username=request.username,
            roles=["admin"]
        )
    elif request.username == "viewer" and request.password == "viewer123":
        return auth_service.create_tokens(
            user_id="user_002",
            username=request.username,
            roles=["viewer"]
        )
    else:
        raise HTTPException(status_code=401, detail="用户名或密码错误")


@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """刷新令牌"""
    global auth_service
    return auth_service.refresh_access_token(request.refresh_token)


@app.get("/auth/me", response_model=TokenPayload)
async def get_me(current_user: TokenPayload = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user


# ============ 后端代理接口 ============

async def proxy_request(
    backend_url: str,
    path: str,
    method: str = "GET",
    body: Optional[dict] = None,
    params: Optional[dict] = None,
    headers: Optional[dict] = None
) -> dict:
    """代理请求到后端服务"""
    url = f"{backend_url}{path}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if method == "GET":
                response = await client.get(url, params=params, headers=headers)
            elif method == "POST":
                response = await client.post(url, json=body, params=params, headers=headers)
            elif method == "PUT":
                response = await client.put(url, json=body, params=params, headers=headers)
            elif method == "DELETE":
                response = await client.delete(url, params=params, headers=headers)
            else:
                raise ValueError(f"不支持的方法: {method}")

            return {
                "status_code": response.status_code,
                "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                "headers": dict(response.headers)
            }

        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail=f"后端服务不可用: {backend_url}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"代理请求失败: {str(e)}")


# 传感器采集服务代理
@app.api_route("/api/sensors/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def sensors_proxy(
    path: str,
    request: Request,
    current_user: TokenPayload = Depends(get_current_user)
):
    """代理到传感器采集服务"""
    return await proxy_request(
        backend_url=config.backend.sensor_collector,
        path=f"/{path}",
        method=request.method,
        body=await request.json() if request.method in ["POST", "PUT"] else None,
        params=dict(request.query_params)
    )


# 视频流服务代理
@app.api_route("/api/video/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def video_proxy(
    path: str,
    request: Request,
    current_user: TokenPayload = Depends(get_current_user)
):
    """代理到视频流服务"""
    return await proxy_request(
        backend_url=config.backend.video_streamer,
        path=f"/{path}",
        method=request.method,
        body=await request.json() if request.method in ["POST", "PUT"] else None,
        params=dict(request.query_params)
    )


# 无人机服务代理
@app.api_route("/api/drone/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def drone_proxy(
    path: str,
    request: Request,
    current_user: TokenPayload = Depends(get_current_user)
):
    """代理到无人机服务"""
    return await proxy_request(
        backend_url=config.backend.drone_integration,
        path=f"/{path}",
        method=request.method,
        body=await request.json() if request.method in ["POST", "PUT"] else None,
        params=dict(request.query_params)
    )


# AI 协调服务代理
@app.api_route("/api/ai/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def ai_proxy(
    path: str,
    request: Request,
    current_user: TokenPayload = Depends(get_current_user)
):
    """代理到 AI 协调服务"""
    return await proxy_request(
        backend_url=config.backend.ai_coordinator,
        path=f"/{path}",
        method=request.method,
        body=await request.json() if request.method in ["POST", "PUT"] else None,
        params=dict(request.query_params)
    )


# ============ 健康检查与状态 ============

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": config.service.name,
        "version": "1.0.0"
    }


@app.get("/status")
async def get_status(current_user: TokenPayload = Depends(get_current_user)):
    """获取系统状态"""
    return {
        "gateway": config.service.name,
        "version": "1.0.0",
        "backends": {
            "sensor_collector": config.backend.sensor_collector,
            "video_streamer": config.backend.video_streamer,
            "drone_integration": config.backend.drone_integration,
            "ai_coordinator": config.backend.ai_coordinator,
        },
        "user": {
            "id": current_user.sub,
            "username": current_user.username,
            "roles": current_user.roles
        }
    }


# ============ 启动与关闭 ============

@app.on_event("startup")
async def startup_event():
    """启动事件"""
    global config, auth_service, rate_limiter

    # 加载配置
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    config = load_config(config_path)

    # 初始化日志
    global logger
    logger = get_logger(LogConfig(**config.log.model_dump()))

    # 初始化认证服务
    auth_service = AuthService(config.jwt)

    # 初始化限流
    rate_limiter = RateLimiter(config.rate_limit)
    await rate_limiter.connect()

    # 设置中间件
    setup_middleware(app, rate_limiter, allow_origins=config.service.cors_origins)

    logger.info("=" * 50)
    logger.info(f"统一接入网关启动")
    logger.info(f"服务名称: {config.service.name}")
    logger.info(f"监听地址: {config.service.host}:{config.service.port}")
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    global rate_limiter

    logger.info("网关正在关闭...")

    if rate_limiter:
        await rate_limiter.close()

    logger.info("网关已关闭")


# ============ 主函数 ============

def main():
    """主函数"""
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cfg = load_config(config_path)

    # 生成默认配置
    if not Path(config_path).exists():
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg.model_dump(), f, default_flow_style=False)
        print(f"已生成默认配置: {config_path}")

    uvicorn.run(
        "gateway.main:app",
        host=cfg.service.host,
        port=cfg.service.port,
        workers=1,  # uvicorn 自身支持多进程
        log_level="info",
        reload=cfg.service.reload
    )


if __name__ == "__main__":
    main()
