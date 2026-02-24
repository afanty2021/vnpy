"""
告警基础类型定义

定义告警引擎中使用的基础类型，避免循环导入
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from enum import IntEnum, Enum


class AlertPriority(IntEnum):
    """告警优先级"""

    INFO = 10
    LOW = 20
    NORMAL = 30
    HIGH = 50
    CRITICAL = 70
    EMERGENCY = 90


class AlertSeverity(Enum):
    """告警严重程度"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertEvent:
    """告警事件

    Attributes:
        id: 告警唯一标识
        priority: 告警优先级
        title: 告警标题
        message: 告警消息
        severity: 严重程度
        source: 告警来源
        timestamp: 告警时间
        data: 附加数据
        acknowledged: 是否已确认
        acknowledged_by: 确认人
        acknowledged_time: 确认时间
    """

    id: str
    priority: AlertPriority
    title: str
    message: str
    severity: AlertSeverity
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_by: str = ""
    acknowledged_time: Optional[datetime] = None

    def __lt__(self, other: "AlertEvent") -> bool:
        """比较优先级用于堆排序（数值越大优先级越高）"""
        return self.priority < other.priority
