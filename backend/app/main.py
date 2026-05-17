"""
水利建设工地质量安全监管系统 - FastAPI 主入口
"""
from contextlib import asynccontextmanager
from datetime import datetime
import asyncio
from typing import List, Dict, Set
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import ORJSONResponse
from sse_starlette.sse import EventSourceResponse
import redis.asyncio as redis

from app.config import settings
from app.db.database import engine, Base, get_db
from app.models.models import Alert, User, Sensor
from app.schemas.schemas import (
    AlertCreate, AlertUpdate, AlertResponse, AlertListResponse, AlertFilter,
    SensorDataResponse, SensorDataPoint,
    DetectionRequest, DetectionResponse, DetectionBox,
    SandboxModelResponse, VideoClipResponse,
    ExpertQueryRequest, ExpertQueryResponse,
    FormGenerateRequest, FormGenerateResponse,
    TokenResponse, UserLogin, UserCreate, UserResponse,
    BaseResponse
)
from app.auth import get_current_user, create_access_token, verify_password, get_password_hash, set_redis_client
from app.audit import get_audit_logger
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json


# ==================== WebSocket 连接管理 ====================
class ConnectionManager:
    """WebSocket 连接管理器"""
    def __init__(self):
        # alert_id -> set of websocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = defaultdict(set)
        # 所有连接的客户端
        self.all_clients: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, alert_id: int = None):
        await websocket.accept()
        self.all_clients.add(websocket)
        if alert_id:
            self.active_connections[alert_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, alert_id: int = None):
        self.all_clients.discard(websocket)
        if alert_id and websocket in self.active_connections.get(alert_id, set()):
            self.active_connections[alert_id].discard(websocket)
    
    async def send_to_all(self, message: dict):
        """广播消息到所有客户端"""
        disconnected = []
        for connection in self.all_clients:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.all_clients.discard(conn)
    
    async def send_to_alert(self, alert_id: int, message: dict):
        """发送消息到特定告警的订阅者"""
        disconnected = []
        for connection in self.active_connections.get(alert_id, set()):
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.all_clients.discard(conn)
            if alert_id in self.active_connections:
                self.active_connections[alert_id].discard(conn)


manager = ConnectionManager()

# Redis 客户端
redis_client = None


# ==================== 生命周期管理 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global redis_client
    
    # 启动时
    print(f"🚀 启动 {settings.APP_NAME}")
    
    # 创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 数据库表已创建/验证")
    
    # 连接 Redis（供 auth 模块复用）
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        # 设置到 auth 模块
        set_redis_client(redis_client)
        print("✅ Redis 连接成功")
    except Exception as e:
        print(f"⚠️ Redis 连接失败: {e}")
        redis_client = None
        set_redis_client(None)
    
    yield
    
    # 关闭时
    print("🛑 关闭应用...")
    if redis_client:
        await redis_client.close()
    await engine.dispose()


# ==================== FastAPI 应用 ====================
app = FastAPI(
    title=settings.APP_NAME,
    description="水利建设工地质量安全监管系统 API",
    version="1.0.0",
    lifespan=lifespan
)


# ==================== CORS 配置 ====================
# 生产环境：通过环境变量配置允许的域名，禁止 "*"
# 示例：ALLOWED_ORIGINS=https://example.com,https://app.example.com
_origins = settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


# ==================== 安全响应头中间件 ====================
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """添加安全响应头"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Content-Security-Policy 可根据实际情况配置
    return response


# ==================== 异常处理 ====================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "detail": str(exc)}
    )


# ==================== API 路由导入 ====================
from app.api import sensors, alerts, vision, sandbox, expert, auth, websocket as ws_router
from app.knowledge.router import router as knowledge_router

app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["认证"])
app.include_router(sensors.router, prefix=f"{settings.API_PREFIX}/sensors", tags=["传感器"])
app.include_router(alerts.router, prefix=f"{settings.API_PREFIX}/alerts", tags=["告警"])
app.include_router(vision.router, prefix=f"{settings.API_PREFIX}/vision", tags=["视觉检测"])
app.include_router(sandbox.router, prefix=f"{settings.API_PREFIX}/sandbox", tags=["电子沙盘"])
app.include_router(expert.router, prefix=f"{settings.API_PREFIX}/expert", tags=["专家系统"])
app.include_router(ws_router.router, tags=["WebSocket"])
app.include_router(knowledge_router, prefix=f"{settings.API_PREFIX}", tags=["知识库"])


# ==================== 根路由 ====================
@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


# ==================== SSE 状态推送 ====================
@app.get("/sse/status")
async def sse_status(request: Request):
    """SSE 端点：推送系统状态更新"""
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            
            # 获取系统统计
            try:
                db = next(get_db())
                stats = {
                    "active_alerts": db.query(Alert).filter(
                        Alert.status.in_(["pending", "processing"])
                    ).count(),
                    "total_sensors": db.query(Sensor).filter(Sensor.is_active == True).count(),
                    "timestamp": datetime.now().isoformat()
                }
            except:
                stats = {"timestamp": datetime.now().isoformat()}
            
            yield {
                "event": "status",
                "data": json.dumps(stats)
            }
            
            await asyncio.sleep(5)  # 每5秒推送一次
    
    return EventSourceResponse(event_generator())


# ==================== WebSocket 告警推送 ====================
@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket, alert_id: int = None):
    """
    WebSocket 端点：实时告警推送
    - 不传 alert_id：接收所有告警更新
    - 传 alert_id：只接收指定告警的更新
    """
    await manager.connect(websocket, alert_id)
    try:
        while True:
            # 保持连接，接收心跳
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, alert_id)


# ==================== 告警广播辅助函数 ====================
async def broadcast_alert(alert: Alert, action: str = "created"):
    """广播告警更新到所有订阅者"""
    message = {
        "type": "alert_update",
        "action": action,
        "data": {
            "id": alert.id,
            "title": alert.title,
            "level": alert.level.value if hasattr(alert.level, 'value') else alert.level,
            "status": alert.status.value if hasattr(alert.status, 'value') else alert.status,
            "location": alert.location,
            "created_at": alert.created_at.isoformat() if alert.created_at else None
        }
    }
    await manager.send_to_all(message)
    
    # 如果配置了 Redis，也发布到 Redis
    if redis_client:
        try:
            await redis_client.publish("alerts", json.dumps(message))
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
