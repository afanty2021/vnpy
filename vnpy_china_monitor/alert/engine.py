"""
告警引擎

管理告警事件、去重和多通道通知
"""

from datetime import datetime
from typing import List, Callable, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import uuid

from loguru import logger

from vnpy.event import EventEngine, Event

from vnpy_china_monitor.event import EVENT_ALERT_SENT, EVENT_ALERT_ACKNOWLEDGED
from vnpy_china_monitor.alert.types import AlertPriority, AlertSeverity, AlertEvent
from vnpy_china_monitor.alert.deduplicator import AlertDeduplicator, DedupeConfig
from vnpy_china_monitor.alert.channels.base import AlertChannel, AlertMessage


class AlertEngine:
    """告警引擎

    负责告警事件的管理、去重和多通道通知
    """

    def __init__(
        self,
        main_engine,
        event_engine: EventEngine,
        dedupe_config: Optional[DedupeConfig] = None,
    ):
        """初始化告警引擎

        Args:
            main_engine: 主引擎
            event_engine: 事件引擎
            dedupe_config: 去重配置
        """
        self.main_engine = main_engine
        self.event_engine = event_engine

        # 去重器
        self._deduplicator = AlertDeduplicator(dedupe_config or DedupeConfig())

        # 活跃告警字典
        self._active_alerts: Dict[str, AlertEvent] = {}

        # 告警历史
        self._alert_history: List[AlertEvent] = []
        self._max_history = 1000

        # 通知通道列表
        self._channels: List[AlertChannel] = []

        # 通道发送线程池：channel.send 可能是同步 SMTP/HTTP，放后台线程避免阻塞事件引擎
        self._channel_executor = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="alert-channel"
        )

        # 告警回调列表
        self._callbacks: List[Callable[[AlertEvent], None]] = []

        # 风控管理器引用（由 connect_risk_manager 注入，供 RiskConnector 集成）
        self._risk_manager: Optional[Any] = None

        # 运行状态
        self._running = False

        # 统计信息
        self._stats = {
            "total_sent": 0,
            "total_deduped": 0,
            "by_severity": {
                "info": 0,
                "warning": 0,
                "critical": 0,
            },
        }

        logger.info("AlertEngine 初始化完成")

    def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        priority: AlertPriority = AlertPriority.NORMAL,
        source: str = "system",
        data: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """发送告警

        Args:
            title: 告警标题
            message: 告警消息
            severity: 严重程度
            priority: 优先级
            source: 告警来源
            data: 附加数据

        Returns:
            告警ID，失败返回None
        """
        # 创建告警事件
        alert_id = str(uuid.uuid4())
        alert = AlertEvent(
            id=alert_id,
            priority=priority,
            title=title,
            message=message,
            severity=severity,
            source=source,
            data=data or {},
        )

        # 去重检查
        fingerprint = self._deduplicator.get_fingerprint(alert)
        if not self._deduplicator.should_send(alert):
            logger.debug(f"告警去重: {title} (fingerprint: {fingerprint})")
            self._stats["total_deduped"] += 1
            return None

        # 记录已发送
        self._deduplicator.record_alert(fingerprint)

        # 添加到活跃告警
        self._active_alerts[alert_id] = alert

        # 更新统计
        self._stats["total_sent"] += 1
        self._stats["by_severity"][severity.value] = (
            self._stats["by_severity"].get(severity.value, 0) + 1
        )

        # 发送到各通道
        self._send_to_channels(alert)

        # 触发回调
        self._trigger_callbacks(alert)

        # 发送事件
        self._emit_alert_event(alert)

        logger.info(f"告警发送: [{severity.value}] {title} - {message}")

        return alert_id

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "user") -> bool:
        """确认告警

        Args:
            alert_id: 告警ID
            acknowledged_by: 确认人

        Returns:
            是否成功
        """
        alert = self._active_alerts.get(alert_id)
        if not alert:
            logger.warning(f"告警不存在: {alert_id}")
            return False

        alert.acknowledged = True
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_time = datetime.now()

        # 从活跃告警移除
        del self._active_alerts[alert_id]

        # 添加到历史
        self._add_to_history(alert)

        # 发送确认事件
        event = Event(
            EVENT_ALERT_ACKNOWLEDGED,
            {
                "alert_id": alert_id,
                "acknowledged_by": acknowledged_by,
                "timestamp": alert.acknowledged_time.isoformat(),
            },
        )
        self.event_engine.put(event)

        logger.info(f"告警已确认: {alert_id} by {acknowledged_by}")
        return True

    def get_active_alerts(self) -> List[AlertEvent]:
        """获取活跃告警列表

        Returns:
            活跃告警列表（按优先级排序）
        """
        alerts = list(self._active_alerts.values())
        return sorted(alerts, key=lambda a: a.priority, reverse=True)

    def get_alert_history(self, limit: int = 100) -> List[AlertEvent]:
        """获取告警历史

        Args:
            limit: 返回数量限制

        Returns:
            告警历史列表
        """
        # limit<=0 时 [-0:] 等价于 [0:] 会返回全部，应返回空列表
        if limit <= 0:
            return []
        return self._alert_history[-limit:]

    def connect_risk_manager(self, risk_manager: Any) -> None:
        """连接风控管理器（供 RiskConnector.connect 调用）

        Args:
            risk_manager: 风控管理器实例
        """
        self._risk_manager = risk_manager
        logger.info("风控管理器已连接到告警引擎")

    def register_channel(self, channel: AlertChannel) -> None:
        """注册通知通道

        Args:
            channel: 告警通道实例
        """
        if channel not in self._channels:
            self._channels.append(channel)
            logger.info(f"告警通道已注册: {channel.__class__.__name__}")

    def unregister_channel(self, channel: AlertChannel) -> None:
        """注销通知通道

        Args:
            channel: 告警通道实例
        """
        if channel in self._channels:
            self._channels.remove(channel)
            logger.info(f"告警通道已注销: {channel.__class__.__name__}")

    def register_callback(self, callback: Callable[[AlertEvent], None]) -> None:
        """注册告警回调

        Args:
            callback: 回调函数
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[AlertEvent], None]) -> None:
        """注销告警回调

        Args:
            callback: 回调函数
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _send_to_channels(self, alert: AlertEvent) -> None:
        """发送告警到所有通道

        Args:
            alert: 告警事件
        """
        message = AlertMessage(
            title=alert.title,
            message=alert.message,
            severity=alert.severity.value,
            priority=alert.priority,
            timestamp=alert.timestamp,
            source=alert.source,
            data=alert.data,
        )

        for channel in self._channels:
            if not channel.enabled:
                continue

            # 提交到后台线程池：channel.send 可能是同步 SMTP/HTTP（部分通道无超时），
            # 在调用线程（可能是 EventEngine 回调）内同步发送会阻塞整个事件分发。
            self._channel_executor.submit(self._send_to_one_channel, channel, message)

    def _send_to_one_channel(self, channel: AlertChannel, message: AlertMessage) -> None:
        """在后台线程发送单个通道告警（隔离慢通道，避免阻塞事件引擎）"""
        try:
            success = channel.send(message)
            if not success:
                logger.warning(f"告警发送失败: {channel.__class__.__name__}")
        except Exception as e:
            logger.error(f"告警通道发送异常: {channel.__class__.__name__}: {e}")

    def _trigger_callbacks(self, alert: AlertEvent) -> None:
        """触发告警回调

        Args:
            alert: 告警事件
        """
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"告警回调执行失败: {e}")

    def _emit_alert_event(self, alert: AlertEvent) -> None:
        """发送告警事件

        Args:
            alert: 告警事件
        """
        event = Event(
            EVENT_ALERT_SENT,
            {
                "alert_id": alert.id,
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity.value,
                "priority": alert.priority.value,
                "source": alert.source,
                "timestamp": alert.timestamp.isoformat(),
            },
        )
        self.event_engine.put(event)

    def _add_to_history(self, alert: AlertEvent) -> None:
        """添加告警到历史

        Args:
            alert: 告警事件
        """
        self._alert_history.append(alert)
        if len(self._alert_history) > self._max_history:
            self._alert_history.pop(0)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return {
            "active_count": len(self._active_alerts),
            "history_count": len(self._alert_history),
            "channels_count": len(self._channels),
            "total_sent": self._stats["total_sent"],
            "total_deduped": self._stats["total_deduped"],
            "by_severity": self._stats["by_severity"].copy(),
        }

    def start(self) -> None:
        """启动告警引擎"""
        if self._running:
            logger.warning("告警引擎已在运行")
            return

        self._running = True
        logger.info("告警引擎已启动")

    def stop(self) -> None:
        """停止告警引擎"""
        if not self._running:
            logger.warning("告警引擎未在运行")
            return

        self._running = False
        # 关闭通道发送线程池（不等待在途发送，避免 stop 被慢通道卡住）
        self._channel_executor.shutdown(wait=False)
        logger.info("告警引擎已停止")

    def is_running(self) -> bool:
        """检查是否在运行"""
        return self._running

    def clear_history(self) -> None:
        """清空告警历史"""
        self._alert_history.clear()
        logger.info("告警历史已清空")

    def clear_active_alerts(self) -> None:
        """清空所有活跃告警"""
        # 将活跃告警移到历史
        for alert in list(self._active_alerts.values()):
            self._add_to_history(alert)

        self._active_alerts.clear()
        logger.info("活跃告警已清空")
