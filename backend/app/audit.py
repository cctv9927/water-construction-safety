"""
审计日志模块 - 记录所有关键操作

包含：
- 用户登录/登出（成功+失败）
- 告警创建/修改/删除
- 敏感数据访问
- 管理操作
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from enum import Enum
from typing import Optional, Any

from .logger import get_logger


class AuditEventType(str, Enum):
    """审计事件类型"""
    # 认证类
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REVOKED = "token_revoked"

    # 告警类
    ALERT_CREATED = "alert_created"
    ALERT_UPDATED = "alert_updated"
    ALERT_DELETED = "alert_deleted"
    ALERT_ASSIGNED = "alert_assigned"
    ALERT_STATUS_CHANGED = "alert_status_changed"

    # 敏感数据访问
    SENSOR_DATA_ACCESSED = "sensor_data_accessed"
    VIDEO_CLIP_ACCESSED = "video_clip_accessed"
    EXPERT_QUERY = "expert_query"

    # 管理操作
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_LOCKED = "user_locked"
    SETTINGS_CHANGED = "settings_changed"


class AuditLogger:
    """审计日志记录器"""

    def __init__(self):
        self.logger = get_logger()

    def log(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        resource: str = "",
        action: str = "",
        result: str = "success",
        ip: str = "unknown",
        user_agent: str = "unknown",
        metadata: Optional[dict] = None,
        request_id: Optional[str] = None,
    ):
        """记录审计日志

        Args:
            event_type: 事件类型
            user_id: 用户ID
            username: 用户名
            resource: 资源类型/路径
            action: 操作动作
            result: 操作结果 (success/failed/blocked)
            ip: 客户端IP
            user_agent: 用户代理
            metadata: 额外元数据
            request_id: 请求ID
        """
        audit_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "user_id": user_id,
            "username": username,
            "resource": resource,
            "action": action,
            "result": result,
            "ip": ip,
            "user_agent": user_agent,
            "metadata": metadata or {},
            "request_id": request_id,
        }

        # 根据结果级别选择日志级别
        if result == "success":
            self.logger.info(f"[AUDIT] {event_type}", **audit_record)
        elif result == "failed":
            self.logger.warning(f"[AUDIT] {event_type}", **audit_record)
        else:  # blocked
            self.logger.warning(f"[AUDIT] {event_type}", **audit_record)

    # ---- 便捷方法：认证类 ----

    def log_login_success(
        self, user_id: str, username: str, ip: str, user_agent: str = "unknown"
    ):
        self.log(
            event_type=AuditEventType.LOGIN_SUCCESS.value,
            user_id=user_id,
            username=username,
            resource="auth",
            action="login",
            result="success",
            ip=ip,
            user_agent=user_agent,
        )

    def log_login_failed(
        self,
        username: str,
        ip: str,
        reason: str = "invalid_credentials",
        user_agent: str = "unknown",
    ):
        self.log(
            event_type=AuditEventType.LOGIN_FAILED.value,
            username=username,
            resource="auth",
            action="login",
            result="failed",
            ip=ip,
            user_agent=user_agent,
            metadata={"reason": reason},
        )

    def log_logout(self, user_id: str, username: str, ip: str):
        self.log(
            event_type=AuditEventType.LOGOUT.value,
            user_id=user_id,
            username=username,
            resource="auth",
            action="logout",
            result="success",
            ip=ip,
        )

    def log_token_revoked(
        self, user_id: str, username: str, ip: str, reason: str = "manual"
    ):
        self.log(
            event_type=AuditEventType.TOKEN_REVOKED.value,
            user_id=user_id,
            username=username,
            resource="auth",
            action="revoke_token",
            result="success",
            ip=ip,
            metadata={"reason": reason},
        )

    # ---- 便捷方法：告警类 ----

    def log_alert_created(
        self, user_id: str, username: str, alert_id: int, level: str, ip: str
    ):
        self.log(
            event_type=AuditEventType.ALERT_CREATED.value,
            user_id=user_id,
            username=username,
            resource=f"alerts/{alert_id}",
            action="create",
            result="success",
            ip=ip,
            metadata={"alert_id": alert_id, "level": level},
        )

    def log_alert_updated(
        self, user_id: str, username: str, alert_id: int, changes: dict, ip: str
    ):
        self.log(
            event_type=AuditEventType.ALERT_UPDATED.value,
            user_id=user_id,
            username=username,
            resource=f"alerts/{alert_id}",
            action="update",
            result="success",
            ip=ip,
            metadata={"alert_id": alert_id, "changes": changes},
        )

    def log_alert_deleted(self, user_id: str, username: str, alert_id: int, ip: str):
        self.log(
            event_type=AuditEventType.ALERT_DELETED.value,
            user_id=user_id,
            username=username,
            resource=f"alerts/{alert_id}",
            action="delete",
            result="success",
            ip=ip,
            metadata={"alert_id": alert_id},
        )

    # ---- 便捷方法：管理类 ----

    def log_user_locked(self, user_id: str, username: str, ip: str, reason: str):
        self.log(
            event_type=AuditEventType.USER_LOCKED.value,
            user_id=user_id,
            username=username,
            resource=f"users/{user_id}",
            action="lock",
            result="success",
            ip=ip,
            metadata={"reason": reason},
        )


# 全局实例
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """获取审计日志实例"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
