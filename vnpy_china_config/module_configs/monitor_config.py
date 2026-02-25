"""
监控告警模块配置

定义系统监控、交易监控和告警通知相关配置。
"""

from typing import List

from pydantic import Field, field_validator

from vnpy_china_config.base import BaseConfig


class MonitorModuleConfig(BaseConfig):
    """监控告警模块配置

    统一管理系统监控、交易监控和告警通知配置。

    Attributes:
        # 系统监控
        enable_system_monitor: 是否启用系统监控
        system_check_interval: 系统检查间隔（秒）
        cpu_threshold: CPU 使用率阈值（%）
        memory_threshold: 内存使用率阈值（%）
        disk_threshold: 磁盘使用率阈值（%）

        # 交易监控
        enable_trade_monitor: 是否启用交易监控
        trade_check_interval: 交易检查间隔（秒）

        # 告警配置
        enable_alert: 是否启用告警
        alert_cooldown: 告警冷却时间（秒）

        # 邮件配置
        email_enabled: 是否启用邮件告警
        smtp_host: SMTP 服务器地址
        smtp_port: SMTP 服务器端口
        email_username: 邮箱用户名
        email_password: 邮箱密码
        email_to: 告警邮件接收人列表

        # 微信配置
        wechat_enabled: 是否启用微信告警
        wechat_webhook: 企业微信 Webhook 地址
    """

    # 系统监控
    enable_system_monitor: bool = True
    system_check_interval: int = 60
    cpu_threshold: float = 80.0
    memory_threshold: float = 80.0
    disk_threshold: float = 90.0

    # 交易监控
    enable_trade_monitor: bool = True
    trade_check_interval: int = 10

    # 告警配置
    enable_alert: bool = True
    alert_cooldown: int = 300

    # 邮件配置
    email_enabled: bool = False
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 465
    email_username: str = ""
    email_password: str = ""
    email_to: List[str] = Field(default_factory=list)

    # 微信配置
    wechat_enabled: bool = False
    wechat_webhook: str = ""

    @field_validator("cpu_threshold", "memory_threshold", "disk_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        """验证阈值"""
        if v < 0 or v > 100:
            raise ValueError(f"阈值必须在 0-100 之间，当前值: {v}")
        return v

    @field_validator("system_check_interval", "trade_check_interval", "alert_cooldown")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        """验证间隔"""
        if v <= 0:
            raise ValueError(f"间隔必须大于 0，当前值: {v}")
        return v
