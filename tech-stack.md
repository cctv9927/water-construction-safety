# 水利建设工地质量安全监管系统 - 技术栈文档

## 1. 技术栈总览

### 1.1 技术架构分层

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              客户端层                                        │
│  Web浏览器 (Chrome 90+), 飞书客户端, 移动端H5                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           接入层 / 网关层                                    │
│  Nginx (反向代理/负载均衡), API Gateway (FastAPI), WebSocket Gateway          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              应用服务层                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ API Gateway │ │ IoT Hub     │ │ Alert Svc   │ │ Expert Svc  │            │
│  │ FastAPI     │ │ MQTT/Async  │ │ Redis Stream│ │ LangChain   │            │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ Workflow Svc│ │ Report Svc  │ │ Video Pipe  │ │ Speech Svc  │            │
│  │ BPMN Engine │ │ Pandas      │ │ FFmpeg/gRPC │ │ Whisper/TTS │            │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI / ML 层                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ YOLO推理    │ │ DeepSort    │ │ RAG Engine  │ │ Orchestrator│            │
│  │ ONNX/PyTorch│ │ Tracking    │ │ Milvus/LLM  │ │ LangChain   │            │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据存储层                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ PostgreSQL  │ │ TimescaleDB │ │    Redis    │ │   Milvus    │            │
│  │  + PostGIS  │ │  时序优化    │ │  缓存/队列  │ │   向量检索  │            │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘            │
│                               ┌─────────────┐                               │
│                               │    MinIO    │                               │
│                               │  对象存储   │                               │
│                               └─────────────┘                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              基础设施层                                      │
│  Docker, Kubernetes, MQTT Broker (Eclipse Mosquitto), Kafka                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 核心技术栈详细版本

### 2.1 后端服务技术栈

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **Web框架** | FastAPI | 0.110.x | 高性能异步API框架 |
| **ASGI服务器** | Uvicorn | 0.29.x | ASGI异步服务器 |
| **ORM** | SQLAlchemy | 2.0.x | 异步ORM，支持PostgreSQL |
| **异步驱动** | asyncpg | 0.29.x | PostgreSQL异步驱动 |
| **时序扩展** | TimescaleDB | 2.14.x (PG15) | PostgreSQL时序扩展 |
| **地理扩展** | PostGIS | 3.4.x | PostgreSQL地理扩展 |
| **缓存/队列** | Redis | 7.2.x | 缓存、会话、消息队列 |
| **异步Redis** | redis-py | 5.0.x | Redis异步客户端 |
| **MQTT** | paho-mqtt | 1.6.x | MQTT客户端 |
| **向量数据库** | Milvus | 2.3.x | 向量检索引擎 |
| **工作流引擎** | BPMN (Camunda/自研) | - | 流程引擎 |
| **配置管理** | Pydantic Settings | 2.x | 配置验证 |
| **认证** | python-jose | 3.3.x | JWT Token |
| **密码加密** | passlib | 1.7.x | 密码哈希 |
| **数据验证** | Pydantic | 2.x | 数据模型验证 |
| **日志** | structlog | 24.x | 结构化日志 |
| **任务队列** | Celery | 5.3.x | 异步任务 |
| **对象存储** | MinIO Python SDK | - | S3兼容存储 |

### 2.2 AI/ML 技术栈

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **深度学习框架** | PyTorch | 2.2.x | 模型训练与推理 |
| **模型推理优化** | ONNX Runtime | 1.17.x | 高性能推理 |
| **目标检测** | YOLOv8 | ultralytics 8.x | 目标检测模型 |
| **目标追踪** | DeepSort / OSNet | - | 多目标追踪 |
| **向量嵌入** | text-embedding-3-small | OpenAI | 文本向量化 |
| **LLM** | GPT-4 / 通义千问 | - | 大语言模型 |
| **RAG框架** | LangChain | 0.1.x | RAG编排 |
| **向量检索** | Milvus | 2.3.x | 向量相似度检索 |
| **OCR** | PaddleOCR / EasyOCR | - | 文字识别 |
| **语音识别** | Whisper | openai-whisper 20231117 | 语音转文字 |
| **语音合成** | Edge-TTS / VALL-E | - | 文字转语音 |

### 2.3 前端技术栈

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **框架** | React | 18.x | UI框架 |
| **状态管理** | Zustand | 4.x | 轻量状态管理 |
| **路由** | React Router | 6.x | 前端路由 |
| **HTTP客户端** | Axios / SWR | - | 数据请求 |
| **UI组件库** | Ant Design | 5.x | 企业级组件库 |
| **3D可视化** | CesiumJS | 1.115.x | 电子沙盘 |
| **地图** | MapboxGL / Leaflet | - | 地理信息展示 |
| **图表** | ECharts | 5.x | 数据可视化 |
| **实时通信** | Socket.io Client | 4.x | WebSocket客户端 |
| **构建工具** | Vite | 5.x | 前端构建 |
| **样式** | Tailwind CSS | 3.x | 原子化CSS |
| **类型检查** | TypeScript | 5.x | 类型安全 |

### 2.4 数据存储技术栈

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **主数据库** | PostgreSQL | 15.x | 关系型数据库 |
| **时序优化** | TimescaleDB | 2.14.x | 时序数据优化 |
| **地理信息** | PostGIS | 3.4.x | 空间数据扩展 |
| **全文搜索** | pg_trgm | 内置 | 模糊匹配搜索 |
| **缓存/队列** | Redis | 7.2.x | 缓存和消息队列 |
| **向量存储** | Milvus | 2.3.x | 向量相似度检索 |
| **对象存储** | MinIO | RELEASE.2024-05 | S3兼容对象存储 |
| **消息队列** | Kafka | 3.7.x | 事件流处理 |

### 2.5 基础设施技术栈

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **容器化** | Docker | 25.x | 容器化部署 |
| **容器编排** | Kubernetes | 1.29.x | 容器编排管理 |
| **MQTT Broker** | Eclipse Mosquitto | 2.0.x | MQTT消息代理 |
| **负载均衡** | Nginx | 1.25.x | 反向代理/负载均衡 |
| **服务网格** | Istio | 1.20.x | 服务治理（可选） |
| **日志收集** | Loki / ELK | - | 日志聚合 |
| **监控** | Prometheus + Grafana | - | 指标监控 |
| **链路追踪** | Jaeger | - | 分布式追踪 |
| **容器镜像仓库** | Harbor | 2.9.x | 镜像仓库 |

---

## 3. 依赖关系矩阵

### 3.1 服务间依赖

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              依赖关系矩阵                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  API Gateway                                                                │
│    ├──→ PostgreSQL (主库)                                                  │
│    ├──→ Redis (缓存/会话)                                                  │
│    ├──→ Milvus (向量查询)                                                  │
│    └──→ MinIO (文件存储)                                                   │
│                                                                             │
│  IoT Hub Service                                                            │
│    ├──→ MQTT Broker                                                        │
│    ├──→ PostgreSQL (元数据)                                                │
│    ├──→ TimescaleDB (时序数据)                                             │
│    └──→ Redis (设备状态)                                                   │
│                                                                             │
│  Video Pipeline                                                             │
│    ├──→ RTSP Camera (视频源)                                               │
│    ├──→ Redis (帧队列)                                                     │
│    └──→ Kafka (事件流)                                                     │
│                                                                             │
│  YOLO Inference Service                                                    │
│    ├──→ ONNX Runtime                                                       │
│    ├──→ MinIO (模型存储)                                                   │
│    └──→ Redis (推理队列)                                                   │
│                                                                             │
│  Alert Service                                                             │
│    ├──→ PostgreSQL                                                         │
│    ├──→ Redis Stream (消息队列)                                            │
│    ├──→ Kafka (事件消费)                                                   │
│    └──→ SMS/Email Gateway (第三方)                                         │
│                                                                             │
│  Expert Service                                                             │
│    ├──→ Milvus (向量检索)                                                  │
│    ├──→ PostgreSQL (知识库)                                                │
│    ├──→ LLM API (第三方)                                                   │
│    └──→ Redis (会话缓存)                                                   │
│                                                                             │
│  Workflow Service                                                           │
│    ├──→ PostgreSQL                                                         │
│    └──→ Redis (任务队列)                                                   │
│                                                                             │
│  Frontend Applications                                                     │
│    └──→ API Gateway (REST + WebSocket)                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Python 包依赖（核心）

```txt
# requirements.txt - 核心后端服务

# === Web Framework ===
fastapi==0.110.0
uvicorn[standard]==0.29.0
starlette==0.37.2

# === Database ===
sqlalchemy[asyncio]==2.0.27
asyncpg==0.29.0
psycopg2-binary==2.9.9
alembic==1.13.1
timescale-sqlalchemy==0.0.2

# === Redis ===
redis==5.0.1
aioredis==2.0.1

# === MQTT ===
paho-mqtt==1.6.2

# === Auth ===
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9

# === Validation & Config ===
pydantic==2.6.1
pydantic-settings==2.1.0
email-validator==2.1.0

# === Async ===
anyio==4.3.0
httpx==0.27.0
aiofiles==23.2.1

# === Task Queue ===
celery==5.3.6
flower==2.0.1

# === Logging & Monitoring ===
structlog==24.1.0
prometheus-client==0.20.0
sentry-sdk==1.42.0

# === Object Storage ===
minio==7.2.3

# === Utils ===
python-dateutil==2.8.2
python-json-logger==2.0.7
tenacity==8.2.3
```

```txt
# requirements-ml.txt - AI/ML 服务

# === Deep Learning ===
torch==2.2.2
torchvision==0.17.2
onnxruntime-gpu==1.17.1  # GPU版本
# onnxruntime==1.17.1     # CPU版本

# === Model Inference ===
ultralytics==8.1.24  # YOLOv8

# === Vector & RAG ===
pymilvus==2.3.7
langchain==0.1.14
langchain-community==0.0.26
langchain-openai==0.1.6

# === Embedding ===
openai==1.17.1
sentence-transformers==2.5.1

# === Speech ===
openai-whisper==20231117
edge-tts==6.1.11

# === Tracking ===
deep-sort-realtime==1.3.2
```

```txt
# requirements-video.txt - 视频处理服务

opencv-python-headless==4.9.0.80
opencv-contrib-python-headless==4.9.0.80
ffmpeg-python==0.2.0
aiogrpc==1.1.0  # gRPC异步支持
```

---

## 4. 第三方服务集成

### 4.1 外部服务清单

| 服务类别 | 服务名称 | 集成方式 | 用途 |
|----------|----------|----------|------|
| **LLM** | OpenAI GPT-4 | REST API | RAG问答生成 |
| **LLM** | 阿里通义千问 | REST API | RAG问答生成（国内） |
| **短信** | 阿里云短信 | REST API | 告警通知 |
| **短信** | 腾讯云短信 | REST API | 告警通知（备选） |
| **邮件** | SMTP服务器 | SMTP | 告警邮件通知 |
| **推送** | 极光推送 | REST API | 移动端推送 |
| **地图** | 高德地图 | REST API | 地理编码/逆编码 |
| **天气** | 和风天气 | REST API | 天气预警 |
| **对象存储** | MinIO (自建) | S3 API | 静态文件存储 |

### 4.2 设备SDK集成

| 设备类型 | SDK | 版本 | 集成方式 |
|----------|-----|------|----------|
| **DJI 无人机** | DJI Web SDK | 4.x | JavaScript SDK |
| **海康摄像头** | 海康ISC SDK | - | REST API / ISAPI |
| **大华摄像头** | 大华API | - | REST API / CGI |
| **IoT传感器** | MQTT | - | MQTT协议直连 |
| **气象站** | 通用传感器 | - | MQTT协议直连 |

### 4.3 API密钥配置

```bash
# .env 文件模板

# ==================== 必填配置 ====================

# 数据库
DATABASE_URL=postgresql+asyncpg://wcs_user:password@postgres:5432/water_construction
POSTGRES_PASSWORD=SecurePassword123!

# Redis
REDIS_URL=redis://:RedisPassword@redis:6379/0
REDIS_PASSWORD=RedisPassword

# MinIO (对象存储)
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET_ALERTS=alerts
MINIO_BUCKET_VIDEOS=videos
MINIO_BUCKET_MODELS=models
MINIO_SECURE=false

# ==================== LLM 配置 ====================

# OpenAI (海外)
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4-turbo-preview

# 阿里通义千问 (国内备选)
QWEN_API_KEY=sk-...
QWEN_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-turbo

# 向量嵌入模型
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# ==================== 第三方服务 ====================

# 短信服务 (阿里云)
ALIYUN_SMS_ACCESS_KEY_ID=...
ALIYUN_SMS_ACCESS_KEY_SECRET=...
ALIYUN_SMS_SIGN_NAME=水利工地安全
ALIYUN_SMS_TEMPLATE_CODE=SMS_xxx

# 腾讯云短信 (备选)
TENCENT_SMS_APP_ID=...
TENCENT_SMS_APP_KEY=...
TENCENT_SMS_SIGN=水利工地

# 邮件服务
SMTP_HOST=smtp.exmail.qq.com
SMTP_PORT=587
SMTP_USER=noreply@example.com
SMTP_PASSWORD=smtppassword
SMTP_FROM=水利工地安全监管 <noreply@example.com>

# 极光推送
JPUSH_APP_KEY=...
JPUSH_MASTER_SECRET=...

# 高德地图
AMAP_API_KEY=...

# 和风天气
QWEATHER_API_KEY=...

# ==================== 安全配置 ====================

# JWT
JWT_SECRET_KEY=your-super-secret-key-min-32-characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 加密
ENCRYPTION_KEY=32-byte-encryption-key-here

# ==================== MQTT 配置 ====================

MQTT_BROKER_URL=mqtt://mqtt:1883
MQTT_USERNAME=mosquitto
MQTT_PASSWORD=mosquittopassword
MQTT_KEEPALIVE=60
MQTT_TLS_ENABLED=false

# ==================== Kafka 配置 ====================

KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_CONSUMER_GROUP=wcs-consumers
KAFKA_AUTO_OFFSET_RESET=latest

# ==================== AI 模型配置 ====================

# YOLO 模型
YOLO_MODEL_PATH=/models/yolov8s.onnx
YOLO_CONFIDENCE_THRESHOLD=0.7
YOLO_DEVICE=cuda  # cuda 或 cpu

# Whisper 语音识别
WHISPER_MODEL=base
WHISPER_LANGUAGE=zh

# ==================== 通知配置 ====================

# 告警通知开关
NOTIFICATION_SMS_ENABLED=true
NOTIFICATION_EMAIL_ENABLED=true
NOTIFICATION_APP_ENABLED=true

# 告警聚合
ALERT_DEDUP_WINDOW_SECONDS=300
ALERT_BATCH_SIZE=10
ALERT_BATCH_INTERVAL_SECONDS=60

# ==================== 日志与监控 ====================

LOG_LEVEL=INFO
SENTRY_DSN=https://xxx@sentry.io/xxx

# ==================== 开发环境 ====================

ENVIRONMENT=development  # development, staging, production
DEBUG=true
```

---

## 5. 开发环境要求

### 5.1 硬件要求

| 环境 | CPU | 内存 | 磁盘 | GPU |
|------|-----|------|------|-----|
| **开发** | 4核+ | 16GB | 100GB SSD | 可选 (用于本地推理) |
| **测试** | 8核+ | 32GB | 200GB SSD | 推荐 (RTX 3060+) |
| **生产** | 16核+ | 64GB+ | 500GB SSD+ | 必须 (RTX 4090/A100) |

### 5.2 软件要求

#### 5.2.1 开发工具

| 工具 | 版本 | 用途 |
|------|------|------|
| **Git** | 2.40+ | 版本控制 |
| **Docker** | 25.x | 容器化 |
| **Docker Compose** | 2.20+ | 本地开发环境 |
| **Python** | 3.11+ | 后端开发 |
| **Node.js** | 20.x | 前端开发 |
| **pnpm** | 8.x | 前端包管理 |
| **VS Code** | 最新 | 推荐IDE |
| **PyCharm** | 最新 | Python IDE |

#### 5.2.2 必需扩展

```bash
# VS Code 扩展 (.vscode/extensions.json)
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-vscode-remote.remote-containers",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "bradlc.vscode-tailwindcss",
    "mikestead.dotenv",
    "eamodio.gitlens",
    "formulahendry.auto-rename-tag",
    "christian-kohler.path-intellisense"
  ]
}
```

#### 5.2.3 Git Hooks

```bash
# .husky/pre-commit
#!/bin/sh
echo "Running pre-commit hooks..."
npx lint-staged
pnpm run type-check

# .husky/commit-msg
#!/bin/sh
commit_msg_file=$1
commit_msg=$(cat "$commit_msg_file")
if ! echo "$commit_msg" | grep -qE "^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?: .{1,50}"; then
    echo "Invalid commit message format!"
    exit 1
fi
```

### 5.3 环境启动脚本

```bash
#!/bin/bash
# scripts/dev-setup.sh

set -e

echo "=== 水利工地安全监管系统 - 开发环境初始化 ==="

# 1. 复制环境变量模板
if [ ! -f .env ]; then
    cp .env.example .env
    echo "已创建 .env 文件，请编辑配置"
fi

# 2. 启动基础服务
echo "启动 Docker Compose 服务..."
docker compose -f docker-compose.dev.yml up -d postgres redis mqtt minio milvus

# 3. 等待服务就绪
echo "等待数据库服务就绪..."
sleep 10

# 4. 运行数据库迁移
echo "执行数据库迁移..."
alembic upgrade head

# 5. 初始化种子数据
echo "初始化种子数据..."
psql $DATABASE_URL -f db/init/seed_data.sql

# 6. 安装 Python 依赖
echo "安装 Python 依赖..."
pip install -r requirements.txt
pip install -r requirements-ml.txt

# 7. 安装前端依赖
echo "安装前端依赖..."
cd frontend && pnpm install && cd ..

echo "=== 开发环境初始化完成 ==="
echo "启动服务: docker compose -f docker-compose.dev.yml up"
echo "访问地址: http://localhost:3000"
```

### 5.4 代码质量检查

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: timescale/timescaledb:latest-pg15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        
      redis:
        image: redis:7.2-alpine
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov black ruff
          
      - name: Lint
        run: |
          black --check .
          ruff check .
          
      - name: Type Check
        run: mypy src/
        
      - name: Test
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379
        run: |
          pytest --cov=src --cov-report=xml tests/
          
  frontend:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'
          
      - name: Install
        run: pnpm install --frozen-lockfile
        
      - name: Lint
        run: pnpm lint
        
      - name: Type Check
        run: pnpm type-check
        
      - name: Test
        run: pnpm test --coverage
```

---

## 6. 服务端口映射

| 服务 | 内部端口 | 外部端口 | 协议 | 说明 |
|------|----------|----------|------|------|
| **API Gateway** | 8000 | 8000 | HTTP | 主API入口 |
| **Sandtable UI** | 80 | 3000 | HTTP | 电子沙盘 |
| **Workflow UI** | 80 | 3001 | HTTP | 问题管理 |
| **Alert UI** | 80 | 3002 | HTTP | 告警平台 |
| **Expert UI** | 80 | 3003 | HTTP | 专家系统 |
| **YOLO Service** | 8000 | 8001 | HTTP/gRPC | 图片推理 |
| **Video Analyzer** | 8000 | 8002 | HTTP | 视频分析 |
| **Speech Service** | 8000 | 8003 | HTTP | 语音处理 |
| **Expert Service** | 8000 | 8004 | HTTP | 专家问答 |
| **PostgreSQL** | 5432 | 5432 | TCP | 主数据库 |
| **Redis** | 6379 | 6379 | TCP | 缓存/队列 |
| **MQTT** | 1883 | 1883 | MQTT | 物联网接入 |
| **MQTT (TLS)** | 8883 | 8883 | MQTT/TLS | 物联网接入 |
| **MinIO API** | 9000 | 9000 | HTTP | 对象存储 |
| **MinIO Console** | 9001 | 9001 | HTTP | 对象存储管理 |
| **Milvus** | 19530 | 19530 | gRPC | 向量数据库 |
| **Milvus Console** | 9091 | 9091 | HTTP | 向量管理 |
| **Kafka** | 9092 | 9092 | TCP | 消息队列 |
| **Nginx** | 80/443 | 80/443 | HTTP/HTTPS | 反向代理 |

---

## 7. 版本兼容性矩阵

### 7.1 Python 版本兼容性

| Package | Python 3.10 | Python 3.11 | Python 3.12 |
|---------|-------------|-------------|-------------|
| FastAPI 0.110 | ✅ | ✅ | ✅ |
| SQLAlchemy 2.0 | ✅ | ✅ | ✅ |
| PyTorch 2.2 | ✅ | ✅ | ✅ |
| LangChain 0.1 | ✅ | ✅ | ✅ |
| Redis 5.0 | ✅ | ✅ | ✅ |

### 7.2 数据库兼容性

| PostgreSQL 版本 | TimescaleDB | PostGIS | 推荐 |
|-----------------|--------------|---------|------|
| 14.x | 2.12.x | 3.3.x | 保守 |
| 15.x | 2.14.x | 3.4.x | ✅ 推荐 |
| 16.x | 2.15.x | 3.4.x | 激进 |

### 7.3 浏览器兼容性

| 浏览器 | 最低版本 | 说明 |
|--------|----------|------|
| Chrome | 90+ | 推荐 |
| Firefox | 90+ | 支持 |
| Safari | 15+ | 支持 |
| Edge | 90+ | 支持 |
| 飞书客户端 | 最新 | 支持 |

---

## 8. 监控与可观测性

### 8.1 指标监控 (Prometheus)

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'api-gateway'
    static_configs:
      - targets: ['api-gateway:8000']
    metrics_path: '/metrics'
    
  - job_name: 'iot-hub'
    static_configs:
      - targets: ['iot-hub:8000']
      
  - job_name: 'alert-service'
    static_configs:
      - targets: ['alert-service:8000']
      
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
```

### 8.2 关键业务指标

| 指标名称 | 类型 | 说明 |
|----------|------|------|
| `wcs_alerts_total` | Counter | 告警总数 |
| `wcs_alerts_by_severity` | Counter | 按严重级别统计 |
| `wcs_alerts_processing_time` | Histogram | 告警处理时长 |
| `wcs_sensors_online_ratio` | Gauge | 传感器在线率 |
| `wcs_camera_online_ratio` | Gauge | 摄像头在线率 |
| `wcs_ai_detection_rate` | Counter | AI检测次数 |
| `wcs_api_request_duration` | Histogram | API响应时长 |
| `wcs_expert_query_count` | Counter | 专家问答次数 |

---

## 9. 安全配置

### 9.1 CORS 配置

```python
# CORS 中间件配置
CORSMiddleware(
    allow_origins=[
        "http://localhost:3000",  # 开发环境
        "https://*.feishu.cn",    # 飞书
        "https://app.example.com"  # 生产环境
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 9.2 速率限制

```python
# API 速率限制配置
RATE_LIMITS = {
    "/api/v1/auth/login": "5/minute",
    "/api/v1/auth/refresh": "10/minute",
    "/api/v1/expert/query": "30/minute",
    "/api/v1/reports/generate": "5/minute",
    "/api/v1/**": "100/minute",  # 默认
}
```

### 9.3 敏感数据处理

- 数据库密码、服务密钥存储在 Kubernetes Secret
- API 密钥通过环境变量注入，不硬编码
- 日志中自动脱敏手机号、身份证等敏感信息
- 文件上传限制类型和大小 (图片≤10MB, 视频≤100MB)
