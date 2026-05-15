"""IoT Hub REST API 上报模块"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from .models import FormattedSensorData, ConfigModel

logger = logging.getLogger(__name__)


class IoTReporter:
    """IoT Hub REST API 上报客户端"""

    def __init__(self, config: ConfigModel.IoTHubConfig):
        self.base_url = config.base_url.rstrip("/")
        self.timeout = config.timeout
        self.retry = config.retry
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def report(self, data: FormattedSensorData) -> bool:
        """上报单条数据"""
        payload = data.to_dict()
        for attempt in range(self.retry):
            try:
                response = await self._client.post("/sensors/data", json=payload)
                if response.status_code in (200, 201, 202):
                    logger.info(
                        "[Reporter] 上报成功 sensor_id=%s value=%.2f%s",
                        data.sensor_id, data.value, data.unit
                    )
                    return True
                logger.warning(
                    "[Reporter] 上报失败 status=%d sensor_id=%s (attempt %d/%d)",
                    response.status_code, data.sensor_id, attempt + 1, self.retry
                )
            except httpx.TimeoutException:
                logger.warning(
                    "[Reporter] 上报超时 sensor_id=%s (attempt %d/%d)",
                    data.sensor_id, attempt + 1, self.retry
                )
            except httpx.RequestError as exc:
                logger.error(
                    "[Reporter] 上报异常 sensor_id=%s error=%s (attempt %d/%d)",
                    data.sensor_id, exc, attempt + 1, self.retry
                )
            await asyncio.sleep(1 * (attempt + 1))
        return False

    async def report_batch(self, data_list: list[FormattedSensorData]) -> tuple[int, int]:
        """批量上报数据。Returns: (success_count, fail_count)"""
        if not data_list:
            return 0, 0

        success, fail = 0, 0
        tasks = [self.report(d) for d in data_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error("[Reporter] 批量上报异常: %s", result)
                fail += 1
            elif result is True:
                success += 1
            else:
                fail += 1

        logger.info(
            "[Reporter] 批量上报完成: success=%d fail=%d total=%d",
            success, fail, len(data_list)
        )
        return success, fail

    async def health_check(self) -> bool:
        """检查 IoT Hub 连通性"""
        try:
            response = await self._client.get("/health", timeout=5)
            return response.status_code == 200
        except Exception as exc:
            logger.warning("[Reporter] IoT Hub 健康检查失败: %s", exc)
            return False
