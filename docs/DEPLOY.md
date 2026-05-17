# 生产环境部署指南

> 工程质量安全智慧管理平台 | v1.0.0 | 2026-05-17

---

## 1. 环境要求

### 1.1 软件依赖

| 软件 | 最低版本 | 推荐版本 | 说明 |
|------|---------|---------|------|
| Docker | 24.0 | 25.0+ | 容器运行时，必须支持 Compose V2 |
| Docker Compose | 2.20 | 2.25+ | 容器编排工具（`docker compose` 子命令） |
| Git | 2.30 | 2.40+ | 代码版本管理 |
| NVIDIA Driver | 535.0 | 545.0+ | GPU 支持（AI 服务必需） |
| NVIDIA Container Toolkit | 1.14 | 最新 | Docker GPU 透传 |

### 1.2 硬件配置

| 规格 | 最低配置 | 推荐配置 | 适用场景 |
|------|---------|---------|---------|
| CPU | 8 核 | 16 核+ | 小规模工地 / 演示 |
| 内存 | 16 GB | 32 GB+ | 8 路视频 + AI 推理并发 |
| GPU | 无 | NVIDIA RTX 3060 12GB | AI 视觉实时推理 |
| 系统盘 | 100 GB SSD | 200 GB SSD | Docker 镜像 + 日志 |
| 数据盘 | 500 GB | 1 TB+ HDD/SSD | 视频流、时序数据 |
| 网络 | 100 Mbps | 1 Gbps | 多路视频推流 |

> **注意**：无 GPU 环境下，AI-vision 服务可降级为 CPU 推理（帧率显著下降）。

### 1.3 网络要求

#### 必需端口

| 端口 | 服务 | 协议 | 用途 |
|------|------|------|------|
| 80 | Nginx | HTTP | Web UI 入口 |
| 443 | Nginx | HTTPS | 加密访问（配置 SSL 后）|
| 9090 | ThingsBoard | HTTP | IoT 平台 Web UI |
| 1883 | ThingsBoard | MQTT | 传感器数据上报 |
| 8000 | Backend | HTTP | REST API |
| 8001 | Gateway | HTTP | 统一接入网关 |
| 8082 | AI-Vision | HTTP | 图像识别服务 |
| 8083 | AI-Voice | HTTP | 语音处理服务 |
| 8084 | AI-Coordinator | HTTP | 多智能体调度 |
| 8085 | Sensor-Collector | HTTP | 传感器采集服务 |
| 8086 | Video-Streamer | HTTP | 视频流处理 |
| 8090 | Drone-Integration | HTTP | 无人机控制 |
| 6379 | Redis | TCP | 消息队列 |
| 10000 | EasyDarwin | HTTP | 流媒体管理 |
| 1935 | EasyDarwin | RTMP | 视频推流 |
| 8087 | EasyDarwin | HTTP-FLV | 视频拉流 |

#### 防火墙放行（示例）

```bash
# Ubuntu/Debian
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 9090/tcp
sudo ufw allow 1883/tcp
sudo ufw allow 6379/tcp  # 仅内网访问

# 生产环境建议限制 Redis 端口仅内网访问
sudo ufw allow from 172.16.0.0/12 to any port 6379
```

---

## 2. 部署前准备

### 2.1 域名配置（如需外网访问）

```bash
# 添加 DNS 记录（以域名为例）
# A 记录：api.your-domain.com → 服务器 IP
# A 记录：sandbox.your-domain.com → 服务器 IP
```

### 2.2 SSL 证书

```bash
# 推荐使用 Let's Encrypt 免费证书
sudo apt install -y certbot python3-certbot-nginx

# 生成证书（域名需已解析到服务器）
sudo certbot --nginx -d api.your-domain.com -d sandbox.your-domain.com

# 证书自动续期（crontab）
sudo crontab -e
# 添加：0 0 * * * certbot renew --quiet
```

### 2.3 环境变量配置

```bash
cd /path/to/water-construction-safety

# 复制环境变量模板
cp .env.example .env

# 编辑 .env，配置以下关键项
nano .env
```

关键配置项说明：

```bash
# ── JWT 安全（必须修改）────────────────────────────
JWT_SECRET=your-super-secret-random-string-min-32-chars

# ── ThingsBoard ──────────────────────────────────
TB_DB_PASSWORD=thingsboard               # 与 docker-compose.yml 中保持一致
TB_SENSOR_TOKEN=YOUR_THINGSBOARD_TOKEN   # 从 ThingsBoard 设备页面复制

# ── 飞书机器人（告警推送）─────────────────────────
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# ── 可选：外部 PostgreSQL ─────────────────────────
# DATABASE_URL=postgresql://user:password@host:5432/water_safety
```

### 2.4 GPU 环境验证

```bash
# 验证 NVIDIA 驱动
nvidia-smi

# 验证 Docker GPU 支持
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi
```

---

## 3. 一键部署

### 3.1 获取代码

```bash
git clone https://github.com/cctv9927/water-construction-safety.git
cd water-construction-safety
```

### 3.2 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入实际值
```

### 3.3 构建并启动所有服务

```bash
# 前台运行（查看日志）
docker compose up --build

# 后台运行（推荐生产环境）
docker compose up -d --build

# 查看服务状态
docker compose ps
```

### 3.4 验证部署

```bash
# 健康检查（所有服务）
docker compose ps

# 逐个验证
curl http://localhost:8000/health        # Backend API
curl http://localhost:8084/health        # AI-Coordinator
curl http://localhost:8082/health        # AI-Vision
curl http://localhost:80/health          # Nginx
```

### 3.5 联调测试

```bash
# 运行集成测试套件
docker compose -f docker-compose.test.yml up --abort-on-container-exit
```

---

## 4. 各服务说明

| 服务名 | 容器名 | 端口 | 说明 | 健康检查 |
|--------|--------|------|------|---------|
| nginx | water-safety-nginx | 80, 443 | 反向代理，统一入口 | `wget -qO- http://localhost/health` |
| backend | water-safety-backend | 8000 | FastAPI REST API 网关 | `curl -f http://localhost:8000/health` |
| gateway | water-safety-gateway | 8001 | 统一接入网关 | `curl -f http://localhost:8001/health` |
| thingsboard | water-safety-thingsboard | 9090, 1883, 5683 | IoT 平台（MQTT Broker）| `curl -f http://localhost:9090/api/health` |
| thingsboard-db | water-safety-tb-db | — | PostgreSQL（ThingsBoard 数据）| `pg_isready` |
| redis | water-safety-redis | 6379 | 消息队列 / 缓存 | `redis-cli ping` |
| ai-coordinator | water-safety-ai-coordinator | 8084 | 多智能体调度中心 | `curl -f http://localhost:8084/health` |
| ai-vision | water-safety-ai-vision | 8082 | YOLOv8 图像识别（GPU）| `curl -f http://localhost:8082/health` |
| ai-voice | water-safety-ai-voice | 8083 | Whisper 语音处理 | `curl -f http://localhost:8083/health` |
| sensor-collector | water-safety-sensor-collector | 8085 | 传感器数据采集 | `curl -f http://localhost:8085/health` |
| video-streamer | water-safety-video-streamer | 8086 | 视频流处理 | `curl -f http://localhost:8081/health` |
| drone-integration | water-safety-drone | 8090 | 无人机集成 | `wget -qO- http://localhost:8090/health` |
| easy-darwin | water-safety-easy-darwin | 10000, 1935, 8087 | 流媒体服务器（RTMP/FLV）| `wget -qO- http://localhost:8080` |

---

## 5. 数据持久化

### 5.1 Docker 卷（自动备份）

| 卷名 | 用途 | 备份频率 |
|------|------|---------|
| thingsboard-db-data | PostgreSQL（设备、告警、用户数据）| 每日增量 |
| redis-data | 消息队列持久化 | 实时复制 |
| easy-darwin-data | 流媒体录制文件 | 按需 |
| ai-vision-data | AI 模型缓存 | 不需要 |
| video-streamer-frames | 视频帧缓存 | 不需要 |
| nginx-logs | Nginx 访问日志 | 每日轮转 |

### 5.2 备份脚本

```bash
#!/bin/bash
# backup.sh — 备份所有持久化数据
BACKUP_DIR=/opt/water-safety-backup
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份 PostgreSQL
docker compose exec -T thingsboard-db pg_dump -U thingsboard thingsboard > $BACKUP_DIR/db_$DATE.sql

# 备份 Redis AOF
docker compose exec -T redis redis-cli BGSAVE
cp -r $BACKUP_DIR/docker/volumes/redis-data $BACKUP_DIR/redis_$DATE

echo "备份完成: $BACKUP_DIR"
```

```bash
# 添加定时任务
sudo crontab -e
# 每日凌晨 2 点备份
0 2 * * * /path/to/backup.sh >> /var/log/water-safety-backup.log 2>&1
```

---

## 6. 升级流程

### 6.1 常规升级

```bash
cd /path/to/water-construction-safety

# 1. 拉取最新代码
git pull origin main

# 2. 拉取更新后的 Docker 镜像
docker compose pull

# 3. 重启服务（自动执行迁移）
docker compose up -d

# 4. 验证
docker compose ps
curl http://localhost:8000/health
```

### 6.2 数据库迁移

```bash
# 进入 backend 容器执行迁移
docker compose exec backend alembic upgrade head
```

### 6.3 回滚

```bash
# 回滚到上一版本
git checkout HEAD~1
docker compose up -d --build
docker compose exec backend alembic downgrade -1
```

---

## 7. 故障排查

### Q1: AI-Vision 容器启动失败，提示 GPU 不可用

**原因**：宿主机未安装 NVIDIA Driver 或 Docker 未配置 GPU。

**解决**：
```bash
# 1. 安装 NVIDIA Driver
sudo apt install nvidia-driver-545

# 2. 安装 NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt update && sudo apt install nvidia-container-toolkit
sudo systemctl restart docker

# 3. 验证
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

### Q2: 传感器数据无法上报

**原因**：ThingsBoard 设备令牌配置错误或 MQTT 端口未开放。

**解决**：
```bash
# 1. 确认 ThingsBoard 正在运行
docker compose ps thingsboard

# 2. 测试 MQTT 连接
# 在 ThingsBoard 界面 → 设备 → 复制访问令牌
# 验证端口：telnet localhost 1883

# 3. 检查 sensor-collector 日志
docker compose logs -f sensor-collector
```

### Q3: WebSocket 连接失败

**原因**：Nginx 未正确配置 WebSocket 代理。

**解决**：
```bash
# 检查 Nginx 配置是否包含 WebSocket 支持
grep -A 10 "proxy_http_version" nginx/conf.d/*.conf

# 重启 Nginx
docker compose restart nginx
```

### Q4: 前端页面无法加载

**原因**：Nginx 配置未正确代理到前端容器（当前版本前端未容器化）。

**解决**：
```bash
# 前端需要单独启动（本地开发）
cd frontend-sandbox && npm install && npm run dev

# 或配置 Nginx 反向代理到前端服务（生产环境）
# 在 nginx/conf.d/ 中添加前端服务代理配置
```

### Q5: Redis 连接失败

**解决**：
```bash
# 检查 Redis 状态
docker compose ps redis
docker compose logs redis

# 手动验证连接
docker compose exec redis redis-cli ping
# 应返回：PONG

# 如果 Redis 数据损坏，可以清空重建
docker compose stop redis
docker volume rm water-construction-safety_redis-data
docker compose up -d redis
```

---

## 8. 监控指标

### 8.1 Docker 健康检查

```bash
# 查看所有容器健康状态
docker compose ps

# 实时日志
docker compose logs -f --tail=100

# 特定服务日志
docker compose logs -f backend
docker compose logs -f ai-vision
```

### 8.2 关键指标

| 指标 | 正常范围 | 告警阈值 |
|------|---------|---------|
| 容器 CPU 使用率 | < 70% | > 85% |
| 容器内存使用率 | < 75% | > 90% |
| Backend 响应时间 | < 500ms | > 2000ms |
| AI-Vision 推理延迟 | < 200ms/帧 | > 1000ms/帧 |
| Redis 连接数 | < 50 | > 100 |
| 数据库连接数 | < 80 | > 150 |
| Nginx 错误率 | < 0.1% | > 1% |
| 磁盘使用率 | < 80% | > 90% |

### 8.3 系统资源监控脚本

```bash
#!/bin/bash
# monitor.sh — 系统资源监控
echo "=== Docker 容器状态 ==="
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== CPU / 内存使用率 ==="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

echo ""
echo "=== 磁盘使用率 ==="
df -h | grep -E "/dev/|overlay"

echo ""
echo "=== 服务健康检查 ==="
for svc in backend ai-coordinator ai-vision ai-voice; do
  status=$(curl -sf http://localhost:${svc}:8080/health 2>/dev/null && echo "✅ 健康" || echo "❌ 异常")
  echo "$svc: $status"
done
```

---

## 9. 快速命令参考

```bash
# 启动
docker compose up -d

# 停止
docker compose stop

# 重启特定服务
docker compose restart backend

# 查看日志
docker compose logs -f [service_name]

# 进入容器
docker compose exec backend bash
docker compose exec redis redis-cli

# 清理（慎用）
docker compose down -v    # 清除所有数据卷
docker system prune -f     # 清理未使用的镜像/容器
```
