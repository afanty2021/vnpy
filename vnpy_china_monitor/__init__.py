"""
A股监控告警模块

提供系统状态监控、交易状态监控、风控告警集成和多通道通知功能
"""

from vnpy_china_monitor.monitor.engine import MonitorEngine, MonitorType, MonitorData
from vnpy_china_monitor.monitor.system_monitor import SystemMonitor
from vnpy_china_monitor.monitor.trade_monitor import TradeMonitor
from vnpy_china_monitor.alert.engine import (
    AlertEngine,
    AlertPriority,
    AlertSeverity,
    AlertEvent,
)
from vnpy_china_monitor.alert.deduplicator import AlertDeduplicator, DedupeConfig
from vnpy_china_monitor.alert.channels.base import AlertChannel, AlertMessage
from vnpy_china_monitor.alert.channels.ui import UIChannel
from vnpy_china_monitor.alert.channels.email import EmailChannel
from vnpy_china_monitor.alert.channels.wechat import WechatChannel
from vnpy_china_monitor.integration.risk_connector import RiskConnector

# 导入事件定义
from vnpy_china_monitor.event import (
    EVENT_MONITOR_DATA,
    EVENT_ALERT_SENT,
    EVENT_ALERT_ACKNOWLEDGED,
    EVENT_RISK_ALERT,
)

__all__ = [
    # 监控模块
    "MonitorEngine",
    "MonitorType",
    "MonitorData",
    "SystemMonitor",
    "TradeMonitor",
    # 告警模块
    "AlertEngine",
    "AlertPriority",
    "AlertSeverity",
    "AlertEvent",
    "AlertDeduplicator",
    "DedupeConfig",
    # 通知通道
    "AlertChannel",
    "AlertMessage",
    "UIChannel",
    "EmailChannel",
    "WechatChannel",
    # 集成模块
    "RiskConnector",
    # 事件定义
    "EVENT_MONITOR_DATA",
    "EVENT_ALERT_SENT",
    "EVENT_ALERT_ACKNOWLEDGED",
    "EVENT_RISK_ALERT",
]
