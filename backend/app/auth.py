from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.config import settings
from app.db.database import get_db
from app.models import User, UserRole

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer Token
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET, 
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """解码令牌"""
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
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
    
    user_id: int = payload.get("sub")
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
