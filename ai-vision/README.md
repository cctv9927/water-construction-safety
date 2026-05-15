# AI Vision Module - 图像识别模块

基于 YOLOv8 ONNX 推理的水利建设工地安全监管图像识别服务。

## 功能特性

- **YOLOv8 ONNX 推理**：使用 ultralytics 导出 ONNX 模型，ONNX Runtime 高效推理
- **检测目标**：安全帽（helmet）、人（person）、车（vehicle）、建材（material）、环境隐患（hazard）
- **输入方式**：图片 URL 或 Base64 编码
- **输出格式**：JSON（检测框坐标、类别、置信度）

## 检测类别

| 类别 ID | 类别名称 | 说明 |
|---------|----------|------|
| 0 | helmet | 安全帽（已佩戴） |
| 1 | no_helmet | 未戴安全帽 |
| 2 | person | 人员 |
| 3 | vehicle | 车辆/机械 |
| 4 | material | 建材/物料 |
| 5 | hazard | 环境安全隐患 |
| 6 | fire | 火灾隐患 |
| 7 | unguarded_edge | 无防护边缘 |

## API 接口

### POST /detect
图片目标检测（支持 URL 和 Base64）

**请求体**：
```json
{
  "image": "https://example.com/image.jpg",
  "confidence": 0.5,
  "max_detections": 50
}
```
或：
```json
{
  "image_base64": "base64 encoded image string",
  "confidence": 0.5,
  "max_detections": 50
}
```

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "width": 1920,
    "height": 1080,
    "detections": [
      {
        "class_id": 0,
        "class_name": "helmet",
        "confidence": 0.95,
        "bbox": {
          "x1": 100, "y1": 200,
          "x2": 300, "y2": 400
        }
      }
    ],
    "count": 1,
    "inference_time_ms": 45
  }
}
```

### GET /health
健康检查

### GET /model/info
获取模型信息

## 运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 导出 ONNX 模型（如无模型文件，首次运行会自动下载）
python export_model.py

# 启动服务
python main.py

# 或使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8082 --workers 1
```

## Docker 部署

```bash
docker build -t water-safety-ai-vision:latest .
docker run -d -p 8082:8082 --gpus all water-safety-ai-vision:latest
```

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| MODEL_PATH | models/yolov8n.onnx | ONNX 模型路径 |
| DEFAULT_CONFIDENCE | 0.5 | 默认置信度阈值 |
| MAX_DETECTIONS | 100 | 最大检测数量 |
| REDIS_HOST | localhost | Redis 主机 |
| REDIS_PORT | 6379 | Redis 端口 |
| LOG_LEVEL | INFO | 日志级别 |
