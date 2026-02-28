"""
VeighNa Alpha Monitor - Performance Metrics

定义性能监控指标的数据结构和计算函数。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import numpy as np
from vnpy.trader.object import BaseData


class MetricCategory(str, Enum):
    """指标类别枚举"""

    RETURN = "return"  # 收益相关指标
    RISK = "risk"  # 风险相关指标
    EFFICIENCY = "efficiency"  # 效率相关指标
    PREDICTION = "prediction"  # 预测相关指标


@dataclass
class PerformanceMetric(BaseData):
    """
    性能指标数据类

    Attributes:
        name: 指标名称
        value: 指标当前值
        category: 指标类别
        timestamp: 记录时间戳
        baseline: 基准值（用于比较）
        deviation: 与基准的偏差
        rolling_mean: 滚动平均值
        rolling_std: 滚动标准差
        percentile: 百分位数排名
        gateway_name: 数据来源
    """

    gateway_name: str = "ALPHA_MONITOR"
    name: str = ""
    value: float = 0.0
    category: MetricCategory = MetricCategory.RETURN
    timestamp: datetime = field(default_factory=datetime.now)
    baseline: Optional[float] = None
    deviation: Optional[float] = None
    rolling_mean: Optional[float] = None
    rolling_std: Optional[float] = None
    percentile: Optional[float] = None

    def __post_init__(self) -> None:
        """初始化后计算衍生字段"""
        if self.baseline is not None and self.deviation is None:
            self.deviation = self.value - self.baseline

    def is_better_than_baseline(self, higher_is_better: bool = True) -> Optional[bool]:
        """
        判断当前值是否优于基准

        Args:
            higher_is_better: 值越高是否越好

        Returns:
            True if better, False if worse, None if no baseline
        """
        if self.baseline is None:
            return None
        if higher_is_better:
            return self.value > self.baseline
        return self.value < self.baseline

    def deviation_pct(self) -> Optional[float]:
        """
        计算与基准的偏差百分比

        Returns:
            偏差百分比，无基准时返回None
        """
        if self.baseline is None or self.baseline == 0:
            return None
        return (self.value - self.baseline) / abs(self.baseline) * 100


@dataclass
class TradingStatistics:
    """
    交易统计数据

    Attributes:
        total_trades: 总交易次数
        long_trades: 做多交易次数
        short_trades: 做空交易次数
        winning_trades: 盈利交易次数
        losing_trades: 亏损交易次数
        avg_return: 平均收益率
        avg_hold_time: 平均持仓时间
        turnover_rate: 换手率
    """

    total_trades: int = 0
    long_trades: int = 0
    short_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_return: float = 0.0
    avg_hold_time: Optional[float] = None
    turnover_rate: float = 0.0

    def win_rate(self) -> float:
        """计算胜率"""
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades

    def profit_loss_ratio(self) -> Optional[float]:
        """
        计算盈亏比

        Returns:
            盈亏比，无法计算时返回None
        """
        if self.losing_trades == 0:
            return None
        return self.winning_trades / self.losing_trades if self.losing_trades > 0 else float("inf")


@dataclass
class ModelPerformanceSnapshot(BaseData):
    """
    模型性能快照

    包含模型在特定时间点的完整性能指标。

    Attributes:
        gateway_name: 数据来源
        model_name: 模型名称
        timestamp: 快照时间戳
        return_metrics: 收益类指标
        risk_metrics: 风险类指标
        efficiency_metrics: 效率类指标
        prediction_metrics: 预测类指标
        trading_stats: 交易统计数据
        metadata: 其他元数据
    """

    gateway_name: str = "ALPHA_MONITOR"
    model_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    return_metrics: dict[str, PerformanceMetric] = field(default_factory=dict)
    risk_metrics: dict[str, PerformanceMetric] = field(default_factory=dict)
    efficiency_metrics: dict[str, PerformanceMetric] = field(default_factory=dict)
    prediction_metrics: dict[str, PerformanceMetric] = field(default_factory=dict)
    trading_stats: Optional[TradingStatistics] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_metric(self, name: str) -> Optional[PerformanceMetric]:
        """
        获取指定名称的指标

        Args:
            name: 指标名称

        Returns:
            指标对象，不存在时返回None
        """
        for metrics_dict in [
            self.return_metrics,
            self.risk_metrics,
            self.efficiency_metrics,
            self.prediction_metrics,
        ]:
            if name in metrics_dict:
                return metrics_dict[name]
        return None

    def get_all_metrics(self) -> dict[str, PerformanceMetric]:
        """
        获取所有指标

        Returns:
            所有指标的字典
        """
        all_metrics: dict[str, PerformanceMetric] = {}
        all_metrics.update(self.return_metrics)
        all_metrics.update(self.risk_metrics)
        all_metrics.update(self.efficiency_metrics)
        all_metrics.update(self.prediction_metrics)
        return all_metrics

    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典格式

        Returns:
            字典格式的快照数据
        """
        return {
            "model_name": self.model_name,
            "timestamp": self.timestamp.isoformat(),
            "return_metrics": {
                name: {
                    "value": metric.value,
                    "baseline": metric.baseline,
                    "deviation": metric.deviation,
                }
                for name, metric in self.return_metrics.items()
            },
            "risk_metrics": {
                name: {
                    "value": metric.value,
                    "baseline": metric.baseline,
                    "deviation": metric.deviation,
                }
                for name, metric in self.risk_metrics.items()
            },
            "efficiency_metrics": {
                name: {
                    "value": metric.value,
                    "baseline": metric.baseline,
                    "deviation": metric.deviation,
                }
                for name, metric in self.efficiency_metrics.items()
            },
            "prediction_metrics": {
                name: {
                    "value": metric.value,
                    "baseline": metric.baseline,
                    "deviation": metric.deviation,
                }
                for name, metric in self.prediction_metrics.items()
            },
            "trading_stats": (
                {
                    "total_trades": self.trading_stats.total_trades,
                    "winning_trades": self.trading_stats.winning_trades,
                    "losing_trades": self.trading_stats.losing_trades,
                    "win_rate": self.trading_stats.win_rate(),
                }
                if self.trading_stats
                else None
            ),
            "metadata": self.metadata,
        }


def calculate_performance_metrics(
    returns: np.ndarray,
    predictions: Optional[np.ndarray] = None,
    targets: Optional[np.ndarray] = None,
    baseline_returns: Optional[np.ndarray] = None,
) -> dict[str, float]:
    """
    计算性能指标

    Args:
        returns: 收益率序列
        predictions: 预测值序列（可选）
        targets: 目标值序列（可选）
        baseline_returns: 基准收益率序列（可选）

    Returns:
        包含各类性能指标的字典
    """
    metrics: dict[str, float] = {}

    if len(returns) == 0:
        return metrics

    # 收益类指标
    metrics["total_return"] = float(np.sum(returns))
    metrics["avg_return"] = float(np.mean(returns))
    metrics["std_return"] = float(np.std(returns))

    if baseline_returns is not None and len(baseline_returns) > 0:
        metrics["excess_return"] = float(np.mean(returns) - np.mean(baseline_returns))

    # 风险类指标
    metrics["max_drawdown"] = float(calculate_max_drawdown(returns))
    negative_returns = returns[returns < 0]
    if len(negative_returns) > 0:
        metrics["downside_risk"] = float(np.std(negative_returns))
    else:
        metrics["downside_risk"] = 0.0

    # 夏普比率（简化版，假设无风险利率为0）
    if len(returns) > 1:
        metrics["sharpe_ratio"] = float(np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0.0)

    # 效率类指标
    if len(returns) > 1:
        metrics["information_ratio"] = (
            metrics["sharpe_ratio"]  # 简化处理
        )

    # 预测类指标
    if predictions is not None and targets is not None and len(predictions) == len(targets):
        from scipy.stats import pearsonr, spearmanr

        try:
            ic, _ = pearsonr(predictions, targets)
            metrics["ic"] = float(ic)

            rank_ic, _ = spearmanr(predictions, targets)
            metrics["rank_ic"] = float(rank_ic)
        except Exception:
            metrics["ic"] = 0.0
            metrics["rank_ic"] = 0.0

    return metrics


def calculate_max_drawdown(returns: np.ndarray) -> float:
    """
    计算最大回撤

    Args:
        returns: 收益率序列

    Returns:
        最大回撤值（负数）
    """
    if len(returns) == 0:
        return 0.0

    cumulative = np.cumsum(returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = cumulative - running_max
    return float(np.min(drawdown))
