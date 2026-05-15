# 水利建设工地质量安全监管系统 - 数据库设计文档

## 1. ER 图（文字描述）

### 1.1 核心实体关系

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SITE (工地)                                     │
│  site_id(PK), name, code, province, city, address, geo_point,               │
│  area_sqm, start_date, end_date, status, created_at, updated_at             │
│                                    │                                        │
│          ┌─────────────────────────┼─────────────────────────┐              │
│          │                         │                         │              │
│          ▼                         ▼                         ▼              │
│  ┌─────────────┐          ┌─────────────┐         ┌─────────────────┐     │
│  │   CAMERA    │          │   SENSOR    │         │  UNIFIED_ALERT  │     │
│  │ camera_id   │          │ sensor_id   │         │ alert_id(PK)    │     │
│  │ site_id(FK) │          │ site_id(FK) │         │ site_id(FK)     │     │
│  │ name, url   │          │ type, unit  │         │ alert_type      │     │
│  │ location    │          │ thresholds  │         │ severity        │     │
│  │ status      │          │ status      │         │ source_id       │     │
│  └─────────────┘          └─────────────┘         └─────────────────┘     │
│          │                         │                         │              │
│          │                         ▼                         │              │
│          │                ┌─────────────────┐               │              │
│          │                │ SENSOR_DATA     │               │              │
│          │                │ (TimescaleDB)  │               │              │
│          │                │ time(PK)        │               │              │
│          │                │ sensor_id(FK)   │               │              │
│          │                │ value           │               │              │
│          │                │ is_anomaly      │               │              │
│          │                └─────────────────┘               │              │
│          │                                                  │              │
│          └────────────────────────────┬──────────────────────┘              │
│                                       ▼                                     │
│                          ┌────────────────────────┐                          │
│                          │       PROBLEM         │                          │
│                          │ problem_id(PK)        │                          │
│                          │ alert_id(FK,nullable) │                          │
│                          │ site_id(FK)           │                          │
│                          │ title, description     │                          │
│                          │ problem_type          │                          │
│                          │ severity, status      │                          │
│                          │ assignee_id(FK)       │                          │
│                          │ due_date              │                          │
│                          │ workflow_instance_id  │                          │
│                          └────────────────────────┘                          │
│                                    │                                         │
│        ┌───────────────────────────┼───────────────────────────┐            │
│        │                           ▼                           │            │
│        │               ┌────────────────────────┐              │            │
│        │               │   WORKFLOW_INSTANCE   │              │            │
│        │               │ instance_id(PK)       │              │            │
│        │               │ template_id(FK)       │              │            │
│        │               │ entity_type,entity_id │              │            │
│        │               │ status                │              │            │
│        │               └────────────────────────┘              │            │
│        │                         │                            │            │
│        │                         ▼                            │            │
│        │               ┌────────────────────────┐              │            │
│        │               │    WORKFLOW_TASK      │              │            │
│        │               │ task_id(PK)           │              │            │
│        │               │ instance_id(FK)       │              │            │
│        │               │ node_id               │              │            │
│        │               │ assignee_id(FK)       │              │            │
│        │               │ status, comment       │              │            │
│        │               └────────────────────────┘              │            │
│        │                                                               │
│        ▼                                                               │
│  ┌─────────────┐                                                       │
│  │ CAMERA_     │                                                       │
│  │ ASSIGN      │                                                       │
│  │camera_id(FK)│                                                       │
│  │user_id(FK)  │                                                       │
│  └─────────────┘                                                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER (用户)                                       │
│  user_id(PK), username, email, phone, role, status, created_at             │
│                               │                                            │
│          ┌───────────────────┼───────────────────┐                          │
│          │                   │                   │                          │
│          ▼                   ▼                   ▼                          │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                 │
│   │ SITE_USER   │     │ PROBLEM_    │     │ WORKFLOW_   │                 │
│   │site_id(FK) │     │ ASSIGNEE    │     │ TASK_ASSIGN │                 │
│   │user_id(FK) │     │problem_id(FK│     │task_id(FK)  │                 │
│   └─────────────┘     └─────────────┘     │user_id(FK)  │                 │
│                                           └─────────────┘                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                       KNOWLEDGE_BASE (知识库)                               │
│  doc_id(PK), title, category, content, file_url, chunk_count                 │
│  status, created_by(FK), created_at, updated_at                            │
│                               │                                             │
│                               ▼                                             │
│                    ┌─────────────────────────┐                              │
│                    │   KNOWLEDGE_CHUNK      │                              │
│                    │ chunk_id(PK)           │                              │
│                    │ doc_id(FK)             │                              │
│                    │ content                │                              │
│                    │ chunk_index            │                              │
│                    │ milvus_id ─────────────┼────→ Milvus Collection       │
│                    │ metadata               │                              │
│                    └─────────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 表分类总览

| 类别 | 表数量 | 描述 |
|------|--------|------|
| 核心业务表 | 8 | 工地、用户、摄像头、传感器、告警、问题等 |
| 工作流表 | 6 | 模板、实例、任务、节点、连线、历史 |
| 知识库表 | 4 | 文档、Chunk、分类、问答历史 |
| 审计表 | 3 | 操作日志、通知历史、系统配置变更 |
| 缓存表 | 2 | 会话token黑名单、限流计数 |
| **合计** | **23** | |

---

## 2. PostgreSQL 主库 DDL

### 2.1 公共扩展与枚举类型

```sql
-- 启用必要扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 模糊搜索支持

-- 创建自定义枚举类型
DO $$ BEGIN
    CREATE TYPE site_status AS ENUM ('planning', 'active', 'suspended', 'completed', 'archived');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE device_status AS ENUM ('online', 'offline', 'maintenance', 'error', 'decommissioned');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE alert_severity AS ENUM ('P0', 'P1', 'P2');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE alert_status AS ENUM ('pending', 'processing', 'processed', 'closed', 'false_positive');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE alert_type AS ENUM (
        'helmet_detection', 'person_fall_detection', 'vehicle_overload',
        'danger_zone_intrusion', 'fire_detection', 'crowd_aggregation',
        'sensor_threshold', 'sensor_anomaly', 'weather_warning',
        'equipment_failure', 'speech_command'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE problem_status AS ENUM ('pending', 'processing', 'completed', 'verified', 'closed', 'rejected');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE problem_type AS ENUM ('safety_hazard', 'quality_issue', 'environmental_violation', 'equipment_fault', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE sensor_type AS ENUM (
        'temperature', 'pressure', 'vibration', 'displacement',
        'flow', 'wind_speed', 'rainfall', 'humidity', 'water_level'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE workflow_status AS ENUM ('active', 'completed', 'cancelled', 'suspended');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE workflow_node_type AS ENUM ('start', 'end', 'task', 'approval', 'condition', 'parallel', 'notify');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE task_status AS ENUM ('pending', 'in_progress', 'completed', 'rejected', 'skipped');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('super_admin', 'admin', 'supervisor', 'engineer', 'worker', 'viewer');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;
```

### 2.2 用户与认证表

```sql
-- 用户表
CREATE TABLE users (
    user_id VARCHAR(64) PRIMARY KEY DEFAULT 'user_' || substr(uuid_generate_v4()::text, 1, 8),
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(20),
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    avatar_url VARCHAR(500),
    role user_role NOT NULL DEFAULT 'viewer',
    department VARCHAR(100),
    employee_id VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_login_at TIMESTAMP WITH TIME ZONE,
    password_changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_phone_format CHECK (phone IS NULL OR phone ~ '^\+?[0-9]{10,15}$'),
    CONSTRAINT chk_failed_attempts CHECK (failed_login_attempts >= 0)
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);

-- 刷新 updated_at 触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Token 黑名单表（用于登出后 Token 失效）
CREATE TABLE token_blacklist (
    id BIGSERIAL PRIMARY KEY,
    jti VARCHAR(64) NOT NULL UNIQUE,  -- JWT ID
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_type VARCHAR(20) NOT NULL DEFAULT 'access',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    blacklisted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_token_blacklist_jti ON token_blacklist(jti);
CREATE INDEX idx_token_blacklist_user ON token_blacklist(user_id);
CREATE INDEX idx_token_blacklist_expires ON token_blacklist(expires_at);

-- 角色权限表
CREATE TABLE role_permissions (
    role user_role NOT NULL,
    permission VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id_pattern VARCHAR(255),
    granted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    granted_by VARCHAR(64) REFERENCES users(user_id),
    PRIMARY KEY (role, permission, resource_type, resource_id_pattern)
);

-- 预定义权限数据
INSERT INTO role_permissions (role, permission, resource_type, resource_id_pattern) VALUES
('super_admin', '*', '*', NULL),
('admin', 'read', 'site', NULL),
('admin', 'write', 'site', NULL),
('admin', 'delete', 'site', NULL),
('admin', 'read', 'user', NULL),
('admin', 'write', 'user', NULL),
('admin', 'read', '*', NULL),
('admin', 'write', '*', NULL),
('admin', 'delete', 'workflow_template', NULL),
('supervisor', 'read', 'site', NULL),
('supervisor', 'read', 'camera', NULL),
('supervisor', 'read', 'sensor', NULL),
('supervisor', 'read', 'alert', NULL),
('supervisor', 'write', 'alert', NULL),
('supervisor', 'read', 'problem', NULL),
('supervisor', 'write', 'problem', NULL),
('supervisor', 'write', 'workflow_task', NULL),
('supervisor', 'read', 'report', NULL),
('engineer', 'read', 'site', NULL),
('engineer', 'read', 'camera', NULL),
('engineer', 'read', 'sensor', NULL),
('engineer', 'read', 'alert', NULL),
('engineer', 'write', 'alert', NULL),
('engineer', 'read', 'problem', NULL),
('engineer', 'write', 'problem', NULL),
('engineer', 'write', 'workflow_task', NULL),
('worker', 'read', 'site', NULL),
('worker', 'read', 'problem', NULL),
('worker', 'write', 'problem', NULL),
('viewer', 'read', 'site', NULL),
('viewer', 'read', 'alert', NULL),
('viewer', 'read', 'problem', NULL);
```

### 2.3 工地管理表

```sql
-- 工地表
CREATE TABLE sites (
    site_id VARCHAR(64) PRIMARY KEY DEFAULT 'site_' || substr(uuid_generate_v4()::text, 1, 8),
    name VARCHAR(200) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    location GEOGRAPHY(POINT, 4326),
    address VARCHAR(500),
    province VARCHAR(50),
    city VARCHAR(50),
    district VARCHAR(50),
    geofence GEOGRAPHY(POLYGON, 4326),
    area_sqm DECIMAL(12, 2),
    construction_type VARCHAR(100),
    importance_level VARCHAR(20),
    start_date DATE,
    end_date DATE,
    actual_start_date DATE,
    actual_end_date DATE,
    chief_engineer_id VARCHAR(64) REFERENCES users(user_id),
    safety_officer_id VARCHAR(64) REFERENCES users(user_id),
    max_worker_count INTEGER,
    status site_status NOT NULL DEFAULT 'planning',
    config JSONB DEFAULT '{}',
    created_by VARCHAR(64) REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_site_dates CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date),
    CONSTRAINT chk_site_area CHECK (area_sqm IS NULL OR area_sqm > 0)
);

CREATE INDEX idx_sites_code ON sites(code);
CREATE INDEX idx_sites_status ON sites(status);
CREATE INDEX idx_sites_location ON sites USING GIST(location);
CREATE INDEX idx_sites_geofence ON sites USING GIST(geofence);
CREATE INDEX idx_sites_province_city ON sites(province, city);
CREATE INDEX idx_sites_chief_engineer ON sites(chief_engineer_id);

CREATE TRIGGER trg_sites_updated_at
    BEFORE UPDATE ON sites
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 工地用户关联表
CREATE TABLE site_users (
    site_id VARCHAR(64) NOT NULL REFERENCES sites(site_id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role_in_site VARCHAR(50) NOT NULL DEFAULT 'member',
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    assigned_by VARCHAR(64) REFERENCES users(user_id),
    can_notify BOOLEAN NOT NULL DEFAULT true,
    PRIMARY KEY (site_id, user_id)
);

CREATE INDEX idx_site_users_user ON site_users(user_id);
CREATE INDEX idx_site_users_role ON site_users(role_in_site);
```

### 2.4 传感器管理表

```sql
-- 传感器表
CREATE TABLE sensors (
    sensor_id VARCHAR(64) PRIMARY KEY DEFAULT 'sensor_' || substr(uuid_generate_v4()::text, 1, 8),
    site_id VARCHAR(64) NOT NULL REFERENCES sites(site_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    type sensor_type NOT NULL,
    unit VARCHAR(20) NOT NULL,
    device_model VARCHAR(100),
    serial_number VARCHAR(100) UNIQUE,
    manufacturer VARCHAR(100),
    firmware_version VARCHAR(50),
    location GEOGRAPHY(POINT, 4326),
    altitude DECIMAL(8, 2),
    location_name VARCHAR(200),
    installed_height DECIMAL(6, 2),
    installed_date DATE,
    thresholds JSONB DEFAULT '{"warning_low": null, "warning_high": null, "critical_low": null, "critical_high": null}',
    sampling_interval_seconds INTEGER NOT NULL DEFAULT 60,
    reporting_interval_seconds INTEGER NOT NULL DEFAULT 300,
    status device_status NOT NULL DEFAULT 'offline',
    last_seen_at TIMESTAMP WITH TIME ZONE,
    last_value DECIMAL(20, 6),
    last_value_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_by VARCHAR(64) REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_sampling_interval CHECK (sampling_interval_seconds > 0),
    CONSTRAINT chk_reporting_interval CHECK (reporting_interval_seconds >= sampling_interval_seconds)
);

CREATE INDEX idx_sensors_site ON sensors(site_id);
CREATE INDEX idx_sensors_type ON sensors(type);
CREATE INDEX idx_sensors_status ON sensors(status);
CREATE INDEX idx_sensors_location ON sensors USING GIST(location);
CREATE INDEX idx_sensors_serial ON sensors(serial_number);

CREATE TRIGGER trg_sensors_updated_at
    BEFORE UPDATE ON sensors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 传感器通知规则表
CREATE TABLE sensor_notification_rules (
    rule_id VARCHAR(64) PRIMARY KEY DEFAULT 'sensor_rule_' || substr(uuid_generate_v4()::text, 1, 8),
    sensor_id VARCHAR(64) NOT NULL REFERENCES sensors(sensor_id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    alert_types TEXT[] NOT NULL,
    notify_channels TEXT[] NOT NULL DEFAULT ARRAY['app', 'sms'],
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (sensor_id, user_id)
);

CREATE INDEX idx_sensor_notification_rules_sensor ON sensor_notification_rules(sensor_id);
CREATE INDEX idx_sensor_notification_rules_user ON sensor_notification_rules(user_id);
```

### 2.5 摄像头管理表

```sql
-- 摄像头表
CREATE TABLE cameras (
    camera_id VARCHAR(64) PRIMARY KEY DEFAULT 'cam_' || substr(uuid_generate_v4()::text, 1, 8),
    site_id VARCHAR(64) NOT NULL REFERENCES sites(site_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    rtsp_url VARCHAR(500) NOT NULL,
    rtsp_username VARCHAR(100),
    rtsp_password VARCHAR(255),
    stream_protocol VARCHAR(20) NOT NULL DEFAULT 'rtsp',
    location GEOGRAPHY(POINT, 4326),
    altitude DECIMAL(8, 2),
    location_name VARCHAR(200),
    installation_height DECIMAL(6, 2),
    pan_angle DECIMAL(6, 2),
    tilt_angle DECIMAL(6, 2),
    device_model VARCHAR(100),
    manufacturer VARCHAR(100),
    ip_address INET,
    mac_address VARCHAR(17),
    ai_analysis_enabled BOOLEAN NOT NULL DEFAULT true,
    ai_config JSONB DEFAULT '{"fps": 5, "detection_interval_seconds": 1, "confidence_threshold": 0.7, "enabled_models": ["helmet", "person", "vehicle"]}',
    stream_config JSONB DEFAULT '{"resolution": "1280x720", "fps": 5, "bitrate_kbps": 2000, "keyframe_interval": 2}',
    status device_status NOT NULL DEFAULT 'offline',
    last_seen_at TIMESTAMP WITH TIME ZONE,
    health_status VARCHAR(50),
    alert_config JSONB DEFAULT '{"helmet_detection": {"enabled": true, "severity": "P1"}, "person_fall_detection": {"enabled": true, "severity": "P0"}, "danger_zone_intrusion": {"enabled": true, "severity": "P0"}}',
    metadata JSONB DEFAULT '{}',
    created_by VARCHAR(64) REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cameras_site ON cameras(site_id);
CREATE INDEX idx_cameras_status ON cameras(status);
CREATE INDEX idx_cameras_location ON cameras USING GIST(location);
CREATE INDEX idx_cameras_ip ON cameras(ip_address);

CREATE TRIGGER trg_cameras_updated_at
    BEFORE UPDATE ON cameras
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 摄像头用户权限表
CREATE TABLE camera_users (
    camera_id VARCHAR(64) NOT NULL REFERENCES cameras(camera_id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    can_view BOOLEAN NOT NULL DEFAULT true,
    can_ptz BOOLEAN NOT NULL DEFAULT false,
    can_config BOOLEAN NOT NULL DEFAULT false,
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (camera_id, user_id)
);

CREATE INDEX idx_camera_users_user ON camera_users(user_id);
```

### 2.6 统一告警表

```sql
-- 统一告警表
CREATE TABLE unified_alerts (
    alert_id VARCHAR(64) PRIMARY KEY DEFAULT 'alert_' || substr(uuid_generate_v4()::text, 1, 8),
    site_id VARCHAR(64) NOT NULL REFERENCES sites(site_id) ON DELETE CASCADE,
    alert_type alert_type NOT NULL,
    severity alert_severity NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    source_type VARCHAR(20) NOT NULL,
    source_id VARCHAR(64) NOT NULL,
    source_name VARCHAR(200),
    source_location JSONB,
    evidence JSONB DEFAULT '{}',
    detections JSONB DEFAULT '[]',
    status alert_status NOT NULL DEFAULT 'pending',
    handled_by VARCHAR(64) REFERENCES users(user_id),
    handled_at TIMESTAMP WITH TIME ZONE,
    handle_comment TEXT,
    problem_id VARCHAR(64),
    workflow_instance_id VARCHAR(64),
    notification_sent BOOLEAN NOT NULL DEFAULT false,
    notification_channels TEXT[],
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    dedup_hash VARCHAR(64),
    dedup_expires_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    CONSTRAINT chk_alert_source CHECK (source_type IN ('camera', 'sensor', 'uav', 'manual', 'system'))
);

CREATE INDEX idx_alerts_site ON unified_alerts(site_id);
CREATE INDEX idx_alerts_type ON unified_alerts(alert_type);
CREATE INDEX idx_alerts_severity ON unified_alerts(severity);
CREATE INDEX idx_alerts_status ON unified_alerts(status);
CREATE INDEX idx_alerts_occurred_at ON unified_alerts(occurred_at);
CREATE INDEX idx_alerts_created_at ON unified_alerts(created_at DESC);
CREATE INDEX idx_alerts_source ON unified_alerts(source_type, source_id);
CREATE INDEX idx_alerts_problem ON unified_alerts(problem_id) WHERE problem_id IS NOT NULL;
CREATE INDEX idx_alerts_dedup ON unified_alerts(dedup_hash, dedup_expires_at) WHERE dedup_hash IS NOT NULL AND dedup_expires_at > NOW();
CREATE INDEX idx_alerts_unprocessed ON unified_alerts(created_at DESC) WHERE status IN ('pending', 'processing');

-- 告警处理历史
CREATE TABLE alert_history (
    history_id BIGSERIAL PRIMARY KEY,
    alert_id VARCHAR(64) NOT NULL REFERENCES unified_alerts(alert_id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    actor_id VARCHAR(64) REFERENCES users(user_id),
    actor_type VARCHAR(20) DEFAULT 'user',
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alert_history_alert ON alert_history(alert_id);
CREATE INDEX idx_alert_history_created ON alert_history(created_at DESC);

-- 告警聚合规则表
CREATE TABLE alert_aggregation_rules (
    rule_id VARCHAR(64) PRIMARY KEY DEFAULT 'agg_rule_' || substr(uuid_generate_v4()::text, 1, 8),
    name VARCHAR(100) NOT NULL,
    alert_type alert_type NOT NULL,
    site_id VARCHAR(64) REFERENCES sites(site_id),
    match_fields TEXT[] NOT NULL,
    time_window_seconds INTEGER NOT NULL DEFAULT 300,
    merge_to_first BOOLEAN NOT NULL DEFAULT true,
    notify_once BOOLEAN NOT NULL DEFAULT true,
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    priority INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alert_aggregation_rules_type ON alert_aggregation_rules(alert_type);
CREATE INDEX idx_alert_aggregation_rules_site ON alert_aggregation_rules(site_id) WHERE site_id IS NOT NULL;
```

### 2.7 问题管理表

```sql
-- 问题表
CREATE TABLE problems (
    problem_id VARCHAR(64) PRIMARY KEY DEFAULT 'prob_' || substr(uuid_generate_v4()::text, 1, 8),
    site_id VARCHAR(64) NOT NULL REFERENCES sites(site_id) ON DELETE CASCADE,
    title VARCHAR(300) NOT NULL,
    description TEXT,
    problem_type problem_type NOT NULL,
    severity alert_severity NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    source_id VARCHAR(64),
    alert_id VARCHAR(64) REFERENCES unified_alerts(alert_id),
    location GEOGRAPHY(POINT, 4326),
    location_name VARCHAR(200),
    status problem_status NOT NULL DEFAULT 'pending',
    assignee_id VARCHAR(64) REFERENCES users(user_id),
    due_date DATE,
    workflow_instance_id VARCHAR(64),
    workflow_template_id VARCHAR(64),
    tags TEXT[],
    category VARCHAR(100),
    attachments JSONB DEFAULT '[]',
    closed_by VARCHAR(64) REFERENCES users(user_id),
    closed_at TIMESTAMP WITH TIME ZONE,
    closure_reason VARCHAR(50),
    closure_comment TEXT,
    verified_by VARCHAR(64) REFERENCES users(user_id),
    verified_at TIMESTAMP WITH TIME ZONE,
    verification_result VARCHAR(50),
    verification_comment TEXT,
    processing_time_seconds INTEGER,
    metadata JSONB DEFAULT '{}',
    created_by VARCHAR(64) REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_problem_due_date CHECK (due_date IS NULL OR due_date >= CURRENT_DATE),
    CONSTRAINT chk_problem_processing_time CHECK (processing_time_seconds IS NULL OR processing_time_seconds >= 0)
);

CREATE INDEX idx_problems_site ON problems(site_id);
CREATE INDEX idx_problems_status ON problems(status);
CREATE INDEX idx_problems_type ON problems(problem_type);
CREATE INDEX idx_problems_severity ON problems(severity);
CREATE INDEX idx_problems_assignee ON problems(assignee_id);
CREATE INDEX idx_problems_due_date ON problems(due_date) WHERE due_date IS NOT NULL AND status NOT IN ('closed', 'verified');
CREATE INDEX idx_problems_created_at ON problems(created_at DESC);
CREATE INDEX idx_problems_alert ON problems(alert_id) WHERE alert_id IS NOT NULL;
CREATE INDEX idx_problems_workflow ON problems(workflow_instance_id) WHERE workflow_instance_id IS NOT NULL;
CREATE INDEX idx_problems_tags ON problems USING GIN(tags);

CREATE TRIGGER trg_problems_updated_at
    BEFORE UPDATE ON problems
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 问题处理历史
CREATE TABLE problem_history (
    history_id BIGSERIAL PRIMARY KEY,
    problem_id VARCHAR(64) NOT NULL REFERENCES problems(problem_id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    actor_id VARCHAR(64) REFERENCES users(user_id),
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_problem_history_problem ON problem_history(problem_id);
CREATE INDEX idx_problem_history_created ON problem_history(created_at DESC);

-- 问题转发记录
CREATE TABLE problem_transfers (
    transfer_id BIGSERIAL PRIMARY KEY,
    problem_id VARCHAR(64) NOT NULL REFERENCES problems(problem_id) ON DELETE CASCADE,
    from_user_id VARCHAR(64) REFERENCES users(user_id),
    to_user_id VARCHAR(64) NOT NULL REFERENCES users(user_id),
    reason VARCHAR(100),
    comment TEXT,
    created_by VARCHAR(64) REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_problem_transfers_problem ON problem_transfers(problem_id);
CREATE INDEX idx_problem_transfers_to_user ON problem_transfers(to_user_id);
```

### 2.8 工作流引擎表

```sql
-- 工作流模板表
CREATE TABLE workflow_templates (
    template_id VARCHAR(64) PRIMARY KEY DEFAULT 'tmpl_' || substr(uuid_generate_v4()::text, 1, 8),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    applicable_entity_type VARCHAR(50) NOT NULL,
    applicable_problem_types problem_type[],
    applicable_sites VARCHAR(64)[],
    nodes JSONB NOT NULL,
    edges JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_system BOOLEAN NOT NULL DEFAULT false,
    priority INTEGER NOT NULL DEFAULT 0,
    previous_version_id VARCHAR(64),
    created_by VARCHAR(64) REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (name, version)
);

CREATE INDEX idx_workflow_templates_entity ON workflow_templates(applicable_entity_type);
CREATE INDEX idx_workflow_templates_active ON workflow_templates(is_active) WHERE is_active = true;

-- 工作流实例表
CREATE TABLE workflow_instances (
    instance_id VARCHAR(64) PRIMARY KEY DEFAULT 'wfi_' || substr(uuid_generate_v4()::text, 1, 8),
    template_id VARCHAR(64) NOT NULL REFERENCES workflow_templates(template_id),
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    status workflow_status NOT NULL DEFAULT 'active',
    current_node_id VARCHAR(64),
    variables JSONB DEFAULT '{}',
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    cancelled_by VARCHAR(64) REFERENCES users(user_id),
    cancellation_reason VARCHAR(200),
    created_by VARCHAR(64) REFERENCES users(user_id),
    UNIQUE (entity_type, entity_id)
);

CREATE INDEX idx_workflow_instances_template ON workflow_instances(template_id);
CREATE INDEX idx_workflow_instances_entity ON workflow_instances(entity_type, entity_id);
CREATE INDEX idx_workflow_instances_status ON workflow_instances(status);
CREATE INDEX idx_workflow_instances_current ON workflow_instances(current_node_id);

-- 工作流任务表
CREATE TABLE workflow_tasks (
    task_id VARCHAR(64) PRIMARY KEY DEFAULT 'wft_' || substr(uuid_generate_v4()::text, 1, 8),
    instance_id VARCHAR(64) NOT NULL REFERENCES workflow_instances(instance_id) ON DELETE CASCADE,
    node_id VARCHAR(64) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    task_type VARCHAR(50) NOT NULL,
    assignee_id VARCHAR(64) REFERENCES users(user_id),
    assignee_type VARCHAR(20),
    assignee_expr VARCHAR(200),
    status task_status NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    due_date TIMESTAMP WITH TIME ZONE,
    comment TEXT,
    action VARCHAR(50),
    parent_task_id VARCHAR(64),
    history_id BIGINT REFERENCES alert_history(history_id),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_workflow_tasks_instance ON workflow_tasks(instance_id);
CREATE INDEX idx_workflow_tasks_assignee ON workflow_tasks(assignee_id);
CREATE INDEX idx_workflow_tasks_status ON workflow_tasks(status);
CREATE INDEX idx_workflow_tasks_due ON workflow_tasks(due_date) WHERE status = 'pending' AND due_date IS NOT NULL;
CREATE INDEX idx_workflow_tasks_pending_assignee ON workflow_tasks(assignee_id, status) WHERE status IN ('pending', 'in_progress');

-- 工作流任务历史
CREATE TABLE workflow_task_history (
    history_id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL REFERENCES workflow_tasks(task_id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    old_status task_status,
    new_status task_status,
    actor_id VARCHAR(64) REFERENCES users(user_id),
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_workflow_task_history_task ON workflow_task_history(task_id);
CREATE INDEX idx_workflow_task_history_created ON workflow_task_history(created_at DESC);

-- 工作流变量历史
CREATE TABLE workflow_variable_history (
    history_id BIGSERIAL PRIMARY KEY,
    instance_id VARCHAR(64) NOT NULL REFERENCES workflow_instances(instance_id) ON DELETE CASCADE,
    variable_name VARCHAR(100) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    changed_by VARCHAR(64) REFERENCES users(user_id),
    changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_workflow_variable_history_instance ON workflow_variable_history(instance_id);
```

### 2.9 知识库表

```sql
-- 知识库文档表
CREATE TABLE knowledge_documents (
    doc_id VARCHAR(64) PRIMARY KEY DEFAULT 'doc_' || substr(uuid_generate_v4()::text, 1, 8),
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    content TEXT,
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    tags TEXT[],
    source_type VARCHAR(50),
    source_url VARCHAR(500),
    source_reference VARCHAR(200),
    file_url VARCHAR(500),
    file_name VARCHAR(200),
    file_size_bytes BIGINT,
    file_hash VARCHAR(64),
    chunk_count INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    is_public BOOLEAN NOT NULL DEFAULT true,
    created_by VARCHAR(64) REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_knowledge_docs_category ON knowledge_documents(category);
CREATE INDEX idx_knowledge_docs_tags ON knowledge_documents USING GIN(tags);
CREATE INDEX idx_knowledge_docs_status ON knowledge_documents(status) WHERE status = 'active';
CREATE INDEX idx_knowledge_docs_created ON knowledge_documents(created_at DESC);
CREATE INDEX idx_knowledge_docs_title_trgm ON knowledge_documents USING GIN(title gin_trgm_ops);

CREATE TRIGGER trg_knowledge_docs_updated_at
    BEFORE UPDATE ON knowledge_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 知识库文档 Chunk 表
CREATE TABLE knowledge_chunks (
    chunk_id VARCHAR(64) PRIMARY KEY DEFAULT 'chunk_' || substr(uuid_generate_v4()::text, 1, 8),
    doc_id VARCHAR(64) NOT NULL REFERENCES knowledge_documents(doc_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    char_start INTEGER,
    char_end INTEGER,
    milvus_id VARCHAR(64),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_knowledge_chunks_doc ON knowledge_chunks(doc_id);
CREATE INDEX idx_knowledge_chunks_index ON knowledge_chunks(doc_id, chunk_index);
CREATE INDEX idx_knowledge_chunks_milvus ON knowledge_chunks(milvus_id) WHERE milvus_id IS NOT NULL;

-- 问答历史表
CREATE TABLE expert_query_history (
    query_id VARCHAR(64) PRIMARY KEY DEFAULT 'eq_' || substr(uuid_generate_v4()::text, 1, 8),
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id),
    site_id VARCHAR(64) REFERENCES sites(site_id),
    question TEXT NOT NULL,
    question_embedding_id VARCHAR(64),
    answer TEXT,
    answer_id VARCHAR(64),
    confidence DECIMAL(5, 4),
    source_chunks JSONB DEFAULT '[]',
    user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 5),
    user_feedback TEXT,
    is_useful BOOLEAN,
    tokens_used INTEGER,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_expert_query_user ON expert_query_history(user_id);
CREATE INDEX idx_expert_query_site ON expert_query_history(site_id);
CREATE INDEX idx_expert_query_created ON expert_query_history(created_at DESC);
CREATE INDEX idx_expert_query_answer ON expert_query_history(answer_id) WHERE answer_id IS NOT NULL;

-- 知识库分类表
CREATE TABLE knowledge_categories (
    category_id VARCHAR(64) PRIMARY KEY DEFAULT 'kc_' || substr(uuid_generate_v4()::text, 1, 8),
    name VARCHAR(100) NOT NULL,
    parent_id VARCHAR(64) REFERENCES knowledge_categories(category_id),
    description TEXT,
    icon VARCHAR(50),
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (name, parent_id)
);

CREATE INDEX idx_knowledge_categories_parent ON knowledge_categories(parent_id);
```

### 2.10 系统配置与日志表

```sql
-- 系统配置表
CREATE TABLE system_config (
    config_key VARCHAR(100) PRIMARY KEY,
    config_value JSONB NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL DEFAULT 'general',
    is_sensitive BOOLEAN NOT NULL DEFAULT false,
    is_readonly BOOLEAN NOT NULL DEFAULT false,
    version INTEGER NOT NULL DEFAULT 1,
    updated_by VARCHAR(64) REFERENCES users(user_id),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_system_config_category ON system_config(category);

-- 预置配置
INSERT INTO system_config (config_key, config_value, description, category) VALUES
('alert.dedup.window_seconds', '{"value": 300}', '告警去重时间窗口（秒）', 'alert'),
('alert.notification.batch_size', '{"value": 10}', '通知批次大小', 'alert'),
('sensor.anomaly.threshold', '{"value": 3}', '传感器异常检测标准差倍数', 'sensor'),
('workflow.task_reminder_hours', '{"value": [8, 24]}', '任务提醒时间点', 'workflow'),
('report.retention_days', '{"value": 90}', '报表保留天数', 'report'),
('expert.max_sources', '{"value": 5}', '专家系统最大引用来源数', 'expert');

-- 操作日志表
CREATE TABLE operation_logs (
    log_id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(64) REFERENCES users(user_id),
    username VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(64),
    description TEXT,
    old_value JSONB,
    new_value JSONB,
    request_id VARCHAR(64),
    request_method VARCHAR(10),
    request_path VARCHAR(500),
    duration_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_operation_logs_user ON operation_logs(user_id);
CREATE INDEX idx_operation_logs_resource ON operation_logs(resource_type, resource_id);
CREATE INDEX idx_operation_logs_action ON operation_logs(action);
CREATE INDEX idx_operation_logs_created ON operation_logs(created_at DESC);

-- 通知发送记录表
CREATE TABLE notification_records (
    record_id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id),
    channel VARCHAR(20) NOT NULL,
    title VARCHAR(200),
    content TEXT NOT NULL,
    alert_id VARCHAR(64) REFERENCES unified_alerts(alert_id),
    problem_id VARCHAR(64) REFERENCES problems(problem_id),
    workflow_task_id VARCHAR(64) REFERENCES workflow_tasks(task_id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    provider_response JSONB,
    error_message TEXT,
    cost DECIMAL(10, 4),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_notification_records_user ON notification_records(user_id);
CREATE INDEX idx_notification_records_channel ON notification_records(channel);
CREATE INDEX idx_notification_records_created ON notification_records(created_at DESC);
```

---

## 3. TimescaleDB 时序表

### 3.1 传感器数据 Hypertable

```sql
-- 传感器原始数据表（转换为 Hypertable）
CREATE TABLE sensor_data (
    time TIMESTAMPTZ NOT NULL,
    sensor_id VARCHAR(64) NOT NULL,
    site_id VARCHAR(64) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    quality VARCHAR(20) NOT NULL DEFAULT 'good',
    quality_code SMALLINT DEFAULT 0,
    is_anomaly BOOLEAN NOT NULL DEFAULT false,
    anomaly_score DOUBLE PRECISION,
    raw_data JSONB,
    metadata JSONB DEFAULT '{}'
);

-- 将表转换为 Hypertable
SELECT create_hypertable('sensor_data', 
    'time', 
    chunk_time_interval => INTERVAL '1 day',
    migrate_data => TRUE,
    if_not_exists => TRUE
);

-- 压缩策略（超过7天的数据压缩）
ALTER TABLE sensor_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'sensor_id'
);

SELECT add_compression_policy('sensor_data', INTERVAL '7 days', if_not_exists => TRUE);

-- 数据保留策略（保留90天）
SELECT add_retention_policy('sensor_data', INTERVAL '90 days', if_not_exists => TRUE);

-- 索引
CREATE INDEX idx_sensor_data_sensor_time ON sensor_data(sensor_id, time DESC);
CREATE INDEX idx_sensor_data_site_time ON sensor_data(site_id, time DESC);
CREATE INDEX idx_sensor_data_anomaly ON sensor_data(time) WHERE is_anomaly = true;

-- 连续聚合：每5分钟统计
CREATE MATERIALIZED VIEW sensor_data_5m
WITH (timescaledb.continuous) AS
SELECT 
    sensor_id,
    site_id,
    time_bucket('5 minutes', time) AS bucket,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    COUNT(*) AS sample_count,
    COUNT(*) FILTER (WHERE is_anomaly) AS anomaly_count
FROM sensor_data
GROUP BY sensor_id, site_id, time_bucket('5 minutes', time)
WITH NO DATA;

SELECT add_continuous_aggregate_policy('sensor_data_5m',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- 连续聚合：每小时统计
CREATE MATERIALIZED VIEW sensor_data_1h
WITH (timescaledb.continuous) AS
SELECT 
    sensor_id,
    site_id,
    time_bucket('1 hour', time) AS bucket,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    STDDEV(value) AS stddev_value,
    COUNT(*) AS sample_count,
    COUNT(*) FILTER (WHERE is_anomaly) AS anomaly_count
FROM sensor_data
GROUP BY sensor_id, site_id, time_bucket('1 hour', time)
WITH NO DATA;

SELECT add_continuous_aggregate_policy('sensor_data_1h',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- 连续聚合：每日统计
CREATE MATERIALIZED VIEW sensor_data_1d
WITH (timescaledb.continuous) AS
SELECT 
    sensor_id,
    site_id,
    time_bucket('1 day', time) AS bucket,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    STDDEV(value) AS stddev_value,
    COUNT(*) AS sample_count,
    COUNT(*) FILTER (WHERE is_anomaly) AS anomaly_count
FROM sensor_data
GROUP BY sensor_id, site_id, time_bucket('1 day', time)
WITH NO DATA;

SELECT add_continuous_aggregate_policy('sensor_data_1d',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);
```

### 3.2 告警统计时序表

```sql
-- 告警统计时序表
CREATE TABLE alert_stats (
    time TIMESTAMPTZ NOT NULL,
    site_id VARCHAR(64) NOT NULL,
    alert_type alert_type NOT NULL,
    severity alert_severity NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    pending_count INTEGER NOT NULL DEFAULT 0,
    processed_count INTEGER NOT NULL DEFAULT 0,
    avg_processing_time_seconds DOUBLE PRECISION,
    p50_processing_time DOUBLE PRECISION,
    p90_processing_time DOUBLE PRECISION,
    p99_processing_time DOUBLE PRECISION,
    metadata JSONB DEFAULT '{}'
);

SELECT create_hypertable('alert_stats', 
    'time', 
    chunk_time_interval => INTERVAL '1 hour',
    migrate_data => TRUE,
    if_not_exists => TRUE
);

ALTER TABLE alert_stats SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'site_id'
);

SELECT add_compression_policy('alert_stats', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('alert_stats', INTERVAL '365 days', if_not_exists => TRUE);

CREATE INDEX idx_alert_stats_site_type_time ON alert_stats(site_id, alert_type, time DESC);
CREATE INDEX idx_alert_stats_severity ON alert_stats(severity, time DESC);
```

### 3.3 传感器状态变更表

```sql
-- 传感器状态变更表
CREATE TABLE sensor_status_log (
    time TIMESTAMPTZ NOT NULL,
    sensor_id VARCHAR(64) NOT NULL,
    site_id VARCHAR(64) NOT NULL,
    old_status device_status,
    new_status device_status NOT NULL,
    reason VARCHAR(100),
    duration_seconds INTEGER,
    metadata JSONB DEFAULT '{}'
);

SELECT create_hypertable('sensor_status_log', 
    'time', 
    chunk_time_interval => INTERVAL '1 day',
    migrate_data => TRUE,
    if_not_exists => TRUE
);

SELECT add_retention_policy('sensor_status_log', INTERVAL '180 days', if_not_exists => TRUE);

CREATE INDEX idx_sensor_status_log_sensor ON sensor_status_log(sensor_id, time DESC);
CREATE INDEX idx_sensor_status_log_new_status ON sensor_status_log(new_status, time DESC) WHERE new_status = 'offline';
```

---

## 4. Redis 数据结构设计

### 4.1 DB 分配

| DB | 用途 |
|----|------|
| DB 0 | 默认：缓存、锁、会话 |
| DB 1 | Video Analyzer：视频帧缓存、追踪状态 |
| DB 2 | 消息队列：告警队列、通知队列 |
| DB 3 | Stream：WebSocket 广播、实时数据 |
| DB 4 | Rate Limiter：限流计数 |
| DB 5 | MLLM 会话管理 |

### 4.2 缓存类数据结构

```python
# ============ 会话 & Token ============

# 用户会话数据 (Hash)
# Key: session:{user_id}
# TTL: 24 hours
session:{user_id} = {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "login_at": "2026-05-14T10:00:00Z",
    "last_active": "2026-05-14T10:30:00Z",
    "device_info": '{"browser": "Chrome", "os": "Windows"}',
    "permissions": '["site:read", "alert:write"]'
}

# Token 黑名单 (Set)
# Key: token_blacklist
token_blacklist = {"token_jti_1", "token_jti_2"}

# ============ 传感器实时数据 ============

# 最新传感器数据 (Hash, 30秒TTL)
# Key: sensor:latest:{sensor_id}
sensor:latest:{sensor_id} = {
    "value": "25.6",
    "timestamp": "2026-05-14T10:30:00Z",
    "quality": "good",
    "is_anomaly": "false"
}

# 传感器在线状态 (Hash)
# Key: sensor:online
sensor:online = {
    "sensor_tmp_001": "online",
    "last_heartbeat:sensor_tmp_001": "2026-05-14T10:30:00Z"
}

# 传感器告警状态 (ZSet)
# Key: sensor:anomalies
# Score: timestamp
sensor:anomalies = {
    "sensor_tmp_001:1715686800000": 1715686800000
}

# ============ 告警缓存 ============

# 未处理告警计数 (Hash)
# Key: alerts:pending:count
alerts:pending:count = {
    "total": "156",
    "P0": "3",
    "P1": "45",
    "P2": "108"
}

# 告警详情缓存 (String, JSON, 1小时TTL)
# Key: alert:{alert_id}
alert:{alert_id} = '{"alert_id": "...", "title": "..."}'

# 告警去重检查 (String, NX EX)
# Key: alert:dedup:{hash}
# TTL: 300秒（5分钟）
alert:dedup:{hash} = "alert_abc123"  # NX EX 300

# ============ 摄像头状态 ============

# 摄像头状态 (Hash)
# Key: camera:status
camera:status = {
    "cam_001": "online",
    "last_frame:cam_001": "2026-05-14T10:30:00Z",
    "health:cam_001": "healthy"
}

# 摄像头AI分析状态 (Hash)
# Key: camera:ai:{camera_id}
camera:ai:{camera_id} = {
    "last_detection": "2026-05-14T10:30:00Z",
    "fps_actual": "4.8",
    "queue_size": "12"
}

# ============ 用户通知偏好 ============

# 用户通知配置 (Hash)
# Key: user:notify:{user_id}
user:notify:{user_id} = {
    "channel:alert": "true",
    "channel:sms": "true",
    "severity:P0": "true",
    "severity:P1": "true",
    "mute_until": ""
}

# ============ 限流 ============

# API 限流 (String)
# Key: ratelimit:{endpoint}:{user_id}:{window}
ratelimit:api:/api/v1/alerts:user_001:2026051410 = "45"
```

### 4.3 消息队列类数据结构

```python
# ============ Redis Stream 消息队列 ============

# 告警通知队列 (Stream)
# Key: stream:alerts:notify
# Consumer Group: alert_workers

# 创建消费者组
XGROUP CREATE stream:alerts:notify alert_workers $ MKSTREAM

# 发送告警通知任务
XADD stream:alerts:notify "*" \
    alert_id "alert_abc123" \
    severity "P1" \
    recipients '[{"user_id": "user_001", "channels": ["app", "sms"]}]' \
    channels '["app", "sms"]' \
    retry_count "0" \
    created_at "2026-05-14T10:30:00Z"

# 消费者读取
XREADGROUP GROUP alert_workers consumer_1 BLOCK 5000 COUNT 1 STREAMS stream:alerts:notify ">"

# 确认消息
XACK stream:alerts:notify alert_workers {message_id}

# 死信队列
XADD stream:alerts:notify:dlq "*" \
    original_message_id "1234567890-0" \
    error "短信API调用失败" \
    failed_at "2026-05-14T10:35:00Z"

# ============ Pub/Sub 实时推送 ============

# 频道命名规范
# alert:{site_id}:new       - 新告警
# alert:{site_id}:update    - 告警更新
# problem:{site_id}:update  - 问题状态变更
# sensor:{site_id}:anomaly  - 传感器异常
# camera:{site_id}:status   - 摄像头状态变更

# 发布
PUBLISH alert:site_abc123:new '{"alert_id": "alert_abc123", "type": "helmet_detection"}'

# 传感器实时数据
PUBLISH sensor:realtime:sensor_tmp_001 '{"value": 25.6, "timestamp": "2026-05-14T10:30:00Z"}'
```

---

## 5. Milvus 向量库设计

### 5.1 Collection: knowledge_embeddings

```python
from pymilvus import Collection, FieldSchema, CollectionSchema, DataType, connections

# 连接 Milvus
connections.connect(
    alias="default",
    host="milvus",
    port="19530"
)

# 定义 Collection Schema
fields = [
    FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
    FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=64),
    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),  # text-embedding-3-small
    FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
    FieldSchema(name="tags", dtype=DataType.ARRAY, element_type=DataType.VARCHAR, max_length=50, max_capacity=10),
    FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=32)
]

schema = CollectionSchema(
    fields=fields,
    description="水利工地安全监管知识库向量集合",
    enable_dynamic_field=True
)

# 创建 Collection
collection = Collection(name="knowledge_embeddings", schema=schema)

# 创建索引
index_params = {
    "index_type": "IVF_FLAT",
    "metric_type": "COSINE",
    "params": {"nlist": 1024}
}

collection.create_index(
    field_name="embedding",
    index_params=index_params
)

# 分区设计
collection.create_partition(partition_name="regulations")      # 法规标准
collection.create_partition(partition_name="safety_rules")    # 安全规程
collection.create_partition(partition_name="technical_docs")   # 技术文档
collection.create_partition(partition_name="case_studies")     # 案例分析

# 加载 Collection
collection.load()

# 搜索示例
search_params = {
    "metric_type": "COSINE",
    "params": {"nprobe": 10}
}

results = collection.search(
    data=[query_embedding],
    anns_field="embedding",
    param=search_params,
    limit=10,
    expr='category == "safety_rules"',
    output_fields=["chunk_id", "doc_id", "content", "category"]
)
```

### 5.2 实体数据映射

| Milvus Field | PostgreSQL Field | 说明 |
|--------------|------------------|------|
| chunk_id | knowledge_chunks.chunk_id | Chunk唯一标识 |
| doc_id | knowledge_documents.doc_id | 文档ID |
| content | knowledge_chunks.content | 文本内容 |
| embedding | - | 向量（API生成） |
| category | knowledge_documents.category | 分类 |
| tags | knowledge_documents.tags | 标签数组 |
| created_at | knowledge_chunks.created_at | 创建时间 |

---

## 6. Alembic 迁移目录结构

```
db/
├── alembic.ini                 # Alembic 配置文件
├── env.py                      # 环境配置
├── script.py.mako              # 迁移脚本模板
│
├── versions/                   # 迁移版本目录
│   ├── 001_initial_schema.py   # 初始数据库结构
│   ├── 002_add_workflow_tables.py  # 添加工作流相关表
│   ├── 003_add_knowledge_base.py   # 添加知识库表
│   ├── 004_add_sensor_timeseries.py # 添加时序表
│   └── 005_add_indexes.py      # 添加性能索引
│
├── init/                       # 初始化脚本
│   └── 001_seed_data.sql      # 种子数据
│
└── migrations/                 # 迁移工具脚本
    ├── migrate_timescale.py    # 时序表迁移脚本
    └── migrate_milvus.py      # 向量库同步脚本
```

### 6.1 alembic.ini 核心配置

```ini
[alembic]
script_location = db
prepend_sys_path = .
version_path_separator = os

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname = alembic

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### 6.2 env.py 配置

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base
from config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """离线模式运行迁移"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """在线模式运行迁移"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 6.3 迁移脚本示例

```python
# versions/001_initial_schema.py
"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-05-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 用户表
    op.create_table(
        'users',
        sa.Column('user_id', sa.String(64), primary_key=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(100), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # 工地表
    op.create_table(
        'sites',
        sa.Column('site_id', sa.String(64), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='planning'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # ... 其他表

def downgrade() -> None:
    op.drop_table('sites')
    op.drop_table('users')
```

---

## 7. 数据流关系总结

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据存储层架构                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │  PostgreSQL  │    │  TimescaleDB │    │    Redis     │                  │
│  │  (主库)      │    │  (时序数据)   │    │  (缓存/队列)  │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
│         │                   │                   │                          │
│         ▼                   ▼                   ▼                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │  结构化业务   │    │  传感器时序  │    │  会话/消息    │                  │
│  │  数据存储    │    │  数据存储    │    │  队列缓存    │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
│                             │                                              │
│                             ▼                                              │
│                      ┌──────────────┐                                       │
│                      │   Milvus     │                                       │
│                      │  (向量数据)   │                                       │
│                      └──────────────┘                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```
