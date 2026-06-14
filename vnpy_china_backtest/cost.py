"""
A股交易成本计算

费率标准（2024年）：
- 佣金: 万3 (不足5元按5元收取)
- 印花税: 千1 (仅卖出收取)
- 过户费: 万0.1 (双向收取)
- 经手费: 万0.0685 (双向收取)
- 证管费: 万0.2 (已包含在经手费中)
"""

from dataclasses import dataclass
from typing import Optional
from vnpy.trader.constant import Direction, Exchange


# A股交易费用常量
class AStockCost:
    """A股交易费用标准"""

    # 佣金
    COMMISSION_RATE = 0.0003        # 万3
    MIN_COMMISSION = 5.0           # 最低5元

    # 印花税 (仅卖出)
    STAMP_DUTY_RATE = 0.001        # 千1

    # 过户费 (双向)
    TRANSFER_FEE_RATE = 0.00001    # 万0.1

    # 经手费 (双向) - 包含证管费
    HANDLING_FEE_RATE = 0.0000685  # 万0.0685

    # 收费标准映射
    EXCHANGE_FEE_RATES = {
        Exchange.SZSE: {
            "transfer": 0.00001,
            "handling": 0.0000685,
        },
        Exchange.SSE: {
            "transfer": 0.00001,
            "handling": 0.0000685,
        },
    }


@dataclass
class TradingCost:
    """交易成本明细"""
    commission: float           # 佣金
    stamp_duty: float          # 印花税
    transfer_fee: float         # 过户费
    handling_fee: float        # 经手费
    total: float               # 总成本
    cost_rate: float           # 成本费率


@dataclass
class CostConfig:
    """成本配置"""
    commission_rate: float = AStockCost.COMMISSION_RATE
    min_commission: float = AStockCost.MIN_COMMISSION
    stamp_duty_rate: float = AStockCost.STAMP_DUTY_RATE
    transfer_fee_rate: float = AStockCost.TRANSFER_FEE_RATE
    handling_fee_rate: float = AStockCost.HANDLING_FEE_RATE


class CostCalculator:
    """交易成本计算器"""

    def __init__(self, config: Optional[CostConfig] = None):
        """
        初始化成本计算器

        Args:
            config: 成本配置，默认使用A股标准配置
        """
        self.config = config or CostConfig()

    def calculate(
        self,
        price: float,
        volume: int,
        direction: Direction,
        exchange: Exchange = Exchange.SZSE
    ) -> TradingCost:
        """计算交易成本

        Args:
            price: 成交价格
            volume: 成交数量
            direction: 交易方向 (LONG=买入, SHORT=卖出)
            exchange: 交易所

        Returns:
            TradingCost: 成本明细
        """
        turnover = price * volume  # 成交金额

        # 1. 佣金计算
        commission = turnover * self.config.commission_rate
        commission = max(commission, self.config.min_commission)

        # 2. 印花税（仅卖出收取）
        stamp_duty = 0.0
        if direction == Direction.SHORT:
            stamp_duty = turnover * self.config.stamp_duty_rate

        # 3. 过户费（双向收取，万0.1，2022年4月起沪深统一，无最低值）
        transfer_fee = turnover * self.config.transfer_fee_rate

        # 4. 经手费（双向收取）
        handling_fee = turnover * self.config.handling_fee_rate

        # 总成本
        total = commission + stamp_duty + transfer_fee + handling_fee
        cost_rate = total / turnover if turnover > 0 else 0

        return TradingCost(
            commission=round(commission, 2),
            stamp_duty=round(stamp_duty, 2),
            transfer_fee=round(transfer_fee, 4),
            handling_fee=round(handling_fee, 4),
            total=round(total, 2),
            cost_rate=round(cost_rate, 6)
        )

    def calculate_buy_cost(self, price: float, volume: int, exchange: Exchange = Exchange.SZSE) -> float:
        """计算买入成本

        Args:
            price: 成交价格
            volume: 成交数量
            exchange: 交易所

        Returns:
            float: 买入成本
        """
        cost = self.calculate(price, volume, Direction.LONG, exchange)
        return cost.total

    def calculate_sell_cost(self, price: float, volume: int, exchange: Exchange = Exchange.SZSE) -> float:
        """计算卖出成本

        Args:
            price: 成交价格
            volume: 成交数量
            exchange: 交易所

        Returns:
            float: 卖出成本
        """
        cost = self.calculate(price, volume, Direction.SHORT, exchange)
        return cost.total


class CostCalculatorFactory:
    """成本计算器工厂"""

    _calculators: dict = {}

    @classmethod
    def get_calculator(cls, market: str = "A") -> CostCalculator:
        """获取成本计算器

        Args:
            market: 市场类型 ("A", "B", "ETF"等)

        Returns:
            CostCalculator: 成本计算器实例
        """
        if market not in cls._calculators:
            config = cls._create_config(market)
            cls._calculators[market] = CostCalculator(config)
        return cls._calculators[market]

    @classmethod
    def _create_config(cls, market: str) -> CostConfig:
        """创建配置"""
        if market == "ETF":
            # ETF佣金更低，无印花税
            return CostConfig(
                commission_rate=0.0001,  # 万1
                min_commission=0,
                stamp_duty_rate=0,  # ETF无印花税
            )
        elif market == "B":
            # B股
            return CostConfig(
                commission_rate=0.001,  # 千1
                min_commission=1,
                stamp_duty_rate=0.001,
                transfer_fee_rate=0,
            )
        else:
            # A股默认
            return CostConfig()
