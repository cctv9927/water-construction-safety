# 水利建设工地质量安全监管系统 - 接口协议文档

## 1. 感知层 → AI平台 数据接口

### 1.1 MQTT 传感器数据上报接口

**Topic 规范**: `site/{site_id}/sensor/{sensor_type}`

**支持的传感器类型**:
- `temperature` - 温度
- `pressure` - 压力
- `vibration` - 震动
- `displacement` - 位移
- `flow` - 流量
- `wind_speed` - 风速
- `rainfall` - 降雨量

**MQTT QoS**: Level 1 (至少一次送达)

**消息 Payload JSON Schema**:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SensorData",
  "description": "传感器数据上报格式",
  "type": "object",
  "required": ["site_id", "sensor_id", "sensor_type", "value", "unit", "timestamp"],
  "properties": {
    "site_id": {
      "type": "string",
      "description": "工地ID",
      "pattern": "^site_[a-zA-Z0-9]{8,32}$",
      "examples": ["site_abc12345"]
    },
    "sensor_id": {
      "type": "string",
      "description": "传感器唯一标识",
      "pattern": "^sensor_[a-zA-Z0-9]{8,32}$",
      "examples": ["sensor_tmp_001"]
    },
    "sensor_type": {
      "type": "string",
      "enum": ["temperature", "pressure", "vibration", "displacement", "flow", "wind_speed", "rainfall"],
      "description": "传感器类型"
    },
    "value": {
      "type": "number",
      "description": "传感器测量值"
    },
    "unit": {
      "type": "string",
      "description": "单位",
      "examples": ["℃", "kPa", "mm/s", "mm", "m³/h", "m/s", "mm"]
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "数据采集时间 (UTC)",
      "examples": ["2026-05-14T10:30:00.000Z"]
    },
    "location": {
      "type": "object",
      "description": "传感器位置坐标",
      "properties": {
        "latitude": {
          "type": "number",
          "minimum": -90,
          "maximum": 90
        },
        "longitude": {
          "type": "number",
          "minimum": -180,
          "maximum": 180
        },
        "altitude": {
          "type": "number",
          "description": "海拔高度 (米)"
        },
        "location_name": {
          "type": "string",
          "description": "位置描述",
          "examples": ["大坝主体-东侧"]
        }
      }
    },
    "metadata": {
      "type": "object",
      "description": "传感器元数据",
      "properties": {
        "device_model": {
          "type": "string",
          "examples": ["TH100"]
        },
        "firmware_version": {
          "type": "string",
          "examples": ["1.2.3"]
        },
        "battery_level": {
          "type": "number",
          "minimum": 0,
          "maximum": 100,
          "description": "电池电量百分比"
        },
        "signal_strength": {
          "type": "integer",
          "description": "信号强度 dBm",
          "examples": [-65]
        }
      }
    }
  }
}
```

**示例消息**:

```json
{
  "site_id": "site_abc12345",
  "sensor_id": "sensor_tmp_001",
  "sensor_type": "temperature",
  "value": 25.6,
  "unit": "℃",
  "timestamp": "2026-05-14T10:30:00.000Z",
  "location": {
    "latitude": 30.5728,
    "longitude": 114.3215,
    "altitude": 52.3,
    "location_name": "大坝主体-东侧"
  },
  "metadata": {
    "device_model": "TH100",
    "firmware_version": "1.2.3",
    "battery_level": 85,
    "signal_strength": -65
  }
}
```

### 1.2 RTSP 视频流注册接口

**说明**: 视频流通过 Video Pipeline 服务内部处理，无需外部API接口。摄像头配置通过管理接口下发。

**摄像头配置数据模型**:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CameraConfig",
  "type": "object",
  "required": ["camera_id", "site_id", "rtsp_url", "name", "location"],
  "properties": {
    "camera_id": {
      "type": "string",
      "pattern": "^cam_[a-zA-Z0-9]{8,32}$"
    },
    "site_id": {
      "type": "string",
      "pattern": "^site_[a-zA-Z0-9]{8,32}$"
    },
    "name": {
      "type": "string",
      "maxLength": 100
    },
    "rtsp_url": {
      "type": "string",
      "format": "uri",
      "description": "RTSP 流地址",
      "examples": ["rtsp://192.168.1.100:554/stream1"]
    },
    "location": {
      "type": "object",
      "properties": {
        "latitude": { "type": "number" },
        "longitude": { "type": "number" },
        "altitude": { "type": "number" },
        "location_name": { "type": "string" }
      }
    },
    "stream_config": {
      "type": "object",
      "properties": {
        "fps": {
          "type": "integer",
          "minimum": 1,
          "maximum": 30,
          "default": 5
        },
        "resolution": {
          "type": "string",
          "enum": ["1920x1080", "1280x720", "640x480"],
          "default": "1280x720"
        },
        "ai_analysis_enabled": {
          "type": "boolean",
          "default": true
        }
      }
    }
  }
}
```

### 1.3 视频帧数据内部接口

**内部 gRPC 接口** (Video Pipeline → AI 推理服务):

```protobuf
syntax = "proto3";

package water_construction.v1;

service VideoAnalysis {
  rpc SubmitFrame(FrameData) returns (SubmitResponse);
  rpc GetResults(GetResultsRequest) returns (DetectionResults);
  rpc SubscribeAlerts(AlertSubscription) returns (stream AlertEvent);
}

message FrameData {
  string frame_id = 1;
  string camera_id = 2;
  bytes image_data = 3;
  int64 timestamp_ms = 4;
  FrameMetadata metadata = 5;
}

message FrameMetadata {
  int32 width = 1;
  int32 height = 2;
  string encoding = 3;  // jpeg, png
  int32 sequence_number = 4;
}

message SubmitResponse {
  bool accepted = 1;
  string message = 2;
}

message GetResultsRequest {
  string frame_id = 1;
  int64 timeout_ms = 2;
}

message DetectionResults {
  string frame_id = 1;
  repeated Detection detections = 2;
  int64 processed_at_ms = 3;
}

message Detection {
  string class_name = 1;      // helmet, no_helmet, worker, vehicle, material, danger_zone, etc.
  float confidence = 2;
  BoundingBox bbox = 3;
  string detection_id = 4;
}

message BoundingBox {
  float x_min = 1;
  float y_min = 2;
  float x_max = 3;
  float y_max = 4;
  float area_ratio = 5;  // 占画面比例
}

message AlertSubscription {
  string site_id = 1;
  repeated string alert_types = 2;
}

message AlertEvent {
  string event_id = 1;
  string alert_type = 2;
  string severity = 3;   // P0, P1, P2
  DetectionResults source = 4;
  int64 timestamp_ms = 5;
}
```

---

## 2. AI平台 → 应用层 API 路由设计

### 2.1 API Gateway 路由总览

```
/api/v1
├── /auth                    # 认证相关
│   ├── POST /auth/login
│   ├── POST /auth/refresh
│   └── POST /auth/logout
│
├── /sites                   # 工地管理
│   ├── GET  /sites                    # 列表
│   ├── POST /sites                    # 创建
│   ├── GET  /sites/{site_id}          # 详情
│   ├── PUT  /sites/{site_id}          # 更新
│   └── DELETE /sites/{site_id}        # 删除
│
├── /sensors                 # 传感器管理
│   ├── GET  /sensors
│   ├── POST /sensors
│   ├── GET  /sensors/{sensor_id}
│   ├── GET  /sensors/{sensor_id}/data  # 时序数据查询
│   └── GET  /sensors/{sensor_id}/stats # 统计信息
│
├── /cameras                 # 摄像头管理
│   ├── GET  /cameras
│   ├── POST /cameras
│   ├── GET  /cameras/{camera_id}
│   ├── PUT  /cameras/{camera_id}
│   └── GET  /cameras/{camera_id}/stream # 获取流地址
│
├── /alerts                  # 告警管理
│   ├── GET  /alerts                     # 列表
│   ├── GET  /alerts/{alert_id}          # 详情
│   ├── PUT  /alerts/{alert_id}/status   # 更新状态
│   └── GET  /alerts/statistics          # 统计
│
├── /problems                # 问题管理
│   ├── GET  /problems                   # 列表
│   ├── POST /problems                   # 创建
│   ├── GET  /problems/{problem_id}      # 详情
│   ├── PUT  /problems/{problem_id}      # 更新
│   ├── POST /problems/{problem_id}/transfer   # 转发
│   ├── POST /problems/{problem_id}/verify     # 复核
│   └── POST /problems/{problem_id}/close       # 关闭
│
├── /workflow                # 工作流
│   ├── GET  /workflow/templates        # 模板列表
│   ├── POST /workflow/instances         # 创建实例
│   ├── GET  /workflow/instances/{instance_id} # 实例详情
│   └── GET  /workflow/tasks             # 待办任务
│
├── /expert                  # 专家系统
│   ├── POST /expert/query              # 问答查询
│   ├── GET  /expert/knowledge           # 知识库浏览
│   └── POST /expert/document           # 生成文档
│
├── /reports                 # 报表
│   ├── GET  /reports                    # 报表列表
│   ├── POST /reports/generate           # 生成报表
│   └── GET  /reports/{report_id}/download # 下载
│
├── /sandtable               # 电子沙盘
│   ├── GET  /sandtable/scene            # 场景数据
│   ├── GET  /sandtable/cameras           # 摄像头位置
│   └── GET  /sandtable/sensors           # 传感器标注
│
└── /ws                      # WebSocket
    ├── /ws/alerts           # 实时告警推送
    ├── /ws/problems         # 问题状态变更推送
    └── /ws/stream/{camera_id} # 实时视频流元数据
```

### 2.2 核心 API 详细定义

#### 2.2.1 认证接口

**POST /api/v1/auth/login**

Request:
```json
{
  "username": "string",
  "password": "string"
}
```

Response (200):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

#### 2.2.2 告警列表接口

**GET /api/v1/alerts**

Query Parameters:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20，最大100 |
| site_id | string | 否 | 工地ID过滤 |
| severity | string | 否 | P0/P1/P2 |
| status | string | 否 | pending/processed/closed |
| start_time | datetime | 否 | 开始时间 |
| end_time | datetime | 否 | 结束时间 |

Response (200):
```json
{
  "total": 1234,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "alert_id": "alert_abc123",
      "site_id": "site_abc12345",
      "site_name": "三峡大坝工地",
      "alert_type": "helmet_detection",
      "severity": "P1",
      "title": "未佩戴安全帽检测",
      "description": "检测到施工人员未佩戴安全帽",
      "source": {
        "type": "camera",
        "id": "cam_001",
        "name": "东门入口摄像头"
      },
      "evidence": {
        "image_url": "https://storage.example.com/alerts/alert_abc123/frame.jpg",
        "video_clip_url": "https://storage.example.com/alerts/alert_abc123/clip.mp4"
      },
      "status": "pending",
      "created_at": "2026-05-14T10:30:00Z",
      "updated_at": "2026-05-14T10:30:00Z",
      "handled_by": null,
      "handled_at": null
    }
  ]
}
```

#### 2.2.3 问题管理接口

**POST /api/v1/problems**

Request:
```json
{
  "site_id": "site_abc12345",
  "title": "东门入口未佩戴安全帽",
  "description": "通过AI检测发现，东门入口处有施工人员未佩戴安全帽进入施工现场",
  "problem_type": "safety_hazard",
  "severity": "P1",
  "source": {
    "type": "ai_detection",
    "alert_id": "alert_abc123"
  },
  "assignee_id": "user_001",
  "due_date": "2026-05-15",
  "tags": ["安全帽", "AI检测"],
  "attachments": [
    {
      "type": "image",
      "url": "https://storage.example.com/problems/prob_001/evidence.jpg"
    }
  ]
}
```

Response (201):
```json
{
  "problem_id": "prob_xyz789",
  "site_id": "site_abc12345",
  "title": "东门入口未佩戴安全帽",
  "status": "pending",
  "workflow_instance_id": "wf_instance_001",
  "created_at": "2026-05-14T10:35:00Z",
  "creator": {
    "user_id": "user_admin",
    "name": "系统管理员"
  }
}
```

**问题状态流转**:

```
pending → processing → completed → verified
   ↓           ↓            ↓
   └─── closed (拒绝/撤销)
```

#### 2.2.4 专家问答接口

**POST /api/v1/expert/query**

Request:
```json
{
  "question": "大坝混凝土浇筑时温度超过多少度需要采取措施？",
  "site_id": "site_abc12345",
  "context": {
    "problem_id": "prob_xyz789",
    "related_docs": ["doc_001", "doc_002"]
  },
  "include_sources": true
}
```

Response (200):
```json
{
  "answer_id": "ans_123",
  "question": "大坝混凝土浇筑时温度超过多少度需要采取措施？",
  "answer": "根据《水利水电工程施工安全技术规程》，大坝混凝土浇筑温度控制要求如下：...",
  "sources": [
    {
      "doc_id": "doc_001",
      "doc_name": "水利水电工程施工安全技术规程",
      "section": "第5.2.3条",
      "relevance_score": 0.95,
      "excerpt": "混凝土浇筑温度不宜超过28℃，在高温季节施工时不应超过32℃..."
    }
  ],
  "related_questions": [
    "混凝土温控措施有哪些？",
    "大坝冷却水管如何布置？"
  ],
  "confidence": 0.92,
  "created_at": "2026-05-14T10:40:00Z"
}
```

---

## 3. 统一告警数据格式

### 3.1 告警数据模型

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "UnifiedAlert",
  "description": "统一告警数据格式 (AI平台 → 应用层 → 通知服务)",
  "type": "object",
  "required": ["alert_id", "site_id", "site_name", "alert_type", "severity", "title", "description", "timestamp", "source"],
  "properties": {
    "alert_id": {
      "type": "string",
      "pattern": "^alert_[a-zA-Z0-9]{8,32}$",
      "description": "告警唯一标识"
    },
    "site_id": {
      "type": "string",
      "pattern": "^site_[a-zA-Z0-9]{8,32}$"
    },
    "site_name": {
      "type": "string",
      "maxLength": 200
    },
    "alert_type": {
      "type": "string",
      "enum": [
        "helmet_detection",       // 安全帽检测
        "person_fall_detection",   // 人员跌落
        "vehicle_overload",        // 车辆超载
        "danger_zone_intrusion",   // 危险区域入侵
        "fire_detection",          // 火灾检测
        "crowd_aggregation",       // 人员聚集
        "sensor_threshold",        // 传感器阈值告警
        "sensor_anomaly",         // 传感器数据异常
        "weather_warning",        // 天气预警
        "equipment_failure",      // 设备故障
        "speech_command"          // 语音指令触发
      ],
      "description": "告警类型"
    },
    "severity": {
      "type": "string",
      "enum": ["P0", "P1", "P2"],
      "description": "告警级别: P0=立即处理, P1=当天处理, P2=计划处理"
    },
    "title": {
      "type": "string",
      "maxLength": 200,
      "description": "告警标题"
    },
    "description": {
      "type": "string",
      "maxLength": 2000,
      "description": "告警详细描述"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "告警发生时间 (UTC)"
    },
    "source": {
      "type": "object",
      "description": "告警来源",
      "required": ["type", "id", "name"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["camera", "sensor", "uav", "manual", "system"]
        },
        "id": {
          "type": "string"
        },
        "name": {
          "type": "string"
        },
        "location": {
          "type": "object",
          "properties": {
            "latitude": { "type": "number" },
            "longitude": { "type": "number" },
            "altitude": { "type": "number" }
          }
        }
      }
    },
    "evidence": {
      "type": "object",
      "description": "告警证据",
      "properties": {
        "image_url": {
          "type": "string",
          "format": "uri"
        },
        "video_clip_url": {
          "type": "string",
          "format": "uri"
        },
        "sensor_data": {
          "type": "object",
          "description": "相关传感器数据快照"
        }
      }
    },
    "detections": {
      "type": "array",
      "description": "AI检测结果详情 (当来源为camera/uav时)",
      "items": {
        "type": "object",
        "properties": {
          "class_name": { "type": "string" },
          "confidence": { "type": "number" },
          "bbox": {
            "type": "object",
            "properties": {
              "x_min": { "type": "number" },
              "y_min": { "type": "number" },
              "x_max": { "type": "number" },
              "y_max": { "type": "number" }
            }
          }
        }
      }
    },
    "status": {
      "type": "string",
      "enum": ["pending", "processing", "processed", "closed"],
      "default": "pending"
    },
    "workflow": {
      "type": "object",
      "description": "关联的工作流信息",
      "properties": {
        "problem_id": { "type": "string" },
        "workflow_instance_id": { "type": "string" }
      }
    },
    "notification": {
      "type": "object",
      "description": "通知状态",
      "properties": {
        "sms_sent": { "type": "boolean", "default": false },
        "email_sent": { "type": "boolean", "default": false },
        "app_push_sent": { "type": "boolean", "default": false },
        "recipients": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "user_id": { "type": "string" },
              "name": { "type": "string" },
              "channels": {
                "type": "array",
                "items": { "type": "string", "enum": ["sms", "email", "app"] }
              }
            }
          }
        }
      }
    },
    "metadata": {
      "type": "object",
      "description": "扩展元数据"
    }
  }
}
```

### 3.2 告警分级规则

| 告警类型 | 条件 | 级别 | 处理要求 |
|---------|------|------|---------|
| 人员跌落检测 | 任意检测 | P0 | 立即处理，通知安全主管 |
| 危险区域入侵 | 高风险区域 | P0 | 立即处理 |
| 火灾检测 | 任意检测 | P0 | 立即处理，联动消防 |
| 传感器阈值 | 超限严重程度>80% | P0 | 立即处理 |
| 未佩戴安全帽 | 单次检测 | P1 | 当天处理 |
| 车辆超载 | 超限>20% | P1 | 当天处理 |
| 人员聚集 | 超过密度阈值 | P1 | 当天处理 |
| 传感器阈值 | 超限严重程度<80% | P2 | 计划处理 |
| 设备离线 | 超过30分钟 | P2 | 计划处理 |

---

## 4. MQTT Topic 规划

### 4.1 Topic 命名规范

```
wcs/{environment}/{site_id}/{category}/{sub_category}/{detail}
```

- `wcs`: 系统前缀
- `environment`: `prod`/`staging`/`dev`
- `site_id`: 工地ID
- `category`: 数据类别
- `sub_category`: 子类别
- `detail`: 详细标识

### 4.2 Topic 列表

| Topic Pattern | 方向 | QoS | 说明 | Payload |
|--------------|------|-----|------|---------|
| `wcs/{env}/site/{site_id}/sensor/+/data` | 上报 | 1 | 传感器数据上报 | SensorData JSON |
| `wcs/{env}/site/{site_id}/sensor/+/status` | 上报 | 1 | 传感器状态变更 | SensorStatus JSON |
| `wcs/{env}/site/{site_id}/camera/+/stream` | 内部 | 2 | 视频流元数据 | StreamMeta JSON |
| `wcs/{env}/site/{site_id}/camera/+/alert` | 上报 | 1 | 摄像头AI告警 | CameraAlert JSON |
| `wcs/{env}/site/{site_id}/uav/+/telemetry` | 上报 | 1 | 无人机遥测数据 | UAVTelemetry JSON |
| `wcs/{env}/site/{site_id}/uav/+/command` | 下发 | 2 | 无人机控制指令 | UAVCommand JSON |
| `wcs/{env}/site/{site_id}/alert/{alert_id}` | 发布 | 1 | 统一告警发布 | UnifiedAlert JSON |
| `wcs/{env}/site/{site_id}/control/+/ack` | 上报 | 1 | 控制指令回执 | CommandAck JSON |
| `wcs/{env}/system/health` | 发布 | 0 | 系统健康状态 | HealthStatus JSON |
| `wcs/{env}/system/shutdown` | 系统 | 2 | 全量关机指令 | - |

### 4.3 Topic 权限矩阵

| Topic Pattern | 客户端角色 | 权限 |
|--------------|-----------|------|
| `wcs/+/site/+/sensor/+/data` | IoT设备 | PUBLISH |
| `wcs/+/site/+/sensor/+/data` | IoT Hub | SUBSCRIBE |
| `wcs/+/site/+/camera/+/alert` | Video Pipeline | PUBLISH |
| `wcs/+/site/+/alert/+/` | Alert Service | SUBSCRIBE |
| `wcs/+/site/+/alert/+/` | 所有管理后台 | SUBSCRIBE |
| `wcs/+/site/+/uav/+/command` | UAV Control | PUBLISH |
| `wcs/+/site/+/uav/+/telemetry` | UAV Control | SUBSCRIBE |
| `wcs/+/site/+/uav/+/command` | 管理员 | PUBLISH |

### 4.4 保留 Topic

| Topic | 说明 |
|-------|------|
| `$SYS/broker/log/#` | Broker日志 |
| `$SYS/broker/clients/#` | 客户端连接状态 |
| `$SYS/broker/cluster/#` | 集群状态 |

---

## 5. WebSocket 实时推送协议

### 5.1 连接规范

**URL**: `wss://api.example.com/api/v1/ws/{endpoint}`

**认证**: 通过 URL Query 参数或首条消息携带 Token

```
wss://api.example.com/api/v1/ws/alerts?token={access_token}
```

### 5.2 消息格式

```json
{
  "type": "message_type",
  "channel": "channel_name",
  "data": { ... },
  "timestamp": "2026-05-14T10:30:00.000Z",
  "id": "msg_unique_id"
}
```

### 5.3 推送消息类型

| type | channel | 说明 | data |
|------|---------|------|------|
| `alert.new` | `alerts` | 新告警 | UnifiedAlert |
| `alert.update` | `alerts` | 告警更新 | {alert_id, status, ...} |
| `problem.update` | `problems` | 问题状态变更 | Problem |
| `sensor.anomaly` | `sensors` | 传感器异常 | SensorData |
| `camera.online` | `cameras` | 摄像头上线 | {camera_id} |
| `camera.offline` | `cameras` | 摄像头离线 | {camera_id} |

### 5.4 心跳机制

- 客户端每 30 秒发送心跳:
```json
{"type": "ping", "timestamp": "2026-05-14T10:30:00.000Z"}
```

- 服务端响应:
```json
{"type": "pong", "timestamp": "2026-05-14T10:30:00.000Z"}
```

- 超时 60 秒未响应则断开连接
