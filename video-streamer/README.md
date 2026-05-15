# 视频流处理模块 (video-streamer)

## 模块概述

负责接收和处理工地摄像头的 RTSP 视频流，提供实时帧处理、黑屏检测、截帧等服务。

## 技术栈

- **Web 框架**: FastAPI + Uvicorn
- **视频流**: ffmpeg-python (RTSP 拉流)
- **图像处理**: Pillow + NumPy
- **通信**: WebSocket 实时推送

## 核心功能

### 1. RTSP 流管理
- 支持多路 RTSP 流并发接入
- 自动重连机制
- 流状态监控

### 2. 截帧服务
- 按时间定时截帧
- 按事件触发截帧
- 支持 JPEG/PNG 格式
- 自动清理过期文件

### 3. 视频质量诊断
- **黑屏检测**: 计算帧平均亮度，低于阈值报警
- **遮挡检测**: 检测画面大面积纯色区域
- **冻结检测**: 检测画面长时间无变化

## 目录结构

```
video-streamer/
├── main.py              # FastAPI 服务入口
├── rtsp_client.py       # RTSP 拉流客户端
├── frame_capture.py      # 截帧服务
├── diagnostics.py        # 视频质量诊断
├── config.py            # 配置模型
├── requirements.txt     # 依赖清单
└── README.md
```

## 配置示例 (config.yaml)

```yaml
rtsp:
  timeout: 30
  retry_interval: 5
  max_retries: 3

frame_capture:
  output_dir: /tmp/frames
  jpeg_quality: 85
  png_compress: 6
  max_storage_days: 7

diagnostics:
  brightness_threshold: 20.0
  occlusion_ratio: 0.8
  check_interval: 5.0

websocket:
  host: 0.0.0.0
  port: 8081

streams:
  - stream_id: cam_001
    rtsp_url: rtsp://192.168.1.100:554/stream1
    name: 入口摄像头
    location: 工地大门
    enabled: true
```

## API 接口

### 视频流管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /streams | 列出所有流 |
| POST | /streams | 添加视频流 |
| DELETE | /streams/{stream_id} | 移除视频流 |
| POST | /streams/{stream_id}/start | 启动流 |
| POST | /streams/{stream_id}/stop | 停止流 |
| GET | /streams/{stream_id}/status | 获取流状态 |

### 截帧服务

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /capture | 手动截帧 |
| POST | /capture/scheduled | 启动定时截帧 |
| DELETE | /capture/scheduled/{stream_id} | 停止定时截帧 |
| GET | /capture/stats | 获取截帧统计 |

### 诊断服务

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /diagnostics/{stream_id}/status | 获取诊断状态 |
| GET | /diagnostics/status | 列出所有诊断状态 |

### WebSocket

| 路径 | 说明 |
|------|------|
| /ws/{stream_id} | 实时视频流订阅 |

## 启动方式

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务（使用默认配置）
python main.py

# 指定配置文件
python main.py config.yaml
```

## WebSocket 使用示例

```javascript
const ws = new WebSocket('ws://localhost:8081/ws/cam_001');

ws.onopen = () => {
    console.log('已连接到摄像头 cam_001');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'diagnostic_alert') {
        console.log('告警:', data.data.message);
    }
};

// 触发截帧
ws.send(JSON.stringify({ type: 'capture' }));
```

## 告警格式

```json
{
    "type": "diagnostic_alert",
    "data": {
        "stream_id": "cam_001",
        "diagnostic_type": "black_screen",
        "severity": "critical",
        "message": "检测到黑屏/画面过暗 (亮度: 5.2)",
        "timestamp": 1715678901.234,
        "value": 5.2
    }
}
```
