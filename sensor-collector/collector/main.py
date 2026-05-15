"""传感器数据采集模块入口"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

import yaml

from .models import RawSensorData, FormattedSensorData, ConfigModel
from .mqtt_client import MQTTSubscriber
from .formatter import SensorFormatter
from .reporter import IoTReporter

logger = logging.getLogger(__name__)


class SensorCollectorApp:
    """传感器数据采集应用主类"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config: Optional[ConfigModel] = None
        self.mqtt_client: Optional[MQTTSubscriber] = None
        self.formatter = SensorFormatter()
        self.reporter: Optional[IoTReporter] = None

        # 批量缓冲区
        self._buffer: list[FormattedSensorData] = []
        self._buffer_lock = asyncio.Lock()
        self._report_task: Optional[asyncio.Task] = None
        self._running = False

    def _load_config(self) -> ConfigModel:
        with open(self.config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return ConfigModel(**raw)

    async def start(self):
        """启动采集应用"""
        self._running = True
        self.config = self._load_config()
        self._setup_logging()

        logger.info("=" * 50)
        logger.info("传感器数据采集模块启动")
        logger.info("MQTT Broker: %s", self.config.mqtt.broker)
        logger.info("IoT Hub: %s", self.config.iot_hub.base_url)
        logger.info("=" * 50)

        self.mqtt_client = MQTTSubscriber(self.config.mqtt)

        # 启动定时上报任务
        self._report_task = asyncio.create_task(self._periodic_report())

        # 启动 MQTT 订阅
        try:
            await self.mqtt_client.subscribe(self._on_raw_data)
        except asyncio.CancelledError:
            logger.info("MQTT 订阅被取消")
        finally:
            await self.shutdown()

    async def _on_raw_data(self, raw: RawSensorData):
        """MQTT 消息回调：格式化 -> 入缓冲区 -> 必要时触发上报"""
        formatted = self.formatter.format(raw)
        logger.debug(
            "[Collect] sensor_id=%s type=%s value=%.2f quality=%s",
            raw.sensor_id, raw.sensor_type, formatted.value, formatted.quality
        )

        async with self._buffer_lock:
            self._buffer.append(formatted)
            # 达到批量上限立即上报
            if len(self._buffer) >= self.config.collector.batch_size:
                await self._flush_buffer()

    async def _periodic_report(self):
        """定时批量上报"""
        interval = self.config.collector.report_interval
        while self._running:
            await asyncio.sleep(interval)
            await self._flush_buffer()

    async def _flush_buffer(self):
        """清空缓冲区并上报"""
        async with self._buffer_lock:
            if not self._buffer:
                return
            batch = self._buffer.copy()
            self._buffer.clear()

        if self.reporter is None:
            async with IoTReporter(self.config.iot_hub) as reporter:
                success, fail = await reporter.report_batch(batch)
                logger.info("[Flush] 批量上报完成: success=%d fail=%d", success, fail)
        else:
            success, fail = await self.reporter.report_batch(batch)
            logger.info("[Flush] 批量上报完成: success=%d fail=%d", success, fail)

    async def shutdown(self):
        """优雅关闭"""
        logger.info("正在关闭采集模块...")
        self._running = False

        if self.mqtt_client:
            self.mqtt_client.stop()

        if self._report_task:
            self._report_task.cancel()
            try:
                await self._report_task
            except asyncio.CancelledError:
                pass

        # 最后一次强制上报
        await self._flush_buffer()
        logger.info("采集模块已关闭")

    def _setup_logging(self):
        level = getattr(logging, self.config.collector.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    app = SensorCollectorApp(config_path)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def signal_handler():
        logger.info("收到中断信号")
        app._running = False
        for task in asyncio.all_tasks(loop):
            task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        loop.run_until_complete(app.start())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
