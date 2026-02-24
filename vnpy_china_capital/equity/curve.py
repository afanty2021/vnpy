"""
资金曲线管理器

记录和管理策略的资金曲线，计算各种风险收益指标。
"""

from typing import List, Optional
from datetime import datetime

from ..objects.types import EquityPoint


class EquityCurveManager:
    """
    资金曲线管理器

    记录和管理策略的资金曲线，计算各种风险收益指标。
    支持资金更新、回撤计算、夏普比率计算等功能。
    """

    def __init__(self, initial_capital: float = 0.0) -> None:
        """
        构造函数

        Args:
            initial_capital: 初始资金
        """
        self.initial_capital: float = initial_capital
        self.equity_curve: List[EquityPoint] = []
        self.peak_equity: float = initial_capital
        self.current_equity: float = initial_capital

    def update(
        self,
        equity: float,
        dt: Optional[datetime] = None
    ) -> EquityPoint:
        """
        更新资金曲线

        Args:
            equity: 当前资金值
            dt: 时间点（默认为当前时间）

        Returns:
            创建的资金曲线点
        """
        if dt is None:
            dt = datetime.now()

        # 更新最高资金
        if equity > self.peak_equity:
            self.peak_equity = equity

        # 计算回撤
        drawdown: float = 0.0
        if self.peak_equity > 0:
            drawdown = (self.peak_equity - equity) / self.peak_equity

        # 计算收益率
        daily_return: float = 0.0
        if self.equity_curve and self.current_equity > 0:
            daily_return = (equity - self.current_equity) / self.current_equity

        cumulative_return: float = 0.0
        if self.initial_capital > 0:
            cumulative_return = (equity - self.initial_capital) / self.initial_capital

        # 创建资金曲线点
        point = EquityPoint(
            datetime=dt,
            equity=equity,
            drawdown=drawdown,
            daily_return=daily_return,
            cumulative_return=cumulative_return
        )

        self.equity_curve.append(point)
        self.current_equity = equity

        return point

    def get_max_drawdown(self) -> float:
        """
        获取最大回撤

        Returns:
            最大回撤比例
        """
        if not self.equity_curve:
            return 0.0
        return max((p.drawdown for p in self.equity_curve), default=0.0)

    def get_current_drawdown(self) -> float:
        """
        获取当前回撤

        Returns:
            当前回撤比例
        """
        if self.peak_equity > 0:
            return (self.peak_equity - self.current_equity) / self.peak_equity
        return 0.0

    def get_returns(self) -> List[float]:
        """
        获取收益率序列

        Returns:
            日收益率列表
        """
        return [p.daily_return for p in self.equity_curve]

    def calculate_sharpe_ratio(
        self,
        risk_free_rate: float = 0.03,
        periods_per_year: int = 252
    ) -> float:
        """
        计算夏普比率

        Args:
            risk_free_rate: 无风险利率（年化）
            periods_per_year: 年化周期数

        Returns:
            夏普比率
        """
        if len(self.equity_curve) < 2:
            return 0.0

        returns = self.get_returns()
        if not returns:
            return 0.0

        avg_return: float = sum(returns) / len(returns)
        variance: float = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_return: float = variance ** 0.5

        if std_return == 0:
            return 0.0

        # 年化
        annual_return: float = avg_return * periods_per_year
        annual_std: float = std_return * (periods_per_year ** 0.5)

        sharpe: float = (annual_return - risk_free_rate) / annual_std
        return sharpe

    def calculate_sortino_ratio(
        self,
        risk_free_rate: float = 0.03,
        periods_per_year: int = 252
    ) -> float:
        """
        计算索提诺比率

        只考虑下行波动率，更适合衡量风险调整后的收益。

        Args:
            risk_free_rate: 无风险利率（年化）
            periods_per_year: 年化周期数

        Returns:
            索提诺比率
        """
        if len(self.equity_curve) < 2:
            return 0.0

        returns = self.get_returns()
        if not returns:
            return 0.0

        avg_return: float = sum(returns) / len(returns)

        # 只计算下行波动率
        downside_returns = [r for r in returns if r < 0]
        if not downside_returns:
            return float('inf') if avg_return > 0 else 0.0

        downside_variance: float = sum(r ** 2 for r in downside_returns) / len(returns)
        downside_std: float = downside_variance ** 0.5

        if downside_std == 0:
            return 0.0

        # 年化
        annual_return: float = avg_return * periods_per_year
        annual_downside_std: float = downside_std * (periods_per_year ** 0.5)

        sortino: float = (annual_return - risk_free_rate) / annual_downside_std
        return sortino

    def calculate_calmar_ratio(self, years: int = 1) -> float:
        """
        计算卡玛比率

        年化收益率与最大回撤的比值。

        Args:
            years: 统计年数

        Returns:
            卡玛比率
        """
        max_dd = self.get_max_drawdown()
        if max_dd == 0:
            return 0.0

        # 计算年化收益率
        if len(self.equity_curve) < 2:
            return 0.0

        first_equity = self.equity_curve[0].equity
        last_equity = self.equity_curve[-1].equity

        if first_equity <= 0:
            return 0.0

        total_return = (last_equity - first_equity) / first_equity
        annual_return = total_return / years

        calmar: float = annual_return / max_dd
        return calmar

    def get_annual_return(self) -> float:
        """
        获取年化收益率

        Returns:
            年化收益率
        """
        if len(self.equity_curve) < 2:
            return 0.0

        first_point = self.equity_curve[0]
        last_point = self.equity_curve[-1]

        if first_point.equity <= 0:
            return 0.0

        total_return = (last_point.equity - first_point.equity) / first_point.equity

        # 计算天数
        days = (last_point.datetime - first_point.datetime).days
        if days <= 0:
            return total_return

        # 年化收益率
        years = days / 365.0
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0

        return annual_return

    def get_volatility(self, periods_per_year: int = 252) -> float:
        """
        获取年化波动率

        Args:
            periods_per_year: 年化周期数

        Returns:
            年化波动率
        """
        if len(self.equity_curve) < 2:
            return 0.0

        returns = self.get_returns()
        if not returns:
            return 0.0

        avg_return: float = sum(returns) / len(returns)
        variance: float = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_return: float = variance ** 0.5

        # 年化波动率
        volatility: float = std_return * (periods_per_year ** 0.5)
        return volatility

    def get_summary(self) -> dict:
        """
        获取资金曲线摘要信息

        Returns:
            包含各项指标的字典
        """
        return {
            "initial_capital": self.initial_capital,
            "current_equity": self.current_equity,
            "peak_equity": self.peak_equity,
            "max_drawdown": self.get_max_drawdown(),
            "current_drawdown": self.get_current_drawdown(),
            "total_return": self.equity_curve[-1].cumulative_return if self.equity_curve else 0.0,
            "annual_return": self.get_annual_return(),
            "sharpe_ratio": self.calculate_sharpe_ratio(),
            "sortino_ratio": self.calculate_sortino_ratio(),
            "calmar_ratio": self.calculate_calmar_ratio(),
            "volatility": self.get_volatility(),
            "num_points": len(self.equity_curve)
        }

    def reset(self) -> None:
        """
        重置资金曲线管理器

        清空所有数据，恢复到初始状态。
        """
        self.equity_curve.clear()
        self.peak_equity = self.initial_capital
        self.current_equity = self.initial_capital
