"""
告警服务

提供告警查询、管理等功能
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from vnpy_china_monitor.alert import AlertEngine, AlertPriority, AlertSeverity

logger = logging.getLogger(__name__)


class AlertService:
    """告警服务

    负责：
    - 告警查询
    - 告警确认
    - 告警历史
    - 告警统计
    """

    def __init__(self, alert_engine: Optional[AlertEngine] = None):
        """初始化告警服务

        Args:
            alert_engine: 告警引擎实例
        """
        self.alert_engine = alert_engine

        logger.info("AlertService initialized")

    def send_alert(
        self,
        title: str,
        message: str,
        severity: str = "info",
        priority: str = "normal",
        source: str = "web",
    ) -> Optional[str]:
        """发送告警

        Args:
            title: 标题
            message: 消息
            severity: 严重级别
            priority: 优先级
            source: 来源

        Returns:
            告警ID，失败返回None
        """
        if not self.alert_engine:
            logger.warning("AlertEngine not initialized")
            return None

        try:
            # 转换字符串为枚举
            severity_enum = AlertSeverity(severity.upper())
            priority_enum = AlertPriority(priority.upper())

            alert_id = self.alert_engine.send_alert(
                title=title,
                message=message,
                severity=severity_enum,
                priority=priority_enum,
                source=source,
            )

            logger.info(f"Alert sent: {alert_id} - {title}")
            return alert_id

        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return None

    def get_active_alerts(self, limit: int = 100) -> List[Dict]:
        """获取活跃告警

        Args:
            limit: 限制数量

        Returns:
            告警列表
        """
        if not self.alert_engine:
            return []

        try:
            alerts = self.alert_engine.get_active_alerts()
            return alerts[:limit]
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []

    def get_alert_history(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        """获取告警历史

        Args:
            limit: 限制数量
            offset: 偏移量

        Returns:
            告警列表
        """
        if not self.alert_engine:
            return []

        try:
            return self.alert_engine.get_alert_history(limit=limit)
        except Exception as e:
            logger.error(f"Failed to get alert history: {e}")
            return []

    def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str,
    ) -> bool:
        """确认告警

        Args:
            alert_id: 告警ID
            acknowledged_by: 确认人

        Returns:
            是否成功
        """
        if not self.alert_engine:
            return False

        try:
            self.alert_engine.acknowledge_alert(alert_id, acknowledged_by)
            logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
            return True
        except Exception as e:
            logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取告警统计

        Returns:
            统计数据
        """
        if not self.alert_engine:
            return {}

        try:
            return self.alert_engine.get_stats()
        except Exception as e:
            logger.error(f"Failed to get alert stats: {e}")
            return {}

    def format_alert(self, alert) -> Dict:
        """格式化告警给前端（兼容 dict 与 AlertEvent dataclass）

        AlertEngine.get_active_alerts 返回 AlertEvent dataclass，本方法同时支持
        dict 与 dataclass，避免在 dataclass 上调用 .get 抛 AttributeError。

        Args:
            alert: 告警数据（dict 或 AlertEvent）

        Returns:
            格式化后的数据
        """
        def _val(key, default=None):
            if isinstance(alert, dict):
                return alert.get(key, default)
            return getattr(alert, key, default)

        return {
            "alert_id": _val("alert_id") or _val("id"),
            "title": _val("title"),
            "message": _val("message"),
            "severity": _val("severity"),
            "priority": _val("priority"),
            "source": _val("source"),
            "timestamp": _val("timestamp", datetime.now().isoformat()),
            "acknowledged": _val("acknowledged", False),
            "acknowledged_by": _val("acknowledged_by"),
        }
