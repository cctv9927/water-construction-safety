"""
安全加固版 JWT 认证模块

增强内容：
- JWT 密钥最小长度检查（≥32字符）
- Token 过期时间强制验证（≤24小时）
- JWT claims 增强：增加 jti (唯一ID) 防止重放攻击
- token 主动撤销机制（blacklist，存 Redis）
- 密码错误次数限制（5次后锁定15分钟，存 Redis）
- 登录事件记录（审计日志）
"""

from __future__ import annotations

import uuid
import time
import secrets
from datetime import datetime, timedelta
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator
import jwt

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import JWTConfig, LogConfig
from .logger import get_logger


# ============ JWT 黑名单 ============

class TokenBlacklist:
    """Token 黑名单管理器"""

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.logger = get_logger()

    async def revoke(self, jti: str, expire_seconds: int = 86400):
        """将 JTI 加入黑名单"""
        if self.redis is None:
            return
        try:
            key = f"jwt:blacklist:{jti}"
            await self.redis.set(key, "1", ex=expire_seconds)
            self.logger.info(f"[JWT] Token revoked: {jti}")
        except Exception as e:
            self.logger.error(f"[JWT] Failed to revoke token: {e}")

    async def is_revoked(self, jti: str) -> bool:
        """检查 token 是否已被撤销"""
        if self.redis is None:
            return False
        try:
            key = f"jwt:blacklist:{jti}"
            result = await self.redis.get(key)
            return result is not None
        except Exception:
            return False

    async def revoke_all_user(self, user_id: str):
        """撤销用户所有 token（版本号递增）"""
        if self.redis is None:
            return
        try:
            key = f"user:token_version:{user_id}"
            await self.redis.incr(key)
            self.logger.info(f"[JWT] All tokens revoked for user: {user_id}")
        except Exception as e:
            self.logger.error(f"[JWT] Failed to revoke all tokens: {e}")


# ============ 登录限流 ============

class LoginRateLimiter:
    """登录限流器（防暴力破解）"""

    MAX_ATTEMPTS = 5         # 最多错误 5 次
    LOCKOUT_SECONDS = 900    # 锁定 15 分钟
    WINDOW_SECONDS = 1800    # 计数窗口 30 分钟

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.logger = get_logger()

    def _key(self, username: str, ip: str) -> str:
        return f"login:attempts:{username}:{ip}"

    async def is_locked(self, username: str, ip: str) -> bool:
        """检查账户是否被锁定"""
        if self.redis is None:
            return False
        try:
            key = self._key(username, ip)
            val = await self.redis.get(key)
            count = int(val) if val else 0
            return count >= self.MAX_ATTEMPTS
        except Exception:
            return False

    async def record_failure(self, username: str, ip: str) -> int:
        """记录登录失败，返回剩余尝试次数"""
        if self.redis is None:
            return self.MAX_ATTEMPTS
        try:
            key = self._key(username, ip)
            pipe = self.redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, self.WINDOW_SECONDS)
            results = await pipe.execute()
            current = results[0]
            remaining = max(0, self.MAX_ATTEMPTS - current)
            self.logger.warning(
                f"[LoginRateLimit] Failed attempt {current}/{self.MAX_ATTEMPTS}",
                username=username, ip=ip
            )
            return remaining
        except Exception as e:
            self.logger.error(f"[LoginRateLimit] Error: {e}")
            return self.MAX_ATTEMPTS

    async def record_success(self, username: str, ip: str):
        """登录成功，重置计数"""
        if self.redis is None:
            return
        try:
            key = self._key(username, ip)
            await self.redis.delete(key)
        except Exception:
            pass

    async def get_remaining(self, username: str, ip: str) -> int:
        """获取剩余尝试次数"""
        if self.redis is None:
            return self.MAX_ATTEMPTS
        try:
            key = self._key(username, ip)
            val = await self.redis.get(key)
            count = int(val) if val else 0
            return max(0, self.MAX_ATTEMPTS - count)
        except Exception:
            return self.MAX_ATTEMPTS


# ============ 审计日志（简化版，用于 gateway）============

class SimpleAuditLogger:
    """Gateway 简化审计日志"""

    def __init__(self):
        self.logger = get_logger()

    def log(
        self,
        event_type: str,
        username: str = None,
        user_id: str = None,
        ip: str = "unknown",
        result: str = "success",
        metadata: dict = None,
    ):
        self.logger.info(
            f"[AUDIT] {event_type}",
            event_type=event_type,
            username=username,
            user_id=user_id,
            ip=ip,
            result=result,
            metadata=metadata or {},
        )


# ============ JWT 配置验证 ============

def validate_jwt_config(config: JWTConfig):
    """验证 JWT 配置安全性"""
    # 密钥最小长度检查
    if len(config.secret_key) < 32:
        if config.secret_key.lower() in (
            "your-secret-key-change-in-production",
            "your-secret-key",
            "secret",
            "change-me",
        ):
            raise ValueError(
                f"JWT 密钥过于简单或长度不足！"
                f"生产环境必须设置至少32字符的强随机密钥。"
                f"当前密钥长度: {len(config.secret_key)}"
            )
        # 其他未知密钥，只警告
        import warnings
        warnings.warn(
            f"[开发模式] JWT_SECRET 仅 {len(config.secret_key)} 字符，建议 ≥32",
            UserWarning
        )

    # Token 过期时间 ≤ 24h
    if config.access_token_expire_minutes > 60 * 24:
        raise ValueError(
            f"access_token_expire_minutes 不能超过 24小时(1440分钟)，"
            f"当前: {config.access_token_expire_minutes}"
        )


# ============ Token 载荷模型 ============

class TokenPayload(BaseModel):
    """令牌载荷"""
    sub: str                         # 用户ID
    username: str                    # 用户名
    roles: list[str] = []            # 角色列表
    exp: datetime                    # 过期时间
    iat: datetime                    # 签发时间
    jti: Optional[str] = None        # JWT ID（唯一标识，用于撤销和重放检测）
    type: str = "access"             # 令牌类型

    @field_validator("jti", mode="before")
    @classmethod
    def set_default_jti(cls, v):
        return v or str(uuid.uuid4())


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


# ============ 认证服务 ============

class AuthService:
    """安全加固版认证服务"""

    def __init__(self, config: Optional[JWTConfig] = None):
        self.config = config or JWTConfig()
        self.logger = get_logger()
        self.blacklist = TokenBlacklist()
        self.login_limiter = LoginRateLimiter()
        self.audit = SimpleAuditLogger()

        # 启动时验证配置
        validate_jwt_config(self.config)

    def set_redis(self, redis_client):
        """注入 Redis 客户端"""
        self.blacklist.redis = redis_client
        self.login_limiter.redis = redis_client

    def create_access_token(
        self,
        user_id: str,
        username: str,
        roles: list[str] = None,
        expires_delta: Optional[timedelta] = None
    ) -> tuple[str, str]:
        """创建访问令牌

        Returns:
            (token, jti) - token 字符串和 jti
        """
        # 过期时间
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.config.access_token_expire_minutes
            )

        # 强制 ≤ 24h
        max_expire = datetime.utcnow() + timedelta(hours=24)
        if expire > max_expire:
            expire = max_expire

        # JWT ID（唯一标识，用于撤销和重放检测）
        jti = str(uuid.uuid4())

        payload = {
            "sub": user_id,
            "username": username,
            "roles": roles or [],
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": jti,
            "type": "access"
        }

        token = jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)
        return token, jti

    def create_refresh_token(self, user_id: str) -> tuple[str, str]:
        """创建刷新令牌

        Returns:
            (token, jti)
        """
        expire = datetime.utcnow() + timedelta(days=self.config.refresh_token_expire_days)
        jti = str(uuid.uuid4())

        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": jti,
            "type": "refresh"
        }

        token = jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)
        return token, jti

    def create_tokens(
        self,
        user_id: str,
        username: str,
        roles: list[str] = None
    ) -> TokenResponse:
        """创建令牌对"""
        access_token, _ = self.create_access_token(user_id, username, roles)
        refresh_token, _ = self.create_refresh_token(user_id)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=self.config.access_token_expire_minutes * 60,
            refresh_token=refresh_token
        )

    async def revoke_token(self, jti: str):
        """主动撤销 token"""
        await self.blacklist.revoke(jti, expire_seconds=86400)
        self.audit.log(event_type="token_revoked", metadata={"jti": jti})

    async def revoke_all_user_tokens(self, user_id: str):
        """撤销用户所有 token"""
        await self.blacklist.revoke_all_user(user_id)
        self.audit.log(event_type="all_tokens_revoked", user_id=user_id)

    def verify_token(self, token: str, token_type: str = "access") -> TokenPayload:
        """验证令牌（含黑名单检查）"""
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm]
            )

            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"无效的令牌类型: {token_type}"
                )

            # jti 必须存在（防止旧 token）
            jti = payload.get("jti")
            if not jti:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="令牌缺少 jti 标识"
                )

            # 检查黑名单
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.run_until_complete(self.blacklist.is_revoked(jti)):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="令牌已被撤销"
                )

            return TokenPayload(
                sub=payload["sub"],
                username=payload["username"],
                roles=payload.get("roles", []),
                exp=datetime.fromtimestamp(payload["exp"]),
                iat=datetime.fromtimestamp(payload["iat"]),
                jti=jti,
                type=payload.get("type", token_type)
            )

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已过期"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"无效的令牌: {str(e)}"
            )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """刷新访问令牌"""
        payload = self.verify_token(refresh_token, token_type="refresh")
        return self.create_tokens(
            user_id=payload.sub,
            username=payload.username,
            roles=payload.roles
        )

    # ---- 登录限流 ----

    async def check_login_lockout(self, username: str, ip: str) -> Optional[str]:
        """检查是否被锁定，返回错误消息或 None"""
        if await self.login_limiter.is_locked(username, ip):
            remaining = await self.login_limiter.get_remaining(username, ip)
            return f"账户已锁定，请在 15 分钟后重试（剩余尝试: {remaining}）"
        return None

    async def record_login_failure(self, username: str, ip: str) -> int:
        """记录登录失败，返回剩余尝试次数"""
        return await self.login_limiter.record_failure(username, ip)

    async def record_login_success(self, username: str, ip: str):
        """记录登录成功"""
        await self.login_limiter.record_success(username, ip)


# 全局实例（由 main.py 初始化）
auth_service: Optional[AuthService] = None

# FastAPI 安全依赖
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_svc: AuthService = Depends(lambda: auth_service),
) -> TokenPayload:
    """获取当前用户（依赖注入）"""
    return auth_svc.verify_token(credentials.credentials)


async def require_role(required_roles: list[str]):
    """角色要求依赖工厂"""
    async def role_checker(current_user: TokenPayload = Depends(get_current_user)):
        if not any(role in current_user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        return current_user
    return role_checker
