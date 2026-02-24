"""
告警通道基类

定义告警通知通道的抽象接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

from loguru import logger


@dataclass
class AlertMessage:
    """告警消息

    Attributes:
        title: 标题
        message: 消息内容
        severity: 严重程度
        priority: 优先级
        timestamp: 时间戳
        source: 来源
        data: 附加数据
    """

    title: str
    message: str
    severity: str
    priority: int
    timestamp: datetime
    source: str
    data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}

    def format_text(self) -> str:
        """格式化纯文本消息

        Returns:
            格式化后的文本
        """
        severity_emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "critical": "🚨",
        }

        emoji = severity_emoji.get(self.severity, "📢")

        lines = [
            f"{emoji} {self.title}",
            f"━━━━━━━━━━━━━━━━━━━━",
            f"消息: {self.message}",
            f"严重程度: {self.severity}",
            f"优先级: {self.priority}",
            f"来源: {self.source}",
            f"时间: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        if self.data:
            lines.append("附加数据:")
            for key, value in self.data.items():
                lines.append(f"  {key}: {value}")

        return "\n".join(lines)

    def format_html(self) -> str:
        """格式化HTML消息

        Returns:
            格式化后的HTML
        """
        severity_colors = {
            "info": "#2196F3",
            "warning": "#FF9800",
            "critical": "#F44336",
        }

        color = severity_colors.get(self.severity, "#757575")

        html = f"""
<div style="font-family: Arial, sans-serif; padding: 10px;">
    <h3 style="color: {color}; margin: 0 0 10px 0;">
        {self.title}
    </h3>
    <p style="margin: 5px 0;">
        <strong>消息:</strong> {self.message}
    </p>
    <p style="margin: 5px 0;">
        <strong>严重程度:</strong> <span style="color: {color};">{self.severity}</span>
    </p>
    <p style="margin: 5px 0;">
        <strong>优先级:</strong> {self.priority}
    </p>
    <p style="margin: 5px 0;">
        <strong>来源:</strong> {self.source}
    </p>
    <p style="margin: 5px 0;">
        <strong>时间:</strong> {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
    </p>
</div>
"""

        return html


class AlertChannel(ABC):
    """告警通道基类

    所有告警通知通道的抽象基类
    """

    def __init__(self, enabled: bool = True, name: str = ""):
        """初始化通道

        Args:
            enabled: 是否启用
            name: 通道名称
        """
        self.enabled = enabled
        self.name = name or self.__class__.__name__

    @abstractmethod
    def send(self, message: AlertMessage) -> bool:
        """发送告警消息

        Args:
            message: 告警消息

        Returns:
            是否发送成功
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """测试通道连接

        Returns:
            是否连接成功
        """
        pass

    def format_message(self, message: AlertMessage, format_type: str = "text") -> str:
        """格式化消息

        Args:
            message: 告警消息
            format_type: 格式类型 (text/html)

        Returns:
            格式化后的消息
        """
        if format_type == "html":
            return message.format_html()
        return message.format_text()

    def is_available(self) -> bool:
        """检查通道是否可用

        Returns:
            是否可用
        """
        return self.enabled

    def get_info(self) -> Dict[str, Any]:
        """获取通道信息

        Returns:
            通道信息字典
        """
        return {
            "name": self.name,
            "enabled": self.enabled,
            "class": self.__class__.__name__,
        }
