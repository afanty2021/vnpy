"""
复利增长计算器

使用凯利公式等方法计算最优仓位，实现资金的复利增长。
"""

from typing import List, Optional


class CompoundGrowthCalculator:
    """
    复利增长计算器

    使用凯利公式等方法计算最优仓位，实现资金的复利增长。
    提供仓位大小计算、资金增长预测等功能。
    """

    def __init__(self, target_return: float = 0.20) -> None:
        """
        构造函数

        Args:
            target_return: 年化目标收益率
        """
        self.target_return: float = target_return

    def calculate_kelly_fraction(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        使用凯利公式计算最优仓位比例

        f* = (bp - q) / b

        其中：
        f* = 最优仓位比例
        b = 盈亏比 = avg_win / avg_loss
        p = 胜率 = win_rate
        q = 1 - p

        Args:
            win_rate: 胜率（0-1之间的浮点数）
            avg_win: 平均盈利金额
            avg_loss: 平均亏损金额（应为正数）

        Returns:
            最优仓位比例（使用半凯利，更保守）
        """
        # 边界检查
        if win_rate <= 0 or win_rate >= 1:
            return 0.0

        if avg_loss == 0:
            return 0.0

        # 计算盈亏比
        b: float = abs(avg_win / avg_loss)

        # 胜率和败率
        p: float = win_rate
        q: float = 1 - p

        # 凯利公式
        f_star: float = (b * p - q) / b

        # 限制在0-1之间，并使用半凯利（更保守）
        f_star = max(0.0, min(1.0, f_star * 0.5))

        return f_star

    def calculate_position_size(
        self,
        current_capital: float,
        kelly_fraction: float,
        max_position: float = 0.25
    ) -> float:
        """
        计算目标仓位金额

        Args:
            current_capital: 当前资金
            kelly_fraction: 凯利比例
            max_position: 最大仓位限制（默认25%）

        Returns:
            目标仓位金额
        """
        position_size: float = current_capital * kelly_fraction
        max_size: float = current_capital * max_position

        return min(position_size, max_size)

    def project_growth(
        self,
        initial_capital: float,
        annual_return: float,
        years: int = 10
    ) -> float:
        """
        计算复利增长后的资金

        Args:
            initial_capital: 初始资金
            annual_return: 年化收益率
            years: 年数

        Returns:
            增长后的资金
        """
        return initial_capital * ((1 + annual_return) ** years)

    def calculate_needed_return(
        self,
        initial_capital: float,
        target_capital: float,
        years: int
    ) -> float:
        """
        计算达到目标资金所需的年化收益率

        Args:
            initial_capital: 初始资金
            target_capital: 目标资金
            years: 年数

        Returns:
            需要的年化收益率
        """
        if initial_capital <= 0 or target_capital <= 0 or years <= 0:
            return 0.0

        # (1 + r)^years = target / initial
        # r = (target / initial)^(1/years) - 1
        needed_return: float = (target_capital / initial_capital) ** (1 / years) - 1
        return needed_return

    def calculate_period_returns(
        self,
        initial_capital: float,
        annual_return: float,
        years: int
    ) -> List[float]:
        """
        计算每年末的资金序列

        Args:
            initial_capital: 初始资金
            annual_return: 年化收益率
            years: 年数

        Returns:
            每年末的资金列表
        """
        returns: List[float] = []
        current: float = initial_capital

        for _ in range(years):
            current = current * (1 + annual_return)
            returns.append(current)

        return returns

    def calculate_fractional_kelly(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float = 0.5
    ) -> float:
        """
        计算分数凯利仓位

        分数凯利是凯利公式的变体，使用固定比例的凯利仓位。
        比半凯利更保守，适合风险厌恶型投资者。

        Args:
            win_rate: 胜率
            avg_win: 平均盈利
            avg_loss: 平均亏损
            fraction: 凯利分数（默认0.5，即半凯利）

        Returns:
            分数凯利仓位比例
        """
        full_kelly = self.calculate_kelly_fraction(win_rate, avg_win, avg_loss)
        return full_kelly * fraction

    def calculate_optimal_f(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        max_position: float = 0.25
    ) -> float:
        """
        计算最优仓位比例（带最大仓位限制）

        Args:
            win_rate: 胜率
            avg_win: 平均盈利
            avg_loss: 平均亏损
            max_position: 最大仓位限制

        Returns:
            最优仓位比例
        """
        kelly = self.calculate_kelly_fraction(win_rate, avg_win, avg_loss)
        return min(kelly, max_position)

    def estimate_max_drawdown_from_kelly(
        self,
        kelly_fraction: float,
        win_rate: float
    ) -> float:
        """
        估算凯利仓位下的最大回撤

        基于凯利公式的理论最大回撤估算。

        Args:
            kelly_fraction: 凯利仓位比例
            win_rate: 胜率

        Returns:
            估算的最大回撤比例
        """
        # 理论最大回撤与凯利比例和胜率相关
        # 这是一个简化的估算公式
        if kelly_fraction <= 0 or win_rate <= 0:
            return 0.0

        # 简化的回撤估算
        estimated_drawdown: float = kelly_fraction * (1 - win_rate) * 2
        return min(estimated_drawdown, 1.0)
