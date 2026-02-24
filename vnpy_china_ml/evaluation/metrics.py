"""
A股评估指标模块

本模块提供A股市场特有的策略评估指标，包括：
- Alpha/Beta: 超额收益和系统风险
- 跟踪误差: 相对于基准的偏离程度
- 信息比率: 超额收益与跟踪误差的比值
- 连续盈亏统计: 最大连续盈利/亏损次数
"""

import numpy as np
from typing import Dict, List, Optional, Tuple


class ChinaMetrics:
    """A股评估指标

    提供A股市场特有的策略评估指标计算功能：
    - Alpha: 超额收益率
    - Beta: 系统风险系数
    - 跟踪误差 (Tracking Error): 相对于基准的偏离程度
    - 信息比率 (Information Ratio): 超额收益与跟踪误差的比值
    - 最大连续盈利/亏损次数

    Attributes:
        risk_free_rate: 无风险利率（年化），默认0.03
    """

    def __init__(self, risk_free_rate: float = 0.03) -> None:
        """初始化评估指标计算器

        Args:
            risk_free_rate: 无风险利率（年化），用于计算夏普比率等指标
        """
        self.risk_free_rate = risk_free_rate

    def calculate_alpha(
        self,
        returns: np.ndarray,
        benchmark_returns: np.ndarray,
        annualization_factor: float = 252.0
    ) -> float:
        """计算Alpha

        Alpha表示策略相对于基准的超额收益。
        Alpha > 0 表示策略优于基准。

        Args:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列
            annualization_factor: 年化因子，默认252（交易日）

        Returns:
            Alpha值（年化超额收益率）
        """
        if len(returns) != len(benchmark_returns):
            raise ValueError("策略收益率和基准收益率长度不匹配")
        if len(returns) == 0:
            return 0.0

        # 计算日均超额收益
        excess_returns = returns - benchmark_returns
        mean_excess_return = np.mean(excess_returns)

        # 年化Alpha
        alpha = mean_excess_return * annualization_factor

        return float(alpha)

    def calculate_beta(
        self,
        returns: np.ndarray,
        benchmark_returns: np.ndarray
    ) -> float:
        """计算Beta

        Beta表示策略相对于基准的系统风险：
        - Beta = 1: 与基准风险相同
        - Beta > 1: 高于基准风险
        - Beta < 1: 低于基准风险

        Args:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列

        Returns:
            Beta值
        """
        if len(returns) != len(benchmark_returns):
            raise ValueError("策略收益率和基准收益率长度不匹配")
        if len(returns) < 2:
            return 1.0

        # 计算协方差和方差
        covariance = np.cov(returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns, ddof=1)

        if benchmark_variance == 0:
            return 1.0

        beta = covariance / benchmark_variance

        return float(beta)

    def calculate_tracking_error(
        self,
        returns: np.ndarray,
        benchmark_returns: np.ndarray,
        annualization_factor: float = 252.0
    ) -> float:
        """计算跟踪误差

        跟踪误差是超额收益的标准差，反映策略相对于基准的波动程度。

        Args:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列
            annualization_factor: 年化因子，默认252（交易日）

        Returns:
            跟踪误差（年化）
        """
        if len(returns) != len(benchmark_returns):
            raise ValueError("策略收益率和基准收益率长度不匹配")
        if len(returns) < 2:
            return 0.0

        # 计算超额收益
        excess_returns = returns - benchmark_returns

        # 计算跟踪误差（日），然后年化
        te_daily = np.std(excess_returns, ddof=1)
        te_annualized = te_daily * np.sqrt(annualization_factor)

        return float(te_annualized)

    def calculate_information_ratio(
        self,
        returns: np.ndarray,
        benchmark_returns: np.ndarray,
        annualization_factor: float = 252.0
    ) -> float:
        """计算信息比率

        信息比率 = 年化超额收益 / 跟踪误差
        反映每承担一单位主动风险获得的超额收益。

        Args:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列
            annualization_factor: 年化因子，默认252（交易日）

        Returns:
            信息比率
        """
        if len(returns) != len(benchmark_returns):
            raise ValueError("策略收益率和基准收益率长度不匹配")
        if len(returns) < 2:
            return 0.0

        # 计算超额收益
        excess_returns = returns - benchmark_returns
        mean_excess_return = np.mean(excess_returns)

        # 年化超额收益
        annualized_excess_return = mean_excess_return * annualization_factor

        # 计算跟踪误差
        te = self.calculate_tracking_error(returns, benchmark_returns, annualization_factor)

        if te == 0:
            return 0.0

        ir = annualized_excess_return / te

        return float(ir)

    def calculate_sharpe_ratio(
        self,
        returns: np.ndarray,
        annualization_factor: float = 252.0
    ) -> float:
        """计算夏普比率

        夏普比率 = (策略收益 - 无风险收益) / 策略收益标准差
        反映每承担一单位总风险获得的超额收益。

        Args:
            returns: 策略收益率序列
            annualization_factor: 年化因子，默认252（交易日）

        Returns:
            夏普比率
        """
        if len(returns) < 2:
            return 0.0

        # 计算平均收益率和标准差
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)

        if std_return == 0:
            return 0.0

        # 年化
        annualized_return = mean_return * annualization_factor
        annualized_std = std_return * np.sqrt(annualization_factor)

        # 夏普比率
        sharpe = (annualized_return - self.risk_free_rate) / annualized_std

        return float(sharpe)

    def calculate_max_consecutive_wins(
        self,
        returns: np.ndarray,
        threshold: float = 0.0
    ) -> int:
        """计算最大连续盈利次数

        Args:
            returns: 收益率序列
            threshold: 盈利阈值，默认0（收益率大于0为盈利）

        Returns:
            最大连续盈利次数
        """
        if len(returns) == 0:
            return 0

        max_consecutive = 0
        current_consecutive = 0

        for r in returns:
            if r > threshold:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    def calculate_max_consecutive_losses(
        self,
        returns: np.ndarray,
        threshold: float = 0.0
    ) -> int:
        """计算最大连续亏损次数

        Args:
            returns: 收益率序列
            threshold: 亏损阈值，默认0（收益率小于0为亏损）

        Returns:
            最大连续亏损次数
        """
        if len(returns) == 0:
            return 0

        max_consecutive = 0
        current_consecutive = 0

        for r in returns:
            if r < threshold:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    def calculate_win_rate(
        self,
        returns: np.ndarray,
        threshold: float = 0.0
    ) -> float:
        """计算胜率

        Args:
            returns: 收益率序列
            threshold: 盈亏阈值

        Returns:
            胜率（0-1之间）
        """
        if len(returns) == 0:
            return 0.0

        wins = np.sum(returns > threshold)
        win_rate = wins / len(returns)

        return float(win_rate)

    def calculate_profit_loss_ratio(
        self,
        returns: np.ndarray,
        threshold: float = 0.0
    ) -> float:
        """计算盈亏比

        平均盈利与平均亏损的比值。

        Args:
            returns: 收益率序列
            threshold: 盈亏阈值

        Returns:
            盈亏比
        """
        profits = returns[returns > threshold]
        losses = returns[returns < threshold]

        if len(losses) == 0 or np.mean(np.abs(losses)) == 0:
            return float('inf') if len(profits) > 0 else 0.0

        avg_profit = np.mean(profits) if len(profits) > 0 else 0.0
        avg_loss = np.mean(np.abs(losses))

        if avg_loss == 0:
            return float('inf') if avg_profit > 0 else 0.0

        pl_ratio = avg_profit / avg_loss

        return float(pl_ratio)

    def calculate_max_drawdown(
        self,
        returns: np.ndarray
    ) -> float:
        """计算最大回撤

        从峰值到谷底的最大跌幅。

        Args:
            returns: 收益率序列

        Returns:
            最大回撤（正数）
        """
        if len(returns) == 0:
            return 0.0

        # 计算累计收益
        cumulative_returns = np.cumprod(1 + returns)

        # 计算历史高点
        peak = np.maximum.accumulate(cumulative_returns)

        # 计算回撤
        drawdown = (cumulative_returns - peak) / peak

        # 最大回撤
        max_dd = np.min(drawdown)

        return float(abs(max_dd))

    def calculate_calmar_ratio(
        self,
        returns: np.ndarray,
        annualization_factor: float = 252.0
    ) -> float:
        """计算Calmar比率

        Calmar比率 = 年化收益 / 最大回撤
        反映每承担一单位下行风险获得的收益。

        Args:
            returns: 收益率序列
            annualization_factor: 年化因子

        Returns:
            Calmar比率
        """
        if len(returns) == 0:
            return 0.0

        # 计算年化收益率
        mean_return = np.mean(returns)
        annualized_return = mean_return * annualization_factor

        # 计算最大回撤
        max_dd = self.calculate_max_drawdown(returns)

        if max_dd == 0:
            return 0.0

        calmar = annualized_return / max_dd

        return float(calmar)

    def calculate_all_metrics(
        self,
        returns: np.ndarray,
        benchmark_returns: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """计算所有评估指标

        一次性计算所有常用的评估指标。

        Args:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列（可选）

        Returns:
            包含所有评估指标的字典
        """
        metrics = {
            "total_return": float(np.sum(returns)),
            "annual_return": float(np.mean(returns) * 252),
            "volatility": float(np.std(returns) * np.sqrt(252)),
            "sharpe_ratio": self.calculate_sharpe_ratio(returns),
            "max_drawdown": self.calculate_max_drawdown(returns),
            "calmar_ratio": self.calculate_calmar_ratio(returns),
            "win_rate": self.calculate_win_rate(returns),
            "profit_loss_ratio": self.calculate_profit_loss_ratio(returns),
            "max_consecutive_wins": self.calculate_max_consecutive_wins(returns),
            "max_consecutive_losses": self.calculate_max_consecutive_losses(returns),
        }

        if benchmark_returns is not None and len(benchmark_returns) == len(returns):
            metrics["alpha"] = self.calculate_alpha(returns, benchmark_returns)
            metrics["beta"] = self.calculate_beta(returns, benchmark_returns)
            metrics["tracking_error"] = self.calculate_tracking_error(returns, benchmark_returns)
            metrics["information_ratio"] = self.calculate_information_ratio(returns, benchmark_returns)

        return metrics
