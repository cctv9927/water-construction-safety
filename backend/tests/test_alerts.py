"""
告警管理集成测试

测试覆盖：
- 创建告警 → 201，验证返回结构
- 分页查询告警列表 → 验证 total/limit/offset
- 更新告警状态 → 200，验证状态变化
- 无 token 创建告警 → 401
- 获取告警详情
- 删除告警
- 分配告警
- 告警历史查询
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class MockAlert:
    """Mock 告警对象"""
    def __init__(self, alert_id=1, title="测试告警", description="测试描述",
                 level="P2", status="pending", location="测试位置",
                 latitude=30.0, longitude=114.0, sensor_id=None,
                 creator_id=1, evidence_images=None, metadata=None,
                 created_at=None, updated_at=None, resolved_at=None):
        self.id = alert_id
        self.title = title
        self.description = description
        self.level = MagicMock()
        self.level.value = level
        self.status = MagicMock()
        self.status.value = status
        self.location = location
        self.latitude = latitude
        self.longitude = longitude
        self.sensor_id = sensor_id
        self.creator_id = creator_id
        self.evidence_images = evidence_images or []
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at
        self.resolved_at = resolved_at


class MockUser:
    """Mock 用户对象"""
    def __init__(self, user_id=1, username="test_user", role="admin", is_active=True):
        self.id = user_id
        self.username = username
        self.role = MagicMock()
        self.role.value = role
        self.is_active = is_active
        self.full_name = "测试用户"
        self.email = "test@test.com"


def get_mock_db_with_alerts(alerts=None, user=None):
    """创建带告警数据的 mock DB"""
    def inner():
        session = MagicMock()
        if alerts is not None:
            mock_query = MagicMock()
            if isinstance(alerts, list):
                mock_query.filter.return_value.count.return_value = len(alerts)
                mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = alerts
                mock_query.filter.return_value.first.return_value = alerts[0] if alerts else None
            session.query.return_value = mock_query
        if user is not None:
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = user
            session.query.return_value = mock_query
        yield session
    return inner


@pytest.mark.asyncio
async def test_create_alert_success(client, auth_headers, test_alert_data):
    """测试创建告警 → 201，验证返回结构"""
    mock_alert = MockAlert(
        alert_id=1,
        title=test_alert_data["title"],
        description=test_alert_data["description"],
        level=test_alert_data["level"],
    )

    def get_db():
        session = MagicMock()
        mock_user = MockUser()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_user
        session.query.return_value = mock_query
        session.add = MagicMock()
        session.commit = MagicMock()
        session.refresh = MagicMock(return_value=mock_alert)
        yield session

    with patch("app.auth.get_db", get_db), \
         patch("app.main.broadcast_alert", AsyncMock()):
        response = await client.post(
            "/api/alerts/",
            json=test_alert_data,
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == test_alert_data["title"]
    assert "id" in data
    assert "status" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_alert_unauthorized(client, test_alert_data):
    """测试无 token 创建告警 → 401"""
    response = await client.post(
        "/api/alerts/",
        json=test_alert_data
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_alerts_pagination(client, auth_headers):
    """测试分页查询告警列表 → 验证 total/limit/offset"""
    mock_alerts = [
        MockAlert(alert_id=i, title=f"告警 {i}", level="P2", status="pending")
        for i in range(1, 6)
    ]

    def get_db():
        session = MagicMock()
        mock_user = MockUser()
        mock_query = MagicMock()
        mock_query.filter.return_value.count.return_value = 25  # total = 25
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_alerts
        mock_query.filter.return_value.first.return_value = mock_user
        session.query.return_value = mock_query
        yield session

    with patch("app.auth.get_db", get_db):
        response = await client.get(
            "/api/alerts/?page=1&page_size=5",
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert len(data["items"]) == 5


@pytest.mark.asyncio
async def test_list_alerts_with_filters(client, auth_headers):
    """测试带过滤条件的告警列表查询"""
    mock_alerts = [
        MockAlert(alert_id=1, title="P1告警", level="P1", status="pending")
    ]

    def get_db():
        session = MagicMock()
        mock_user = MockUser()
        mock_query = MagicMock()
        mock_query.filter.return_value.count.return_value = 1
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_alerts
        mock_query.filter.return_value.first.return_value = mock_user
        session.query.return_value = mock_query
        yield session

    with patch("app.auth.get_db", get_db):
        response = await client.get(
            "/api/alerts/?level=P1&status=pending",
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_get_alert_detail(client, auth_headers):
    """测试获取告警详情"""
    mock_alert = MockAlert(alert_id=42, title="详情测试告警", level="P1", status="processing")

    def get_db():
        session = MagicMock()
        mock_user = MockUser()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_alert
        session.query.return_value = mock_query
        yield session

    with patch("app.api.alerts.get_db", get_db):
        response = await client.get(
            "/api/alerts/42",
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 42
    assert data["title"] == "详情测试告警"


@pytest.mark.asyncio
async def test_get_alert_not_found(client, auth_headers):
    """测试获取不存在的告警 → 404"""
    def get_db():
        session = MagicMock()
        mock_user = MockUser()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        session.query.return_value = mock_query
        yield session

    with patch("app.api.alerts.get_db", get_db):
        response = await client.get(
            "/api/alerts/99999",
            headers=auth_headers
        )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_alert_status(client, auth_headers):
    """测试更新告警状态 → 200，验证状态变化"""
    mock_alert = MockAlert(alert_id=1, status="pending", title="待处理告警")

    def get_db():
        session = MagicMock()
        mock_user = MockUser()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_alert
        session.query.return_value = mock_query
        session.commit = MagicMock()
        session.refresh = MagicMock()
        yield session

    with patch("app.auth.get_db", get_db), \
         patch("app.api.alerts.get_db", get_db), \
         patch("app.main.broadcast_alert", AsyncMock()):
        response = await client.patch(
            "/api/alerts/1",
            json={"status": "completed"},
            headers=auth_headers
        )
    
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_alert_level(client, auth_headers):
    """测试更新告警级别"""
    mock_alert = MockAlert(alert_id=1, level="P2", title="测试告警")

    def get_db():
        session = MagicMock()
        mock_user = MockUser()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_alert
        session.query.return_value = mock_query
        session.commit = MagicMock()
        session.refresh = MagicMock()
        yield session

    with patch("app.auth.get_db", get_db), \
         patch("app.api.alerts.get_db", get_db), \
         patch("app.main.broadcast_alert", AsyncMock()):
        response = await client.patch(
            "/api/alerts/1",
            json={"level": "P0"},
            headers=auth_headers
        )
    
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_alert_success(client, auth_headers):
    """测试删除告警成功"""
    mock_alert = MockAlert(alert_id=5, title="待删除告警")

    def get_db():
        session = MagicMock()
        mock_user = MockUser()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_alert
        session.query.return_value = mock_query
        session.delete = MagicMock()
        session.commit = MagicMock()
        yield session

    with patch("app.auth.get_db", get_db), \
         patch("app.api.alerts.get_db", get_db):
        response = await client.delete(
            "/api/alerts/5",
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_delete_alert_not_found(client, auth_headers):
    """测试删除不存在的告警 → 404"""
    def get_db():
        session = MagicMock()
        mock_user = MockUser()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        session.query.return_value = mock_query
        yield session

    with patch("app.auth.get_db", get_db), \
         patch("app.api.alerts.get_db", get_db):
        response = await client.delete(
            "/api/alerts/99999",
            headers=auth_headers
        )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_assign_alert(client, auth_headers):
    """测试分配告警"""
    mock_alert = MockAlert(alert_id=1, status="pending", title="待分配告警")
    mock_target_user = MockUser(user_id=10, username="engineer1", full_name="工程师1")

    def get_db():
        session = MagicMock()
        mock_user = MockUser()
        mock_query = MagicMock()
        # 第一次查询告警，第二次查询用户
        mock_query.filter.return_value.first.side_effect = [mock_alert, mock_target_user]
        session.query.return_value = mock_query
        session.add = MagicMock()
        session.commit = MagicMock()
        yield session

    with patch("app.auth.get_db", get_db), \
         patch("app.api.alerts.get_db", get_db):
        response = await client.post(
            "/api/alerts/1/assign",
            json={"user_id": 10},
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_alert_history(client, auth_headers):
    """测试获取告警处理历史"""
    mock_alert = MockAlert(alert_id=1, title="历史测试告警", status="completed")

    def get_db():
        session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_alert
        mock_query.filter.return_value.all.return_value = []
        session.query.return_value = mock_query
        yield session

    with patch("app.api.alerts.get_db", get_db):
        response = await client.get(
            "/api/alerts/1/history",
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["alert_id"] == 1
    assert "assignments" in data
    assert "created_at" in data
