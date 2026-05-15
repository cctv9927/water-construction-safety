# 水利建设工地质量安全监管系统 - 系统架构文档

## 1. 整体架构图

```mermaid
graph TB
    subgraph 感知层["第一层：感知层"]
        subgraph 传感器["数字传感器"]
            S1[温度传感器]
            S2[压力传感器]
            S3[震动传感器]
            S4[位移传感器]
            S5[流量传感器]
            S6[风速传感器]
            S7[降雨量传感器]
        end
        subgraph 视频设备["视频监控"]
            CAM1[摄像头-1]
            CAM2[摄像头-N]
        end
        subgraph 无人机["无人机设备"]
            UAV[DJI无人机]
        end
    end

    subgraph 传输层["传输层"]
        MQTT[(MQTT Broker<br/>Port 1883)]
        RTSP[RTSP Server]
        RTMP[RTMP Server]
        WS[WebSocket Gateway]
    end

    subgraph AI平台["第二层：AI平台"]
        subgraph 数据采集["数据采集服务"]
            IOT_HUB[IoT Hub Service]
            VIDEO_PIPELINE[Video Pipeline]
            UAV_CONTROL[UAV Control Service]
        end
        
        subgraph AI分析["AI分析引擎"]
            YOLO[图片识别服务<br/>YOLOv8 + ONNX]
            SENSOR_ANALYZER[传感器分析服务]
            VIDEO_ANALYZER[视频分析服务<br/>DeepSort追踪]
            SPEECH_SVC[语音处理服务<br/>Whisper/TTS]
            VECTOR_ENGINE[向量检索引擎<br/>Milvus]
        end
        
        subgraph 多智能体["多智能体系统"]
            ORCHESTRATOR[Orchestrator Agent]
            DECISION[决策 Agent]
            EXECUTION[执行 Agent]
        end
        
        MODEL_REGISTRY[(Model Registry)]
        RAG_ENGINE[RAG Engine]
    end

    subgraph 应用层["第三层：应用层"]
        subgraph 前端应用["前端应用"]
            SANDTABLE[电子沙盘<br/>CesiumJS + React]
            WORKFLOW[问题管理平台<br/>React Admin]
            ALERT_UI[告警提示平台<br/>React]
            EXPERT_SYS[专家系统<br/>React + RAG UI]
        end
        
        subgraph 后端服务["后端服务"]
            API_GATEWAY[API Gateway<br/>FastAPI]
            AUTH_SVC[认证服务<br/>JWT/OAuth2]
            WORKFLOW_SVC[工作流服务]
            ALERT_SVC[告警服务]
            EXPERT_SVC[专家服务]
            REPORT_SVC[报表服务]
        end
        
        subgraph 第三方集成["第三方集成"]
            DJI_SDK[(DJI SDK)]
            SMS_GATEWAY[(短信网关)]
            EMAIL_GATEWAY[(邮件网关)]
            APP_PUSH[(APP推送服务)]
        end
    end

    subgraph 数据层["数据层"]
        POSTGRES[(PostgreSQL<br/>主数据库)]
        TIMESCALE[(TimescaleDB<br/>时序数据)]
        REDIS[(Redis<br/>缓存/消息队列)]
        MILVUS[(Milvus<br/>向量数据库)]
        MINIO[(MinIO<br/>对象存储)]
    end

    %% 数据流连接
    S1 & S2 & S3 & S4 & S5 & S6 & S7 --> MQTT
    CAM1 & CAM2 --> RTSP
    UAV --> RTMP
    
    MQTT --> IOT_HUB
    RTSP --> VIDEO_PIPELINE
    RTMP --> UAV_CONTROL
    
    IOT_HUB --> TIMESCALE
    IOT_HUB --> SENSOR_ANALYZER
    VIDEO_PIPELINE --> YOLO
    VIDEO_PIPELINE --> VIDEO_ANALYZER
    UAV_CONTROL --> YOLO
    
    YOLO --> ORCHESTRATOR
    SENSOR_ANALYZER --> ORCHESTRATOR
    VIDEO_ANALYZER --> ORCHESTRATOR
    SPEECH_SVC --> ORCHESTRATOR
    
    ORCHESTRATOR --> DECISION
    DECISION --> EXECUTION
    EXECUTION --> ALERT_SVC
    EXECUTION --> WORKFLOW_SVC
    
    RAG_ENGINE --> VECTOR_ENGINE
    MODEL_REGISTRY --> YOLO
    MODEL_REGISTRY --> VIDEO_ANALYZER
    
    ALERT_SVC --> WS
    WS --> SANDTABLE
    WS --> ALERT_UI
    
    ALERT_SVC --> SMS_GATEWAY
    ALERT_SVC --> EMAIL_GATEWAY
    ALERT_SVC --> APP_PUSH
    
    API_GATEWAY --> AUTH_SVC
    API_GATEWAY --> WORKFLOW_SVC
    API_GATEWAY --> EXPERT_SVC
    API_GATEWAY --> REPORT_SVC
    
    WORKFLOW_SVC --> POSTGRES
    EXPERT_SVC --> POSTGRES
    EXPERT_SVC --> MILVUS
    REPORT_SVC --> POSTGRES
    
    SANDTABLE --> API_GATEWAY
    WORKFLOW --> API_GATEWAY
    ALERT_UI --> API_GATEWAY
    EXPERT_SYS --> API_GATEWAY
    
    DJI_SDK --> UAV_CONTROL
```

---

## 2. 模块划分及职责说明

### 2.1 感知层模块

| 模块 | 职责 | 技术实现 |
|------|------|----------|
| IoT Hub Service | 接收MQTT传感器数据，进行协议解析、数据校验、格式转换 | Python/asyncio/paho-mqtt |
| Video Pipeline | RTSP拉流、FFmpeg截帧、帧预处理、视频流分发 | FFmpeg/GStreamer/Python |
| UAV Control Service | DJI SDK集成、RTMP接收、航线控制指令下发 | DJI Web SDK/Node.js |

### 2.2 AI平台模块

| 模块 | 职责 | 技术实现 |
|------|------|----------|
| 图片识别服务 | YOLOv8目标检测、边缘+云端推理、结果后处理 | PyTorch/ONNX Runtime/FastAPI |
| 传感器分析服务 | 时序异常检测、阈值告警、趋势预测 | TimescaleDB/Prophet/FastAPI |
| 视频分析服务 | DeepSort目标追踪、视频浓缩、质量诊断 | OpenCV/DeepSort/FastAPI |
| 语音处理服务 | 语音识别、语音合成、关键词检测 | Whisper/TTS/FastAPI |
| 向量检索引擎 | 知识库向量存储与检索、语义匹配 | Milvus/Pymilvus |
| Orchestrator Agent | 多智能体协调、任务分发、结果聚合 | LangChain/LangGraph |
| Decision Agent | 事件分级、处置建议生成 | LLM/Prompt Engineering |
| Execution Agent | 告警触发、工作流执行、外部系统对接 | FastAPI/Celery |

### 2.3 应用层模块

| 模块 | 职责 | 技术实现 |
|------|------|----------|
| API Gateway | 统一API入口、认证授权、流量控制、路由分发 | FastAPI/Uvicorn |
| 认证服务 | 用户认证、权限管理、Token签发 | JWT/OAuth2/Passlib |
| 工作流服务 | 问题全生命周期管理、状态流转、审批流程 | FastAPI/Workflow Engine |
| 告警服务 | 告警生成、聚合、分级、通知渠道管理 | FastAPI/Redis Stream |
| 专家服务 | 知识库问答、RAG检索、文档生成 | LangChain/Milvus/FastAPI |
| 报表服务 | 数据统计、可视化报表导出 | Pandas/Aggregation |

---

## 3. 三层之间的数据流

### 3.1 感知层 → AI平台 数据流

```
传感器数据流:
[温度/压力/震动/位移/流量/风速/降雨量]
    ↓ MQTT Publish (topic: site/{site_id}/sensor/{sensor_type})
    ↓
[MQTT Broker]
    ↓
[IoT Hub Service] → 数据校验 → 格式标准化
    ↓
[TimescaleDB] (原始时序存储)
    ↓
[传感器分析服务] → 异常检测 → 告警事件
```

```
视频数据流:
[摄像头 RTSP]
    ↓ RTSP Pull
[Video Pipeline]
    ↓ FFmpeg截帧 (1fps/5fps可配置)
[帧缓存] → 推送至YOLO推理队列
    ↓
[图片识别服务] → 检测结果(JSON)
    ↓
[Orchestrator Agent] → 事件聚合
```

```
告警事件流:
[AI分析结果] (YOLO/传感器/视频/语音)
    ↓
[Orchestrator Agent]
    ↓ JSON事件
[Decision Agent] → 告警分级 (P0/P1/P2)
    ↓
[Execution Agent]
    ↓
[告警服务] → [Redis Stream]
    ↓ ↓ ↓
[WebSocket] [短信/邮件/APP] [工作流]
```

### 3.2 AI平台 → 应用层 数据流

```
检测结果推送:
[图片识别服务] 
    ↓ gRPC/protobuf
[API Gateway]
    ↓ REST/JSON
[电子沙盘前端] → CesiumJS标注叠加
[告警前端] → 实时弹窗
```

```
工作流数据:
[Execution Agent]
    ↓ 数据库写入
[PostgreSQL - 问题表]
    ↓
[工作流服务] → 状态更新 → [工作流前端]
```

```
知识问答:
[专家系统前端]
    ↓ 用户Query
[API Gateway]
    ↓
[专家服务]
    ↓ embedding → [Milvus]相似检索
    ↓
[RAG Engine] → LLM生成答案
    ↓
[专家系统前端] → 答案展示
```

---

## 4. 部署架构

### 4.1 Docker Compose 整体部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  # ============ 网关/代理 ============
  nginx:
    image: nginx:1.25-alpine
    container_name: wcs-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - api-gateway
      - sandtable
      - workflow-ui
    networks:
      - wcs-network

  # ============ 数据库层 ============
  postgres:
    image: timescale/timescaledb:latest-pg15
    container_name: wcs-postgres
    environment:
      POSTGRES_DB: water_construction
      POSTGRES_USER: wcs_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "5432:5432"
    command: 
      - "-c"
      - "shared_preload_libraries=timescaledb"
    networks:
      - wcs-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U wcs_user -d water_construction"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7.2-alpine
    container_name: wcs-redis
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - wcs-network
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  milvus-etcd:
    image: quay.io/coreos/etcd:v3.5.5
    container_name: wcs-milvus-etcd
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
    volumes:
      - milvus_etcd_data:/etcd
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd
    networks:
      - wcs-network

  minio:
    image: minio/minio:latest
    container_name: wcs-minio
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    command: server /data --console-address ":9001"
    networks:
      - wcs-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  # ============ AI 推理服务 ============
  yolo-inference:
    build:
      context: ./services/yolo-service
      dockerfile: Dockerfile
    container_name: wcs-yolo
    environment:
      - MODEL_PATH=/models/yolov8s.onnx
      - DEVICE=cuda  # or cpu
      - INFERENCE_WORKERS=4
    volumes:
      - ./models:/models:ro
      - ./services/yolo-service/config.yaml:/app/config.yaml:ro
    ports:
      - "8001:8000"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    networks:
      - wcs-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  video-analyzer:
    build:
      context: ./services/video-analyzer
      dockerfile: Dockerfile
    container_name: wcs-video-analyzer
    environment:
      - DEEPSORT_MODEL=osnet_x0_25
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
    volumes:
      - ./services/video-analyzer/config.yaml:/app/config.yaml:ro
      - video_cache:/app/cache
    ports:
      - "8002:8000"
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - wcs-network

  speech-service:
    build:
      context: ./services/speech-service
      dockerfile: Dockerfile
    container_name: wcs-speech
    environment:
      - WHISPER_MODEL=base
      - TTS_ENGINE=edge-tts
    volumes:
      - ./models/whisper:/app/models:ro
    ports:
      - "8003:8000"
    networks:
      - wcs-network

  # ============ 消息队列/中间件 ============
  mqtt-broker:
    image: eclipse-mosquitto:2.0
    container_name: wcs-mqtt
    volumes:
      - ./mqtt/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro
      - mqtt_data:/mosquitto/data
      - mqtt_logs:/mosquitto/log
    ports:
      - "1883:1883"
      - "8883:8883"
    networks:
      - wcs-network

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    container_name: wcs-kafka
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    depends_on:
      - zookeeper
    volumes:
      - kafka_data:/var/lib/kafka/data
    ports:
      - "9092:9092"
    networks:
      - wcs-network

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    container_name: wcs-zookeeper
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    networks:
      - wcs-network

  # ============ 后端服务 ============
  api-gateway:
    build:
      context: ./services/api-gateway
      dockerfile: Dockerfile
    container_name: wcs-api
    environment:
      - DATABASE_URL=postgresql+asyncpg://wcs_user:${POSTGRES_PASSWORD}@postgres:5432/water_construction
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - MILVUS_HOST=milvus
    env_file:
      - .env
    volumes:
      - ./services/api-gateway/config.yaml:/app/config.yaml:ro
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - wcs-network

  iot-hub:
    build:
      context: ./services/iot-hub
      dockerfile: Dockerfile
    container_name: wcs-iot-hub
    environment:
      - MQTT_BROKER=mqtt-broker
      - MQTT_PORT=1883
      - TIMESERIES_DB=postgresql+asyncpg://wcs_user:${POSTGRES_PASSWORD}@postgres:5432/water_construction
    volumes:
      - ./services/iot-hub/config.yaml:/app/config.yaml:ro
    depends_on:
      mqtt-broker:
        condition: service_started
    networks:
      - wcs-network

  alert-service:
    build:
      context: ./services/alert-service
      dockerfile: Dockerfile
    container_name: wcs-alert
    environment:
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - SMS_GATEWAY=${SMS_GATEWAY_URL}
      - EMAIL_SMTP_HOST=${SMTP_HOST}
      - EMAIL_SMTP_PORT=${SMTP_PORT}
    volumes:
      - ./services/alert-service/config.yaml:/app/config.yaml:ro
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - wcs-network

  expert-service:
    build:
      context: ./services/expert-service
      dockerfile: Dockerfile
    container_name: wcs-expert
    environment:
      - MILVUS_HOST=milvus
      - MILVUS_PORT=19530
      - LLM_API_KEY=${LLM_API_KEY}
      - LLM_BASE_URL=${LLM_BASE_URL}
    volumes:
      - ./services/expert-service/config.yaml:/app/config.yaml:ro
      - expert_data:/app/data
    ports:
      - "8004:8000"
    networks:
      - wcs-network

  # ============ Milvus 向量数据库 ============
  milvus:
    image: milvusdb/milvus:v2.3.3
    container_name: wcs-milvus
    environment:
      ETCD_ENDPOINTS: milvus-etcd:2379
      MINIO_ADDRESS: minio:9000
      MINIO_ACCESS_KEY_ID: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_ACCESS_KEY: ${MINIO_SECRET_KEY}
    volumes:
      - milvus_data:/var/lib/milvus
    ports:
      - "19530:19530"
      - "9091:9091"
    depends_on:
      - milvus-etcd
      - minio
    networks:
      - wcs-network

  # ============ 前端应用 ============
  sandtable:
    build:
      context: ./frontend/sandtable
      dockerfile: Dockerfile
    container_name: wcs-sandtable
    environment:
      - API_BASE_URL=http://api-gateway:8000
    volumes:
      - ./frontend/sandtable/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "3000:80"
    depends_on:
      - api-gateway
    networks:
      - wcs-network

  workflow-ui:
    build:
      context: ./frontend/workflow
      dockerfile: Dockerfile
    container_name: wcs-workflow
    environment:
      - API_BASE_URL=http://api-gateway:8000
    volumes:
      - ./frontend/workflow/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "3001:80"
    depends_on:
      - api-gateway
    networks:
      - wcs-network

  alert-ui:
    build:
      context: ./frontend/alert-ui
      dockerfile: Dockerfile
    container_name: wcs-alert-ui
    environment:
      - API_BASE_URL=http://api-gateway:8000
      - WS_URL=ws://api-gateway:8000/ws/alerts
    volumes:
      - ./frontend/alert-ui/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "3002:80"
    depends_on:
      - api-gateway
    networks:
      - wcs-network

  expert-ui:
    build:
      context: ./frontend/expert-ui
      dockerfile: Dockerfile
    container_name: wcs-expert-ui
    environment:
      - API_BASE_URL=http://api-gateway:8000
    volumes:
      - ./frontend/expert-ui/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "3003:80"
    depends_on:
      - api-gateway
    networks:
      - wcs-network

# ============ 网络定义 ============
networks:
  wcs-network:
    driver: bridge

# ============ 卷定义 ============
volumes:
  postgres_data:
  redis_data:
  minio_data:
  milvus_data:
  milvus_etcd_data:
  kafka_data:
  mqtt_data:
  mqtt_logs:
  video_cache:
  expert_data:
```

### 4.2 环境变量文件

```bash
# .env
# 数据库
POSTGRES_PASSWORD=YourSecurePassword123!

# Redis
REDIS_PASSWORD=YourRedisPassword456!

# MinIO
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123

# 邮件
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=noreply@example.com
SMTP_PASSWORD=emailpassword

# 短信
SMS_GATEWAY_URL=https://sms.example.com/api

# LLM
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.example.com/v1

# JWT
JWT_SECRET_KEY=your-jwt-secret-key-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 4.3 Kubernetes 部署说明（生产环境）

生产环境推荐使用 Kubernetes 部署，以下是关键资源配置：

```yaml
# k8s-deployment.yaml (示例片段)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wcs-api-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: wcs-api-gateway
  template:
    spec:
      containers:
      - name: api-gateway
        image: registry.example.com/wcs/api-gateway:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        env:
          - name: DATABASE_URL
            valueFrom:
              secretKeyRef:
                name: wcs-secrets
                key: database-url
```

---

## 5. 安全架构

### 5.1 网络隔离

```
公网 → WAF → Nginx → API Gateway (内部网络)
                        ↓
              ┌─────────┼─────────┐
              ↓         ↓         ↓
         PostgreSQL  Redis    MinIO
         (VPC内)    (VPC内)   (VPC内)
```

### 5.2 认证授权

- **API Gateway**: JWT Bearer Token
- **内部服务通信**: mTLS 或服务间认证Token
- **MQTT**: 用户名+密码 + TLS
- **数据库**: 强密码 + IP白名单

### 5.3 数据安全

- **传输加密**: 全站HTTPS/TLS
- **存储加密**: PostgreSQL TDE + MinIO SSE
- **备份策略**: 每日增量 + 每周全量 + 跨区域复制

---

## 架构优化报告（2026-05-15）

### 发现的问题

#### A. 架构问题（5个）

| ID | 问题描述 | 影响 | 位置 |
|----|---------|------|------|
| A1 | **多 Agent 协调架构过于简单**：ai-coordinator 只是简单的状态机 + 事件路由，缺乏真正的多 Agent 协作能力（决策 Agent、执行 Agent 未实现） | 无法实现复杂事件处理 | `ai-coordinator/main.py` |
| A2 | **数据库初始化方式不当**：使用 `Base.metadata.create_all()` 在应用启动时创建表，不适合生产环境 | 生产部署风险、数据迁移困难 | `backend/app/main.py` |
| A3 | **Kafka 架构未实现**：文档提到 Kafka，但代码库只有 Redis Stream | 消息处理能力受限 | 整体架构 |
| A4 | **服务发现缺失**：硬编码服务地址如 `http://localhost:8081` | 部署灵活性差、服务编排困难 | `ai-coordinator/event_router.py` |
| A5 | **模块边界不清晰**：各服务之间耦合度高，sensor-collector/collector 和 backend/app 职责有重叠 | 维护困难、扩展性差 | 整体代码 |

#### B. 代码问题（7个）

| ID | 问题描述 | 级别 | 位置 |
|----|---------|------|------|
| B1 | **拼写错误导致 WebSocket 断连失败**：`self.all_connections` 应为 `self.all_clients` | P0 | `backend/app/main.py:58` |
| B2 | **CORS 配置过于宽松**：`allow_origins=["*"]` 允许所有来源，生产环境存在安全风险 | P0 | 多处 `CORSMiddleware` |
| B3 | **JWT 密钥验证缺失**：`gateway/auth.py` 中未验证密钥长度和复杂度 | P1 | `gateway/auth.py` |
| B4 | **传感器类型验证不足**：只有静态列表检查，未做运行时验证 | P1 | `sensor-collector/collector/validator.py` |
| B5 | **Redis 连接未注入**：fusion_engine 使用全局变量而非依赖注入 | P1 | `ai-coordinator/main.py` |
| B6 | **错误处理过于宽泛**：大量使用 `except Exception` 而非细分异常类型 | P1 | 多处 |
| B7 | **状态机超时机制未实现**：`register_timeout` 方法有定义但未实际生效 | P1 | `ai-coordinator/state_machine.py` |

#### C. 最佳实践问题（6个）

| ID | 问题描述 | 建议 | 位置 |
|----|---------|------|------|
| C1 | **缺少单元测试和集成测试**：整个代码库没有测试文件 | 建立测试体系 | 整体 |
| C2 | **未使用 Alembic 迁移**：依赖 `create_all()` 而非版本化迁移 | 改用 Alembic | `backend/app/main.py` |
| C3 | **硬编码敏感配置**：JWT_SECRET 等写在代码中 | 使用环境变量或密钥管理服务 | `gateway/config.py` |
| C4 | **重复代码**：多处重复的 `EventConverter` 逻辑 | 抽象为公共模块 | `ai-coordinator/event_router.py` |
| C5 | **缺少 API 版本控制**：API 路由未使用版本化前缀 | 添加 `/api/v2/` 版本 | `backend/app/main.py` |
| C6 | **日志不规范**：混合使用 print 和 logging，缺少结构化日志 | 统一使用 structlog | 整体 |

#### D. 遗漏功能（5个）

| ID | 功能描述 | 优先级 | 状态 |
|----|---------|--------|------|
| D1 | **工作流引擎**：数据库表已定义但引擎未实现 | P1 | 未实现 |
| D2 | **RAG 专家系统**：API 端点存在但 LLM 集成未实现 | P1 | 框架存在 |
| D3 | **权限控制系统**：role_permissions 表存在但 RBAC 未实现 | P1 | 未实现 |
| D4 | **无人机集成**：只有 README，无实际代码 | P2 | 框架存在 |
| D5 | **报表服务**：API 端点存在但统计逻辑未实现 | P2 | 框架存在 |

---

### 改进建议

#### 1. 紧急修复（B1 拼写错误）

```python
# backend/app/main.py 第58行
# 错误：self.all_connections.discard(conn)
# 修正为：self.all_clients.discard(conn)
```

#### 2. 安全加固（B2、B3）

```python
# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.example.com",
        "https://*.feishu.cn"
    ],  # 不再使用 *
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # 限制方法
    allow_headers=["Authorization", "Content-Type"],  # 限制头
)

# JWT 密钥验证
def _validate_secret_key(key: str) -> str:
    if len(key) < 32:
        raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
    return key
```

#### 3. 多 Agent 协调架构升级（A1）

引入 LangChain/LangGraph 实现真正的多 Agent 协作：

```python
from langgraph.graph import StateGraph
from langchain_core.messages import BaseMessage

class CoordinatorState(TypedDict):
    messages: List[BaseMessage]
    current_alert: Alert
    decision_result: Optional[Dict]
    execution_result: Optional[Dict]

# 构建 Agent 图
workflow = StateGraph(CoordinatorState)
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("decision", decision_agent_node)
workflow.add_node("execution", execution_agent_node)
workflow.add_edge("orchestrator", "decision")
workflow.add_edge("decision", "execution")
```

#### 4. 数据库迁移规范化（C2）

```bash
# 使用 Alembic 替代 create_all
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

#### 5. 服务发现配置（A4）

```yaml
# docker-compose.yml
services:
  iot-hub:
    environment:
      - SERVICE_NAME=iot-hub
      - SERVICE_URL=http://iot-hub:8000
    labels:
      - "com.docker.service.name=iot-hub"
```

---

### 优先级排序

#### P0（必须修复 - 安全/严重Bug）
1. **B1**：修复 `all_connections` 拼写错误（WebSocket 断连功能失效）
2. **B2**：限制 CORS origins，生产环境禁用 `*`
3. **B3**：JWT 密钥最小长度验证

#### P1（建议修复 - 功能缺陷）
4. **A1**：升级多 Agent 协调架构，引入 LangGraph
5. **A2**：改用 Alembic 数据库迁移
6. **B5**：修复依赖注入问题
7. **B7**：实现状态机超时机制
8. **D1**：实现工作流引擎
9. **D3**：实现 RBAC 权限控制

#### P2（可选优化 - 长期改进）
10. **A3**：引入 Kafka 消息队列
11. **A4**：实现服务发现机制
12. **C1**：建立测试体系
13. **D2**：完善 RAG 专家系统
14. **D4**：实现无人机集成
15. **D5**：实现报表统计功能
