# API 接口文档

> 工程质量安全智慧管理平台 | v1.0.0 | Base URL: `http://localhost:8000/api/v1`

---

## 1. 认证 (Auth)

**基础路径**: `/api/v1/auth`

### 1.1 用户登录

```
POST /auth/login
```

**请求体**:

```json
{
  "username": "string",
  "password": "string"
}
```

**成功响应** (200):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "full_name": "系统管理员",
    "role": "admin",
    "is_active": true,
    "created_at": "2026-05-01T08:00:00Z"
  }
}
```

**错误响应** (401):

```json
{
  "detail": "用户名或密码错误"
}
```

---

### 1.2 用户注册

```
POST /auth/register
```

**请求体**:

```json
{
  "username": "string",
  "password": "string",
  "email": "string",
  "full_name": "string",
  "role": "admin | user | inspector"
}
```

**成功响应** (200):

```json
{
  "id": 2,
  "username": "inspector01",
  "email": "inspector@example.com",
  "full_name": "张检查员",
  "role": "inspector",
  "is_active": true,
  "created_at": "2026-05-02T10:30:00Z"
}
```

---

### 1.3 获取当前用户信息

```
GET /auth/me
```

**请求头**: `Authorization: Bearer <token>`

**成功响应** (200):

```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "系统管理员",
  "role": "admin",
  "is_active": true,
  "created_at": "2026-05-01T08:00:00Z"
}
```

---

### 1.4 刷新 Token

```
POST /auth/refresh
```

**请求头**: `Authorization: Bearer <token>`

**成功响应** (200):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

---

### 1.5 登出

```
POST /auth/logout
```

**成功响应** (200):

```json
{
  "success": true,
  "message": "已退出登录"
}
```

---

## 2. 告警管理 (Alerts)

**基础路径**: `/api/v1/alerts`

### 2.1 获取告警列表

```
GET /alerts/
```

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| level | string | 否 | 告警级别：`critical` / `warning` / `info` |
| status | string | 否 | 状态：`pending` / `processing` / `resolved` / `closed` |
| start_date | datetime | 否 | 开始时间（ISO 8601）|
| end_date | datetime | 否 | 结束时间（ISO 8601）|
| sensor_id | int | 否 | 传感器 ID |
| search | string | 否 | 关键词搜索（标题/描述）|
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页数量，默认 20，最大 100 |

**成功响应** (200):

```json
{
  "total": 156,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": 1,
      "title": "大坝主体-温度过高",
      "description": "监测点 D1-001 温度超过阈值 60°C，当前值 72°C",
      "level": "critical",
      "status": "pending",
      "sensor_id": 5,
      "location": "大坝主体-东侧",
      "created_at": "2026-05-15T14:30:00Z",
      "updated_at": "2026-05-15T14:30:00Z"
    }
  ]
}
```

---

### 2.2 获取告警详情

```
GET /alerts/{alert_id}
```

**路径参数**: `alert_id` — 告警 ID

**成功响应** (200): 返回单条告警对象（同列表项结构）

**错误响应** (404):

```json
{
  "detail": "告警不存在"
}
```

---

### 2.3 创建告警

```
POST /alerts/
```

**请求头**: `Authorization: Bearer <token>`

**请求体**:

```json
{
  "title": "string",
  "description": "string",
  "level": "critical | warning | info",
  "sensor_id": 1,
  "location": "string",
  "metadata": {}
}
```

**成功响应** (200): 返回创建的告警对象

---

### 2.4 更新告警

```
PATCH /alerts/{alert_id}
```

**请求头**: `Authorization: Bearer <token>`

**请求体**（字段可选）:

```json
{
  "status": "processing | resolved | closed",
  "description": "string",
  "resolution_notes": "string"
}
```

**成功响应** (200): 返回更新后的告警对象

---

### 2.5 删除告警

```
DELETE /alerts/{alert_id}
```

**请求头**: `Authorization: Bearer <token>`

**成功响应** (200):

```json
{
  "success": true,
  "message": "告警已删除"
}
```

---

### 2.6 分配告警

```
POST /alerts/{alert_id}/assign
```

**请求体**:

```json
{
  "user_id": 2,
  "notes": "请优先处理"
}
```

**成功响应** (200):

```json
{
  "success": true,
  "message": "已分配给 张检查员"
}
```

---

### 2.7 获取告警处理历史

```
GET /alerts/{alert_id}/history
```

**成功响应** (200):

```json
{
  "alert_id": 1,
  "current_status": "processing",
  "assignments": [
    {
      "user_id": 2,
      "assigned_at": "2026-05-15T15:00:00Z",
      "completed_at": null,
      "notes": "请优先处理"
    }
  ],
  "created_at": "2026-05-15T14:30:00Z",
  "resolved_at": null
}
```

---

## 3. 传感器 (Sensors)

**基础路径**: `/api/v1/sensors`

### 3.1 获取传感器列表

```
GET /sensors/
```

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 否 | 传感器类型 |
| is_active | bool | 否 | 是否在线 |

**成功响应** (200):

```json
[
  {
    "id": 1,
    "name": "温度传感器 D1-T001",
    "type": "temperature",
    "unit": "°C",
    "location": "大坝主体-东侧",
    "is_active": true,
    "last_seen": "2026-05-15T14:55:00Z",
    "created_at": "2026-05-01T08:00:00Z"
  }
]
```

---

### 3.2 获取传感器详情

```
GET /sensors/{sensor_id}
```

**成功响应** (200): 返回单条传感器对象

---

### 3.3 创建传感器

```
POST /sensors/
```

**请求体**:

```json
{
  "name": "string",
  "type": "temperature | pressure | vibration | displacement | flow | wind_speed | rainfall",
  "unit": "string",
  "location": "string",
  "threshold_min": 0.0,
  "threshold_max": 100.0,
  "metadata": {}
}
```

---

### 3.4 获取传感器数据

```
GET /sensors/{sensor_id}/data
```

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_time | datetime | 否 | 开始时间（默认最近24小时）|
| end_time | datetime | 否 | 结束时间（默认当前）|
| limit | int | 否 | 数据点数量，默认 100，最大 10000 |

**成功响应** (200):

```json
{
  "sensor_id": 1,
  "sensor_name": "温度传感器 D1-T001",
  "sensor_type": "temperature",
  "unit": "°C",
  "data": [
    {
      "timestamp": "2026-05-15T14:55:00Z",
      "value": 25.3,
      "quality": "good"
    },
    {
      "timestamp": "2026-05-15T14:50:00Z",
      "value": 25.1,
      "quality": "good"
    }
  ],
  "stats": {
    "min": 22.5,
    "max": 28.7,
    "avg": 25.2,
    "count": 288
  }
}
```

---

### 3.5 添加传感器数据点

```
POST /sensors/{sensor_id}/data
```

**请求体**:

```json
{
  "value": 25.3,
  "timestamp": "2026-05-15T14:55:00Z",
  "quality": "good | uncertain | bad"
}
```

**成功响应** (200):

```json
{
  "success": true,
  "data_point_id": 12345
}
```

---

## 4. 视觉检测 (Vision)

**基础路径**: `/api/v1/vision`

### 4.1 目标检测

```
POST /vision/detect
```

**请求体**:

```json
{
  "image_url": "string",
  "image_data": "string (base64)",
  "confidence_threshold": 0.5
}
```

> `image_url` 和 `image_data` 二选一

**成功响应** (200):

```json
{
  "detections": [
    {
      "class": "person",
      "confidence": 0.92,
      "bbox": [120, 80, 340, 520],
      "label": "人员"
    },
    {
      "class": "helmet",
      "confidence": 0.88,
      "bbox": [180, 60, 280, 140],
      "label": "安全帽"
    }
  ],
  "image_url": "",
  "processing_time_ms": 125.3,
  "model_version": "yolov8n-1.0"
}
```

**错误响应** (503):

```json
{
  "detail": "AI Vision 服务不可用: Connection refused"
}
```

---

### 4.2 文件上传检测

```
POST /vision/detect/file
```

**表单参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 图片文件（JPEG/PNG）|
| confidence_threshold | float | 否 | 置信度阈值，默认 0.5 |

**成功响应** (200): 同上

---

### 4.3 健康检查

```
GET /vision/health
```

**成功响应** (200):

```json
{
  "status": "healthy",
  "model": "yolov8n",
  "gpu_available": true
}
```

---

## 5. 电子沙盘 (Sandbox)

**基础路径**: `/api/v1/sandbox`

### 5.1 获取沙盘模型列表

```
GET /sandbox/models
```

**成功响应** (200):

```json
[
  {
    "id": 1,
    "name": "大坝主体三维模型",
    "model_url": "/static/models/dam.glb",
    "location": "大坝主体",
    "type": "dam",
    "created_at": "2026-05-01T08:00:00Z"
  }
]
```

---

### 5.2 获取视频片段列表

```
GET /sandbox/videos
```

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| camera_id | string | 否 | 摄像头 ID |
| limit | int | 否 | 返回数量，默认 50 |

---

### 5.3 获取摄像头列表

```
GET /sandbox/cameras
```

**成功响应** (200):

```json
[
  {
    "camera_id": "cam_001",
    "location": "大坝主体-东侧"
  },
  {
    "camera_id": "cam_002",
    "location": "导流洞入口"
  }
]
```

---

### 5.4 获取沙盘统计

```
GET /sandbox/stats
```

**成功响应** (200):

```json
{
  "total_models": 12,
  "total_videos": 345,
  "total_cameras": 8
}
```

---

## 6. 专家系统 (Expert)

**基础路径**: `/api/v1/expert`

### 6.1 知识问答

```
POST /expert/query
```

**请求体**:

```json
{
  "question": "大坝渗漏的应急处置流程是什么？",
  "context": {}
}
```

**成功响应** (200):

```json
{
  "answer": "根据《水利工程施工安全应急处置规范》，大坝渗漏应急处置流程如下：\n\n1. **立即上报**：发现渗漏后 5 分钟内向项目部报告\n2. **启动预案**：项目部在 10 分钟内启动应急响应\n3. **人员撤离**：按预定路线撤离危险区域\n4. **现场警戒**：设置警示标志，禁止无关人员进入\n5. **专家会商**：联系上级主管部门和专家\n6. **处置实施**：采用堵漏、导流等应急措施",
  "sources": [
    {
      "title": "水利工程施工安全应急处置规范",
      "section": "第 4.2 条",
      "relevance": 0.95
    }
  ],
  "confidence": 0.92
}
```

---

### 6.2 生成安全检查表格

```
POST /expert/forms/generate
```

**请求体**:

```json
{
  "form_type": "inspection",
  "project_name": "某水库大坝工程",
  "date": "2026-05-15",
  "location": "大坝主体",
  "inspector": "张三",
  "data": {}
}
```

**`form_type` 可选值**: `inspection` | `check` | `rectification` | `acceptance`

**成功响应** (200):

```json
{
  "form_id": "a1b2c3d4",
  "form_type": "inspection",
  "title": "安全检查表 - 某水库大坝工程",
  "content": {
    "project": "某水库大坝工程",
    "date": "2026-05-15",
    "location": "大坝主体",
    "inspector": "张三",
    "items": [
      {"name": "临边防护", "status": "待检查", "remark": ""},
      {"name": "用电安全", "status": "待检查", "remark": ""},
      {"name": "消防安全", "status": "待检查", "remark": ""},
      {"name": "特种设备", "status": "待检查", "remark": ""},
      {"name": "高空作业", "status": "待检查", "remark": ""},
      {"name": "基坑支护", "status": "待检查", "remark": ""}
    ]
  },
  "generated_at": "2026-05-15T14:30:00Z"
}
```

---

### 6.3 知识库统计

```
GET /expert/knowledge/stats
```

**成功响应** (200):

```json
{
  "total_documents": 156,
  "safety_regulations": 42,
  "case_studies": 38,
  "technical_standards": 76,
  "last_updated": "2026-05-15T10:00:00Z"
}
```

---

## 7. 知识库 (Knowledge)

**基础路径**: `/api/v1/knowledge`

### 7.1 添加文档

```
POST /knowledge/add
```

**请求体**:

```json
{
  "content": "文档内容...",
  "title": "文档标题",
  "source": "规范 | 案例 | 法规 | 其他",
  "category": "安全帽 | 水位 | 边坡 | 消防"
}
```

**成功响应** (200):

```json
{
  "success": true,
  "id": "chunk_abc123",
  "chunks_count": 15,
  "message": "成功添加 15 个知识块"
}
```

---

### 7.2 RAG 问答

```
POST /knowledge/query
```

**请求体**:

```json
{
  "question": "string",
  "top_k": 5,
  "category": "string (可选)"
}
```

**成功响应** (200):

```json
{
  "answer": "根据相关规范和案例分析...",
  "sources": [
    {
      "content": "相关文档片段...",
      "title": "文档标题",
      "source": "来源",
      "score": 0.92
    }
  ],
  "generated_at": "2026-05-15T14:30:00Z"
}
```

---

### 7.3 生成安全检查表格

```
POST /knowledge/table
```

**请求体**:

```json
{
  "topic": "高空作业安全检查",
  "rows": 10
}
```

**成功响应** (200):

```json
{
  "table_data": {
    "headers": ["序号", "检查项目", "检查内容", "标准要求", "检查结果"],
    "rows": [
      ["1", "安全带", "是否正确佩戴", "高挂低用", "符合"],
      ["2", "脚手架", "是否验收合格", "有验收标识", "待查"]
    ]
  },
  "generated_at": "2026-05-15T14:30:00Z"
}
```

---

### 7.4 知识库统计

```
GET /knowledge/stats
```

**成功响应** (200):

```json
{
  "total_documents": 156,
  "total_chunks": 2340,
  "categories": {
    "安全帽": 42,
    "水位": 38,
    "边坡": 56,
    "消防": 20
  },
  "sources": {
    "规范": 42,
    "案例": 38,
    "法规": 76
  }
}
```

---

### 7.5 事故案例分析

```
POST /knowledge/case/analyze
```

**请求体**:

```json
{
  "case_description": "2026年4月，某工地发生一起高处坠落事故...",
  "background": "当日天气晴，风力3级..."
}
```

**成功响应** (200):

```json
{
  "analysis": {
    "cause_analysis": "直接原因：违规作业，未系安全带...",
    "similar_cases": "类似案例：某电站进水口坠落事故...",
    "prevention_measures": "1. 加强安全教育培训..."
  },
  "generated_at": "2026-05-15T14:30:00Z"
}
```

---

## 8. WebSocket 实时推送

**路径**: `/ws/alerts`

### 8.1 连接

```
ws://host:port/ws/alerts?alert_id={alert_id}
```

- 不传 `alert_id`：接收所有告警更新广播
- 传 `alert_id`：只接收指定告警的更新

### 8.2 接收消息类型

**告警更新**:

```json
{
  "type": "alert_update",
  "action": "created | updated",
  "data": {
    "id": 1,
    "title": "温度告警",
    "level": "critical",
    "status": "pending",
    "location": "大坝主体",
    "created_at": "2026-05-15T14:30:00Z"
  }
}
```

**心跳响应**:

```json
{"type": "heartbeat_ack", "timestamp": "..."}
```

### 8.3 发送消息

**心跳**:

```
ping
```

**订阅特定告警**:

```
subscribe:123
```

**取消订阅**:

```
unsubscribe:123
```

---

## 9. SSE 实时状态

**路径**: `/sse/status`

无需认证，用于实时大屏展示系统状态数据。

**推送数据**:

```json
{
  "active_alerts": 12,
  "total_sensors": 45,
  "timestamp": "2026-05-15T14:30:00Z"
}
```

每 5 秒推送一次。

---

## 10. 全局错误码

| HTTP 状态码 | 说明 |
|-------------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证或 Token 过期 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 503 | 下游服务不可用 |

---

*文档版本：v1.0.0 | 更新日期：2026-05-17*
