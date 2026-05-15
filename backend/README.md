# 水利建设工地质量安全监管系统 - 后端 API 服务

## 技术栈
- **框架**: FastAPI (异步高性能)
- **ORM**: SQLAlchemy 2.0
- **数据库**: PostgreSQL + TimescaleDB
- **认证**: JWT + RBAC
- **消息队列**: Redis Stream

## 目录结构

```
backend/
├── app/
│   ├── main.py          # FastAPI 入口
│   ├── config.py        # 配置管理
│   ├── auth.py          # JWT + RBAC 认证
│   ├── models/          # SQLAlchemy 模型
│   ├── schemas/         # Pydantic schemas
│   ├── api/             # API 路由
│   │   ├── sensors.py   # 传感器 API
│   │   ├── alerts.py    # 告警 API
│   │   ├── vision.py    # AI 视觉 API
│   │   └── sandbox.py   # 电子沙盘 API
│   │   └── expert.py    # 专家系统 API
│   └── db/
│       └── database.py  # 数据库连接
├── alembic/             # 数据库迁移
├── requirements.txt
└── README.md
```

## 核心 API

### 认证
- `POST /api/auth/login` - 用户登录

### 传感器
- `GET /api/sensors/{id}/data` - 获取传感器时序数据

### 告警
- `GET /api/alerts` - 获取告警列表（支持筛选）
- `POST /api/alerts` - 创建告警
- `PATCH /api/alerts/{id}` - 更新告警状态
- `WebSocket /ws/alerts` - 实时告警推送

### AI 视觉
- `POST /api/vision/detect` - 图片检测

### 电子沙盘
- `GET /api/sandbox/models` - 获取 3D 模型列表
- `GET /api/sandbox/videos` - 获取监控视频列表

### 专家系统
- `POST /api/expert/query` - RAG 知识问答
- `POST /api/expert/forms/generate` - 表格自动生成

## 快速启动

```bash
# 安装依赖
pip install -r requirements.txt

# 数据库迁移
alembic upgrade head

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| DATABASE_URL | PostgreSQL 连接字符串 | postgresql://user:pass@localhost:5432/water_safety |
| REDIS_URL | Redis 连接字符串 | redis://localhost:6379/0 |
| JWT_SECRET | JWT 密钥 | change-me-in-production |
| JWT_ALGORITHM | JWT 算法 | HS256 |
| JWT_EXPIRE_MINUTES | Token 过期时间(分钟) | 60 |

## API 认证

所有 API（除登录外）需要在请求头中携带 JWT Token：

```
Authorization: Bearer <token>
```

## 角色权限

| 角色 | 权限 |
|------|------|
| admin | 全部权限 |
| manager | 告警管理、传感器查看、专家系统 |
| viewer | 告警查看、传感器查看 |
