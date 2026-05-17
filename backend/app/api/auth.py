"""
认证 API 路由（安全加固版）

增强：
- 登录限流（密码错误次数限制 + 账户锁定）
- 审计日志记录
- JWT token 撤销支持
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import (
    UserLogin, TokenResponse, UserCreate, UserResponse
)
from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    authenticate_user,
    revoke_token,
    set_redis_client,
)
from app.config import settings

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    """用户登录（含登录限流、审计日志）"""
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # 使用安全加固版的认证函数
    user, error_msg = await authenticate_user(
        db=db,
        username=credentials.username,
        password=credentials.password,
        ip=client_ip,
        user_agent=user_agent,
    )

    if user is None:
        raise HTTPException(status_code=401, detail=error_msg)

    # 生成带 jti 的 token
    access_token, jti = create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value if hasattr(user.role, 'value') else user.role,
            is_active=user.is_active,
            created_at=user.created_at
        )
    )


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否已存在
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 检查邮箱是否已存在
    if user_data.email:
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="邮箱已被使用")

    # 创建用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, 'value') else user.role,
        is_active=user.is_active,
        created_at=user.created_at
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value if hasattr(current_user.role, 'value') else current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )


@router.post("/refresh")
async def refresh_token(request: Request, current_user: User = Depends(get_current_user)):
    """刷新 Token"""
    access_token, _ = create_access_token(
        data={"sub": str(current_user.id), "username": current_user.username}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.JWT_EXPIRE_MINUTES * 60
    }


@router.post("/logout")
async def logout(request: Request, current_user: User = Depends(get_current_user)):
    """用户登出"""
    # 从请求头获取 token 以撤销 jti
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        from app.auth import decode_token
        payload = decode_token(token)
        if payload and payload.get("jti"):
            await revoke_token(payload["jti"])

    return {"success": True, "message": "已退出登录"}
