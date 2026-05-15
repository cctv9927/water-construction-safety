# AI Video Module - 视频处理模块

水利建设工地视频智能分析服务，提供目标追踪、视频浓缩、异常诊断能力。

## 功能模块

### 1. 目标追踪（Object Tracking）
- **算法**：ByteTrack（高性能多目标追踪）
- **功能**：实时追踪视频中的人员/车辆，基于检测框关联 ID
- **输出**：每帧检测框 + Track ID + 类别

### 2. 视频浓缩（Video Summarization）
- **功能**：将长时间视频浓缩为关键片段
- **策略**：动静变化检测 + 安全事件帧提取 + 事件优先级排序
- **输出**：关键片段时间戳列表 + 浓缩视频

### 3. 异常视频诊断（Video Quality Diagnosis）
- **检测类型**：
  - 黑屏（black_screen）：画面全黑
  - 画面模糊（blurry）：清晰度不足
  - 遮挡（occluded）：摄像头被遮挡
  - 角度异常（angle_error）：摄像头角度偏移
- **输出**：异常类型 + 时间戳 + 严重程度

### 4. Redis Stream 异步任务队列
- **队列名称**：`video:tasks`
- **任务类型**：`track` | `summarize` | `diagnose`
- **消息格式**：JSON（见 API 文档）

## API 接口

### POST /task/track
提交目标追踪任务

**请求体**：
```json
{
  "video_url": "rtsp://camera:554/stream",
  "camera_id": "CAM-001",
  "model_url": "http://ai-vision:8082/detect"
}
```

### POST /task/summarize
提交视频浓缩任务

```json
{
  "video_url": "https://storage/video/20240501.mp4",
  "camera_id": "CAM-001",
  "min_segments": 5,
  "max_segments": 20
}
```

### POST /task/diagnose
提交异常诊断任务

```json
{
  "video_url": "https://storage/video/20240501.mp4",
  "camera_id": "CAM-001"
}
```

### GET /task/{task_id}
查询任务状态

### GET /health
健康检查

## 运行方式

```bash
pip install -r requirements.txt
python main.py
```

## Redis 配置

确保 Redis 可用（默认 localhost:6379），Redis Stream 用于异步任务队列。
