# 任务：感知层软件设计

## 项目
水利建设工地质量安全监管系统

## 你的职责
作为感知层 Agent，负责感知层所有软件模块的设计与实现。

## 产出要求

### 1. 传感器数据采集模块（sensor-collector/）
- MQTT Client 连接各类型传感器
- 数据校验、清洗、格式化
- 上报到 IoT Hub 的 REST API 调用
- 异常值检测（简单规则）

代码要求：
- Python（asyncio + aiomqtt）
- 配置文件（config.yaml）管理传感器节点
- 单元测试

### 2. 视频流处理模块（video-streamer/）
- RTSP 拉流（FFmpeg + OpenCV）
- 截帧服务（按时间/按事件）
- 视频流转推（RTMP → WebRTC）
- 视频质量诊断（黑屏、遮挡检测）

代码要求：
- Python（FastAPI + FFmpeg subprocess）
- 支持多路并发
- 健康检查接口

### 3. 无人机集成模块（drone-integration/）
- DJI Web SDK 集成文档
- 视频流回传接收服务
- 航线数据接收接口
- 状态上报服务

代码要求：
- JavaScript/TypeScript（DJI SDK）
- 模拟测试数据（无真实无人机时）
- 接口：WebSocket 事件推送

### 4. 统一数据接入网关（gateway/）
- 统一入口，屏蔽底层差异
- 认证：JWT Token
- 限流：Redis 计数
- 日志：结构化 JSON Log

代码要求：
- Python（FastAPI）
- Middleware 链式处理

## 保存位置
/home/gem/workspace/agent/workspace-agent-orchestrator/projects/water-construction-safety/

## 参考文件
PROJECT_OVERVIEW.md（项目概述）
