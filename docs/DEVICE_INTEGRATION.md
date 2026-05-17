# 真实设备接入指南

本文档详细介绍水利工地安全监管系统中各类真实传感设备和视频设备的接入方法，包括硬件配置、通信协议、数据格式和 ThingsBoard 平台对接步骤。

---

## 目录

1. [传感器接入](#1-传感器接入)
2. [视频设备接入](#2-视频设备接入)
3. [设备接入配置示例](#3-设备接入配置示例)
4. [ThingsBoard 平台配置](#4-thingsboard-平台配置)
5. [故障排查](#5-故障排查)

---

## 1. 传感器接入

### 1.1 水位传感器

#### 硬件选型建议

| 型号 | 品牌 | 协议 | 量程 | 精度 | 适用场景 |
|------|------|------|------|------|----------|
| WL-100 | 恒润 | Modbus RTU | 0-50m | ±0.1%FS | 河道/水库 |
| PTP-201 | ABB | Modbus TCP | 0-30m | ±0.2%FS | 大坝 |
| E+H FMU40 | Endress+Hauser | HART | 0-10m | ±2mm | 明渠 |

#### 通信协议

**Modbus RTU (RS485)**
- 波特率：9600/19200/38400 bps
- 数据位：8
- 停止位：1
- 校验：无校验 (N, 8, 1)

**Modbus TCP**
- 默认端口：502
- 设备IP需在同一网段

#### 数据格式 (JSON)

```json
{
  "sensor_id": "WL-001",
  "type": "water_level",
  "value": 12.5,
  "unit": "meter",
  "timestamp": 1716000000,
  "location": {
    "lat": 29.65,
    "lon": 91.1
  },
  "metadata": {
    "device_model": "WL-100",
    "firmware_version": "2.1.4",
    "signal_strength": -65,
    "battery_level": 85
  }
}
```

#### 寄存器映射

| 寄存器地址 | 名称 | 数据类型 | 说明 |
|------------|------|----------|------|
| 40001 | 水位值 | FLOAT | 当前水位(m) |
| 40003 | 水位变化率 | FLOAT | m/h |
| 40005 | 传感器状态 | INT | 0=正常,1=告警 |
| 40006 | 采集时间 | UINT32 | Unix时间戳 |

#### ThingsBoard 配置步骤

1. **创建设备**
   - 进入 ThingsBoard → 设备管理 → 添加设备
   - 设备名称：`WL-001_水位传感器`
   - 设备类型：`WaterLevelSensor`
   - 获取访问令牌

2. **配置转换器**
   - 进入规则链 → 创建新的转换器
   - 上行转换器解析 Modbus 数据
   - 数据模板映射到时序数据

3. **配置规则链**
   - 添加 Modbus 集成节点
   - 配置 RS485/TCP 连接参数
   - 设置轮询间隔（建议10秒）

### 1.2 雨量传感器

#### 硬件选型

| 型号 | 类型 | 精度 | 输出 |
|------|------|------|------|
| RG-01 | 翻斗式 | ±2% | 脉冲/RS485 |
| TR-02 | 光学式 | ±5% | RS485 |
| RG-50 | 虹吸式 | ±1% | 4-20mA |

#### 通信协议

**脉冲计数**
- 每个脉冲代表 0.1mm 或 1mm 降雨量
- 采集频率：建议每分钟读取累计值

**RS485 Modbus**
- 功能码：0x04 (读输入寄存器)
- 寄存器：累计降雨量、瞬时雨强

#### 数据格式

```json
{
  "sensor_id": "RF-001",
  "type": "rainfall",
  "value": 15.5,
  "unit": "mm/h",
  "accumulated": 125.8,
  "accumulated_unit": "mm",
  "timestamp": 1716000000,
  "location": {
    "lat": 29.65,
    "lon": 91.1
  }
}
```

#### 阈值告警规则

| 雨强等级 | 阈值 (mm/h) | 告警级别 | 处置建议 |
|----------|-------------|----------|----------|
| 小雨 | 0.1-10 | 正常 | 持续监测 |
| 中雨 | 10-25 | 黄色 | 加强巡查 |
| 大雨 | 25-50 | 橙色 | 现场值守 |
| 暴雨 | >50 | 红色 | 紧急撤离 |

### 1.3 边坡位移传感器

#### 硬件类型

| 类型 | 原理 | 精度 | 安装方式 |
|------|------|------|----------|
| GNSS位移计 | 卫星定位 | ±2mm | 基准站+监测点 |
| 拉线位移计 | 电阻式 | ±0.1%FS | 固定在边坡 |
| 振动光纤 | 布里渊散射 | ±0.01% | 埋入边坡 |
| 边坡雷达 | InSAR | ±0.1mm | 非接触式 |

#### 通信协议

**LoRa 无线**
- 工作频段：470-510MHz (中国)
- 扩频因子：7-12
- 发射功率：≤17dBm
- 典型距离：3-5km (视距)

**RS485 有线**
- 推荐用于固定安装
- 抗干扰能力强

#### 数据格式

```json
{
  "sensor_id": "DP-001",
  "type": "displacement",
  "value": 25.3,
  "unit": "mm",
  "displacement_x": 15.2,
  "displacement_y": 8.5,
  "displacement_z": 1.6,
  "velocity": 0.5,
  "velocity_unit": "mm/day",
  "timestamp": 1716000000,
  "location": {
    "lat": 29.65,
    "lon": 91.1,
    "depth": 2.5
  }
}
```

#### 安装位置建议

1. **测点布置原则**
   - 沿边坡走向布置 3-5 个测点
   - 在潜在滑动面附近加密布设
   - 远离施工扰动区域

2. **安装高度**
   - 基准点：边坡顶部稳定区域
   - 监测点：边坡中下部重点区域
   - 间距：5-20m（根据风险等级）

3. **保护措施**
   - 加装防护箱防水防尘
   - 定期校准和清洁
   - 接地防雷

### 1.4 温湿度传感器

#### 硬件选型

| 型号 | 测温范围 | 湿度范围 | 精度 | 协议 |
|------|----------|----------|------|------|
| SHT40 | -40~125°C | 0-100%RH | ±0.3°C | I2C/RS485 |
| DS18B20 | -55~125°C | - | ±0.5°C | 1-Wire |
| PT100 | -200~600°C | - | ±0.1°C | Modbus |

#### 通信协议

**Modbus RTU**
```bash
# 读取温度 (功能码 0x04)
Request:  01 04 00 00 00 02 C1 CB
Response: 01 04 04 0C D8 41 20 7A 3F
```

**Modbus TCP**
- 标准 Modbus TCP 封装
- Unit ID 标识不同传感器

#### 数据格式

```json
{
  "sensor_id": "TH-001",
  "type": "temperature_humidity",
  "temperature": 25.3,
  "temperature_unit": "°C",
  "humidity": 65.5,
  "humidity_unit": "%RH",
  "dew_point": 18.2,
  "timestamp": 1716000000,
  "location": {
    "lat": 29.65,
    "lon": 91.1
  }
}
```

---

## 2. 视频设备接入

### 2.1 RTSP 摄像头

#### 支持品牌

- 海康威视 (Hikvision)
- 大华 (Dahua)
- 宇视 (Uniview)
- 华为 (Huawei)
- TP-Link、宇视等主流品牌

#### ONVIF 协议配置

1. **启用 ONVIF**
   - 摄像头 Web UI → 网络 → 高级设置
   - 启用 ONVIF 协议
   - 设置 ONVIF 用户

2. **获取设备信息**
```bash
# 使用 ONVIF Device Manager 扫描
# 或使用命令行工具
wsdl https://www.onvif.org/ver10/device/wsdl/devicemgmt.wsdl
```

3. **推流地址格式**

| 协议 | 地址格式 | 示例 |
|------|----------|------|
| RTSP | `rtsp://user:pass@ip:554/stream` | `rtsp://192.168.1.64:554/live` |
| RTSP | `rtsp://ip:554/h264/ch1/main/av_stream` | 海康主码流 |
| RTSP | `rtsp://ip:554/h264/ch1/sub/av_stream` | 海康子码流 |
| RTMP | `rtmp://ip:1935/live/stream1` | 需要转码 |

### 2.2 EasyDarwin 流媒体服务

EasyDarwin 是开源的 RTMP/HLS 流媒体服务器，用于接收摄像头推流并转发。

#### Docker 部署

```yaml
# docker-compose.yml
services:
  easy-darwin:
    image: minglongtech/easy-darwin:latest
    ports:
      - "1935:1935"   # RTMP
      - "8080:8080"   # HTTP API
    environment:
      - GOPATH=/go
    volumes:
      - ./hls:/usr/local/minglong/workspace/hls
```

#### 推流命令

```bash
# 使用 ffmpeg 推流
ffmpeg -rtsp_transport tcp \
  -i "rtsp://camera_ip:554/stream" \
  -c copy \
  -f flv \
  rtmp://easy-darwin:1935/live/stream1

# HLS 输出配置
ffmpeg -rtsp_transport tcp \
  -i "rtsp://camera_ip:554/stream" \
  -c:v libx264 -c:a aac \
  -f hls \
  -hls_time 2 \
  -hls_list_size 10 \
  http://easy-darwin:8080/hls/stream1.m3u8
```

### 2.3 无人机接入

#### DJI SDK 配置

1. **开发准备**
   - 注册 DJI Developer 账号
   - 创建应用获取 App Key
   - 下载 DJI Mobile SDK

2. **无人机型号支持**
   - Mavic 系列
   - Phantom 4 Pro+
   - Matrice 300 RTK

3. **WebSocket 视频流**

```javascript
// 无人机视频流 WebSocket 服务
const ws = new WebSocket('ws://drone-server:8080/video');

ws.onopen = () => {
  console.log('已连接到无人机视频流');
};

ws.onmessage = (event) => {
  const frame = event.data;
  // 渲染到 Canvas
  ctx.drawImage(frame, 0, 0);
};
```

#### 巡检路线模拟

| 航点 | 纬度 | 经度 | 高度(m) | 动作 |
|------|------|------|---------|------|
| WP1 | 29.6501 | 91.1001 | 50 | 悬停拍照 |
| WP2 | 29.6502 | 91.1002 | 60 | 继续飞行 |
| WP3 | 29.6503 | 91.1003 | 50 | 悬停监测 |
| WP4 | 29.6504 | 91.1004 | 40 | 返航点 |

---

## 3. 设备接入配置示例

### sensor-collector/config.yaml

```yaml
# 传感器采集器配置
mqtt:
  broker: "tcp://thingsboard:1883"
  client_id: "sensor-collector-01"
  username: "YOUR_THINGSBOARD_TOKEN"
  password: ""
  topics:
    - "v1/devices/me/attributes"
    - "v1/devices/me/rpc/request/+"
    - "device/+/temperature"
    - "device/+/pressure"
    - "device/+/vibration"
    - "device/+/displacement"
    - "device/+/flow"
    - "device/+/wind_speed"
    - "device/+/rainfall"
  qos: 1
  keepalive: 60
  reconnect_delay: 5

# 设备列表
devices:
  # 水位传感器
  - name: 水位传感器1号
    sensor_id: WL-001
    type: water_level
    protocol: modbus_tcp
    host: 192.168.1.100
    port: 502
    unit_id: 1
    register_address: 0
    data_type: float32
    polling_interval: 10  # 秒
    enabled: true
    
  # 雨量传感器
  - name: 雨量传感器1号
    sensor_id: RF-001
    type: rainfall
    protocol: modbus_rtu
    host: /dev/ttyUSB0
    baudrate: 9600
    unit_id: 2
    register_address: 0
    data_type: int16
    polling_interval: 60  # 秒
    enabled: true
    
  # 边坡位移传感器
  - name: 位移传感器1号
    sensor_id: DP-001
    type: displacement
    protocol: lora
    device_addr: 0x0011
    spreading_factor: 10
    polling_interval: 30
    enabled: true
    
  # 温湿度传感器
  - name: 温湿度传感器1号
    sensor_id: TH-001
    type: temperature_humidity
    protocol: modbus_tcp
    host: 192.168.1.101
    port: 502
    unit_id: 3
    polling_interval: 60
    enabled: true

# 告警阈值配置
alert_rules:
  water_level:
    warning: 8.0
    critical: 9.5
    unit: meter
    
  rainfall:
    warning: 100.0
    critical: 150.0
    unit: mm/h
    
  displacement:
    warning: 200.0
    critical: 350.0
    unit: mm

# 采集配置
collector:
  report_interval: 5      # 批量上报间隔（秒）
  batch_size: 100         # 达到此数量立即触发上报
  log_level: "INFO"
```

### video-streamer/config.yaml

```yaml
# 摄像头配置
cameras:
  - name: 工地入口
    camera_id: CAM-001
    rtsp_url: rtsp://camera-ip-1:554/stream
    enabled: true
    ai_detection: true
    stream_quality: high
    fps: 25
    resolution: 1920x1080
    
  - name: 高边坡监控
    camera_id: CAM-002
    rtsp_url: rtsp://camera-ip-2:554/stream
    enabled: true
    ai_detection: true
    stream_quality: high
    fps: 25
    resolution: 1920x1080
    
  - name: 材料堆放区
    camera_id: CAM-003
    rtsp_url: rtsp://camera-ip-3:554/stream
    enabled: true
    ai_detection: false
    stream_quality: medium
    fps: 15
    
  - name: 塔吊监控
    camera_id: CAM-004
    rtsp_url: rtsp://camera-ip-4:554/stream
    enabled: true
    ai_detection: true
    ptz_control: true
    presets:
      - name: 全景
        position: 0,0,0
      - name: 特写
        position: 180,45,10

# 流媒体服务
streaming:
  server: easy-darwin
  rtmp_port: 1935
  http_port: 8080
  hls_enabled: true
  hls_path: /usr/local/minglong/workspace/hls
  hls_segment_duration: 2
  hls_list_size: 10

# AI 检测配置
ai_detection:
  enabled: true
  model_path: /models/yolov8n.pt
  confidence_threshold: 0.5
  nms_threshold: 0.4
  classes:
    - person
    - helmet
    - vest
    - vehicle
    - machinery
  alert_on:
    - person_without_helmet
    - person_without_vest
    - unauthorized_vehicle

# 录像配置
recording:
  enabled: true
  storage_path: /录像
  retention_days: 30
  motion_detection: true
  schedule:
    - name: 全天录制
      enabled: true
      time_range: "00:00-24:00"
      days: [0,1,2,3,4,5,6]
```

---

## 4. ThingsBoard 平台配置

### 4.1 设备接入流程

```
真实设备 → 采集器 → MQTT Broker → ThingsBoard → 规则链 → 告警/存储
```

### 4.2 MQTT 连接参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 协议 | MQTT | TLS 可选 |
| 端口 | 1883 (1884 TLS) | |
| 主题 | v1/devices/me/telemetry | 上报遥测数据 |
| 主题 | v1/devices/me/attributes | 上报属性 |
| 主题 | v1/devices/me/rpc/request/+ | 接收RPC请求 |
| 认证 | Access Token | 设备级别 |

### 4.3 数据上报格式

```json
// 遥测数据
{
  "ts": 1716000000000,
  "values": {
    "temperature": 25.3,
    "humidity": 65.5,
    "battery": 85
  }
}

// 属性数据
{
  "sensor_id": "WL-001",
  "firmware_version": "2.1.4",
  "hardware_version": "1.0",
  "location": {
    "lat": 29.65,
    "lon": 91.1
  }
}
```

---

## 5. 故障排查

### 5.1 传感器常见问题

| 症状 | 可能原因 | 解决方案 |
|------|----------|----------|
| 无数据 | 通信线缆断开 | 检查RS485接线 |
| 数据异常 | 地址冲突 | 修改设备地址 |
| 读取超时 | 波特率不匹配 | 统一设置为9600 |
| 数值跳变 | 接地不良 | 增加屏蔽接地 |

### 5.2 视频流常见问题

| 症状 | 可能原因 | 解决方案 |
|------|----------|----------|
| 无法连接 | 防火墙阻止 | 开放554端口 |
| 卡顿/延迟 | 带宽不足 | 降低码率/分辨率 |
| 花屏/黑屏 | 编码格式不支持 | 使用H.264 |
| 频繁断连 | 网络不稳定 | 启用TCP传输 |

### 5.3 网络诊断命令

```bash
# 测试设备连通性
ping 192.168.1.100

# 测试端口开放
telnet 192.168.1.100 554

# RTSP 流测试
ffplay rtsp://192.168.1.100:554/live

# MQTT 连接测试
mosquitto_pub -h thingsboard -p 1883 -t test -m "hello"

# 查看 ThingsBoard 日志
docker logs -f thingsboard
```

### 5.4 日志查看

```bash
# 传感器采集器日志
tail -f sensor-collector/logs/collector.log

# 视频流服务日志
tail -f video-streamer/logs/streamer.log

# Docker 容器日志
docker-compose logs -f sensor-collector
docker-compose logs -f video-streamer
```

---

## 附录：设备模拟器

在没有真实设备的情况下，可使用以下模拟器进行测试：

- **sensor-collector/simulator.py** - 传感器数据模拟
- **video-streamer/test_stream.py** - 视频流模拟
- **drone-integration/src/simulator.ts** - 无人机模拟

启动脚本：`scripts/test_device_simulation.sh`

---

*文档版本: v1.0*  
*最后更新: 2024-05-17*  
*维护团队: 水利工地安全监管系统开发组*
