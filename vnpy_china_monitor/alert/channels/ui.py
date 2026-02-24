"""
UI告警通道

通过界面弹窗显示告警消息
"""

from typing import Dict, Any, Optional
import threading

from loguru import logger

from vnpy_china_monitor.alert.channels.base import AlertChannel, AlertMessage


class UIChannel(AlertChannel):
    """UI告警通道

    通过界面弹窗显示告警消息
    """

    def __init__(
        self,
        enabled: bool = True,
        popup_duration: int = 10,
        main_window=None,
    ):
        """初始化UI通道

        Args:
            enabled: 是否启用
            popup_duration: 弹窗持续时间（秒）
            main_window: 主窗口实例
        """
        super().__init__(enabled=enabled, name="UIChannel")
        self.popup_duration = popup_duration
        self.main_window = main_window

        # 消息队列（用于异步显示）
        self._message_queue = []
        self._queue_lock = threading.Lock()

        # 回调函数
        self._on_message_callback = None

        logger.info(f"UIChannel 初始化完成: popup_duration={popup_duration}s")

    def set_main_window(self, main_window) -> None:
        """设置主窗口

        Args:
            main_window: 主窗口实例
        """
        self.main_window = main_window

    def set_message_callback(self, callback) -> None:
        """设置消息回调函数

        Args:
            callback: 回调函数，接收 (title, message, severity) 参数
        """
        self._on_message_callback = callback

    def send(self, message: AlertMessage) -> bool:
        """发送告警消息

        Args:
            message: 告警消息

        Returns:
            是否发送成功
        """
        try:
            # 尝试调用回调函数
            if self._on_message_callback:
                self._on_message_callback(
                    title=message.title,
                    message=message.message,
                    severity=message.severity,
                )
                return True

            # 如果没有回调，尝试使用主窗口
            if self.main_window:
                return self._send_via_main_window(message)

            # 否则记录日志
            logger.info(f"[UI告警] {message.title}: {message.message}")
            return True

        except Exception as e:
            logger.error(f"UI通道发送失败: {e}")
            return False

    def _send_via_main_window(self, message: AlertMessage) -> bool:
        """通过主窗口发送消息

        Args:
            message: 告警消息

        Returns:
            是否发送成功
        """
        try:
            # 尝试调用主窗口的告警显示方法
            if hasattr(self.main_window, "show_alert_message"):
                self.main_window.show_alert_message(
                    title=message.title,
                    message=message.message,
                    severity=message.severity,
                    duration=self.popup_duration,
                )
                return True

            if hasattr(self.main_window, "displayAlert"):
                self.main_window.displayAlert(message.title, message.message)
                return True

            # 尝试使用Qt信号
            if hasattr(self.main_window, "alert_signal"):
                self.main_window.alert_signal.emit(
                    message.title,
                    message.message,
                    message.severity,
                )
                return True

            logger.warning("主窗口不支持告警显示方法")
            return False

        except Exception as e:
            logger.error(f"通过主窗口发送告警失败: {e}")
            return False

    def test_connection(self) -> bool:
        """测试通道连接

        Returns:
            是否连接成功
        """
        # UI通道始终可用
        return True

    def show_notification(
        self,
        title: str,
        message: str,
        severity: str = "info",
    ) -> bool:
        """显示通知

        Args:
            title: 标题
            message: 消息
            severity: 严重程度

        Returns:
            是否成功
        """
        msg = AlertMessage(
            title=title,
            message=message,
            severity=severity,
            priority=30,
            timestamp=__import__("datetime").datetime.now(),
            source="UIChannel",
        )
        return self.send(msg)

    def get_info(self) -> Dict[str, Any]:
        """获取通道信息

        Returns:
            通道信息字典
        """
        info = super().get_info()
        info.update({
            "popup_duration": self.popup_duration,
            "has_main_window": self.main_window is not None,
            "has_callback": self._on_message_callback is not None,
        })
        return info
