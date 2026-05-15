# 任务：应用层设计与实现

## 项目
水利建设工地质量安全监管系统

## 你的职责
作为应用层 Agent，负责面向用户的所有软件模块设计与实现。

## 产出要求

### 1. 后端 API 服务（backend/）
**框架**：FastAPI + SQLAlchemy + Alembic（迁移）

**主要模块**：
- 认证授权（JWT + RBAC）
- 传感器数据查询 API（时序数据 + 聚合）
- 视频流管理 API（拉流地址、录制控制）
- 告警管理 API（创建/查询/更新/关闭）
- AI 结果查询 API（检测记录检索）
- 电子沙盘数据 API（3D 模型 URL、标注数据）
- 专家系统 API（问答、表格生成）

**数据库**：
- PostgreSQL + TimescaleDB
- Alembic 迁移脚本

**实时能力**：
- WebSocket 端点（实时告警推送）
- SSE 端点（视频流状态变更）

**接口文档**：自动生成 OpenAPI（FastAPI 自带）

### 2. 电子沙盘前端（frontend-sandbox/）
**框架**：React + TypeScript + Vite

**核心功能**：
- CesiumJS 3D 地图（工地全景）
- 实时监控画面嵌入（视频播放组件）
- AI 检测结果叠加（框选标注 + 颜色区分）
- 传感器数据热力图覆盖
- 传感器数值仪表盘
- 时间轴回放（录像 + AI 结果）

**UI 组件**：Ant Design Pro 或 shadcn/ui

### 3. 闭环管理前端（frontend-workflow/）
**框架**：React + TypeScript + Vite

**核心功能**：
- 问题列表（筛选、搜索、分页）
- 问题详情（关联视频、传感器数据、AI 结果）
- 问题流转（创建→派发→处理→复核→归档）
- 流程状态可视化
- 移动端适配

### 4. 专家系统前端（frontend-expert/）
**框架**：React + TypeScript + Vite

**核心功能**：
- 知识库问答界面（RAG 检索）
- 检查表生成器（表单向导）
- 表格智慧填报（AI 辅助填写）
- 历史记录管理

## 保存位置
/home/gem/workspace/agent/workspace-agent-orchestrator/projects/water-construction-safety/

## 参考文件
PROJECT_OVERVIEW.md（项目概述）
