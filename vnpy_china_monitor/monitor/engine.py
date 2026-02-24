"""
监控引擎

管理所有监控项，协调系统监控和交易监控
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from enum import Enum

from loguru import logger

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import MainEngine

from vnpy_china_monitor.event import EVENT_MONITOR_DATA


class MonitorType(Enum):
    """监控类型"""

    SYSTEM = "system"  # 系统监控
    TRADE = "trade"  # 交易监控
    RISK = "risk"  # 风控监控


@dataclass
class MonitorData:
    """监控数据"""

    monitor_type: MonitorType
    name: str
    value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    status: str = "normal"  # normal, warning, critical
    unit: str = ""  # 单位
    description: str = ""  # 描述


class MonitorEngine:
    """监控引擎

    管理所有监控项，协调系统监控和交易监控，提供监控数据查询接口
    """

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        self.main_engine: MainEngine = main_engine
        self.event_engine: EventEngine = event_engine

        # 监控项字典 {name: MonitorData}
        self._monitors: Dict[str, MonitorData] = {}

        # 监控器实例
        self._system_monitor: Optional[Any] = None
        self._trade_monitor: Optional[Any] = None

        # 回调函数列表
        self._callbacks: List[Callable] = []

        # 运行状态
        self._running: bool = False

        logger.info("MonitorEngine 初始化完成")

    def register_system_monitor(self, monitor) -> None:
        """注册系统监控器

        Args:
            monitor: SystemMonitor实例
        """
        self._system_monitor = monitor
        logger.info("系统监控器注册成功")

    def register_trade_monitor(self, monitor) -> None:
        """注册交易监控器

        Args:
            monitor: TradeMonitor实例
        """
        self._trade_monitor = monitor
        logger.info("交易监控器注册成功")

    def get_monitor_data(self, name: str) -> Optional[MonitorData]:
        """获取指定监控数据

        Args:
            name: 监控项名称

        Returns:
            MonitorData或None
        """
        return self._monitors.get(name)

    def get_all_monitors(self) -> List[MonitorData]:
        """获取所有监控数据

        Returns:
            MonitorData列表
        """
        return list(self._monitors.values())

    def get_monitors_by_type(self, monitor_type: MonitorType) -> List[MonitorData]:
        """获取指定类型的监控数据

        Args:
            monitor_type: 监控类型

        Returns:
            MonitorData列表
        """
        return [m for m in self._monitors.values() if m.monitor_type == monitor_type]

    def update_monitor(
        self,
        name: str,
        monitor_type: MonitorType,
        value: Any,
        status: str = "normal",
        unit: str = "",
        description: str = "",
    ) -> None:
        """更新监控数据

        Args:
            name: 监控项名称
            monitor_type: 监控类型
            value: 监控值
            status: 状态 (normal/warning/critical)
            unit: 单位
            description: 描述
        """
        old_data = self._monitors.get(name)

        monitor_data = MonitorData(
            monitor_type=monitor_type,
            name=name,
            value=value,
            timestamp=datetime.now(),
            status=status,
            unit=unit,
            description=description,
        )

        self._monitors[name] = monitor_data

        # 触发回调
        for callback in self._callbacks:
            try:
                callback(monitor_data)
            except Exception as e:
                logger.error(f"监控回调执行失败: {e}")

        # 发送事件
        if old_data is None or old_data.status != status:
            self._emit_event(monitor_data)

    def register_callback(self, callback: Callable) -> None:
        """注册数据变化回调

        Args:
            callback: 回调函数
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)
            logger.debug(f"注册监控回调: {callback.__name__}")

    def unregister_callback(self, callback: Callable) -> None:
        """注销回调

        Args:
            callback: 回调函数
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            logger.debug(f"注销监控回调: {callback.__name__}")

    def start(self) -> None:
        """启动监控"""
        if self._running:
            logger.warning("监控引擎已在运行中")
            return

        self._running = True
        logger.info("监控引擎已启动")

    def stop(self) -> None:
        """停止监控"""
        if not self._running:
            logger.warning("监控引擎未在运行")
            return

        self._running = False
        logger.info("监控引擎已停止")

    def is_running(self) -> bool:
        """检查是否在运行"""
        return self._running

    def get_system_monitor(self):
        """获取系统监控器"""
        return self._system_monitor

    def get_trade_monitor(self):
        """获取交易监控器"""
        return self._trade_monitor

    def _emit_event(self, data: MonitorData) -> None:
        """发送监控数据事件"""
        event = Event(
            EVENT_MONITOR_DATA,
            {
                "monitor_type": data.monitor_type.value,
                "name": data.name,
                "value": data.value,
                "status": data.status,
                "timestamp": data.timestamp.isoformat(),
                "unit": data.unit,
                "description": data.description,
            },
        )
        self.event_engine.put(event)

    def clear_monitors(self) -> None:
        """清空所有监控数据"""
        self._monitors.clear()
        logger.info("监控数据已清空")

    def get_monitor_summary(self) -> Dict[str, Any]:
        """获取监控摘要

        Returns:
            监控摘要信息
        """
        return {
            "total": len(self._monitors),
            "normal": len([m for m in self._monitors.values() if m.status == "normal"]),
            "warning": len([m for m in self._monitors.values() if m.status == "warning"]),
            "critical": len([m for m in self._monitors.values() if m.status == "critical"]),
            "running": self._running,
        }
