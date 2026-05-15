# Docker 冒烟测试报告 - v0.2

测试时间：2026-05-15
测试类型：冒烟测试（smoke test）
测试方式：代码静态验证 + docker-compose 配置检查
测试环境：Sandbox（Docker 不可用，仅做文件级验证）

---

## 一、Docker Compose 配置检查

> ⚠️ **注意**：测试环境中 Docker 不可用（`docker: not found`），以下服务清单和端口分析基于 docker-compose.yml 静态解析。

### 服务清单

| # | 服务名 | 容器名 | 状态 |
|---|--------|--------|------|
| 1 | thingsboard | water-safety-thingsboard | ✅ 定义完整 |
| 2 | thingsboard-db | water-safety-tb-db | ✅ 定义完整 |
| 3 | easy-darwin | water-safety-easy-darwin | ✅ 定义完整 |
| 4 | ai-vision | water-safety-ai-vision | ✅ 定义完整 |
| 5 | ai-voice | water-safety-ai-voice | ✅ 定义完整 |
| 6 | ai-coordinator | water-safety-ai-coordinator | ✅ 定义完整 |
| 7 | sensor-collector | water-safety-sensor-collector | ✅ 定义完整 |
| 8 | video-streamer | water-safety-video-streamer | ✅ 定义完整 |
| 9 | backend | water-safety-backend | ✅ 定义完整 |
| 10 | redis | water-safety-redis | ✅ 定义完整 |
| 11 | nginx | water-safety-nginx | ✅ 定义完整 |

### 端口映射检查

| 服务 | 主机端口 | 容器端口 | 用途 | 状态 |
|------|---------|---------|------|------|
| thingsboard | 9090 | 9090 | Web UI | ✅ |
| thingsboard | 1883 | 1883 | MQTT Broker | ✅ |
| thingsboard | 5683 | 5683 | CoAP | ✅ |
| easy-darwin | 10000 | 10000 | HTTP 管理 | ✅ |
| easy-darwin | 1935 | 1935 | RTMP 推流 | ✅ |
| easy-darwin | 8087 | 8080 | HTTP-FLV | ✅ |
| ai-vision | 8082 | 8082 | HTTP API | ✅ |
| ai-voice | 8083 | 8083 | HTTP API | ✅ |
| ai-coordinator | 8084 | 8084 | HTTP API | ✅ |
| sensor-collector | 8085 | 8085 | 管理端口 | ✅ |
| video-streamer | 8086 | 8081 | HTTP API | ✅ |
| backend | 8000 | 8000 | FastAPI | ✅ |
| redis | 6379 | 6379 | Redis | ✅ |
| nginx | 80 | 80 | HTTP | ✅ |

**端口冲突检查：✅ 无冲突**（所有主机端口 10000, 1935, 8087, 8082-8086, 8000, 6379, 80, 9090, 1883, 5683 均不重复）

### 依赖关系检查

| 服务 | 依赖项 | 条件 | 状态 |
|------|--------|------|------|
| thingsboard | thingsboard-db | service_healthy | ✅ |
| thingsboard-db | 无 | — | ✅ |
| easy-darwin | 无 | — | ✅ |
| ai-vision | 无 | — | ✅ |
| ai-voice | 无 | — | ✅ |
| ai-coordinator | redis | service_healthy | ✅ |
| sensor-collector | thingsboard, ai-coordinator | — | ✅ |
| video-streamer | ai-vision, ai-coordinator | — | ✅ |
| backend | thingsboard-db, redis | service_healthy | ✅ |
| redis | 无 | — | ✅ |
| nginx | backend, ai-coordinator, ai-vision, ai-voice | — | ✅ |

**依赖关系检查：✅ 无循环依赖，依赖顺序合理**

---

## 二、核心文件存在性检查

| 文件路径 | 状态 |
|----------|------|
| backend/app/main.py | ✅ |
| backend/app/api/alerts.py | ✅ |
| backend/app/api/auth.py | ✅ |
| backend/app/api/expert.py | ✅ |
| backend/app/api/sandbox.py | ✅ |
| backend/app/api/sensors.py | ✅ |
| backend/app/api/vision.py | ✅ |
| backend/app/api/websocket.py | ✅ |
| backend/app/api/__init__.py | ✅ |
| ai-coordinator/main.py | ✅ |
| ai-vision/main.py | ✅ |
| sensor-collector/collector/main.py | ✅ |
| sensor-collector/collector/mqtt_client.py | ✅ |
| sensor-collector/collector/reporter.py | ✅ |
| sensor-collector/collector/validator.py | ✅ |
| video-streamer/main.py | ✅ |
| ai-voice/main.py | ✅ |
| gateway/main.py | ✅ |
| easy-darwin/config.toml | ✅ |
| docker-compose.yml | ✅ |
| docker-compose.test.yml | ✅ |
| .env.example | ✅ |

---

## 三、Python 语法检查

> ⚠️ **注意**：使用 `python3 -m py_compile` 进行语法验证（不执行代码）

| 文件 | 状态 | 备注 |
|------|------|------|
| backend/app/main.py | ✅ | 语法正确 |
| ai-coordinator/main.py | ✅ | 语法正确 |
| ai-vision/main.py | ✅ | 语法正确 |
| sensor-collector/collector/main.py | ✅ | 语法正确 |
| sensor-collector/collector/mqtt_client.py | ✅ | 语法正确 |
| sensor-collector/collector/reporter.py | ✅ | 语法正确 |
| sensor-collector/collector/validator.py | ✅ | 语法正确 |
| video-streamer/main.py | ✅ | 语法正确 |
| ai-voice/main.py | ✅ | 语法正确 |
| gateway/main.py | ✅ | 语法正确 |

**Python 语法检查：10/10 通过，0 失败 ✅**

---

## 四、Dockerfile 检查

| 服务 | Dockerfile 路径 | 存在 | 备注 |
|------|-----------------|------|------|
| backend | backend/Dockerfile | ✅ | 基于 python:3.11-slim |
| ai-vision | ai-vision/Dockerfile | ✅ | 含 GPU 资源配置 |
| ai-coordinator | ai-coordinator/Dockerfile | ✅ | |
| sensor-collector | sensor-collector/Dockerfile | ✅ | 基于 python:3.11-slim |
| easy-darwin | easy-darwin/Dockerfile | ✅ | 基于 alpine（开发版） |
| video-streamer | video-streamer/Dockerfile | ✅ | |
| ai-voice | ai-voice/Dockerfile | ✅ | |
| gateway | gateway/Dockerfile | ⚠️ 缺失 | gateway 目录存在，但 docker-compose.yml 中无此服务 |

**Dockerfile 检查：7/8 完整**（gateway 服务在 docker-compose.yml 中未定义，其 Dockerfile 缺失不影响当前部署）

---

## 五、API 路由检查

### Backend 主路由注册（backend/app/main.py）

| 前缀 | 标签 | 路由文件 |
|------|------|----------|
| /api/auth | 认证 | auth.py |
| /api/sensors | 传感器 | sensors.py |
| /api/alerts | 告警 | alerts.py |
| /api/vision | 视觉检测 | vision.py |
| /api/sandbox | 电子沙盘 | sandbox.py |
| /api/expert | 专家系统 | expert.py |
| /ws/alerts | WebSocket | websocket.py |

### 各路由文件详情

**auth.py** — 认证路由：
- `POST /login` — 登录
- `POST /register` — 注册
- `GET /me` — 获取当前用户
- `POST /refresh` — 刷新 Token
- `POST /logout` — 登出

**sensors.py** — 传感器路由：
- `GET /` — 列出传感器
- `GET /{sensor_id}` — 获取传感器详情
- `POST /` — 创建传感器
- `GET /{sensor_id}/data` — 获取传感器数据
- `POST /{sensor_id}/data` — 上报传感器数据

**alerts.py** — 告警路由：
- `GET /` — 列出告警
- `GET /{alert_id}` — 获取告警详情
- `POST /` — 创建告警
- `PATCH /{alert_id}` — 更新告警
- `DELETE /{alert_id}` — 删除告警
- `POST /{alert_id}/assign` — 分派告警
- `GET /{alert_id}/history` — 告警历史

**vision.py** — 视觉检测路由：
- `POST /detect` — 图像检测

**sandbox.py** — 电子沙盘路由：
- `GET /models` — 模型列表
- `GET /models/{model_id}` — 模型详情
- `GET /videos` — 视频列表
- `GET /videos/{video_id}` — 视频详情
- `GET /cameras` — 摄像头列表
- `GET /stats` — 统计数据

**expert.py** — 专家系统路由：
- `POST /query` — 专家查询
- `POST /forms/generate` — 表单生成
- `GET /knowledge/stats` — 知识库统计

**websocket.py** — WebSocket 路由：
- `WS /ws/alerts` — 告警实时推送

**健康检查：**
- `GET /` — 根路径
- `GET /health` — 健康检查
- `GET /sse/status` — SSE 状态

---

## 六、问题清单

### 🟡 警告（不影响启动但需关注）

1. **gateway/Dockerfile 缺失**
   - `gateway/` 目录存在且包含 Python 代码（main.py、middleware.py、rate_limiter.py 等），但 `docker-compose.yml` 中没有定义 `gateway` 服务
   - 如后续需启用 API Gateway 服务，需创建 Dockerfile 并在 docker-compose.yml 中补充服务定义
   - **当前不影响部署**：因为 gateway 服务未被引用

2. **easy-darwin 使用 alpine 镜像（开发版）**
   - Dockerfile 注释明确标注："这是简化版本，仅用于本地开发测试"
   - 生产部署建议使用官方 EasyDarwin 镜像
   - **建议**：评估后替换为官方镜像或完善 alpine 版本

3. **ThingsBoard 健康检查端点可能不准确**
   - `thingsboard` 服务 healthcheck：`curl -f http://localhost:9090/api/health`
   - ThingsBoard 标准的健康检查端点通常为 `http://localhost:9090/swagger-ui.html` 或无认证的 `/api/health`
   - 需确认 ThingsBoard 版本是否支持该端点（不带认证）

### 🔴 阻塞性问题（必须修复才能启动）

**无阻塞性问题**

---

## 七、测试结论

- ⚠️ **Docker Compose 配置可用**（无法实际执行 docker，但静态分析显示配置结构正确）
- ✅ **核心服务代码无语法错误**（10/10 Python 文件语法正确）
- ✅ **Dockerfile 完整**（7/8，主要缺失的 gateway 服务未在 compose 中引用）

### 综合结论：**⚠️ 建议验证后通过**

docker-compose.yml 配置结构完整，所有端口无冲突，依赖关系合理，核心 Python 代码语法全部正确。主要风险点：

1. `gateway/Dockerfile` 缺失 — 如果将来要启用 gateway 服务需补全
2. Docker 在当前沙箱环境中不可用，建议在具备 Docker 的机器上执行 `docker compose config` 和 `docker compose up -d` 做实际验证
3. `easy-darwin` 使用的是开发版 alpine 镜像，建议生产替换

### 建议下一步操作

1. **必须验证**：在有 Docker 的环境中执行 `docker compose config` 确认配置可正常解析
2. **必须验证**：执行 `docker compose up -d` 启动所有服务，确认容器启动无报错
3. **可选完善**：评估 gateway 服务需求，如有需要补充 Dockerfile 和服务定义
4. **可选完善**：确认 ThingsBoard 健康检查端点有效性

---

*测试执行者：QA Agent (Subagent) | 测试时间：2026-05-15 05:37 UTC*
