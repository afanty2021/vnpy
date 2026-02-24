"""
仓位管理器基类接口

定义仓位管理的抽象基类，提供仓位计算的统一接口和验证方法。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from vnpy.trader.object import TickData
from ..objects.types import PositionAllocation


class PositionSizer(ABC):
    """
    仓位管理器抽象基类

    负责根据策略信号和资金情况，计算各股票的目标仓位。
    所有具体的仓位管理算法都应继承此类。
    """

    def __init__(self) -> None:
        """构造函数"""
        self.allocations: Dict[str, PositionAllocation] = {}

    @abstractmethod
    def calculate_positions(
        self,
        symbols: List[str],
        total_capital: float,
        prices: Dict[str, float],
        **kwargs: Any
    ) -> Dict[str, int]:
        """
        计算各股票的目标仓位

        Args:
            symbols: 股票代码列表
            total_capital: 总资金
            prices: 各股票当前价格 {symbol: price}
            **kwargs: 其他参数

        Returns:
            {symbol: 股数} 的字典

        Raises:
            ValueError: 参数无效时
        """
        pass

    def validate_position(
        self,
        symbol: str,
        volume: int,
        price: float
    ) -> bool:
        """
        验证仓位是否合法

        Args:
            symbol: 股票代码
            volume: 股数
            price: 价格

        Returns:
            是否合法
        """
        # A股交易单位检查
        if volume % 100 != 0:
            return False
        if volume <= 0:
            return False
        if price <= 0:
            return False
        return True

    def get_allocation_summary(self) -> Dict[str, Any]:
        """获取仓位分配摘要"""
        return {
            "total_positions": len(self.allocations),
            "allocations": self.allocations
        }
