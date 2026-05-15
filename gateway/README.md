# 统一接入网关 (gateway)

## 模块概述

作为水利工地安全监管系统的统一入口，提供认证、限流、日志和后端服务代理功能。

## 技术栈

- **Web 框架**: FastAPI + Uvicorn
- **认证**: JWT (PyJWT)
- **限流**: Redis (滑动窗口算法)
- **日志**: 结构化 JSON 日志

## 核心功能

### 1. JWT 认证
- 访问令牌 + 刷新令牌
- 角色权限验证
- FastAPI 依赖注入

### 2. Redis 限流
- 滑动窗口算法
- 支持突发限流
- 按用户/IP 限流

### 3. 结构化日志
- JSON 格式输出
- 请求追踪 (Request ID)
- 性能指标

### 4. 后端代理
- 统一代理到各感知层服务
- 自动携带认证信息
- 错误处理与重试

## 目录结构

```
gateway/
├── main.py           # FastAPI 主入口
├── auth.py           # JWT 认证
├── rate_limiter.py   # Redis 限流
├── logger.py         # 结构化日志
├── middleware.py     # 中间件链
├── config.py         # 配置模型
├── requirements.txt  # 依赖清单
└── README.md
```

## 配置示例 (config.yaml)

```yaml
jwt:
  secret_key: your-secret-key-change-in-production
  algorithm: HS256
  access_token_expire_minutes: 30
  refresh_token_expire_days: 7

rate_limit:
  enabled: true
  redis_url: redis://localhost:6379/0
  default_limit: 100
  default_window: 60
  burst_multiplier: 1.5

log:
  level: INFO
  format: json
  output: stdout

service:
  name: water-safety-gateway
  host: 0.0.0.0
  port: 8000
  workers: 4
  reload: false
  cors_origins:
    - "*"

backend:
  sensor_collector: http://localhost:8001
  video_streamer: http://localhost:8081
  drone_integration: http://localhost:8082
  ai_coordinator: http://localhost:8002
```

## API 接口

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /auth/login | 用户登录 |
| POST | /auth/refresh | 刷新令牌 |
| GET | /auth/me | 获取当前用户 |

### 代理

| 方法 | 路径 | 说明 |
|------|------|------|
| * | /api/sensors/{path} | 传感器采集服务代理 |
| * | /api/video/{path} | 视频流服务代理 |
| * | /api/drone/{path} | 无人机服务代理 |
| * | /api/ai/{path} | AI 协调服务代理 |

### 系统

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 健康检查 |
| GET | /status | 系统状态 |

## 启动方式

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务（使用默认配置）
python main.py

# 指定配置文件
python main.py config.yaml
```

## 使用示例

### 登录获取令牌

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

响应：
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800,
  "refresh_token": "eyJ..."
}
```

### 调用受保护的 API

```bash
curl http://localhost:8000/api/sensors/streams \
  -H "Authorization: Bearer eyJ..."
```

### 刷新令牌

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ..."}'
```

## 限流说明

- 默认限制：100 请求/分钟
- 突发倍数：1.5x（允许短期超过限制）
- 响应头包含限流信息：
  - `X-RateLimit-Limit`: 限制数
  - `X-RateLimit-Remaining`: 剩余请求数
  - `X-RateLimit-Reset`: 重置时间戳

## 日志格式

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "logger": "gateway",
  "message": "请求完成",
  "method": "GET",
  "path": "/api/sensors/streams",
  "status": 200,
  "duration": "0.123s",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```
