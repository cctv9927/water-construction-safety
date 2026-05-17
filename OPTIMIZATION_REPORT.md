# 架构优化总结报告

## 优化概述

本次优化针对 `water-construction-safety` 项目，聚焦于 **可靠性**、**可维护性** 和 **扩展性** 三个维度。

---

## 1. sensor-collector 模块优化

### 文件位置
`/sensor-collector/collector/mqtt_client_enhanced.py`

### 优化内容

#### 1.1 QoS 2 支持
```python
# 之前：QoS 1
self.qos = config.qos  # 默认为 1

# 现在：支持 QoS 2（Exactly-Once 投递）
async with aiomqtt.Client(
    identifier=self.client_id,
    clean_session=False,  # 持久化会话
) as client:
    await client.subscribe(topic, qos=2)  # QoS 2
```

#### 1.2 离线缓冲
```python
class OfflineBuffer:
    """
    断网时缓存消息，恢复后自动重传
    使用文件存储，进程重启后数据不丢失
    """
    
    def push(self, message: BufferedMessage) -> bool:
        """添加消息到缓冲区"""
        
    def pop_all(self) -> List[BufferedMessage]:
        """取出所有缓冲消息（恢复时调用）"""
```

#### 1.3 指数退避重连
```python
# 之前：固定延迟重连
await asyncio.sleep(self.reconnect_delay)

# 现在：指数退避，最大 5 分钟
delay = min(
    self.reconnect_delay * (2 ** self._reconnect_attempts),
    300  # 最大 5 分钟
)
```

### 使用方式

```python
# 直接替换原 mqtt_client.py
from .mqtt_client_enhanced import MQTTSubscriber, OfflineBuffer

# 或增量使用
subscriber = MQTTSubscriber(config)
# 自动启用离线缓冲
```

---

## 2. gateway 模块优化

### 文件位置
`/gateway/proxy_enhanced.py`

### 优化内容

#### 2.1 熔断器模式
```python
class CircuitBreaker:
    """
    状态转换：
    CLOSED → OPEN：连续失败达到阈值（默认 5 次）
    OPEN → HALF_OPEN：30 秒后尝试恢复
    HALF_OPEN → CLOSED：连续成功 3 次
    HALF_OPEN → OPEN：任何失败
    """
    
    async def can_execute(self) -> bool:
        """检查是否可以执行请求"""
        
    async def record_success(self):
        """记录成功"""
        
    async def record_failure(self):
        """记录失败"""
```

#### 2.2 后端健康检查
```python
class HealthChecker:
    """
    定期检查后端服务可用性
    每 30 秒检查一次 /health 接口
    """
    
    async def start(self, backends: Dict[str, str]):
        """启动健康检查"""
        
    async def is_healthy(self, name: str) -> bool:
        """检查特定服务是否健康"""
```

#### 2.3 增强版代理
```python
class EnhancedProxy:
    """
    带熔断器和重试的代理
    - 自动熔断不健康的后端
    - 5xx 错误自动重试（最多 3 次）
    - 超时控制（默认 30 秒）
    """
```

### 使用方式

```python
from .proxy_enhanced import BackendManager, EnhancedProxy, CircuitBreakerConfig

# 在 main.py 中替换原代理逻辑
backend_manager = BackendManager(
    backends={
        "sensor_collector": "http://localhost:8001",
        "video_streamer": "http://localhost:8081",
    },
    health_check_interval=30.0,
)

# 启动健康检查
await backend_manager.start()

# 使用代理（自动熔断保护）
proxy = await backend_manager.get_proxy("sensor_collector")
result = await proxy.request("/sensors/data")
```

### 配置项

```yaml
circuit_breaker:
  failure_threshold: 5      # 失败多少次打开熔断器
  success_threshold: 3     # 半开后成功多少次关闭
  timeout: 30.0             # 熔断器打开后多久尝试半开
  half_open_max_calls: 3   # 半开状态最大并发请求数
```

---

## 3. ai-coordinator 模块优化

### 文件位置
`/ai-coordinator/retry_handler.py`

### 优化内容

#### 3.1 死信队列（Dead Letter Queue）
```python
class DeadLetterQueue:
    """
    存储处理失败的任务
    - 持久化到磁盘
    - 7 天 TTL 自动清理
    - 支持重新入队
    """
    
    async def add(self, task: Task, error_message: str, source_event: str):
        """任务失败后进入死信队列"""
        
    async def retry(self, task_id: str) -> Optional[Task]:
        """将死信重新转为任务"""
        
    def get_stats(self) -> Dict:
        """获取统计：总数、按类型分布"""
```

#### 3.2 智能重试
```python
class RetryHandler:
    """
    指数退避重试
    - 最大重试 3 次
    - 延迟：1s → 2s → 4s（±25% 抖动）
    """
    
    def calculate_delay(self, task_id: str, retry_count: int) -> float:
        """计算重试延迟"""
```

#### 3.3 任务追踪
```python
class EnhancedEventProcessor:
    """
    统一的任务处理器
    - 任务状态持久化
    - 完整的执行历史
    - 统计分析
    """
    
    async def submit(self, task_type: str, payload: Dict) -> Task:
        """提交任务"""
        
    async def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        
    async def retry_dead_letter(self, task_id: str) -> bool:
        """重试死信任务"""
```

### 使用方式

```python
from .retry_handler import (
    EnhancedEventProcessor,
    DeadLetterQueue,
    RetryHandler,
    TaskConfig,
)

# 初始化
processor = EnhancedEventProcessor(
    task_config=TaskConfig(
        max_retries=3,
        retry_base_delay=1.0,
        dead_letter_after_retries=True,
    )
)

# 注册处理器
async def handle_sensor(payload):
    # 处理逻辑
    return {"status": "ok"}

processor.register_handler("sensor", handle_sensor)

# 提交任务
task = await processor.submit("sensor", {"sensor_id": "S-001", "value": 25.6})

# 查询状态
status = await processor.get_task_status(task.task_id)

# 获取统计
stats = processor.get_stats()

# 查看死信
dlq_stats = processor.dlq.get_stats()

# 重试死信
await processor.retry_dead_letter("task_id_xxx")
```

---

## 4. 前端 Monorepo 优化

### 文件位置
`/frontend/`

### 架构变更

```
之前：                                    现在：
├── frontend-sandbox/                    frontend/
├── frontend-workflow/                    ├── apps/
├── frontend-expert/                      │   ├── sandbox/      # 电子沙盘
│   ├── src/                              │   ├── workflow/    # 闭环管理
│   ├── package.json                      │   └── expert/      # 专家系统
│   └── ...                               ├── packages/
└── ...                                   │   ├── ui/          # 共享 UI 组件
                                          │   ├── api-client/  # API 客户端
                                          │   └── utils/       # 工具函数
                                          ├── package.json     # workspace 定义
                                          └── turbo.json       # Turborepo 配置
```

### 共享包说明

#### @water-safety/ui
```typescript
// 共享 UI 组件
import { AlertCard, SensorCard, StatusBadge } from '@water-safety/ui';
```

#### @water-safety/api-client
```typescript
// 统一 API 调用
import { alertApi, sensorApi, api } from '@water-safety/api-client';

// 自动携带 Token
// 统一错误处理
// WebSocket 支持
```

### 使用方式

```bash
# 安装依赖（根目录执行一次）
cd frontend
npm install

# 开发（启动所有应用）
npm run dev

# 或启动单个应用
npm run dev --filter=@water-safety/app-sandbox

# 构建
npm run build
```

### 迁移原有代码

```typescript
// 之前 (frontend-sandbox)
import { Button, Card } from 'antd';
import { fetchData } from '../utils/api';

// 现在
import { AlertCard, StatusBadge } from '@water-safety/ui';
import { sensorApi } from '@water-safety/api-client';
```

---

## 优化效果评估

| 模块 | 优化项 | 效果 |
|------|--------|------|
| sensor-collector | QoS 2 + 离线缓冲 | **数据可靠性提升** 断网不丢数据 |
| sensor-collector | 指数退避重连 | **抗抖动能力提升** 避免频繁重连 |
| gateway | 熔断器 | **系统稳定性提升** 防止级联故障 |
| gateway | 健康检查 | **故障感知时间缩短** 从数分钟到 30 秒 |
| ai-coordinator | 死信队列 | **可追溯性提升** 失败任务可分析重试 |
| ai-coordinator | 智能重试 | **处理成功率提升** 临时故障自动恢复 |
| frontend | Monorepo | **维护效率提升** 代码复用、风格统一 |

---

## 下一步建议

### 高优先级
1. **配置中心化**：使用 etcd 或 Consul 管理配置
2. **监控完善**：添加 Prometheus metrics
3. **链路追踪**：OpenTelemetry 集成

### 中优先级
4. **Kubernetes 部署**：GPU 调度、滚动更新
5. **Kafka 替代 Redis Stream**：大规模数据场景

### 低优先级
6. **ClickHouse 分析库**：时序聚合查询优化
7. **多活架构**：跨机房容灾

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `sensor-collector/collector/mqtt_client_enhanced.py` | 增强版 MQTT 客户端 |
| `gateway/proxy_enhanced.py` | 增强版代理（熔断器+健康检查） |
| `ai-coordinator/retry_handler.py` | 死信队列+重试机制 |
| `frontend/` | Monorepo 结构 |
| `OPTIMIZATION_REPORT.md` | 本文档 |
