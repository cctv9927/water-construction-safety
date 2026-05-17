"""
Pytest 配置和共享 Fixtures
"""
import pytest
import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

# 确保 backend/app 在路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 设置测试环境变量
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_water_safety.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-testing-only-32chars")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("ALLOWED_ORIGINS", "*")


@pytest.fixture(scope="session")
def event_loop():
    """创建 session 级别的事件循环"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_redis():
    """Mock Redis 客户端"""
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.publish = AsyncMock(return_value=1)
    mock.close = AsyncMock()
    mock.zremrangebyscore = AsyncMock()
    mock.zcard = AsyncMock(return_value=0)
    mock.zadd = AsyncMock()
    mock.expire = AsyncMock()
    mock.zcount = AsyncMock(return_value=0)
    mock.zrange = AsyncMock(return_value=[])
    mock.pipeline = MagicMock()
    pipe = AsyncMock()
    pipe.zremrangebyscore = AsyncMock()
    pipe.zcard = AsyncMock()
    pipe.zadd = AsyncMock()
    pipe.expire = AsyncMock()
    pipe.execute = AsyncMock(return_value=[None, 0, None, None])
    mock.pipeline.return_value = pipe
    return mock


@pytest.fixture
def mock_db_session():
    """Mock 数据库会话"""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.query = MagicMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def app_with_mocks(mock_redis, mock_db_session):
    """创建带 mock 的 FastAPI 应用"""
    # Mock broadcast_alert 避免 WebSocket 依赖
    with patch("app.main.redis_client", mock_redis), \
         patch("app.main.broadcast_alert", AsyncMock()), \
         patch("app.main.engine") as mock_engine, \
         patch("app.main.ConnectionManager") as mock_manager:
        
        mock_manager_instance = MagicMock()
        mock_manager_instance.connect = AsyncMock()
        mock_manager_instance.disconnect = MagicMock()
        mock_manager_instance.send_to_all = AsyncMock()
        mock_manager_instance.send_to_alert = AsyncMock()
        mock_manager.return_value = mock_manager_instance
        
        # Mock lifespan 中的异步操作
        with patch("app.db.database.engine") as mock_db_engine:
            mock_conn = AsyncMock()
            mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_conn.__aexit__ = AsyncMock()
            mock_db_engine.begin = MagicMock(return_value=mock_conn)
            
            from app.main import app
            yield app


@pytest.fixture
async def client(app_with_mocks):
    """异步 HTTP 客户端"""
    from httpx import AsyncClient, ASGITransport
    transport = ASGITransport(app=app_with_mocks)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_user_data():
    """测试用户数据"""
    return {
        "username": "test_admin",
        "email": "admin@test.com",
        "password": "TestPass123!",
        "full_name": "测试管理员",
        "role": "admin"
    }


@pytest.fixture
def test_sensor_data():
    """测试传感器数据"""
    return {
        "name": "大坝位移传感器-01",
        "type": "displacement",
        "location": "大坝A区",
        "latitude": 30.5728,
        "longitude": 114.2526,
        "device_id": "DISP-001",
        "unit": "mm",
        "min_value": 0.0,
        "max_value": 100.0
    }


@pytest.fixture
def test_alert_data():
    """测试告警数据"""
    return {
        "title": "测试告警：基坑位移超限",
        "description": "基坑A区水平位移监测数据超过预警阈值",
        "level": "P1",
        "location": "基坑A区",
        "latitude": 30.5728,
        "longitude": 114.2526,
        "evidence_images": [],
        "metadata": {"threshold": 50.0, "actual": 65.3}
    }


@pytest.fixture
def auth_token(test_user_data):
    """生成测试用 JWT token"""
    from app.auth import create_access_token
    token = create_access_token(
        data={"sub": "999", "username": test_user_data["username"]}
    )
    return token


@pytest.fixture
def auth_headers(auth_token):
    """带认证的请求头"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def expired_token():
    """生成过期 token"""
    from app.auth import create_access_token
    token = create_access_token(
        data={"sub": "999", "username": "test"},
        expires_delta=timedelta(seconds=-10)  # 已过期
    )
    return token


@pytest.fixture
def expired_auth_headers(expired_token):
    """带过期 token 的请求头"""
    return {"Authorization": f"Bearer {expired_token}"}
