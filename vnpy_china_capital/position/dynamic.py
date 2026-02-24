"""
动态仓位管理器

根据市场状况（如波动率、趋势强度）动态调整仓位大小。
市场环境好时高仓位，环境差时低仓位。
"""

from typing import Dict, List, Optional
from .base import PositionSizer
from .equal_weight import EqualWeightPosition
from ..objects.types import PositionAllocation


class DynamicPosition(PositionSizer):
    """
    动态仓位管理器

    根据市场状况（如波动率、趋势强度）动态调整仓位大小。
    市场环境好时高仓位，环境差时低仓位。
    """

    def __init__(
        self,
        base_position: float = 0.8,
        min_position: float = 0.3,
        max_position: float = 1.0,
        max_position_count: int = 10
    ) -> None:
        """
        Args:
            base_position: 基础仓位比例
            min_position: 最小仓位比例
            max_position: 最大仓位比例
            max_position_count: 最大持仓数量
        """
        super().__init__()
        self.base_position = base_position
        self.min_position = min_position
        self.max_position = max_position
        self.max_position_count = max_position_count
        self.current_ratio = base_position

        # 内部使用等权重分配器
        self._equal_weight_sizer = EqualWeightPosition(max_position=max_position_count)

    def calculate_dynamic_ratio(
        self,
        market_volatility: float,
        trend_strength: Optional[float] = None
    ) -> float:
        """
        根据市场波动率计算动态仓位比例

        Args:
            market_volatility: 市场波动率
            trend_strength: 趋势强度 (0-1)，越高表示趋势越强

        Returns:
            仓位比例
        """
        # 波动率因子：波动率越低，仓位越高
        volatility_factor = self.base_position / (1 + market_volatility * 10)

        # 趋势因子：趋势越强，仓位越高
        if trend_strength is not None:
            # 调整趋势因子影响范围，确保更明显的差异
            trend_factor = 0.8 + trend_strength * 0.4  # 0.8 to 1.2
            ratio = volatility_factor * trend_factor
        else:
            ratio = volatility_factor

        # 限制在范围内
        ratio = max(self.min_position, min(self.max_position, ratio))
        self.current_ratio = ratio
        return ratio

    def calculate_positions(
        self,
        symbols: List[str],
        total_capital: float,
        prices: Dict[str, float],
        market_volatility: Optional[float] = None,
        trend_strength: Optional[float] = None,
        volatilities: Optional[Dict[str, float]] = None,
        **kwargs
    ) -> Dict[str, int]:
        """
        动态仓位分配

        Args:
            symbols: 目标股票列表
            total_capital: 总资金
            prices: 各股票价格
            market_volatility: 市场波动率
            trend_strength: 趋势强度
            volatilities: 各股票波动率（用于风险平价内部计算）

        Returns:
            {symbol: 股数}
        """
        if not symbols:
            return {}

        # 计算动态仓位比例
        if market_volatility is not None:
            ratio = self.calculate_dynamic_ratio(market_volatility, trend_strength)
        else:
            ratio = self.base_position
            self.current_ratio = ratio

        # 实际可用资金
        available_capital = total_capital * ratio

        # 使用等权重方法分配仓位
        positions = self._equal_weight_sizer.calculate_positions(
            symbols, available_capital, prices, **kwargs
        )

        # 更新 allocations，记录动态比例信息
        self.allocations = {}
        for symbol, volume in positions.items():
            price = prices.get(symbol, 0)
            if price > 0:
                weight = (volume * price) / available_capital if available_capital > 0 else 0
                self.allocations[symbol] = PositionAllocation(
                    symbol=symbol,
                    target_volume=volume,
                    target_value=volume * price,
                    weight=weight,
                    reason=f"动态仓位分配(比例:{ratio:.1%}, 市场波动率:{market_volatility})"
                )

        return positions

    def get_current_ratio(self) -> float:
        """
        获取当前仓位比例

        Returns:
            当前仓位比例
        """
        return self.current_ratio

    def reset_ratio(self) -> None:
        """重置仓位比例到默认值"""
        self.current_ratio = self.base_position
