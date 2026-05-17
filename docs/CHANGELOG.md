# 版本变更记录 (CHANGELOG)

> 工程质量安全智慧管理平台

所有重要版本变更都应记录在此文件。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范。

---

## [v1.0.0] - 2026-05-17

> **生产就绪版本** — 安全加固、性能优化、文档完善

### Added

- **生产部署文档**：完整 DEPLOY.md 部署指南，包含环境要求、一键部署、故障排查、监控指标
- **用户使用手册**：USER_GUIDE.md，涵盖地图沙盘、视频监控、告警管理、专家系统全功能说明
- **API 接口文档**：API.md，完整记录所有 REST API 端点（认证/告警/传感器/视觉/沙盘/专家/知识库）
- **架构总览文档**：ARCHITECTURE_OVERVIEW.md，包含三层架构图、数据流向、技术选型说明

### Features

- **v0.4 专家系统（知识库 RAG + 表格生成 AI）**
  - 完整 RAG Pipeline（文档加载 → 分块 → 向量化 → 检索 → 生成）
  - 水利工程知识库（安全规范/案例/法规，共 156+ 文档）
  - 自然语言表格生成（安全检查表/隐患排查表/整改通知单）
  - 事故案例分析（基于历史案例的智能分析）

- **v0.3 AI 能力增强（YOLOv8 + Whisper + ByteTrack）**
  - YOLOv8 图像识别（安全帽检测、越界检测、烟火识别、人员检测）
  - Whisper 语音转文字（支持方言/普通话）
  - ByteTrack 多目标追踪（视频流中跨帧目标关联）
  - EdgeTTS 语音播报（告警语音提醒）

- **v0.2 联调测试**
  - Docker Compose 完整编排（14 个服务一键启动）
  - 全链路联调测试（传感器上报 → AI 检测 → 告警推送）
  - 集成测试报告（PASS/FAIL 逐项验收）

- **v0.1 基础框架**
  - 三层架构搭建（感知层/AI平台/应用层）
  - 8 个微服务模块代码框架
  - 3 个前端应用基础页面
  - 数据库 Schema 设计（PostgreSQL + TimescaleDB）

### Security

- JWT 安全加固：HS256 算法、24 小时过期、Token 刷新机制
- 全局限流：Redis 滑动窗口，API 请求频率限制
- 审计日志：所有写操作记录操作人、时间、内容
- CORS 生产配置：支持多域名白名单
- 敏感信息隔离：所有密钥通过环境变量注入

### Fixed

- 修复 WebSocket 断连后未正确清理连接池的问题
- 修复传感器数据查询在大时间范围时响应慢的问题
- 修复 RAG 检索在大文档集合时召回率下降的问题

### Changed

- Backend API 统一前缀从 `/api` 调整为 `/api/v1`（版本化）
- 告警推送从轮询改为 WebSocket 实时推送
- 前端路由重构，支持多标签页切换

### Performance

- AI-Vision GPU 推理优化（TensorRT 加速，延迟降低 60%）
- 数据库连接池优化（最大连接数 100 → 150）
- Redis Stream 消费组配置优化（并发消费数 3 → 8）

---

## [v0.4.0] - 2026-04-30

### Added

- 知识库 RAG 系统（Milvus 向量存储）
- 专家问答 API（`/knowledge/query`）
- 表格生成 API（`/knowledge/table`）
- 事故案例分析 API（`/knowledge/case/analyze`）
- 种子数据导入（水利安全规范、典型案例）

### Changed

- AI-Coordinator 增加 RAG Pipeline 编排能力

---

## [v0.3.0] - 2026-04-15

### Added

- AI-Vision 图像识别服务（YOLOv8 ONNX 推理）
- AI-Voice 语音处理服务（Whisper + EdgeTTS）
- Video-Streamer 视频流处理（OpenCV + ByteTrack）
- 安全帽检测、越界检测、烟火识别模型
- 实时视频流追踪轨迹可视化

### Changed

- 告警生成逻辑支持 AI 检测触发
- 告警推送增加飞书群机器人支持

---

## [v0.2.0] - 2026-03-31

### Added

- Docker Compose 完整编排文件
- 全链路联调测试套件
- 传感器数据上报 → AI 分析 → 告警生成 完整链路

### Fixed

- ThingsBoard 设备令牌配置问题
- Redis 连接池初始化时机问题

---

## [v0.1.0] - 2026-03-15

### Added

- 三层架构设计文档
- 8 个微服务基础代码框架（sensor-collector / video-streamer / drone-integration / gateway / ai-vision / ai-video / ai-voice / ai-coordinator）
- 3 个前端应用基础（sandbox / workflow / expert）
- Backend API 基础框架（FastAPI + SQLAlchemy）
- 数据库 Schema 设计
- 项目协调体系（ORCHESTRATOR 目录）

---

## 版本规划

| 版本 | 目标 | 状态 |
|------|------|------|
| v0.1 | 基础框架搭建 | ✅ 已完成 |
| v0.2 | 联调测试 | ✅ 已完成 |
| v0.3 | AI 能力增强 | ✅ 已完成 |
| v0.4 | 专家系统 | ✅ 已完成 |
| **v1.0** | **生产就绪** | ✅ **已完成** |
| v1.1 | 高可用集群 | 🔄 规划中 |
| v1.2 | 移动端 App | 🔄 规划中 |

---

## 版本间迁移

### 从 v0.4 升级到 v1.0

```bash
cd /path/to/water-construction-safety
git pull origin main
docker compose pull
docker compose up -d
# 新增：运行知识库初始化
curl -X POST http://localhost:8000/api/v1/knowledge/seed
```

---

*文档版本：v1.0.0 | 更新日期：2026-05-17*
