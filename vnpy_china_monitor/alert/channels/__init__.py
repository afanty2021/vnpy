"""
告警通知通道
"""

from vnpy_china_monitor.alert.channels.base import AlertChannel, AlertMessage
from vnpy_china_monitor.alert.channels.ui import UIChannel
from vnpy_china_monitor.alert.channels.email import EmailChannel
from vnpy_china_monitor.alert.channels.wechat import WechatChannel

__all__ = [
    "AlertChannel",
    "AlertMessage",
    "UIChannel",
    "EmailChannel",
    "WechatChannel",
]
