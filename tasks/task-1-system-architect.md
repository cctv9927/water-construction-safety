# 任务：系统架构设计

## 项目
水利建设工地质量安全监管系统

## 你的职责
作为系统架构 Agent，负责整体架构设计、模块划分、接口协议定义、数据库设计。

## 产出要求

### 1. 系统架构文档（system-architecture.md）
- 整体架构图（ASCII 或 Mermaid）
- 模块划分及职责说明
- 三层之间的数据流图
- 部署架构（Docker + K8s）

### 2. 接口协议文档（api-contracts.md）
- 感知层 → AI 平台：数据接口（JSON Schema）
- AI 平台 → 应用层：API 路由设计（REST + WebSocket）
- 告警数据格式（统一告警结构）
- 传感器数据 MQTT Topic 规划

### 3. 数据库设计（database-schema.md）
- PostgreSQL 表结构设计（ER 图描述）
- TimescaleDB 时序表设计
- Redis 数据结构设计
- 向量数据库（Milvus）Collection 设计

### 4. 技术选型确认文档（tech-stack.md）
- 确认所有技术选型
- 版本兼容性
- 依赖关系矩阵

## 保存位置
/home/gem/workspace/agent/workspace-agent-orchestrator/projects/water-construction-safety/

## 参考文件
PROJECT_OVERVIEW.md（项目概述）
