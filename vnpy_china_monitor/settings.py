"""
监控告警模块配置

定义所有可配置的参数
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MonitorSettings:
    """监控设置"""

    # 系统监控
    qmt_check_interval: int = 30  # QMT连接检查间隔(秒)
    system_check_interval: int = 60  # 系统检查间隔(秒)
    memory_warning_threshold: float = 0.80  # 内存警告阈值
    memory_critical_threshold: float = 0.90  # 内存严重阈值
    cpu_warning_threshold: float = 0.80  # CPU警告阈值
    cpu_critical_threshold: float = 0.90  # CPU严重阈值
    disk_warning_threshold: float = 0.85  # 磁盘警告阈值
    disk_critical_threshold: float = 0.95  # 磁盘严重阈值

    # 交易监控
    trade_check_interval: int = 5  # 交易检查间隔(秒)
    max_trade_history: int = 10000  # 最大成交历史记录
    max_order_history: int = 5000  # 最大委托历史记录

    # 告警设置
    alert_check_interval: int = 1  # 告警检查间隔(秒)
    max_active_alerts: int = 100  # 最大活跃告警数
    alert_history_limit: int = 1000  # 告警历史限制


@dataclass
class DedupeSettings:
    """去重设置"""

    window_seconds: int = 300  # 去重时间窗口（5分钟）
    cooldown_seconds: int = 600  # 冷却时间（10分钟）
    max_same_alerts: int = 3  # 相同告警最大次数


@dataclass
class ChannelSettings:
    """通知通道设置"""

    # UI通道
    ui_enabled: bool = True
    ui_popup_duration: int = 10  # 弹窗持续时间(秒)

    # 邮件通道
    email_enabled: bool = False
    smtp_host: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: Optional[List[str]] = None

    # 微信通道
    wechat_enabled: bool = False
    wechat_webhook_url: str = ""


@dataclass
class MonitorSystemSettings:
    """监控系统总配置"""

    monitor: MonitorSettings = field(default_factory=MonitorSettings)
    dedupe: DedupeSettings = field(default_factory=DedupeSettings)
    channels: ChannelSettings = field(default_factory=ChannelSettings)

    # 是否启用
    monitor_enabled: bool = True
    alert_enabled: bool = True

    # 日志级别
    log_level: str = "INFO"


# 默认配置
DEFAULT_SETTINGS = MonitorSystemSettings()
