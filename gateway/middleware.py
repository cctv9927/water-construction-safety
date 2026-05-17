"""中间件模块"""

from __future__ import annotations

import time
from typing import Callable, Optional
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logger import get_logger
from .rate_limiter import RateLimiter, RateLimitDependency


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求ID中间件 - 为每个请求添加唯一ID"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """日志中间件 - 记录请求和响应"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = get_logger()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # 记录请求
        self.logger.info(
            "请求开始",
            method=request.method,
            path=request.url.path,
            query=str(request.query_params),
            client=request.client.host if request.client else "unknown",
            request_id=getattr(request.state, "request_id", "unknown")
        )

        response = await call_next(request)

        # 计算耗时
        duration = time.time() - start_time

        # 记录响应
        self.logger.info(
            "请求完成",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration=f"{duration:.3f}s",
            request_id=getattr(request.state, "request_id", "unknown")
        )

        # 添加响应头
        response.headers["X-Response-Time"] = f"{duration:.3f}s"

        return response


class CORSMiddleware(BaseHTTPMiddleware):
    """CORS 中间件（安全加固版）"""

    # 生产环境禁止的源
    BLOCKED_ORIGINS = {"*", "null", "undefined"}

    def __init__(
        self,
        app: ASGIApp,
        allow_origins: list[str] = None,
        allow_methods: list[str] = None,
        allow_headers: list[str] = None
    ):
        super().__init__(app)
        # 过滤掉非法源
        self.allow_origins = [
            o for o in (allow_origins or []) if o not in self.BLOCKED_ORIGINS
        ]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        origin = request.headers.get("origin")

        # 生产环境必须配置 allow_origins 且不能包含 *
        if origin and (
            origin in self.allow_origins
            or (origin.startswith("http://localhost") and not self.allow_origins)
        ):
            response = await call_next(request)

            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = ", ".join(
                m.upper() for m in self.allow_methods
            )
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
            response.headers["Access-Control-Allow-Credentials"] = "true"
            # 安全头
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

            return response

        # 没有匹配的 origin，拒绝跨域请求
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""

    def __init__(self, app: ASGIApp, limiter: RateLimiter):
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 跳过 OPTIONS 请求
        if request.method == "OPTIONS":
            return await call_next(request)

        # 获取标识符
        identifier = None
        if hasattr(request.state, "user_id"):
            identifier = f"user:{request.state.user_id}"
        elif request.client:
            identifier = f"ip:{request.client.host}"
        else:
            identifier = "unknown"

        endpoint = request.url.path

        # 检查限流
        result = await self.limiter.check_rate_limit(identifier, endpoint)

        if not result.allowed:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail="请求过于频繁",
                headers={
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": str(result.remaining),
                    "X-RateLimit-Reset": str(result.reset_at),
                    "Retry-After": str(max(1, result.reset_at - int(time.time())))
                }
            )

        response = await call_next(request)

        # 添加限流头（从 request.state 获取已计算的限流结果）
        rate_result = getattr(request.state, "rate_limit", None)
        if rate_result:
            for key, value in self.limiter.build_headers(rate_result).items():
                response.headers[key] = value

        return response


def setup_middleware(app: ASGIApp, limiter: Optional[RateLimiter] = None, **kwargs):
    """设置中间件链"""
    # 请求ID
    app.add_middleware(RequestIDMiddleware)

    # 日志
    app.add_middleware(LoggingMiddleware)

    # CORS（安全加固版）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=kwargs.get("allow_origins", [])
    )

    # 限流（全局）
    if limiter:
        app.add_middleware(RateLimitMiddleware, limiter=limiter)
