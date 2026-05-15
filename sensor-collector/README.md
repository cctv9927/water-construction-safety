# 传感器数据采集模块 (sensor-collector)

## 用途

通过 MQTT 协议采集工地现场的各类传感器数据（温度、压力、震动、位移、流量、风速、降雨量等），对数据进行校验、清洗、格式化后，统一上报到 IoT Hub REST API。

## 技术栈

- Python 3.10+
- asyncio + aiomqtt（异步 MQTT 客户端）
- httpx（异步 HTTP 上报）
- pydantic（数据模型验证）
- PyYAML（配置文件）

## 目录结构

```
sensor-collector/
├── config.yaml          # 配置文件
├── requirements.txt     # 依赖
├── README.md            # 本文件
├── collector/
│   ├── __init__.py
│   ├── main.py          # 入口，asyncio main
│   ├── mqtt_client.py   # MQTT 订阅客户端
│   ├── validator.py     # 数据校验与清洗
│   ├── formatter.py     # 数据格式化
│   ├── reporter.py       # IoT Hub REST API 上报
│   └── models.py         # Pydantic 数据模型
└── tests/
    ├── __init__.py
    └── test_sensor.py    # 单元测试
```

## 配置说明（config.yaml）

```yaml
mqtt:
  broker: "mqtt://localhost:1883"
  client_id: "sensor-collector-01"
  topics:
    - "site/+/temperature"
    - "site/+/pressure"
    - "site/+/vibration"
    - "site/+/displacement"
    - "site/+/flow"
    - "site/+/wind_speed"
    - "site/+/rainfall"
  qos: 1

iot_hub:
  base_url: "http://localhost:8080/api/v1/iot"
  timeout: 10
  retry: 3

collector:
  report_interval: 5    # 秒，批量上报间隔
  batch_size: 100       # 最大批量大小
  log_level: "INFO"
```

## 运行方式

```bash
pip install -r requirements.txt
python -m collector.main
```

## 测试

```bash
pytest tests/test_sensor.py -v
```

## MQTT 数据格式

传感器发布到 MQTT 的 JSON 数据格式：

```json
{
  "sensor_id": "T-001",
  "sensor_type": "temperature",
  "site_id": "site-A",
  "value": 25.6,
  "unit": "℃",
  "timestamp": "2025-01-15T10:30:00Z",
  "location": {
    "lat": 30.5728,
    "lng": 114.2525,
    "altitude": 45.2
  }
}
```

## 上报格式（IoT Hub REST API）

```json
{
  "site_id": "site-A",
  "sensor_id": "T-001",
  "sensor_type": "temperature",
  "value": 25.6,
  "unit": "℃",
  "timestamp": "2025-01-15T10:30:00Z",
  "location": {
    "lat": 30.5728,
    "lng": 114.2525,
    "altitude": 45.2
  },
  "quality": "good",
  "raw_value": 25.6
}
```
