# 安全加固说明文档

> 水利工地安全监管系统 — v1.0 生产环境安全基线
> 更新日期：2026-05-17

---

## 1. JWT 安全配置

### 1.1 密钥要求

| 配置项 | 要求 |
|--------|------|
| `JWT_SECRET` | **≥32 字符**，生产环境必须使用强随机密钥 |
| `JWT_ALGORITHM` | 推荐 `HS256`，禁止使用 `none` |
| `JWT_EXPIRE_MINUTES` | **≤1440 分钟（24小时）**，超出自动拒绝 |

**生产环境密钥示例**：
```bash
# 生成强随机密钥（≥32 字符）
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 1.2 Token 安全机制

| 功能 | 说明 |
|------|------|
| **jti 声明** | 每个 Token 包含唯一 `jti`（JWT ID），用于重放攻击防护 |
| **Token 黑名单** | 登出时将 jti 写入 Redis（TTL=24h），验证时查询黑名单 |
| **Refresh Token** | 独立 Token，TTL=7天，仅限获取新 Access Token |
| **版本号机制** | 支持 `revoke_all_user_tokens`（递增用户版本号，所有旧 Token 失效） |

### 1.3 密码策略

| 策略 | 配置 |
|------|------|
| 哈希算法 | `bcrypt`（自动 salt，默认 cost=12） |
| 最小长度 | 6 字符（`UserCreate.password` Pydantic 验证） |
| 登录失败锁定 | 5 次错误后锁定 **15 分钟** |
| 计数窗口 | 30 分钟（超时重置计数） |

### 1.4 登录安全流程

```
用户登录请求
    ↓
① 检查 Redis「login:attempts:{user}:{ip}」
    → 已达 5 次 → 返回 429 + "账户已锁定"
    → 未达 5 次 → 继续
    ↓
② 验证用户名 + 密码（bcrypt）
    → 失败 → Redis INCR 计数，记录审计日志
    → 成功 → Redis DEL 计数，记录审计日志
    ↓
③ 创建 JWT（含 jti） → 返回 TokenResponse
```

---

## 2. 全局限流策略

### 2.1 限流规则

| 端点 | 限制 | 窗口 | 算法 |
|------|------|------|------|
| 全局（所有请求） | 100 次/分钟 | 60s | Redis 滑动窗口 |
| `/auth/login` | **10 次/分钟** | 60s | Redis 滑动窗口 |
| `/auth/refresh` | 20 次/分钟 | 60s | Redis 滑动窗口 |
| `/auth/logout` | 30 次/分钟 | 60s | Redis 滑动窗口 |
| 突发流量 | 150 次（全局×1.5） | 10s | Redis 滑动窗口 |

### 2.2 限流响应头

所有限流响应（含 429）均包含标准头：

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1750000000
Retry-After: 42
```

### 2.3 滑动窗口算法原理

使用 Redis 有序集合（ZSET）实现：

```
ZREMRANGEBYSCORE key (now-window)  // 删除过期记录
ZCARD key                          // 获取当前窗口内请求数
ZADD key now:now now                // 添加当前请求
EXPIRE key window                  // 设置 TTL
```

---

## 3. 审计日志

### 3.1 记录范围

| 事件类型 | 触发条件 | 记录内容 |
|----------|----------|----------|
| `login_success` | 登录成功 | user_id, username, IP, UA |
| `login_failed` | 登录失败 | username, IP, UA, 失败原因, 剩余尝试次数 |
| `login_blocked_lockout` | 账户被锁定 | username, IP, UA |
| `logout` | 登出 | user_id, username, IP |
| `token_revoked` | Token 被撤销 | jti, user_id |
| `alert_created` | 告警创建 | alert_id, level, creator |
| `alert_updated` | 告警修改 | alert_id, 变更字段 |
| `alert_deleted` | 告警删除 | alert_id, 操作者 |

### 3.2 日志格式（JSON）

```json
{
  "timestamp": "2026-05-17T09:01:00.000Z",
  "event_type": "login_failed",
  "user_id": null,
  "username": "admin",
  "resource": "auth",
  "action": "login",
  "result": "failed",
  "ip": "10.0.0.1",
  "user_agent": "Mozilla/5.0...",
  "metadata": {"reason": "invalid_password", "remaining": 3},
  "request_id": "550e8400-e29b..."
}
```

### 3.3 存储位置

审计日志写入结构化日志系统（JSON 格式），由 `gateway/logger.py` 的 `StructuredLogger` 统一处理。

---

## 4. CORS 安全

### 4.1 生产环境配置

```bash
# 环境变量配置
ALLOWED_ORIGINS=https://safety.example.com,https://app.example.com
```

**严禁配置：**
```python
ALLOWED_ORIGINS = "*"  # ❌ 禁止通配符
```

### 4.2 防护措施

| 措施 | 说明 |
|------|------|
| `allow_credentials=True` | 仅在明确配置的域名下生效 |
| `allow_methods` | 限制为 `GET, POST, PUT, DELETE, OPTIONS` |
| `allow_headers` | 限制为 `Authorization, Content-Type, X-Request-ID` |
| 动态 origin 匹配 | 仅当请求 origin 在白名单中才设置响应头 |

---

## 5. SQL 注入防御

### 5.1 检查结果

- ✅ **所有数据查询使用 SQLAlchemy ORM**，无直接 SQL 拼接
- ✅ **LIKE 查询防注入**：转义 `%`、`_`、`\` 特殊字符
- ✅ **Alembic 迁移**：使用 `op.execute` + 参数化，迁移文件不处理用户输入

### 5.2 LIKE 查询安全示例

```python
# alerts.py - 安全搜索
safe_search = (
    search.replace("\\", "\\\\")
    .replace("%", "\\%")
    .replace("_", "\\_")
)
query.filter(Alert.title.ilike(f"%{safe_search}%"))
```

---

## 6. 输入验证

### 6.1 Pydantic 模型验证

| 字段 | 验证规则 |
|------|----------|
| `username` | `min_length=3, max_length=50` |
| `password` | `min_length=6` |
| `email` | `EmailStr` 格式校验 |
| `AlertBase.title` | `min_length=1, max_length=200` |
| `AlertBase.latitude` | `ge=-90, le=90` |
| `AlertBase.longitude` | `ge=-180, le=180` |
| `SensorDataPoint.value` | `ge=-1e9, le=1e9` |
| `SensorBase.device_id` | `pattern="^[A-Za-z0-9_-]+$"` |
| `SensorBase.max_value` | ≥ `min_value`（自定义验证器） |
| `AlertFilter.page_size` | `ge=1, le=100` |

---

## 7. 安全响应头

所有响应自动附加以下安全头：

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

---

## 8. 生产环境部署清单

### 8.1 必须配置

- [ ] `JWT_SECRET` ≥ 32 字符强随机密钥
- [ ] `JWT_EXPIRE_MINUTES` ≤ 1440
- [ ] `ALLOWED_ORIGINS` 具体域名列表（禁止 `*`）
- [ ] `DEBUG=False`
- [ ] `DATABASE_URL` 生产数据库（非 localhost）
- [ ] `REDIS_URL` 生产 Redis（非 localhost）
- [ ] HTTPS 启用（`Strict-Transport-Security` 自动生效）

### 8.2 推荐配置

- [ ] 启用 Redis 持久化（限流、黑名单、登录计数依赖）
- [ ] 日志输出到文件（而非 stdout），便于审计追溯
- [ ] 配置日志聚合（ELK/Loki 等）

### 8.3 密钥轮换

建议每 90 天轮换一次 `JWT_SECRET`，轮换步骤：

1. 更新环境变量
2. 重启所有服务实例
3. 用户下次登录自动获取新 Token
4. 旧 Token 在过期前仍有效（黑名单机制可选）

---

## 9. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-05-17 | 初始安全加固：JWT 强化、限流、审计日志、CORS、输入验证 |
