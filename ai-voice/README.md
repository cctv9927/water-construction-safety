# AI Voice Module - 语音处理模块

## 模块概述

水利工地安全监管系统的语音处理模块，提供语音识别、意图检测和告警播报功能。

## 技术栈

- **语音识别**：OpenAI Whisper (base 模型)
- **语音合成**：Microsoft Edge TTS (免费，无需 API Key)
- **Web 框架**：FastAPI

## 功能特性

### 1. 语音识别 (Whisper)
- 支持中文普通话识别
- 支持音频文件上传和 URL 拉取
- 返回识别文本、语言、时长和分段信息

### 2. 意图识别
- 基于关键词的意图检测
- 支持多种水利工地安全相关意图：
  - 紧急求助 (alert_help)
  - 火灾报警 (alert_fire)
  - 人员伤亡 (alert_injury)
  - 环境异常 (alert_environment)
  - 启动/停止指令 (command_start/stop)
  - 疏散指令 (command_evacuate)
  - 状态查询 (status_query)

### 3. 告警触发
- 根据意图类型自动判断告警级别 (P0/P1/P2)
- 支持自动语音播报
- 可配置的回调函数扩展

### 4. TTS 语音播报
- 多种中文音色可选
- 可调节语速、音量和音调
- 支持流式播报

## API 接口

### 健康检查
```
GET /health
```

### 语音识别
```
POST /recognize
  - Content-Type: multipart/form-data
  - file: 音频文件 (mp3/wav/ogg/m4a)
  - trigger_alert: 是否触发告警 (默认 true)

Response:
{
  "code": 0,
  "message": "success",
  "text": "救命，这里着火了",
  "language": "zh",
  "duration": 3.5,
  "intent": {
    "type": "alert_fire",
    "confidence": 0.95,
    "entities": {"location": "这里"},
    "keywords_matched": ["火", "着"]
  },
  "alert": {
    "level": "P0",
    "message": "检测到火灾报警，请立即确认",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### URL 语音识别
```
POST /recognize/url
{
  "audio_url": "https://example.com/audio.mp3",
  "trigger_alert": true
}
```

### 文本转语音
```
POST /tts
{
  "text": "检测到紧急告警，请立即撤离",
  "voice": "zh-CN-Xiaoxiao"
}
```

### 播报告警
```
POST /alert/announce?message=检测到紧急告警&level=P0
```

### 列出可用音色
```
GET /voices
```

## 告警级别

| 级别 | 说明 | 响应时间 |
|------|------|----------|
| P0 | 紧急（求助/火灾/伤亡/疏散） | 立即响应 |
| P1 | 重要（环境异常/停止指令） | 快速响应 |
| P2 | 一般（状态查询/启动指令） | 正常处理 |

## 安装

```bash
cd ai-voice
pip install -r requirements.txt
```

## 运行

```bash
# 直接运行
python main.py

# 或使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8083
```

## 依赖

- Python 3.9+
- torch (Whisper 依赖)
- ffmpeg (音频处理)

安装 ffmpeg:
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# 下载 https://ffmpeg.org/download.html
```

## 示例

### Python 客户端调用

```python
import httpx
import base64

# 1. 语音识别
with open("test.mp3", "rb") as f:
    response = httpx.post(
        "http://localhost:8083/recognize",
        files={"file": f},
        data={"trigger_alert": True}
    )
result = response.json()
print(result["text"], result["intent"]["type"])

# 2. TTS 播报
response = httpx.post(
    "http://localhost:8083/tts",
    json={"text": "检测到紧急告警，请立即撤离"}
)
audio_base64 = response.json()["audio_data"]
audio_bytes = base64.b64decode(audio_base64)
with open("output.mp3", "wb") as f:
    f.write(audio_bytes)
```

## 与其他模块集成

- **ai-coordinator**: 接收告警事件，协调多模块响应
- **ai-vision**: 接收视频检测结果，综合判断
- **sensor-collector**: 接收传感器数据，辅助判断

## 开发注意事项

1. Whisper 模型首次运行会下载，耐心等待
2. TTS 需要网络连接访问 Edge TTS 服务
3. 告警播报在后台进行，不阻塞请求响应
