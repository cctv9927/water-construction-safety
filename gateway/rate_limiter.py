"""Redis 限流模块（安全加固版）

增强：
- 全局限流：100请求/分钟（基于 IP）
- 敏感接口独立限流（登录 10次/分钟）
- Redis 滑动窗口算法
- 限流响应头：X-RateLimit-Limit, X-RateLimit-Remaining, Retry-After
"""

from __future__ import annotations

import time
from typing import Optional, Dict
from dataclasses import dataclass

import redis.asyncio as redis
from fastapi import HTTPException, Request, status

from .config import RateLimitConfig
from .logger import get_logger


@dataclass
class RateLimitResult:
    """限流结果"""
    allowed: bool
    limit: int
    remaining: int
    reset_at: int  # Unix timestamp
    retry_after: int  # seconds


class EndpointRateLimitConfig:
    """端点级别限流配置"""

    # 敏感端点的独立限流规则（覆盖全局）
    ENDPOINT_LIMITS: Dict[str, tuple[int, int]] = {
        # (limit, window_seconds)
        "/auth/login": (10, 60),       # 登录：10次/分钟
        "/auth/refresh": (20, 60),     # 刷新 token：20次/分钟
        "/auth/logout": (30, 60),      # 登出：30次/分钟
    }

    @classmethod
    def get_limit(cls, path: str) -> tuple[int, int]:
        """获取端点的限流配置"""
        for endpoint, (limit, window) in cls.ENDPOINT_LIMITS.items():
            if path.startswith(endpoint):
                return limit, window
        return None, None  # 使用全局默认


class RateLimiter:
    """基于 Redis 的限流器"""

    def __init__(
        self,
        config: Optional[RateLimitConfig] = None,
        redis_client: Optional[redis.Redis] = None
    ):
        self.config = config or RateLimitConfig()
        self.redis: Optional[redis.Redis] = redis_client
        self.logger = get_logger()
        self._connected = False

    async def connect(self):
        """连接 Redis"""
        if self.redis is None:
            try:
                self.redis = redis.from_url(self.config.redis_url)
                await self.redis.ping()
                self._connected = True
                self.logger.info(f"[RateLimit] 已连接到 Redis: {self.config.redis_url}")
            except Exception as e:
                self.logger.warning(f"[RateLimit] 无法连接 Redis: {e}, 限流功能将禁用")
                self._connected = False

    async def close(self):
        """关闭连接"""
        if self.redis:
            await self.redis.close()
            self._connected = False

    def _get_key(self, identifier: str, endpoint: str = "default") -> str:
        """生成限流 key"""
        return f"ratelimit:{endpoint}:{identifier}"

    def _build_headers(self, result: RateLimitResult) -> dict:
        """构建限流响应头"""
        return {
            "X-RateLimit-Limit": str(result.limit),
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(result.reset_at),
            "Retry-After": str(result.retry_after),
        }

    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str = "default",
        limit: Optional[int] = None,
        window: Optional[int] = None,
        for_login: bool = False,
    ) -> RateLimitResult:
        """检查限流

        使用滑动窗口算法
        """
        if not self.config.enabled or not self._connected:
            # 限流禁用或 Redis 未连接
            return RateLimitResult(
                allowed=True,
                limit=-1,
                remaining=-1,
                reset_at=int(time.time()) + (window or self.config.default_window)
            )

        # 优先使用端点级别的严格限制
        if endpoint != "default":
            ep_limit, ep_window = EndpointRateLimitConfig.get_limit(endpoint)
            if ep_limit is not None:
                limit = ep_limit
                window = ep_window

        limit = limit or self.config.default_limit
        window = window or self.config.default_window
        key = self._get_key(identifier, endpoint)

        try:
            now = time.time()
            window_start = now - window

            # 使用 Redis 有序集合实现滑动窗口
            pipe = self.redis.pipeline()

            # 删除窗口外的旧记录
            pipe.zremrangebyscore(key, 0, window_start)

            # 计算当前请求数
            pipe.zcard(key)

            # 添加当前请求
            pipe.zadd(key, {str(now): now})

            # 设置过期时间
            pipe.expire(key, window)

            results = await pipe.execute()
            current_count = results[1]

            if current_count >= limit:
                # 计算重置时间
                oldest = await self.redis.zrange(key, 0, 0, withscores=True)
                reset_at = int(oldest[0][1] + window) if oldest else int(now + window)
                retry_after = max(1, reset_at - int(now))

                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_at=reset_at,
                    retry_after=retry_after,
                )

            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit - current_count - 1,
                reset_at=int(now + window),
                retry_after=0,
            )

        except Exception as e:
            self.logger.error(f"[RateLimit] 检查限流失败: {e}")
            # 失败时允许请求
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_at=int(time.time() + window),
                retry_after=0,
            )

    async def check_burst_limit(
        self,
        identifier: str,
        endpoint: str = "default"
    ) -> RateLimitResult:
        """检查突发限流（10秒窗口）"""
        limit = int(self.config.default_limit * self.config.burst_multiplier)
        return await self.check_rate_limit(identifier, endpoint, limit, 10)

    def build_headers(self, result: RateLimitResult) -> dict:
        """构建限流响应头"""
        return self._build_headers(result)

    async def reset_limit(self, identifier: str, endpoint: str = "default"):
        """重置限流"""
        if self.redis and self._connected:
            key = self._get_key(identifier, endpoint)
            await self.redis.delete(key)

    async def get_limit_status(
        self,
        identifier: str,
        endpoint: str = "default"
    ) -> Optional[RateLimitResult]:
        """获取限流状态"""
        if not self.redis or not self._connected:
            return None

        key = self._get_key(identifier, endpoint)
        now = time.time()

        try:
            count = await self.redis.zcount(key, now - self.config.default_window, now)
            limit = self.config.default_limit

            return RateLimitResult(
                allowed=count < limit,
                limit=limit,
                remaining=max(0, limit - count),
                reset_at=int(now + self.config.default_window)
            )
        except Exception as e:
            self.logger.error(f"[RateLimit] 获取限流状态失败: {e}")
            return None


class RateLimitDependency:
    """限流 FastAPI 依赖"""

    def __init__(self, limiter: RateLimiter):
        self.limiter = limiter

    async def __call__(
        self,
        request: Request,
        endpoint: Optional[str] = None
    ):
        # 获取标识符（优先使用用户ID，其次 IP）
        identifier = None
        if hasattr(request.state, "user_id"):
            identifier = f"user:{request.state.user_id}"
        else:
            identifier = f"ip:{request.client.host}"

        endpoint = endpoint or request.url.path

        result = await self.limiter.check_rate_limit(identifier, endpoint)

        # 添加响应头
        request.state.rate_limit = result

        if not result.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后再试",
                headers={
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": str(result.remaining),
                    "X-RateLimit-Reset": str(result.reset_at),
                    "Retry-After": str(max(1, result.reset_at - int(time.time())))
                }
            )

        return result
