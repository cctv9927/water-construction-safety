# 水利建设工地质量安全监管系统

> 基于多 Agent 协作开发的智能化监管平台

## 项目概述

对水利建设工地实现全面的质量安全智能化监管，包含三层架构：

- **感知层**：传感器数据采集、视频流处理、无人机集成
- **AI平台**：图像识别、视频分析、语音处理、多智能体协同调度
- **应用层**：电子沙盘、告警闭环管理、专家系统

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python / FastAPI / SQLAlchemy / PostgreSQL / TimescaleDB |
| AI推理 | YOLOv8 / ONNX Runtime / Whisper / ByteTrack |
| 前端 | React / TypeScript / CesiumJS / Ant Design |
| 消息队列 | Redis Stream |
| 向量库 | Milvus |
| 部署 | Docker / Docker Compose |

## 目录结构

```
├── ORCHESTRATOR/          # 协调体系（项目管家用）
│   ├── coordination.md    # 模块持有登记
│   ├── progress.md        # 进度追踪
│   └── version.md         # 版本规划
├── sensor-collector/      # 传感器数据采集
├── video-streamer/        # 视频流处理
├── drone-integration/     # 无人机集成
├── gateway/               # 统一接入网关
├── ai-vision/             # AI视觉识别
├── ai-video/              # AI视频处理
├── ai-voice/              # AI语音处理
├── ai-coordinator/        # AI协调调度
├── backend/               # 后端API服务
├── frontend-sandbox/       # 电子沙盘前端
├── frontend-workflow/      # 闭环管理前端
├── frontend-expert/        # 专家系统前端
└── docs/                  # 架构文档
    ├── system-architecture.md
    ├── api-contracts.md
    ├── database-schema.md
    └── tech-stack.md
```

## 快速开始

```bash
# 后端
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# 前端（分别运行）
cd frontend-sandbox && npm install && npm run dev
cd frontend-workflow && npm install && npm run dev
cd frontend-expert && npm install && npm run dev
```

## 多 Agent 开发

本项目通过多 Agent 协作开发，详见 [ORCHESTRATOR/](ORCHESTRATOR/) 目录下的协调文件。
