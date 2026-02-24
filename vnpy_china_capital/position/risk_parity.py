"""
风险平价仓位管理器

根据各股票的波动率分配资金，使得各股票对组合的
风险贡献相等。适用于多资产配置场景。
"""

import numpy as np
from typing import Dict, List, Optional
from .base import PositionSizer
from ..objects.types import PositionAllocation


class RiskParityPosition(PositionSizer):
    """
    风险平价仓位管理器

    根据各股票的波动率分配资金，使得各股票对组合的
    风险贡献相等。适用于多资产配置场景。
    """

    def __init__(self, risk_target: float = 0.1) -> None:
        """
        构造函数

        Args:
            risk_target: 目标组合波动率
        """
        super().__init__()
        self.risk_target = risk_target
        self.default_volatility = 0.2  # 默认年化波动率 20%

    def calculate_positions(
        self,
        symbols: List[str],
        total_capital: float,
        prices: Dict[str, float],
        volatilities: Optional[Dict[str, float]] = None,
        **kwargs
    ) -> Dict[str, int]:
        """
        风险平价分配

        Args:
            symbols: 目标股票列表
            total_capital: 总资金
            prices: 各股票价格
            volatilities: 各股票波动率 {symbol: volatility}

        Returns:
            {symbol: 股数}
        """
        if not symbols:
            return {}

        # 使用默认波动率
        if volatilities is None:
            volatilities = {}

        # 获取波动率数组
        vols = np.array([
            volatilities.get(s, self.default_volatility)
            for s in symbols
        ])

        # 避免除零
        vols = np.maximum(vols, 1e-6)

        # 风险平价权重 = 1/波动率
        inverse_vols = 1.0 / vols
        weights = inverse_vols / inverse_vols.sum()

        # 计算仓位
        positions = {}
        self.allocations = {}

        for symbol, weight in zip(symbols, weights):
            price = prices.get(symbol, 0)
            if price <= 0:
                continue

            volatility = volatilities.get(symbol, self.default_volatility)
            position_value = total_capital * weight
            volume = int(position_value / price / 100) * 100

            if volume > 0 and self.validate_position(symbol, volume, price):
                positions[symbol] = volume
                self.allocations[symbol] = PositionAllocation(
                    symbol=symbol,
                    target_volume=volume,
                    target_value=volume * price,
                    weight=weight,
                    reason=f"风险平价分配(波动率:{volatility:.2%})"
                )

        return positions

    def set_default_volatility(self, volatility: float) -> None:
        """
        设置默认波动率

        Args:
            volatility: 年化波动率
        """
        self.default_volatility = volatility

    def get_volatility(self, symbol: str) -> float:
        """
        获取指定股票的波动率

        Args:
            symbol: 股票代码

        Returns:
            波动率
        """
        return self.default_volatility
