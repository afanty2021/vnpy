"""
VeighNa Alpha Monitor - Alert System

定义预警规则和事件系统。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
import operator


class AlertLevel(str, Enum):
    """
    预警级别枚举

    INFO: 信息级别，仅记录
    WARNING: 警告级别，需要关注
    CRITICAL: 严重级别，需要处理
    EMERGENCY: 紧急级别，需要立即处理
    """

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

    def priority(self) -> int:
        """获取预警优先级（数字越大越严重）"""
        return {
            AlertLevel.INFO: 1,
            AlertLevel.WARNING: 2,
            AlertLevel.CRITICAL: 3,
            AlertLevel.EMERGENCY: 4,
        }[self]


@dataclass
class AlertRule:
    """
    预警规则定义

    Attributes:
        name: 规则名称
        metric_name: 监控的指标名称
        category: 指标类别
        level: 触发时的预警级别
        condition: 触发条件函数
        threshold: 阈值
        comparison_operator: 比较操作符
        higher_is_better: 值越高是否越好（用于判断恶化）
        cooldown_seconds: 冷却时间（秒），防止重复触发
        enabled: 是否启用
    """

    name: str
    metric_name: str
    category: str
    level: AlertLevel
    condition: Callable[[float], bool]
    threshold: float
    comparison_operator: Callable[[float, float], bool]
    higher_is_better: bool = True
    cooldown_seconds: int = 3600  # 默认1小时
    enabled: bool = True

    def evaluate(self, value: float) -> bool:
        """
        评估指标值是否触发预警

        Args:
            value: 指标值

        Returns:
            是否触发预警
        """
        if not self.enabled:
            return False
        return self.condition(value)

    def __str__(self) -> str:
        """规则的字符串表示"""
        op_name = self.comparison_operator.__name__
        return f"{self.name}: {self.metric_name} {op_name} {self.threshold}"


@dataclass
class Alert:
    """
    预警事件

    Attributes:
        rule_name: 触发规则名称
        metric_name: 指标名称
        level: 预警级别
        current_value: 当前指标值
        threshold: 触发阈值
        message: 预警消息
        timestamp: 触发时间
        model_name: 模型名称
        acknowledged: 是否已确认
        acknowledged_at: 确认时间
        acknowledged_by: 确认人
        metadata: 其他元数据
    """

    rule_name: str
    metric_name: str
    level: AlertLevel
    current_value: float
    threshold: float
    message: str
    timestamp: datetime
    model_name: str = ""
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def acknowledge(self, user: str = "system") -> None:
        """
        确认预警

        Args:
            user: 确认人
        """
        self.acknowledged = True
        self.acknowledged_at = datetime.now()
        self.acknowledged_by = user

    def is_active(self) -> bool:
        """是否为活跃预警（未确认）"""
        return not self.acknowledged

    def age_seconds(self) -> float:
        """
        预警年龄（秒）

        Returns:
            从触发到现在经过的秒数
        """
        return (datetime.now() - self.timestamp).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典格式

        Returns:
            字典格式的预警数据
        """
        return {
            "rule_name": self.rule_name,
            "metric_name": self.metric_name,
            "level": self.level.value,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "model_name": self.model_name,
            "acknowledged": self.acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "metadata": self.metadata,
        }


def create_threshold_rule(
    name: str,
    metric_name: str,
    category: str,
    level: AlertLevel,
    operator_str: str,
    threshold: float,
    higher_is_better: bool = True,
    cooldown_seconds: int = 3600,
) -> AlertRule:
    """
    创建基于阈值的预警规则

    Args:
        name: 规则名称
        metric_name: 指标名称
        category: 指标类别
        level: 预警级别
        operator_str: 比较操作符 ('<', '<=', '>', '>=', '==', '!=')
        threshold: 阈值
        higher_is_better: 值越高是否越好
        cooldown_seconds: 冷却时间

    Returns:
        预警规则对象

    Raises:
        ValueError: 不支持的操作符
    """
    op_map: dict[str, Callable[[float, float], bool]] = {
        "<": operator.lt,
        "<=": operator.le,
        ">": operator.gt,
        ">=": operator.ge,
        "==": operator.eq,
        "!=": operator.ne,
    }

    if operator_str not in op_map:
        raise ValueError(f"Unsupported operator: {operator_str}. Must be one of {list(op_map.keys())}")

    comparison_op = op_map[operator_str]

    def condition(value: float) -> bool:
        return comparison_op(value, threshold)

    return AlertRule(
        name=name,
        metric_name=metric_name,
        category=category,
        level=level,
        condition=condition,
        threshold=threshold,
        comparison_operator=comparison_op,
        higher_is_better=higher_is_better,
        cooldown_seconds=cooldown_seconds,
    )


# 默认预警规则集合
DEFAULT_ALERT_RULES: list[AlertRule] = [
    # 收益类规则
    create_threshold_rule(
        name="低夏普比率",
        metric_name="sharpe_ratio",
        category="return",
        level=AlertLevel.WARNING,
        operator_str="<",
        threshold=1.0,
        higher_is_better=True,
        cooldown_seconds=7200,
    ),
    create_threshold_rule(
        name="极低夏普比率",
        metric_name="sharpe_ratio",
        category="return",
        level=AlertLevel.CRITICAL,
        operator_str="<",
        threshold=0.5,
        higher_is_better=True,
        cooldown_seconds=7200,
    ),
    # 风险类规则
    create_threshold_rule(
        name="高回撤警告",
        metric_name="max_drawdown",
        category="risk",
        level=AlertLevel.WARNING,
        operator_str="<",
        threshold=-0.05,
        higher_is_better=False,
        cooldown_seconds=3600,
    ),
    create_threshold_rule(
        name="严重回撤",
        metric_name="max_drawdown",
        category="risk",
        level=AlertLevel.CRITICAL,
        operator_str="<",
        threshold=-0.10,
        higher_is_better=False,
        cooldown_seconds=1800,
    ),
    create_threshold_rule(
        name="紧急回撤",
        metric_name="max_drawdown",
        category="risk",
        level=AlertLevel.EMERGENCY,
        operator_str="<",
        threshold=-0.15,
        higher_is_better=False,
        cooldown_seconds=900,
    ),
    # 预测类规则
    create_threshold_rule(
        name="IC值下降",
        metric_name="ic",
        category="prediction",
        level=AlertLevel.WARNING,
        operator_str="<",
        threshold=0.05,
        higher_is_better=True,
        cooldown_seconds=5400,
    ),
    # 效率类规则
    create_threshold_rule(
        name="负超额收益",
        metric_name="excess_return",
        category="efficiency",
        level=AlertLevel.WARNING,
        operator_str="<",
        threshold=0.0,
        higher_is_better=True,
        cooldown_seconds=3600,
    ),
]


def check_alerts(
    metrics: dict[str, float],
    rules: list[AlertRule],
    model_name: str = "",
) -> list[Alert]:
    """
    检查指标是否触发预警

    Args:
        metrics: 指标字典
        rules: 预警规则列表
        model_name: 模型名称

    Returns:
        触发的预警列表
    """
    alerts: list[Alert] = []

    for rule in rules:
        if rule.metric_name not in metrics:
            continue

        value = metrics[rule.metric_name]

        if rule.evaluate(value):
            alert = Alert(
                rule_name=rule.name,
                metric_name=rule.metric_name,
                level=rule.level,
                current_value=value,
                threshold=rule.threshold,
                message=f"{rule.name}: {rule.metric_name} = {value:.4f}, 阈值: {rule.threshold}",
                timestamp=datetime.now(),
                model_name=model_name,
            )
            alerts.append(alert)

    return alerts
