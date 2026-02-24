"""
风控告警桥接器

将 AStockRiskManager 的风控告警转换为监控告警
"""

import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any

from loguru import logger

from vnpy_china_monitor.alert.engine import AlertEngine
from vnpy_china_monitor.alert.types import AlertPriority, AlertSeverity
from vnpy_china_monitor.monitor.engine import MonitorEngine, MonitorType


# 尝试导入风控模块
try:
    from vnpy_china_rules.risk import AStockRiskManager, RiskAlertEvent
    RISK_MODULE_AVAILABLE = True
except ImportError:
    RISK_MODULE_AVAILABLE = False
    AStockRiskManager = None
    RiskAlertEvent = None


class RiskAlertBridge:
    """风控告警桥接器

    订阅 AStockRiskManager 的风控事件，定期查询风控状态，
    将风控告警转换为监控告警
    """

    def __init__(
        self,
        alert_engine: AlertEngine,
        risk_manager: Any,
        check_interval: int = 60,
    ):
        """初始化风控桥接器

        Args:
            alert_engine: 告警引擎
            risk_manager: AStockRiskManager实例
            check_interval: 检查间隔（秒）
        """
        self.alert_engine = alert_engine
        self.risk_manager = risk_manager
        self.check_interval = check_interval

        # 运行状态
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 缓存
        self._last_check = datetime.now()
        self._last_alert_count = 0

        # 回调
        self._on_risk_alert_callback: Optional[Callable] = None

        logger.info("RiskAlertBridge 初始化完成")

    def start(self) -> None:
        """启动桥接器"""
        if self._running:
            logger.warning("风控桥接器已在运行")
            return

        # 检查风控模块是否可用
        if not RISK_MODULE_AVAILABLE:
            logger.error("风控模块不可用，无法启动桥接器")
            return

        # 订阅风控事件
        if hasattr(self.risk_manager, "subscribe_risk_events"):
            self.risk_manager.subscribe_risk_events(self._on_risk_alert)
            logger.info("已订阅风控事件")

        # 启动检查线程
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

        logger.info("风控桥接器已启动")

    def stop(self) -> None:
        """停止桥接器"""
        if not self._running:
            logger.warning("风控桥接器未在运行")
            return

        self._running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=5)

        logger.info("风控桥接器已停止")

    def check_risk_status(self) -> Dict[str, Any]:
        """检查风控状态

        Returns:
            风控状态字典
        """
        if not self.risk_manager:
            return {"available": False, "message": "未连接风控管理器"}

        try:
            # 获取活跃告警
            if hasattr(self.risk_manager, "get_active_risk_alerts"):
                alerts = self.risk_manager.get_active_risk_alerts()
            else:
                alerts = []

            # 获取风控状态摘要
            if hasattr(self.risk_manager, "get_risk_status"):
                status = self.risk_manager.get_risk_status()
            else:
                status = {}

            # 更新监控数据
            self._update_monitor_data(alerts, status)

            self._last_check = datetime.now()
            self._last_alert_count = len(alerts)

            return {
                "available": True,
                "alert_count": len(alerts),
                "status": status,
            }

        except Exception as e:
            logger.error(f"检查风控状态失败: {e}")
            return {
                "available": False,
                "message": str(e),
            }

    def _on_risk_alert(self, alert: Any) -> None:
        """处理风控告警事件

        Args:
            alert: RiskAlertEvent
        """
        try:
            # 转换告警
            title = f"[风控] {alert.rule_name}"
            message = alert.message

            # 转换严重程度
            severity = self._convert_severity(alert.severity)

            # 转换优先级
            priority = self._convert_priority(alert.severity)

            # 发送告警
            self.alert_engine.send_alert(
                title=title,
                message=message,
                severity=severity,
                priority=priority,
                source="risk_manager",
                data={
                    "rule_name": alert.rule_name,
                    "rule_type": alert.rule_type,
                    "timestamp": alert.timestamp.isoformat() if alert.timestamp else None,
                },
            )

            # 触发回调
            if self._on_risk_alert_callback:
                self._on_risk_alert_callback(alert)

            logger.info(f"风控告警已转换: {alert.rule_name} - {alert.message}")

        except Exception as e:
            logger.error(f"处理风控告警失败: {e}")

    def _convert_severity(self, severity: str) -> AlertSeverity:
        """转换严重程度

        Args:
            severity: 原始严重程度

        Returns:
            AlertSeverity
        """
        mapping = {
            "info": AlertSeverity.INFO,
            "warning": AlertSeverity.WARNING,
            "critical": AlertSeverity.CRITICAL,
        }
        return mapping.get(severity.lower(), AlertSeverity.INFO)

    def _convert_priority(self, severity: str) -> AlertPriority:
        """转换优先级

        Args:
            severity: 原始严重程度

        Returns:
            AlertPriority
        """
        mapping = {
            "info": AlertPriority.INFO,
            "warning": AlertPriority.HIGH,
            "critical": AlertPriority.CRITICAL,
        }
        return mapping.get(severity.lower(), AlertPriority.NORMAL)

    def set_risk_alert_callback(self, callback: Callable) -> None:
        """设置风控告警回调

        Args:
            callback: 回调函数
        """
        self._on_risk_alert_callback = callback

    def _update_monitor_data(self, alerts: List, status: Dict) -> None:
        """更新监控数据

        Args:
            alerts: 活跃告警列表
            status: 风控状态
        """
        # 注意：这里需要传入 MonitorEngine，实际使用时由外部传入
        # 暂时跳过，需要在 MonitorSystem 中统一管理

    def _monitor_loop(self) -> None:
        """监控循环"""
        while not self._stop_event.is_set():
            try:
                self.check_risk_status()
            except Exception as e:
                logger.error(f"风控状态检查失败: {e}")

            # 等待下一个检查周期
            self._stop_event.wait(self.check_interval)

    def get_last_check_time(self) -> datetime:
        """获取最后检查时间"""
        return self._last_check

    def get_last_alert_count(self) -> int:
        """获取最后告警数量"""
        return self._last_alert_count
