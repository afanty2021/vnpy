"""
等权重仓位管理器

将资金平均分配到所有目标股票，适用于多因子选股、
指数增强等需要均匀分散风险的策略。
"""

from typing import Dict, List
from .base import PositionSizer
from ..objects.types import PositionAllocation


class EqualWeightPosition(PositionSizer):
    """
    等权重仓位管理器

    将资金平均分配到所有目标股票，适用于多因子选股、
    指数增强等需要均匀分散风险的策略。
    """

    def __init__(self, max_position: int = 10) -> None:
        """
        构造函数

        Args:
            max_position: 最大持仓数量
        """
        super().__init__()
        self.max_position = max_position

    def calculate_positions(
        self,
        symbols: List[str],
        total_capital: float,
        prices: Dict[str, float],
        **kwargs
    ) -> Dict[str, int]:
        """
        等权重分配仓位

        Args:
            symbols: 目标股票列表
            total_capital: 总资金
            prices: 各股票价格

        Returns:
            {symbol: 股数}
        """
        if not symbols:
            return {}

        n = min(len(symbols), self.max_position)
        if n == 0:
            return {}

        # 平均分配资金
        capital_per_stock = total_capital / n

        positions = {}
        self.allocations = {}

        for symbol in symbols[:n]:
            price = prices.get(symbol, 0)
            if price <= 0:
                continue

            # 计算股数（取整到100股）
            volume = int(capital_per_stock / price / 100) * 100

            if volume > 0 and self.validate_position(symbol, volume, price):
                positions[symbol] = volume
                self.allocations[symbol] = PositionAllocation(
                    symbol=symbol,
                    target_volume=volume,
                    target_value=volume * price,
                    weight=1.0 / n,
                    reason="等权重分配"
                )

        return positions
