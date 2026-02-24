"""
滑点模型

支持多种滑点计算方式：
- 固定滑点
- 百分比滑点
- 冲击成本滑点
- 自适应滑点
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from vnpy.trader.constant import Direction


@dataclass
class SlippageConfig:
    """滑点配置"""
    model_type: str = "percent"      # 模型类型
    fixed_value: float = 0.01         # 固定滑点值
    percent_value: float = 0.001       # 百分比滑点 (0.1%)
    impact_factor: float = 0.1         # 冲击成本因子
    volume_share_factor: float = 0.5  # 成交量占比因子


class SlippageModel(ABC):
    """滑点模型基类"""

    @abstractmethod
    def apply(
        self,
        price: float,
        volume: int,
        direction: Direction,
        market_volume: int = 0,
        **kwargs
    ) -> float:
        """应用滑点，返回调整后的价格

        Args:
            price: 原始价格
            volume: 委托数量
            direction: 交易方向
            market_volume: 市场成交量（用于冲击成本计算）
            **kwargs: 其他参数（如波动率等）

        Returns:
            float: 调整后的价格
        """
        pass


class FixedSlippage(SlippageModel):
    """固定滑点

    买入时价格上涨，卖出时价格下跌
    """

    def __init__(self, slippage: float = 0.01):
        """
        Args:
            slippage: 固定滑点金额 (默认1分)
        """
        self.slippage = slippage

    def apply(
        self,
        price: float,
        volume: int,
        direction: Direction,
        market_volume: int = 0,
        **kwargs
    ) -> float:
        if direction == Direction.LONG:
            return price + self.slippage
        return price - self.slippage


class PercentSlippage(SlippageModel):
    """百分比滑点

    按价格百分比计算滑点
    """

    def __init__(self, percent: float = 0.001):
        """
        Args:
            percent: 滑点百分比 (默认0.1%)
        """
        self.percent = percent

    def apply(
        self,
        price: float,
        volume: int,
        direction: Direction,
        market_volume: int = 0,
        **kwargs
    ) -> float:
        slippage = price * self.percent
        if direction == Direction.LONG:
            return price + slippage
        return price - slippage


class ImpactCostSlippage(SlippageModel):
    """冲击成本滑点

    滑点与成交量成正比，大单冲击成本更高
    """

    def __init__(self, impact_factor: float = 0.1):
        """
        Args:
            impact_factor: 冲击因子 (默认0.1)
        """
        self.impact_factor = impact_factor

    def apply(
        self,
        price: float,
        volume: int,
        direction: Direction,
        market_volume: int = 0,
        **kwargs
    ) -> float:
        if market_volume <= 0:
            # 无市场成交量时使用默认滑点
            slippage = price * 0.0005
        else:
            # 成交量占比 * 冲击因子 * 价格
            volume_ratio = min(1.0, volume / market_volume)
            slippage = price * self.impact_factor * volume_ratio * 0.1

        if direction == Direction.LONG:
            return price + slippage
        return price - slippage


class AdaptiveSlippage(SlippageModel):
    """自适应滑点

    根据市场状态和波动率动态调整滑点
    """

    def __init__(
        self,
        base_percent: float = 0.001,
        volatility_factor: float = 1.5,
        liquidity_factor: float = 0.5
    ):
        self.base_percent = base_percent
        self.volatility_factor = volatility_factor
        self.liquidity_factor = liquidity_factor

    def apply(
        self,
        price: float,
        volume: int,
        direction: Direction,
        market_volume: int = 0,
        volatility: float = 0.0,
        **kwargs
    ) -> float:
        # 基础滑点
        slippage = price * self.base_percent

        # 波动率调整
        if volatility > 0:
            slippage *= (1 + volatility * self.volatility_factor)

        # 流动性调整
        if market_volume > 0:
            volume_ratio = volume / market_volume
            slippage *= (1 + volume_ratio * self.liquidity_factor)

        if direction == Direction.LONG:
            return price + slippage
        return price - slippage


class SlippageModelFactory:
    """滑点模型工厂"""

    _models = {
        "fixed": FixedSlippage,
        "percent": PercentSlippage,
        "impact": ImpactCostSlippage,
        "adaptive": AdaptiveSlippage,
    }

    @classmethod
    def create(cls, model_type: str, **kwargs) -> SlippageModel:
        """创建滑点模型

        Args:
            model_type: 模型类型 ("fixed", "percent", "impact", "adaptive")
            **kwargs: 模型参数

        Returns:
            SlippageModel: 滑点模型实例
        """
        model_class = cls._models.get(model_type, PercentSlippage)
        return model_class(**kwargs)

    @classmethod
    def register(cls, name: str, model_class: type) -> None:
        """注册自定义滑点模型

        Args:
            name: 模型名称
            model_class: 模型类
        """
        cls._models[name] = model_class
