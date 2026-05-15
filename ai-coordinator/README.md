# AI Coordinator Module - 多智能体调度模块

## 模块概述

水利工地安全监管系统的核心调度模块，负责协调视觉、传感器、语音等多个 AI Agent，实现统一的事件处理、告警分级和多模态融合。

## 技术栈

- **Web 框架**：FastAPI
- **消息队列**：Redis Stream
- **状态管理**：事件驱动状态机

## 核心功能

### 1. 事件驱动状态机

系统状态流转：

```
NORMAL → VIGILANT → WARNING → CRITICAL → EMERGENCY
              ↑         ↓
          (TIMEOUT 恢复)
```

状态定义：
- **NORMAL**：正常
- **VIGILANT**：警戒（单项告警）
- **WARNING**：警告（多项告警）
- **CRITICAL**：严重（需紧急处理）
- **EMERGENCY**：紧急（全量响应）
- **RECOVERING**：恢复中

### 2. 告警分级（P0/P1/P2）

| 级别 | 说明 | 响应时间 |
|------|------|----------|
| P0 | 紧急 | 立即响应 |
| P1 | 重要 | 快速响应 |
| P2 | 一般 | 正常处理 |

#### 传感器告警规则

| 传感器类型 | P2 (异常) | P1 (警告) | P0 (严重) |
|-----------|----------|----------|----------|
| 温度 | >35°C | >40°C | >45°C |
| 振动 | >2mm/s | >5mm/s | >8mm/s |
| 位移 | >10mm | >20mm | >30mm |
| 风速 | >10m/s | >15m/s | >20m/s |
| 降雨量 | >50mm/h | >100mm/h | >150mm/h |

#### 视觉检测告警规则

| 检测类型 | P0 | P1 | P2 |
|---------|----|----|-----|
| 火焰 | 置信度≥90% | 置信度≥70% | 其他 |
| 危险区域入侵 | 置信度≥90% | 置信度≥70% | 其他 |
| 安全帽缺失 | - | 置信度≥90% | 置信度≥70% |
| 人员检测 | - | 置信度≥90% | 其他 |

#### 语音告警规则

| 意图类型 | 级别 |
|---------|------|
| 紧急求助/火灾/伤亡/疏散指令 | P0 |
| 环境异常/停止指令 | P1 |
| 状态查询/启动指令 | P2 |

### 3. 多模态融合

综合以下数据源进行融合判断：
- **传感器数据**：温度、振动、位移等
- **视觉检测**：火焰、安全帽、人员等
- **语音指令**：求助、告警、命令等

融合算法：
- 时间窗口内（60秒）的告警进行加权融合
- 多源告警分数 = Σ(级别分数 × 置信度 × 来源权重)
- 来源权重：vision=0.4, sensor=0.3, voice=0.3

### 4. 事件路由

| 事件类型 | 路由目标 |
|---------|---------|
| SENSOR_ANOMALY | sensor-collector |
| SENSOR_CRITICAL | sensor-collector |
| VISION_DETECTION | ai-vision |
| VISION_CRITICAL | ai-vision |
| VOICE_ALERT | ai-voice |
| VOICE_COMMAND | ai-voice |
| MANUAL_ALERT | backend |

## API 接口

### 健康检查
```
GET /health
```

### 获取系统状态
```
GET /state
```

### 重置状态
```
POST /state/reset
```

### 传感器事件
```
POST /event/sensor
{
  "sensor_id": "temp-001",
  "sensor_type": "temperature",
  "value": 46.5,
  "location": "zone-a",
  "confidence": 1.0
}
```

### 视觉事件
```
POST /event/vision
{
  "camera_id": "cam-001",
  "detection_type": "fire",
  "confidence": 0.95,
  "location": "zone-a"
}
```

### 语音事件
```
POST /event/voice
{
  "intent_type": "alert_help",
  "raw_text": "救命，这里着火了",
  "confidence": 0.9
}
```

### 手动告警
```
POST /event/manual
{
  "message": "工地发生塌方",
  "level": "P0",
  "location": "zone-b"
}
```

### 获取融合告警
```
GET /fusion/alerts
```

### 跨位置融合
```
GET /fusion/cross-location
```

## Redis Stream

### Stream 列表
- `water:alerts:sensor` - 传感器告警流
- `water:alerts:vision` - 视觉告警流
- `water:alerts:voice` - 语音告警流
- `water:coordinator:events` - 协调器事件流
- `water:actions` - 执行动作流

## 安装

```bash
cd ai-coordinator
pip install -r requirements.txt
```

需要 Redis 服务：
```bash
# Docker
docker run -d -p 6379:6379 redis

# 或本地安装
# https://redis.io/download
```

## 运行

```bash
# 直接运行
python main.py

# 或使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8084
```

## 与其他模块集成

### 模块架构

```
                    ┌─────────────────┐
                    │  ai-coordinator │
                    │   (端口 8084)    │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
    ┌─────▼─────┐      ┌─────▼─────┐      ┌─────▼─────┐
    │ ai-vision │      │   redis   │      │  ai-voice │
    │ (端口8082)│      │  Stream   │      │ (端口8083)│
    └─────┬─────┘      └───────────┘      └─────┬─────┘
          │                                     │
    ┌─────▼─────┐                        ┌─────▼─────┐
    │sensor-col │                        │ TTS/Whisper│
    │ (端口8081)│                        └───────────┘
    └───────────┘
```

### HTTP API 调用

```python
import httpx

# 发送传感器事件
async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8084/event/sensor",
        json={
            "sensor_id": "temp-001",
            "sensor_type": "temperature",
            "value": 46.5,
            "location": "zone-a",
        }
    )
    print(resp.json())

# 获取系统状态
resp = await client.get("http://localhost:8084/state")
print(resp.json())
```

## 开发注意事项

1. Redis Stream 支持消息持久化和消费者组
2. 状态机转换是幂等的，重复事件不会重复触发
3. 融合引擎会自动清理过期告警（60秒窗口）
4. 所有时间戳使用 ISO 8601 格式
