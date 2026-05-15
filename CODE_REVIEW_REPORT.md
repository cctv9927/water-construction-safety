# 代码审查报告 - 2026-05-15

## 总体评价

水利建设工地质量安全监管系统是一个功能较为完整的水利工程安全监管平台，包含后端 FastAPI 服务、AI 协调器、视觉检测模块、传感器采集和前端界面。代码整体结构清晰，模块划分合理，但存在若干安全、代码质量和性能问题需要修复。

---

## 详细问题清单

### 🔴 严重问题（必须修复）

| 文件 | 行号 | 问题 | 严重程度 | 建议 |
|------|------|------|---------|------|
| `backend/app/config.py` | 40 | **硬编码 JWT_SECRET 默认值**：`JWT_SECRET: str = "change-me-in-production-water-safety-2024"` | 高危 | 生产环境必须使用强随机密钥，建议从环境变量或密钥管理服务读取，不应有默认值 |
| `backend/app/main.py` | 181 | **全局异常处理器泄露敏感信息**：`content={"success": False, "detail": str(exc)}` 直接暴露异常信息 | 高危 | 生产环境应返回通用错误信息，日志记录详细异常，将 `settings.DEBUG` 作为条件判断 |
| `backend/app/config.py` | 18 | **CORS 配置默认允许所有来源**：`ALLOWED_ORIGINS: str = "*"` | 中危 | 生产环境应限制为具体域名列表，避免跨域攻击 |
| `backend/app/api/alerts.py` | 36 | **搜索参数存在 SQL 注入风险**：`Alert.title.ilike(f"%{search}%")` 未对 search 参数进行严格验证 | 高危 | 使用 ORM 的 bind 参数或添加输入验证，过滤特殊字符 |
| `ai-vision/main.py` | 189 | **FFmpeg 进程未设置超时参数**：`run_async()` 没有 timeout，进程可能僵死 | 中危 | 添加进程超时或使用 `timeout` 参数限制执行时间 |
| `ai-coordinator/main.py` | 139 | **CORS 允许所有来源**：`allow_origins=["*"]` | 中危 | 限制为具体域名 |

### 🟡 中等问题（建议修复）

| 文件 | 行号 | 问题 | 建议 |
|------|------|------|------|
| `backend/app/main.py` | 166-178 | **SSE endpoint 中使用同步数据库查询**：`db = next(get_db())` 在 async 函数中同步调用 | 改用 `async_sessionmaker` 或 `AsyncSession`，使用 `await db.execute()` |
| `backend/app/main.py` | 217-219 | **WebSocket 异常被静默吞掉**：`except Exception:` 只记录日志不断开连接 | 添加重连逻辑或标记连接状态 |
| `backend/app/main.py` | 107 | **Redis 错误被静默吞掉**：`except: pass` 静默处理错误 | 至少记录警告日志 |
| `backend/app/api/alerts.py` | 40-47 | **数据库连接未使用依赖注入**：`db: Session = next(get_db())` 绕过了 FastAPI 依赖注入机制 | 使用 `Depends(get_db)` 统一管理会话生命周期 |
| `ai-coordinator/main.py` | 73 | **异步任务未处理异常**：`asyncio.create_task()` 创建后未 await，可能导致异常丢失 | 使用 `asyncio.shield()` 或添加任务完成回调 |
| `ai-vision/rtsp_stream.py` | 150-156 | **读取帧时固定假设分辨率**：`frame_size = 1920 * 1080 * 3` 假设固定分辨率 | 从视频流元数据获取实际帧大小，或动态计算 |
| `sensor-collector/collector/mqtt_client.py` | 50 | **消息处理错误被静默吞掉**：`except Exception as exc: logger.error(...)` 后没有其他处理 | 添加失败计数或告警机制 |
| `video-streamer/rtsp_client.py` | 95-97 | **ffmpeg 参数错误**：`timeout=self.timeout * 1000000` 将秒转换为微秒但 ffmpeg-python 期望纳秒 | 修正超时参数单位 |

### 🟢 轻微问题（可选优化）

| 文件 | 行号 | 问题 | 建议 |
|------|------|------|------|
| `backend/app/main.py` | 36-37 | **重复导入**：文件末尾再次导入 auth.py 中的函数 | 移除重复导入，保持代码顶部统一导入 |
| `backend/app/main.py` | 195 | **函数命名不规范**：`broadcast_alert` 与 `broadcast` 方法命名相似 | 重命名为 `notify_alert_subscribers` 提高可读性 |
| `ai-coordinator/event_router.py` | 84 | **空列表返回不够明确**：`return []` 应返回结构化响应 | 返回包含警告信息的对象 |
| `ai-vision/main.py` | 58 | **直接使用外部 URL**：`COORDINATOR_URL` 无验证 | 添加 URL 格式验证和超时保护 |
| `frontend-sandbox/src/App.tsx` | 13 | **WebSocket 连接无错误重连机制**：`ws?.close()` 没有 reconnection 逻辑 | 添加自动重连逻辑 |
| `frontend-workflow/src/pages/AlertList.tsx` | 34-40 | **硬编码分页大小**：`page_size: 20` 应从配置或用户偏好读取 | 提取为常量或配置项 |
| `sensor-collector/collector/mqtt_client.py` | 26 | **属性未类型注解**：`self._client: Optional[aiomqtt.Client] = None` 类型不完整 | 添加完整类型注解 |
| `video-streamer/rtsp_client.py` | 42 | **硬编码默认值**：`max_retries: int = 3` 缺少上限检查 | 添加验证防止配置滥用 |

---

## 代码亮点

1. **模块化设计优秀** - 系统采用清晰的微服务架构，后端、AI协调器、视觉模块、传感器模块分离良好
2. **AI 事件路由设计合理** - `EventRouter` 类实现了灵活的事件路由机制，支持多优先级处理
3. **状态机实现完整** - AI Coordinator 的状态机设计清晰，支持状态历史记录
4. **RTSP 流管理器设计良好** - `RTSPStreamManager` 类封装了多路流管理的逻辑
5. **告警等级设计完善** - P0/P1/P2 多级告警机制合理，支持飞书通知集成
6. **前端 React Query 使用规范** - AlertList 组件正确使用了 TanStack Query 进行数据获取和缓存

---

## 审查统计

| 类别 | 数量 |
|------|------|
| 🔴 严重问题 | 6 个 |
| 🟡 中等问题 | 8 个 |
| 🟢 轻微问题 | 8 个 |
| ⭐ 优秀代码 | 6 处 |

---

## 重点修复建议

### 1. 安全优先（立即修复）

```python
# backend/app/config.py - 移除硬编码密钥
JWT_SECRET: str = ""  # 必须从环境变量读取，不设默认值

# backend/app/main.py - 修复异常处理
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    error_id = str(uuid.uuid4())
    logger.error(f"Error {error_id}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "detail": "服务器内部错误", "error_id": error_id}
    )
```

### 2. 性能优化

```python
# backend/app/main.py - SSE 使用异步数据库
from sqlalchemy.ext.asyncio import AsyncSession

@app.get("/sse/status")
async def sse_status(request: Request):
    async def event_generator():
        # 使用异步会话
        async with async_session() as session:
            # ...
```

### 3. Bug 修复

```python
# ai-vision/rtsp_stream.py - 动态获取帧大小
# 改用 cv2.CAP_PROP_FRAME_WIDTH/HEIGHT 获取实际分辨率

# video-streamer/rtsp_client.py - 修正超时单位
.timeout(int(self.timeout * 1000000))  # 转换为纳秒（ffmpeg-python 格式）
```

---

*审查时间：2026-05-15*
*审查工具：AI Code Review Agent*
