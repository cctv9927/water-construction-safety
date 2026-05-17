"""
传感器数据模块集成测试

测试覆盖：
- 获取传感器列表
- 获取传感器详情
- 创建传感器
- 获取传感器数据
- 添加传感器数据点
- 传感器类型过滤
- 数据统计计算
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta


class MockSensor:
    """Mock 传感器对象"""
    def __init__(self, sensor_id=1, name="位移传感器", sensor_type="displacement",
                 location="大坝A区", latitude=30.0, longitude=114.0,
                 device_id="DISP-001", unit="mm", is_active=True,
                 min_value=0.0, max_value=100.0, last_seen=None, created_at=None):
        self.id = sensor_id
        self.name = name
        self.type = MagicMock()
        self.type.value = sensor_type
        self.location = location
        self.latitude = latitude
        self.longitude = longitude
        self.device_id = device_id
        self.unit = unit
        self.min_value = min_value
        self.max_value = max_value
        self.is_active = is_active
        self.last_seen = last_seen or datetime.now()
        self.created_at = created_at or datetime.now()


class MockSensorData:
    """Mock 传感器数据点"""
    def __init__(self, sensor_id=1, value=25.3, timestamp=None, quality="good"):
        self.id = 1
        self.sensor_id = sensor_id
        self.value = value
        self.timestamp = timestamp or datetime.now()
        self.quality = quality


def get_mock_sensor_db(sensors=None):
    """创建带传感器数据的 mock DB"""
    def inner():
        session = MagicMock()
        if sensors is not None:
            mock_query = MagicMock()
            mock_query.filter.return_value.order_by.return_value.all.return_value = sensors
            mock_query.filter.return_value.first.return_value = sensors[0] if sensors else None
            mock_query.filter.return_value.count.return_value = len(sensors)
            session.query.return_value = mock_query
        yield session
    return inner


@pytest.mark.asyncio
async def test_list_sensors_success(client):
    """测试获取传感器列表"""
    mock_sensors = [
        MockSensor(sensor_id=1, name="位移传感器-01", sensor_type="displacement"),
        MockSensor(sensor_id=2, name="水位传感器-01", sensor_type="water_level"),
        MockSensor(sensor_id=3, name="温度传感器-01", sensor_type="temperature"),
    ]

    def get_db():
        session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = mock_sensors
        session.query.return_value = mock_query
        yield session

    with patch("app.api.sensors.get_db", get_db):
        response = await client.get("/api/sensors/")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["name"] == "位移传感器-01"


@pytest.mark.asyncio
async def test_list_sensors_filter_by_type(client):
    """测试按类型过滤传感器"""
    mock_sensors = [
        MockSensor(sensor_id=2, name="水位传感器-01", sensor_type="water_level"),
    ]

    def get_db():
        session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = mock_sensors
        session.query.return_value = mock_query
        yield session

    with patch("app.api.sensors.get_db", get_db):
        response = await client.get("/api/sensors/?type=water_level")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "water_level"


@pytest.mark.asyncio
async def test_list_sensors_filter_inactive(client):
    """测试过滤停用状态的传感器"""
    def get_db():
        session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = []
        session.query.return_value = mock_query
        yield session

    with patch("app.api.sensors.get_db", get_db):
        response = await client.get("/api/sensors/?is_active=false")
    
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_sensor_detail_success(client):
    """测试获取传感器详情"""
    mock_sensor = MockSensor(sensor_id=5, name="高精度位移传感器", sensor_type="displacement")

    def get_db():
        session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_sensor
        session.query.return_value = mock_query
        yield session

    with patch("app.api.sensors.get_db", get_db):
        response = await client.get("/api/sensors/5")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 5
    assert data["name"] == "高精度位移传感器"


@pytest.mark.asyncio
async def test_get_sensor_not_found(client):
    """测试获取不存在的传感器 → 404"""
    def get_db():
        session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        session.query.return_value = mock_query
        yield session

    with patch("app.api.sensors.get_db", get_db):
        response = await client.get("/api/sensors/9999")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_sensor_success(client, test_sensor_data):
    """测试创建传感器"""
    mock_sensor = MockSensor(sensor_id=10, **test_sensor_data)

    def get_db():
        session = MagicMock()
        session.add = MagicMock()
        session.commit = MagicMock()
        session.refresh = MagicMock(return_value=mock_sensor)
        yield session

    with patch("app.api.sensors.get_db", get_db):
        response = await client.post(
            "/api/sensors/",
            json=test_sensor_data
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == test_sensor_data["name"]
    assert "id" in data


@pytest.mark.asyncio
async def test_get_sensor_data_success(client):
    """测试获取传感器数据"""
    mock_sensor = MockSensor(sensor_id=1, name="位移传感器-01", sensor_type="displacement", unit="mm")
    now = datetime.now()
    mock_data_points = [
        MockSensorData(sensor_id=1, value=20.1, timestamp=now - timedelta(hours=2)),
        MockSensorData(sensor_id=1, value=22.5, timestamp=now - timedelta(hours=1)),
        MockSensorData(sensor_id=1, value=25.3, timestamp=now),
    ]

    def get_db():
        session = MagicMock()
        # 第一次查询传感器，第二次查询数据
        mock_query = MagicMock()
        mock_query.filter.return_value.first.side_effect = [mock_sensor, None]
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_data_points
        session.query.return_value = mock_query
        yield session

    with patch("app.api.sensors.get_db", get_db):
        response = await client.get("/api/sensors/1/data?limit=100")
    
    assert response.status_code == 200
    data = response.json()
    assert data["sensor_id"] == 1
    assert "data" in data
    assert len(data["data"]) == 3
    assert "stats" in data
    assert data["stats"]["min"] == 20.1
    assert data["stats"]["max"] == 25.3
    assert data["stats"]["avg"] == pytest.approx(22.63, rel=0.01)


@pytest.mark.asyncio
async def test_get_sensor_data_with_time_range(client):
    """测试带时间范围的传感器数据查询"""
    mock_sensor = MockSensor(sensor_id=2, name="水位传感器", sensor_type="water_level")
    mock_data = [MockSensorData(sensor_id=2, value=10.0 + i, timestamp=datetime.now() - timedelta(hours=i))
                 for i in range(5)]

    def get_db():
        session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.side_effect = [mock_sensor, None]
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_data
        session.query.return_value = mock_query
        yield session

    with patch("app.api.sensors.get_db", get_db):
        start = datetime.now() - timedelta(days=1)
        end = datetime.now()
        response = await client.get(
            f"/api/sensors/2/data?start_time={start.isoformat()}&end_time={end.isoformat()}"
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["sensor_id"] == 2
    assert len(data["data"]) == 5


@pytest.mark.asyncio
async def test_get_sensor_data_sensor_not_found(client):
    """测试获取不存在传感器的数据 → 404"""
    def get_db():
        session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        session.query.return_value = mock_query
        yield session

    with patch("app.api.sensors.get_db", get_db):
        response = await client.get("/api/sensors/9999/data")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_sensor_data_stats_calculation(client):
    """测试传感器数据统计计算"""
    mock_sensor = MockSensor(sensor_id=3, name="振动传感器", sensor_type="vibration", unit="mm/s")
    mock_data = [
        MockSensorData(sensor_id=3, value=1.5, timestamp=datetime.now() - timedelta(minutes=30)),
        MockSensorData(sensor_id=3, value=2.0, timestamp=datetime.now() - timedelta(minutes=20)),
        MockSensorData(sensor_id=3, value=2.5, timestamp=datetime.now() - timedelta(minutes=10)),
        MockSensorData(sensor_id=3, value=3.0, timestamp=datetime.now()),
    ]

    def get_db():
        session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.side_effect = [mock_sensor, None]
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_data
        session.query.return_value = mock_query
        yield session

    with patch("app.api.sensors.get_db", get_db):
        response = await client.get("/api/sensors/3/data")
    
    assert response.status_code == 200
    data = response.json()
    stats = data["stats"]
    assert stats["min"] == 1.5
    assert stats["max"] == 3.0
    assert stats["avg"] == 2.25
    assert stats["count"] == 4


@pytest.mark.asyncio
async def test_add_sensor_data_success(client):
    """测试添加传感器数据点"""
    mock_sensor = MockSensor(sensor_id=1, name="位移传感器", last_seen=datetime.now())

    def get_db():
        session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_sensor
        session.query.return_value = mock_query
        session.add = MagicMock()
        session.commit = MagicMock()
        yield session

    with patch("app.api.sensors.get_db", get_db):
        response = await client.post(
            "/api/sensors/1/data",
            params={"value": 28.7, "quality": "good"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_add_sensor_data_sensor_not_found(client):
    """测试向不存在的传感器添加数据 → 404"""
    def get_db():
        session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        session.query.return_value = mock_query
        yield session

    with patch("app.api.sensors.get_db", get_db):
        response = await client.post(
            "/api/sensors/9999/data",
            params={"value": 100.0}
        )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_sensor_data_with_timestamp(client):
    """测试带时间戳添加传感器数据"""
    mock_sensor = MockSensor(sensor_id=4, name="温度传感器")

    def get_db():
        session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_sensor
        session.query.return_value = mock_query
        session.add = MagicMock()
        session.commit = MagicMock()
        yield session

    with patch("app.api.sensors.get_db", get_db):
        timestamp = datetime.now() - timedelta(hours=1)
        response = await client.post(
            "/api/sensors/4/data",
            params={"value": 22.5, "timestamp": timestamp.isoformat(), "quality": "good"}
        )
    
    assert response.status_code == 200
