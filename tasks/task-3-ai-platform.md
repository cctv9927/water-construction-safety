# 任务：AI 平台设计与实现

## 项目
水利建设工地质量安全监管系统

## 你的职责
作为 AI 平台 Agent，负责 AI 分析层所有模块的设计与实现。

## 产出要求

### 1. 图像识别模块（ai-vision/）
- 目标检测：YOLOv8 ONNX 推理
- 安全帽检测、人车识别、建材识别、环境隐患识别
- 推理服务：FastAPI + ONNX Runtime
- 输入：图片 URL 或 Base64
- 输出：检测结果 JSON（框、类别、置信度）

代码要求：
- Python
- 模型文件：使用 COCO 预训练权重初始化
- 推理延迟目标：<100ms/张

### 2. 3D 建模模块（ai-3d/）
- Photogrammetry 流水线（照片 → 3D 模型）
- CLI 工具封装
- 输出：GLTF 格式
- 与电子沙盘集成接口

代码要求：
- Python（OpenCV + Open3D）
- 模拟数据模式（无真实照片输入时）

### 3. 视频处理模块（ai-video/）
- 目标追踪：DeepSort 封装
- 视频浓缩算法（帧差法 + 目标过滤）
- 异常视频诊断（黑屏、模糊、遮挡）

代码要求：
- Python（OpenCV + ByteTrack）
- 异步任务队列（Redis Stream）

### 4. 语音处理模块（ai-voice/）
- 语音识别：Whisper API 封装
- 关键词告警触发
- 语音播报：TTS 合成
- 指令解析（intent detection）

代码要求：
- Python
- 麦克风输入（可选，文件输入优先）

### 5. 多智能体调度模块（ai-coordinator/）
- 事件驱动的 Agent 协作
- 异常分级（P0/P1/P2）自动判定
- 多模态融合：视频+传感器联合判断
- 下发执行指令到应用层

代码要求：
- Python（asyncio + Redis Stream）
- 状态机实现

## 保存位置
/home/gem/workspace/agent/workspace-agent-orchestrator/projects/water-construction-safety/

## 参考文件
PROJECT_OVERVIEW.md（项目概述）
