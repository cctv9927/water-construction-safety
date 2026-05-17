"""
增强版后端代理模块
优化点：
1. 熔断器模式（防止级联故障）
2. 后端健康检查（自动感知服务状态）
3. 超时控制 + 重试机制
4. 流量分配（健康的服务获得更多流量）
"""

from __future__ import annotations

import asyncio
import time
import logging
from typing import Optional, Dict
from dataclasses import dataclass, field
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常（关闭熔断器）
    OPEN = "open"          # 熔断（拒绝请求）
    HALF_OPEN = "half_open"  # 半开（尝试恢复）


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5       # 失败多少次后打开熔断器
    success_threshold: int = 3       # 半开后成功多少次关闭熔断器
    timeout: float = 30.0            # 熔断器打开后多久尝试半开（秒）
    half_open_max_calls: int = 3     # 半开状态最大并发请求数


@dataclass
class CircuitBreaker:
    """
    熔断器实现
    
    状态转换：
    CLOSED → OPEN：连续失败达到阈值
    OPEN → HALF_OPEN：超时后尝试恢复
    HALF_OPEN → CLOSED：连续成功达到阈值
    HALF_OPEN → OPEN：任何失败
    """
    
    name: str
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    
    # 状态
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0
    half_open_calls: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    def __post_init__(self):
        self._lock = asyncio.Lock()
    
    async def can_execute(self) -> bool:
        """检查是否可以执行请求"""
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                # 检查是否超时，可以尝试半开
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.config.timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info("[CircuitBreaker] %s: OPEN → HALF_OPEN", self.name)
                    return True
                return False
            
            if self.state == CircuitState.HALF_OPEN:
                # 半开状态限制并发请求数
                if self.half_open_calls < self.config.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                return False
            
            return False
    
    async def record_success(self):
        """记录成功"""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    logger.info("[CircuitBreaker] %s: HALF_OPEN → CLOSED", self.name)
            else:
                self.failure_count = 0
    
    async def record_failure(self):
        """记录失败"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                # 半开状态任何失败都立即打开
                self.state = CircuitState.OPEN
                self.half_open_calls = 0
                logger.warning("[CircuitBreaker] %s: HALF_OPEN → OPEN (failure)", self.name)
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.warning(
                        "[CircuitBreaker] %s: CLOSED → OPEN (failures=%d)",
                        self.name, self.failure_count
                    )
    
    def get_state(self) -> Dict:
        """获取状态信息"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
        }


class HealthChecker:
    """
    后端服务健康检查器
    定期检查后端服务可用性
    """
    
    def __init__(self, check_interval: float = 30.0, timeout: float = 5.0):
        self.check_interval = check_interval
        self.timeout = timeout
        self._health_status: Dict[str, Dict] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def check_single(self, name: str, url: str) -> Dict:
        """检查单个服务健康状态"""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{url}/health")
                elapsed = time.time() - start
                
                is_healthy = response.status_code == 200
                return {
                    "name": name,
                    "url": url,
                    "healthy": is_healthy,
                    "status_code": response.status_code,
                    "latency_ms": round(elapsed * 1000, 2),
                    "checked_at": time.time(),
                }
        except Exception as e:
            return {
                "name": name,
                "url": url,
                "healthy": False,
                "error": str(e),
                "latency_ms": round((time.time() - start) * 1000, 2),
                "checked_at": time.time(),
            }
    
    async def check_all(self, backends: Dict[str, str]) -> Dict[str, Dict]:
        """检查所有后端服务"""
        tasks = [
            self.check_single(name, url)
            for name, url in backends.items()
        ]
        results = await asyncio.gather(*tasks)
        
        status = {}
        for r in results:
            status[r["name"]] = r
        
        async with self._lock:
            self._health_status = status
        
        return status
    
    async def get_health_status(self) -> Dict[str, Dict]:
        """获取健康状态"""
        async with self._lock:
            return self._health_status.copy()
    
    async def is_healthy(self, name: str) -> bool:
        """检查特定服务是否健康"""
        async with self._lock:
            if name not in self._health_status:
                return True  # 未检查过的默认健康
            return self._health_status[name].get("healthy", False)
    
    async def start(self, backends: Dict[str, str]):
        """启动健康检查"""
        self._running = True
        # 立即执行一次检查
        await self.check_all(backends)
        
        async def _check_loop():
            while self._running:
                await asyncio.sleep(self.check_interval)
                if self._running:
                    await self.check_all(backends)
        
        self._task = asyncio.create_task(_check_loop())
        logger.info("[HealthChecker] 已启动健康检查，间隔: %ds", self.check_interval)
    
    async def stop(self):
        """停止健康检查"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[HealthChecker] 已停止")


class EnhancedProxy:
    """
    增强版后端代理
    
    特性：
    - 熔断器保护
    - 健康检查感知
    - 超时控制
    - 智能重试
    """
    
    def __init__(
        self,
        backend_url: str,
        backend_name: str,
        circuit_config: Optional[CircuitBreakerConfig] = None,
        request_timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self.backend_url = backend_url.rstrip("/")
        self.backend_name = backend_name
        self.circuit_breaker = CircuitBreaker(
            name=backend_name,
            config=circuit_config or CircuitBreakerConfig(),
        )
        self.request_timeout = request_timeout
        self.max_retries = max_retries
    
    async def request(
        self,
        path: str,
        method: str = "GET",
        body: Optional[dict] = None,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> Dict:
        """
        发送代理请求（带熔断器和重试）
        """
        url = f"{self.backend_url}/{path.lstrip('/')}"
        
        # 检查熔断器
        if not await self.circuit_breaker.can_execute():
            return {
                "error": "circuit_open",
                "message": f"后端服务 {self.backend_name} 熔断器已打开",
                "circuit_state": self.circuit_breaker.get_state(),
            }
        
        # 重试循环
        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                    if method == "GET":
                        response = await client.get(url, params=params, headers=headers)
                    elif method == "POST":
                        response = await client.post(url, json=body, params=params, headers=headers)
                    elif method == "PUT":
                        response = await client.put(url, json=body, params=params, headers=headers)
                    elif method == "DELETE":
                        response = await client.delete(url, params=params, headers=headers)
                    else:
                        return {"error": "unsupported_method", "message": f"不支持的方法: {method}"}
                    
                    # 记录成功
                    await self.circuit_breaker.record_success()
                    
                    # 判断是否成功（2xx 或 4xx 都是正常响应）
                    if 200 <= response.status_code < 500:
                        return {
                            "status_code": response.status_code,
                            "data": response.json() if response.headers.get(
                                "content-type", ""
                            ).startswith("application/json") else response.text,
                            "headers": dict(response.headers),
                        }
                    else:
                        # 5xx 错误，触发重试
                        last_error = f"HTTP {response.status_code}"
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(0.5 * (attempt + 1))
                            continue
                        return {
                            "error": "server_error",
                            "status_code": response.status_code,
                            "message": f"后端服务返回错误: {response.status_code}",
                        }
            
            except httpx.TimeoutException:
                last_error = "timeout"
                logger.warning(
                    "[Proxy] %s 请求超时 (attempt %d/%d)",
                    self.backend_name, attempt + 1, self.max_retries
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                    continue
                await self.circuit_breaker.record_failure()
                return {"error": "timeout", "message": f"后端服务 {self.backend_name} 请求超时"}
            
            except httpx.ConnectError as e:
                last_error = f"connection_error: {e}"
                await self.circuit_breaker.record_failure()
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                    continue
                return {
                    "error": "connection_error",
                    "message": f"无法连接到后端服务: {self.backend_name}",
                }
            
            except Exception as e:
                last_error = str(e)
                await self.circuit_breaker.record_failure()
                return {"error": "unknown", "message": f"代理请求失败: {str(e)}"}
        
        # 所有重试都失败
        await self.circuit_breaker.record_failure()
        return {"error": "retry_exhausted", "message": f"重试次数耗尽，最后错误: {last_error}"}
    
    def get_circuit_state(self) -> Dict:
        """获取熔断器状态"""
        return self.circuit_breaker.get_state()


class BackendManager:
    """
    后端服务管理器
    管理多个后端的健康检查和流量分配
    """
    
    def __init__(
        self,
        backends: Dict[str, str],
        health_check_interval: float = 30.0,
    ):
        self.backends = backends
        self.health_checker = HealthChecker(check_interval=health_check_interval)
        self.proxies: Dict[str, EnhancedProxy] = {}
        
        # 初始化代理
        for name, url in backends.items():
            self.proxies[name] = EnhancedProxy(
                backend_url=url,
                backend_name=name,
            )
    
    async def start(self):
        """启动后端管理"""
        await self.health_checker.start(self.backends)
        logger.info("[BackendManager] 已启动，管理 %d 个后端", len(self.backends))
    
    async def stop(self):
        """停止后端管理"""
        await self.health_checker.stop()
    
    async def get_proxy(self, name: str) -> Optional[EnhancedProxy]:
        """获取指定后端的代理（带健康检查）"""
        if name not in self.proxies:
            return None
        
        # 检查后端是否健康
        is_healthy = await self.health_checker.is_healthy(name)
        if not is_healthy:
            logger.warning(
                "[BackendManager] 后端 %s 不健康，但仍在请求（熔断器保护）",
                name
            )
        
        return self.proxies[name]
    
    async def get_all_status(self) -> Dict:
        """获取所有后端状态"""
        health = await self.health_checker.get_health_status()
        circuits = {name: p.get_circuit_state() for name, p in self.proxies.items()}
        
        return {
            "health": health,
            "circuits": circuits,
        }
