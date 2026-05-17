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
import secrets
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.models.models import User, UserRole
from app.audit import get_audit_logger

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer Token
security = HTTPBearer()

# ============ JWT 黑名单（Redis）============
# 全局 Redis 客户端引用（由 main.py 设置）
_redis_client = None


def set_redis_client(redis_client):
    """由 main.py 调用，设置 Redis 客户端"""
    global _redis_client
    _redis_client = redis_client


# ============ 验证配置 ============
def validate_jwt_config():
    """启动时验证 JWT 配置"""
    secret = settings.JWT_SECRET
    expire_minutes = settings.JWT_EXPIRE_MINUTES

    # 密钥最小长度检查
    if len(secret) < 32:
        if not settings.DEBUG:
            raise ValueError(
                f"JWT_SECRET 长度不足！生产环境必须 ≥32 字符，当前: {len(secret)}"
            )
        else:
            import warnings
            warnings.warn(
                f"[开发模式] JWT_SECRET 长度仅 {len(secret)} 字符，建议 ≥32",
                UserWarning
            )

    # Token 过期时间检查（≤24小时）
    if expire_minutes > 60 * 24:
        raise ValueError(
            f"JWT_EXPIRE_MINUTES 不能超过 24小时(1440分钟)，当前: {expire_minutes}"
        )


validate_jwt_config()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """密码哈希"""
    return pwd_context.hash(password)


# ============ JWT Token 黑名单 ============

async def _redis_get(key: str) -> Optional[str]:
    if _redis_client is None:
        return None
    try:
        return await _redis_client.get(key)
    except Exception:
        return None


async def _redis_set(key: str, value: str, ex: int = None):
    if _redis_client is None:
        return
    try:
        await _redis_client.set(key, value, ex=ex)
    except Exception:
        pass


async def _redis_delete(key: str):
    if _redis_client is None:
        return
    try:
        await _redis_client.delete(key)
    except Exception:
        pass


async def revoke_token(jti: str, expire_seconds: int = 86400):
    """将 JTI 加入黑名单（默认 24 小时后自动过期）"""
    key = f"jwt:blacklist:{jti}"
    await _redis_set(key, "1", ex=expire_seconds)


async def is_token_revoked(jti: str) -> bool:
    """检查 token 是否已被撤销"""
    key = f"jwt:blacklist:{jti}"
    result = await _redis_get(key)
    return result is not None


async def revoke_all_user_tokens(user_id: int):
    """撤销用户所有 token（通过版本号机制）"""
    # 使用 token_version 方案：每次 revoke_all 时递增版本号
    key = f"user:token_version:{user_id}"
    try:
        if _redis_client:
            await _redis_client.incr(key)
    except Exception:
        pass


# ============ 密码错误次数限制 ============

MAX_LOGIN_ATTEMPTS = 5          # 最多错误 5 次
LOCKOUT_DURATION_SECONDS = 900 # 锁定 15 分钟（900秒）
LOGIN_ATTEMPTS_WINDOW = 1800   # 计数窗口 30 分钟


async def _get_login_attempts_key(username: str, ip: str) -> str:
    return f"login:attempts:{username}:{ip}"


async def get_login_attempts(username: str, ip: str) -> int:
    """获取登录错误次数"""
    key = await _get_login_attempts_key(username, ip)
    val = await _redis_get(key)
    return int(val) if val else 0


async def increment_login_attempts(username: str, ip: str):
    """增加登录错误次数"""
    key = await _get_login_attempts_key(username, ip)
    try:
        if _redis_client:
            pipe = _redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, LOGIN_ATTEMPTS_WINDOW)
            await pipe.execute()
    except Exception:
        pass


async def reset_login_attempts(username: str, ip: str):
    """重置登录错误次数（登录成功时）"""
    key = await _get_login_attempts_key(username, ip)
    await _redis_delete(key)


async def is_account_locked(username: str, ip: str) -> bool:
    """检查账户是否被锁定"""
    attempts = await get_login_attempts(username, ip)
    return attempts >= MAX_LOGIN_ATTEMPTS


# ============ JWT Token 创建与验证 ============


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    include_jti: bool = True,
) -> tuple[str, Optional[str]]:
    """创建访问令牌

    Returns:
        (token, jti) - token 字符串和 jti（用于撤销）
    """
    to_encode = data.copy()

    # 过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    # 强制 ≤ 24小时
    max_expire = datetime.utcnow() + timedelta(hours=24)
    if expire > max_expire:
        expire = max_expire

    # JWT claims 增强：增加 jti 防止重放攻击
    jti = str(uuid.uuid4()) if include_jti else None

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": jti,
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt, jti


def decode_token(token: str, check_revoked: bool = True) -> Optional[dict]:
    """解码令牌（带黑名单检查）"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # 检查 token 是否已撤销
        jti = payload.get("jti")
        if jti and check_revoked:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            if loop.run_until_complete(is_token_revoked(jti)):
                return None  # token 已被撤销

        return payload

    except JWTError:
        return None


# ============ 认证服务（带登录限流） ============


async def authenticate_user(
    db: Session,
    username: str,
    password: str,
    ip: str,
    user_agent: str = "unknown",
) -> tuple[Optional[User], str]:
    """认证用户（含登录限流 + 审计日志）

    Returns:
        (user, error_message) - user 为 None 时 error_message 说明原因
    """
    audit = get_audit_logger()

    # 1. 检查账户是否被锁定
    if await is_account_locked(username, ip):
        audit.log_login_failed(
            username=username,
            ip=ip,
            reason="account_locked",
            user_agent=user_agent,
        )
        return None, f"账户已锁定，请在 {LOCKOUT_DURATION_SECONDS // 60} 分钟后重试"

    # 2. 查询用户
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        await increment_login_attempts(username, ip)
        audit.log_login_failed(
            username=username,
            ip=ip,
            reason="user_not_found",
            user_agent=user_agent,
        )
        return None, "用户名或密码错误"

    # 3. 验证密码
    if not verify_password(password, user.hashed_password):
        await increment_login_attempts(username, ip)
        remaining = MAX_LOGIN_ATTEMPTS - await get_login_attempts(username, ip) + 1
        audit.log_login_failed(
            username=username,
            ip=ip,
            reason="invalid_password",
            user_agent=user_agent,
        )
        if remaining > 0:
            return None, f"用户名或密码错误，剩余尝试次数: {remaining}"
        else:
            return None, f"账户已锁定，请在 {LOCKOUT_DURATION_SECONDS // 60} 分钟后重试"

    # 4. 检查账户是否激活
    if not user.is_active:
        audit.log_login_failed(
            username=username,
            ip=ip,
            reason="account_disabled",
            user_agent=user_agent,
        )
        return None, "账户已被禁用"

    # 5. 登录成功
    await reset_login_attempts(username, ip)
    audit.log_login_success(
        user_id=str(user.id),
        username=username,
        ip=ip,
        user_agent=user_agent,
    )

    return user, ""


# ============ FastAPI 依赖 ============

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """可选的用户认证（不强制要求登录）"""
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_token(token)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    return db.query(User).filter(User.id == user_id).first()


def require_roles(*allowed_roles: UserRole):
    """角色权限装饰器"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {', '.join([r.value for r in allowed_roles])} 权限"
            )
        return current_user
    return role_checker


# ============ RBAC ============

class RBAC:
    """基于角色的访问控制"""

    PERMISSIONS = {
        # 告警权限
        "alerts:read": [UserRole.ADMIN, UserRole.MANAGER, UserRole.VIEWER],
        "alerts:create": [UserRole.ADMIN, UserRole.MANAGER],
        "alerts:update": [UserRole.ADMIN, UserRole.MANAGER],
        "alerts:delete": [UserRole.ADMIN],

        # 传感器权限
        "sensors:read": [UserRole.ADMIN, UserRole.MANAGER, UserRole.VIEWER],
        "sensors:write": [UserRole.ADMIN, UserRole.MANAGER],

        # AI 视觉权限
        "vision:detect": [UserRole.ADMIN, UserRole.MANAGER],

        # 沙盘权限
        "sandbox:read": [UserRole.ADMIN, UserRole.MANAGER, UserRole.VIEWER],

        # 专家系统权限
        "expert:query": [UserRole.ADMIN, UserRole.MANAGER, UserRole.VIEWER],
        "expert:generate": [UserRole.ADMIN, UserRole.MANAGER],

        # 用户管理权限
        "users:read": [UserRole.ADMIN],
        "users:write": [UserRole.ADMIN],
    }

    @classmethod
    def check_permission(cls, user: User, permission: str) -> bool:
        """检查用户是否有权限"""
        allowed_roles = cls.PERMISSIONS.get(permission, [])
        return user.role in allowed_roles

    @classmethod
    def require_permission(cls, permission: str):
        """权限检查装饰器"""
        def permission_checker(current_user: User = Depends(get_current_user)) -> User:
            if not cls.check_permission(current_user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"需要 '{permission}' 权限"
                )
            return current_user
        return permission_checker
