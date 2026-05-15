"""结构化日志模块"""

from __future__ import annotations

import logging
import sys
import json
from datetime import datetime
from typing import Any, Optional
from pathlib import Path

from .config import LogConfig


class JSONFormatter(logging.Formatter):
    """JSON 格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加额外字段
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(self, config: Optional[LogConfig] = None):
        self.config = config or LogConfig()
        self._setup_logger()

    def _setup_logger(self):
        """设置日志器"""
        self.logger = logging.getLogger("gateway")
        self.logger.setLevel(getattr(logging, self.config.level.upper()))

        # 清除现有处理器
        self.logger.handlers.clear()

        # 创建处理器
        if self.config.output == "file" and self.config.file_path:
            handler = logging.FileHandler(self.config.file_path)
        else:
            handler = logging.StreamHandler(sys.stdout)

        # 设置格式化器
        if self.config.format == "json":
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            ))

        self.logger.addHandler(handler)

    def _log(self, level: str, message: str, **kwargs: Any):
        """记录日志"""
        extra = {"extra": kwargs} if kwargs else None
        getattr(self.logger, level.lower())(message, extra=extra)

    def debug(self, message: str, **kwargs: Any):
        self._log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs: Any):
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs: Any):
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs: Any):
        self._log("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs: Any):
        self._log("CRITICAL", message, **kwargs)


# 全局日志实例
_logger: Optional[StructuredLogger] = None


def get_logger(config: Optional[LogConfig] = None) -> StructuredLogger:
    """获取日志实例"""
    global _logger
    if _logger is None:
        _logger = StructuredLogger(config)
    return _logger
