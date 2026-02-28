"""
VeighNa Alpha Monitor - Notification System

通知系统，支持多种通知渠道。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import smtplib
from typing import Any, Optional
import json
import urllib.request
from urllib.error import URLError

from .alert import Alert, AlertLevel


logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """
    通知渠道抽象基类

    所有通知渠道必须实现 notify 方法。
    """

    @abstractmethod
    def notify(self, alert: Alert) -> bool:
        """
        发送通知

        Args:
            alert: 预警对象

        Returns:
            是否发送成功
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """渠道名称"""
        ...


@dataclass
class LogNotifierConfig:
    """日志通知配置"""
    level_mapping: dict[AlertLevel, int] = field(default_factory=lambda: {
        AlertLevel.INFO: logging.INFO,
        AlertLevel.WARNING: logging.WARNING,
        AlertLevel.CRITICAL: logging.ERROR,
        AlertLevel.EMERGENCY: logging.CRITICAL,
    })


class LogNotifier(NotificationChannel):
    """
    日志通知渠道

    将预警信息写入日志系统。

    Usage:
        notifier = LogNotifier()
        notifier.notify(alert)
    """

    def __init__(self, config: Optional[LogNotifierConfig] = None) -> None:
        """
        初始化日志通知器

        Args:
            config: 配置对象
        """
        self.config = config or LogNotifierConfig()
        self._name = "log"

    def notify(self, alert: Alert) -> bool:
        """
        记录预警到日志

        Args:
            alert: 预警对象

        Returns:
            是否成功
        """
        try:
            log_level = self.config.level_mapping.get(alert.level, logging.INFO)
            logger.log(
                log_level,
                f"[{alert.level.value.upper()}] {alert.message}",
                extra={
                    "model_name": alert.model_name,
                    "metric_name": alert.metric_name,
                    "current_value": alert.current_value,
                    "threshold": alert.threshold,
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to log alert: {e}")
            return False

    @property
    def name(self) -> str:
        """渠道名称"""
        return self._name


@dataclass
class EmailNotifierConfig:
    """邮件通知配置"""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    from_addr: str = ""
    to_addrs: list[str] = field(default_factory=list)
    use_tls: bool = True


class EmailNotifier(NotificationChannel):
    """
    邮件通知渠道

    通过SMTP发送邮件通知。

    Usage:
        config = EmailNotifierConfig(
            smtp_server="smtp.gmail.com",
            username="your@gmail.com",
            password="your_password",
            from_addr="your@gmail.com",
            to_addrs=["recipient@example.com"]
        )
        notifier = EmailNotifier(config)
        notifier.notify(alert)
    """

    def __init__(self, config: EmailNotifierConfig) -> None:
        """
        初始化邮件通知器

        Args:
            config: 邮件配置
        """
        self.config = config
        self._name = "email"

    def notify(self, alert: Alert) -> bool:
        """
        发送邮件通知

        Args:
            alert: 预警对象

        Returns:
            是否成功
        """
        if not self.config.username or not self.config.to_addrs:
            logger.warning("Email notifier not configured, skipping notification")
            return False

        try:
            # 构建邮件
            msg = MIMEMultipart()
            msg["From"] = self.config.from_addr
            msg["To"] = ", ".join(self.config.to_addrs)
            msg["Subject"] = f"[{alert.level.value.upper()}] {alert.model_name} - {alert.metric_name}"

            # 邮件正文
            body = f"""
模型性能预警

模型名称: {alert.model_name}
预警级别: {alert.level.value.upper()}
指标名称: {alert.metric_name}
当前值: {alert.current_value:.4f}
阈值: {alert.threshold}
消息: {alert.message}
时间: {alert.timestamp.isoformat()}
"""

            msg.attach(MIMEText(body, "plain", "utf-8"))

            # 发送邮件
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls()
                server.login(self.config.username, self.config.password)
                server.send_message(msg)

            logger.info(f"Email notification sent for {alert.rule_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False

    @property
    def name(self) -> str:
        """渠道名称"""
        return self._name


@dataclass
class WebhookNotifierConfig:
    """Webhook通知配置"""
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    timeout: int = 10


class WebhookNotifier(NotificationChannel):
    """
    Webhook通知渠道

    通过HTTP POST发送通知。

    Usage:
        config = WebhookNotifierConfig(
            url="https://your-webhook-url.com/alerts",
            headers={"Authorization": "Bearer your_token"}
        )
        notifier = WebhookNotifier(config)
        notifier.notify(alert)
    """

    def __init__(self, config: WebhookNotifierConfig) -> None:
        """
        初始化Webhook通知器

        Args:
            config: Webhook配置
        """
        self.config = config
        self._name = "webhook"

    def notify(self, alert: Alert) -> bool:
        """
        发送Webhook通知

        Args:
            alert: 预警对象

        Returns:
            是否成功
        """
        if not self.config.url:
            logger.warning("Webhook URL not configured, skipping notification")
            return False

        try:
            # 构建请求数据
            data = {
                "model_name": alert.model_name,
                "rule_name": alert.rule_name,
                "metric_name": alert.metric_name,
                "level": alert.level.value,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "metadata": alert.metadata,
            }

            # 发送请求
            req = urllib.request.Request(
                self.config.url,
                data=json.dumps(data).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    **self.config.headers,
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                if response.status >= 200 and response.status < 300:
                    logger.info(f"Webhook notification sent for {alert.rule_name}")
                    return True
                else:
                    logger.warning(f"Webhook returned status {response.status}")
                    return False

        except URLError as e:
            logger.error(f"Webhook notification failed (URLError): {e}")
            return False
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")
            return False

    @property
    def name(self) -> str:
        """渠道名称"""
        return self._name


class AlertNotifier:
    """
    预警通知管理器

    管理多个通知渠道，支持同时向多个渠道发送通知。

    Usage:
        notifier = AlertNotifier()
        notifier.add_channel(LogNotifier())
        notifier.add_channel(EmailNotifier(config))
        notifier.notify(alert)
    """

    def __init__(self) -> None:
        """初始化通知管理器"""
        self._channels: list[NotificationChannel] = []

    def add_channel(self, channel: NotificationChannel) -> None:
        """
        添加通知渠道

        Args:
            channel: 通知渠道对象
        """
        if channel not in self._channels:
            self._channels.append(channel)
            logger.info(f"Added notification channel: {channel.name}")

    def remove_channel(self, channel_name: str) -> bool:
        """
        移除通知渠道

        Args:
            channel_name: 渠道名称

        Returns:
            是否成功移除
        """
        original_length = len(self._channels)
        self._channels = [ch for ch in self._channels if ch.name != channel_name]
        return len(self._channels) < original_length

    def notify(self, alert: Alert) -> dict[str, bool]:
        """
        向所有渠道发送通知

        Args:
            alert: 预警对象

        Returns:
            各渠道发送结果的字典 {channel_name: success}
        """
        results: dict[str, bool] = {}

        if not self._channels:
            logger.warning("No notification channels configured")
            return results

        for channel in self._channels:
            try:
                success = channel.notify(alert)
                results[channel.name] = success
            except Exception as e:
                logger.error(f"Channel {channel.name} failed: {e}")
                results[channel.name] = False

        return results

    def notify_batch(
        self,
        alerts: list[Alert],
    ) -> dict[str, dict[str, bool]]:
        """
        批量发送通知

        Args:
            alerts: 预警列表

        Returns:
            {alert_id: {channel_name: success}}
        """
        all_results: dict[str, dict[str, bool]] = {}

        for alert in alerts:
            alert_id = f"{alert.model_name}_{alert.metric_name}_{alert.timestamp.timestamp()}"
            all_results[alert_id] = self.notify(alert)

        return all_results

    def get_channels(self) -> list[str]:
        """
        获取所有已配置的渠道名称

        Returns:
            渠道名称列表
        """
        return [ch.name for ch in self._channels]
