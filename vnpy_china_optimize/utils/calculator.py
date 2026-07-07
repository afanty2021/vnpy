"""
计算工具

提供各种金融指标的计算函数。
"""

from typing import List
import numpy as np


def calculate_sharpe_ratio(
    returns: List[float],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252
) -> float:
    """
    计算夏普比率

    Args:
        returns: 收益率序列
        risk_free_rate: 无风险利率（年化）
        periods_per_year: 每年周期数

    Returns:
        夏普比率
    """
    if not returns or len(returns) < 2:
        return 0.0

    returns_array = np.array(returns)

    # 计算均值和标准差
    mean_return = np.mean(returns_array)
    std_return = np.std(returns_array)

    if std_return == 0:
        return 0.0

    # 年化
    annualized_return = mean_return * periods_per_year
    annualized_std = std_return * np.sqrt(periods_per_year)

    # 计算夏普比率
    sharpe = (annualized_return - risk_free_rate) / annualized_std

    return sharpe


def calculate_max_drawdown(equity_curve: List[float]) -> float:
    """
    计算最大回撤

    Args:
        equity_curve: 权益曲线

    Returns:
        最大回撤
    """
    if not equity_curve or len(equity_curve) < 2:
        return 0.0

    equity_array = np.array(equity_curve)

    # 计算累计最大值
    cummax = np.maximum.accumulate(equity_array)

    # 计算回撤
    drawdown = (equity_array - cummax) / cummax

    return abs(np.min(drawdown))


def calculate_calmar_ratio(
    total_return: float,
    max_drawdown: float,
    periods: int = 252
) -> float:
    """
    计算卡玛比率

    Args:
        total_return: 总收益率
        max_drawdown: 最大回撤
        periods: 周期数

    Returns:
        卡玛比率
    """
    if max_drawdown == 0:
        return 0.0

    # periods 为回测总周期数，年化应乘 252/periods（原 periods/252 方向反了）
    if periods <= 0:
        periods = 252

    # 年化收益率
    annual_return = total_return * (252 / periods)

    return annual_return / abs(max_drawdown)


def calculate_sortino_ratio(
    returns: List[float],
    risk_free_rate: float = 0.0,
    target_return: float = 0.0,
    periods_per_year: int = 252
) -> float:
    """
    计算索提诺比率

    Args:
        returns: 收益率序列
        risk_free_rate: 无风险利率
        target_return: 目标收益率
        periods_per_year: 每年周期数

    Returns:
        索提诺比率
    """
    if not returns or len(returns) < 2:
        return 0.0

    returns_array = np.array(returns)

    # 计算 downside deviation
    downside_returns = returns_array[returns_array < target_return]

    if len(downside_returns) == 0:
        return float('inf') if np.mean(returns_array) > target_return else 0.0

    downside_deviation = np.std(downside_returns)

    if downside_deviation == 0:
        return 0.0

    # 年化
    mean_return = np.mean(returns_array)
    annualized_return = mean_return * periods_per_year
    annualized_downside_dev = downside_deviation * np.sqrt(periods_per_year)

    # 计算索提诺比率
    sortino = (annualized_return - risk_free_rate) / annualized_downside_dev

    return sortino
