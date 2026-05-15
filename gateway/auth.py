"""JWT 认证模块"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Any
import jwt
from pydantic import BaseModel
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import JWTConfig


class TokenPayload(BaseModel):
    """令牌载荷"""
    sub: str                    # 用户ID
    username: str                # 用户名
    roles: list[str] = []        # 角色列表
    exp: datetime                # 过期时间
    iat: datetime = None        # 签发时间


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class AuthService:
    """认证服务"""

    def __init__(self, config: Optional[JWTConfig] = None):
        self.config = config or JWTConfig()

    def create_access_token(
        self,
        user_id: str,
        username: str,
        roles: list[str] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建访问令牌"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.config.access_token_expire_minutes)

        payload = {
            "sub": user_id,
            "username": username,
            "roles": roles or [],
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }

        return jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """创建刷新令牌"""
        expire = datetime.utcnow() + timedelta(days=self.config.refresh_token_expire_days)

        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }

        return jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)

    def create_tokens(
        self,
        user_id: str,
        username: str,
        roles: list[str] = None
    ) -> TokenResponse:
        """创建令牌对"""
        access_token = self.create_access_token(user_id, username, roles)
        refresh_token = self.create_refresh_token(user_id)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=self.config.access_token_expire_minutes * 60,
            refresh_token=refresh_token
        )

    def verify_token(self, token: str, token_type: str = "access") -> TokenPayload:
        """验证令牌"""
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

            return TokenPayload(
                sub=payload["sub"],
                username=payload["username"],
                roles=payload.get("roles", []),
                exp=datetime.fromtimestamp(payload["exp"]),
                iat=datetime.fromtimestamp(payload["iat"])
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

    def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """刷新访问令牌"""
        payload = self.verify_token(refresh_token, token_type="refresh")

        return self.create_tokens(
            user_id=payload.sub,
            username=payload.username,
            roles=payload.roles
        )


# FastAPI 安全依赖
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends()
) -> TokenPayload:
    """获取当前用户（依赖注入）"""
    return auth_service.verify_token(credentials.credentials)


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
