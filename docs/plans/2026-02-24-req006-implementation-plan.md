# REQ-006 增强回测系统实施方案

> 文档版本：v1.0
> 创建日期：2026-02-24
> 需求编号：REQ-006
> 优先级：P1
> 状态：待实施

---

## 1. 模块概述

### 1.1 模块定位

`vnpy_china_backtest` 是A股增强回测模块，在VeighNa现有回测系统基础上增加A股特色交易模拟功能：

1. **交易成本模拟**：佣金、印花税、过户费、经手费
2. **滑点模拟**：固定、百分比、冲击成本
3. **涨跌停处理**：涨停无法买入、跌停无法卖出
4. **T+1规则模拟**：当日买入次日才能卖出
5. **回测报告增强**：A股特有指标

### 1.2 模块位置

```
vnpy_china_backtest/
├── __init__.py                    # 模块入口
├── CLAUDE.md                     # 模块文档
├── engine.py                     # 增强回测引擎
├── cost.py                      # 交易成本计算
├── slippage.py                   # 滑点模型
├── rules/                        # 交易规则模拟
│   ├── __init__.py
│   ├── price_limit.py           # 涨跌停处理
│   ├── t1_simulator.py         # T+1模拟
│   └── trade_limit.py           # 交易限制
├── report/                       # 回测报告
│   ├── __init__.py
│   ├── generator.py             # 报告生成器
│   ├── metrics.py               # 指标计算
│   └── analyzer.py              # 归因分析
├── config.py                    # 配置管理
└── tests/                       # 测试
    ├── __init__.py
    ├── test_cost.py
    ├── test_slippage.py
    ├── test_rules.py
    └── test_report.py
```

---

## 2. 核心组件设计

### 2.1 交易成本计算器

**文件**: `vnpy_china_backtest/cost.py`

```python
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
from decimal import Decimal
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
    stamp_duty: float         # 印花税
    transfer_fee: float        # 过户费
    handling_fee: float       # 经手费
    total: float              # 总成本
    cost_rate: float          # 成本费率


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

    def __init__(self, config: CostConfig = None):
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

        # 3. 过户费（双向收取）
        transfer_fee = turnover * self.config.transfer_fee_rate
        # 过户费有最低值
        transfer_fee = max(transfer_fee, 0.1)  # 最低0.1元

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
        """计算买入成本"""
        cost = self.calculate(price, volume, Direction.LONG, exchange)
        return cost.total

    def calculate_sell_cost(self, price: float, volume: int, exchange: Exchange = Exchange.SZSE) -> float:
        """计算卖出成本"""
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
```

### 2.2 滑点模型

**文件**: `vnpy_china_backtest/slippage.py`

```python
"""
滑点模型

支持多种滑点计算方式：
- 固定滑点
- 百分比滑点
- 冲击成本滑点
- 成交量占比滑点
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from vnpy.trader.constant import Direction
import math


@dataclass
class SlippageConfig:
    """滑点配置"""
    model_type: str = "percent"      # 模型类型
    fixed_value: float = 0.01         # 固定滑点值
    percent_value: float = 0.001      # 百分比滑点 (0.1%)
    impact_factor: float = 0.1        # 冲击成本因子
    volume_share_factor: float = 0.5  # 成交量占比因子


class SlippageModel(ABC):
    """滑点模型基类"""

    @abstractmethod
    def apply(
        self,
        price: float,
        volume: int,
        direction: Direction,
        market_volume: int = 0
    ) -> float:
        """应用滑点，返回调整后的价格

        Args:
            price: 原始价格
            volume: 委托数量
            direction: 交易方向
            market_volume: 市场成交量（用于冲击成本计算）

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

    def apply(self, price: float, volume: int, direction: Direction, market_volume: int = 0) -> float:
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

    def apply(self, price: float, volume: int, direction: Direction, market_volume: int = 0) -> float:
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

    def apply(self, price: float, volume: int, direction: Direction, market_volume: int = 0) -> float:
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
        volatility: float = 0.0
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
```

### 2.3 涨跌停处理器

**文件**: `vnpy_china_backtest/rules/price_limit.py`

```python
"""
涨跌停处理

功能：
1. 计算涨跌停价格
2. 判断是否涨停/跌停
3. 处理涨停无法买入、跌停无法卖出
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional, Tuple
from vnpy.trader.constant import Exchange, Product


@dataclass
class LimitPrices:
    """涨跌停价格"""
    symbol: str
    trade_date: date
    prev_close: float          # 昨日收盘价
    limit_up: float            # 涨停价
    limit_down: float          # 跌停价
    is_limit_up: bool = False  # 是否涨停
    is_limit_down: bool = False  # 是否跌停


@dataclass
class OrderCheckResult:
    """订单检查结果"""
    can_execute: bool           # 是否可执行
    reason: str                 # 原因
    adjusted_price: float       # 调整后的价格
    fill_ratio: float = 1.0   # 成交比例


class PriceLimitEngine:
    """涨跌停引擎"""

    # 涨跌停比例配置
    LIMIT_RATIOS = {
        "main": 0.10,      # 主板: 10%
        "chinext": 0.20,  # 创业板: 20%
        "star": 0.20,     # 科创板: 20%
        "bse": 0.30,     # 北交所: 30%
        "st": 0.05,       # ST: 5%
    }

    def __init__(self, data_service=None):
        self.data_service = data_service
        self._limit_cache = {}  # 缓存涨跌停价格

    def get_limit_prices(
        self,
        symbol: str,
        trade_date: date,
        prev_close: float
    ) -> LimitPrices:
        """获取涨跌停价格

        Args:
            symbol: 股票代码
            trade_date: 交易日期
            prev_close: 昨日收盘价

        Returns:
            LimitPrices: 涨跌停价格
        """
        # 判断股票类型
        market_type = self._get_market_type(symbol)

        # 获取涨跌停比例
        ratio = self.LIMIT_RATIOS.get(market_type, 0.10)

        # 计算涨跌停价
        limit_up = round(prev_close * (1 + ratio), 2)
        limit_down = round(prev_close * (1 - ratio), 2)

        # 判断是否涨停/跌停（当日涨跌幅达到限制）
        # 需要结合当日开盘价判断，这里简化处理
        is_limit_up = False
        is_limit_down = False

        return LimitPrices(
            symbol=symbol,
            trade_date=trade_date,
            prev_close=prev_close,
            limit_up=limit_up,
            limit_down=limit_down,
            is_limit_up=is_limit_up,
            is_limit_down=is_limit_down
        )

    def check_order(
        self,
        symbol: str,
        direction: Direction,
        price: float,
        volume: int,
        limit_prices: LimitPrices,
        allow_limit_up: bool = False,
        allow_limit_down: bool = False
    ) -> OrderCheckResult:
        """检查订单是否可执行

        Args:
            symbol: 股票代码
            direction: 交易方向
            price: 委托价格
            volume: 委托数量
            limit_prices: 涨跌停价格
            allow_limit_up: 是否允许涨停买入
            allow_limit_down: 是否允许跌停卖出

        Returns:
            OrderCheckResult: 检查结果
        """
        # 涨停时无法买入
        if direction == Direction.LONG:
            if limit_prices.is_limit_up and not allow_limit_up:
                return OrderCheckResult(
                    can_execute=False,
                    reason=f"涨停板无法买入",
                    adjusted_price=limit_prices.limit_up,
                    fill_ratio=0.0
                )

            # 买入价格不能超过涨停价
            if price > limit_prices.limit_up:
                return OrderCheckResult(
                    can_execute=False,
                    reason=f"买入价格{price}超过涨停价{limit_prices.limit_up}",
                    adjusted_price=limit_prices.limit_up,
                    fill_ratio=0.0
                )

        # 跌停时无法卖出
        else:
            if limit_prices.is_limit_down and not allow_limit_down:
                return OrderCheckResult(
                    can_execute=False,
                    reason=f"跌停板无法卖出",
                    adjusted_price=limit_prices.limit_down,
                    fill_ratio=0.0
                )

            # 卖出价格不能低于跌停价
            if price < limit_prices.limit_down:
                return OrderCheckResult(
                    can_execute=False,
                    reason=f"卖出价格{price}低于跌停价{limit_prices.limit_down}",
                    adjusted_price=limit_prices.limit_down,
                    fill_ratio=0.0
                )

        return OrderCheckResult(
            can_execute=True,
            reason="可执行",
            adjusted_price=price,
            fill_ratio=1.0
        )

    def _get_market_type(self, symbol: str) -> str:
        """判断市场类型"""
        if symbol.startswith("ST") or "ST" in symbol:
            return "st"
        elif symbol.startswith("688"):
            return "star"
        elif symbol.startswith("8") or symbol.startswith("4"):
            return "bse"
        elif symbol.startswith("300"):
            return "chinext"
        else:
            return "main"


class PriceLimitHandler:
    """涨跌停处理器（简化版）"""

    def __init__(self, price_limit_engine: PriceLimitEngine = None):
        self.engine = price_limit_engine or PriceLimitEngine()

    def process_order(
        self,
        symbol: str,
        direction: Direction,
        price: float,
        volume: int,
        trade_date: date,
        prev_close: float
    ) -> Tuple[bool, str, float, int]:
        """处理订单

        Returns:
            (是否成交, 原因, 成交价格, 成交数量)
        """
        limit_prices = self.engine.get_limit_prices(symbol, trade_date, prev_close)
        result = self.engine.check_order(symbol, direction, price, volume, limit_prices)

        if not result.can_execute:
            return False, result.reason, price, 0

        # 部分成交处理（简化：全部成交或全部不成交）
        return True, "成交", result.adjusted_price, int(volume * result.fill_ratio)
```

### 2.4 T+1模拟器

**文件**: `vnpy_china_backtest/rules/t1_simulator.py`

```python
"""
T+1规则模拟器

A股T+1规则：
- 当日买入的股票，次日才能卖出
- 当日卖出股票的资金，可以立即使用
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional


@dataclass
class BuyRecord:
    """买入记录"""
    symbol: str
    volume: int                  # 买入数量
    price: float                # 买入价格
    buy_date: date              # 买入日期
    sold_volume: int = 0       # 已卖出数量


@dataclass
class PositionRecord:
    """持仓记录"""
    symbol: str
    volume: int                 # 总持仓
    available: int              # 可卖出数量
    frozen: int                 # 冻结数量（当日买入）
    avg_price: float           # 平均成本


class T1Simulator:
    """T+1规则模拟器"""

    def __init__(self):
        # 买入记录: {symbol: [BuyRecord, ...]}
        self._buy_records: Dict[str, List[BuyRecord]] = {}

        # 当前持仓: {symbol: PositionRecord}
        self._positions: Dict[str, PositionRecord] = {}

    def record_buy(
        self,
        symbol: str,
        volume: int,
        price: float,
        trade_date: date
    ) -> None:
        """记录买入

        Args:
            symbol: 股票代码
            volume: 买入数量
            price: 买入价格
            trade_date: 交易日期
        """
        # 记录买入
        if symbol not in self._buy_records:
            self._buy_records[symbol] = []

        self._buy_records[symbol].append(BuyRecord(
            symbol=symbol,
            volume=volume,
            price=price,
            buy_date=trade_date
        ))

        # 更新持仓
        self._update_position(symbol, volume, price, is_buy=True)

    def record_sell(
        self,
        symbol: str,
        volume: int,
        price: float,
        trade_date: date
    ) -> Tuple[bool, str, int]:
        """记录卖出

        Args:
            symbol: 股票代码
            volume: 卖出数量
            price: 卖出价格
            trade_date: 交易日期

        Returns:
            (是否成功, 原因, 实际卖出数量)
        """
        # 检查可卖出数量
        sellable = self.get_sellable_volume(symbol, trade_date)

        if sellable == 0:
            return False, f"T+1限制：{symbol}当前无可卖出股票", 0

        if volume > sellable:
            # 尝试卖出超过可卖出数量的部分
            return False, f"卖出数量{volume}超过可卖出数量{sellable}", 0

        # 记录卖出（使用FIFO原则）
        self._process_sell(symbol, volume, trade_date)

        # 更新持仓
        self._update_position(symbol, volume, price, is_buy=False)

        return True, "卖出成功", volume

    def get_sellable_volume(self, symbol: str, trade_date: date) -> int:
        """获取可卖出数量

        Args:
            symbol: 股票代码
            trade_date: 当前日期

        Returns:
            int: 可卖出数量（T+1：当日之前买入的股票）
        """
        if symbol not in self._buy_records:
            return 0

        total_available = 0
        for record in self._buy_records[symbol]:
            # T+1: 必须是前一天及之前买入的
            if record.buy_date < trade_date:
                available = record.volume - record.sold_volume
                total_available += available

        return total_available

    def get_position(self, symbol: str) -> Optional[PositionRecord]:
        """获取持仓"""
        return self._positions.get(symbol)

    def get_all_positions(self) -> Dict[str, PositionRecord]:
        """获取所有持仓"""
        return self._positions.copy()

    def get_total_position_value(self, current_prices: Dict[str, float]) -> float:
        """计算总持仓市值"""
        total = 0.0
        for symbol, pos in self._positions.items():
            if pos.volume > 0 and symbol in current_prices:
                total += pos.volume * current_prices[symbol]
        return total

    def _process_sell(self, symbol: str, volume: int, trade_date: date) -> None:
        """处理卖出（FIFO原则）"""
        if symbol not in self._buy_records:
            return

        remaining = volume
        for record in self._buy_records[symbol]:
            if remaining <= 0:
                break

            # 必须是T+1的持仓
            if record.buy_date >= trade_date:
                continue

            available = record.volume - record.sold_volume
            if available > 0:
                sold = min(remaining, available)
                record.sold_volume += sold
                remaining -= sold

    def _update_position(
        self,
        symbol: str,
        volume: int,
        price: float,
        is_buy: bool
    ) -> None:
        """更新持仓"""
        if symbol not in self._positions:
            self._positions[symbol] = PositionRecord(
                symbol=symbol,
                volume=0,
                available=0,
                frozen=0,
                avg_price=0.0
            )

        pos = self._positions[symbol]

        if is_buy:
            # 买入：增加持仓
            old_volume = pos.volume
            pos.volume += volume
            # 新买入的股票冻结（T+1）
            pos.frozen += volume
            # 更新平均成本
            if old_volume > 0:
                pos.avg_price = (pos.avg_price * old_volume + price * volume) / pos.volume
            else:
                pos.avg_price = price
        else:
            # 卖出：减少持仓
            pos.volume -= volume
            # 解冻相应数量
            pos.frozen = max(0, pos.volume - self.get_sellable_volume(symbol, date.today()))

            if pos.volume == 0:
                pos.avg_price = 0.0

        # 更新可用数量
        pos.available = pos.volume - pos.frozen

    def reset(self) -> None:
        """重置模拟器"""
        self._buy_records.clear()
        self._positions.clear()
```

### 2.5 增强回测引擎

**文件**: `vnpy_china_backtest/engine.py`

```python
"""
增强回测引擎

整合交易成本、滑点、涨跌停、T+1规则
"""

from vnpy.backtesting import BacktestingEngine
from vnpy.trader.object import OrderData, TradeData
from vnpy_china_backtest.cost import CostCalculator, CostConfig
from vnpy_china_backtest.slippage import SlippageModel, SlippageModelFactory
from vnpy_china_backtest.rules.price_limit import PriceLimitHandler
from vnpy_china_backtest.rules.t1_simulator import T1Simulator


class EnhancedBacktestEngine(BacktestingEngine):
    """增强回测引擎"""

    def __init__(self):
        super().__init__()

        # 交易成本计算器
        self.cost_calculator = CostCalculator()

        # 滑点模型
        self.slippage_model = None

        # 涨跌停处理器
        self.price_limit_handler = PriceLimitHandler()

        # T+1模拟器
        self.t1_simulator = T1Simulator()

        # 配置
        self.enable_cost = True           # 启用交易成本
        self.enable_slippage = True      # 启用滑点
        self.enable_price_limit = True    # 启用涨跌停
        self.enable_t1 = True            # 启用T+1

        # 统计
        self.total_cost = 0.0
        self.blocked_orders = 0          # 被阻止的订单数

    def set_cost_config(self, config: CostConfig):
        """设置成本配置"""
        self.cost_calculator = CostCalculator(config)

    def set_slippage(self, model_type: str = "percent", **kwargs):
        """设置滑点模型"""
        self.slippage_model = SlippageModelFactory.create(model_type, **kwargs)

    def process_order(self, order: OrderData) -> bool:
        """处理订单

        Returns:
            bool: 订单是否成交
        """
        if not self.enable_price_limit:
            return super().process_order(order)

        # 涨跌停检查
        limit_prices = self._get_limit_prices(order.symbol, order.datetime.date())
        check_result = self.price_limit_handler.engine.check_order(
            order.symbol,
            order.direction,
            order.price,
            order.volume,
            limit_prices
        )

        if not check_result.can_execute:
            self.blocked_orders += 1
            self.write_log(f"订单被阻止: {check_result.reason}")
            return False

        # T+1检查（卖出时）
        if order.direction == Direction.SHORT and self.enable_t1:
            sellable = self.t1_simulator.get_sellable_volume(
                order.symbol,
                order.datetime.date()
            )
            if order.volume > sellable:
                self.blocked_orders += 1
                self.write_log(f"T+1限制：卖出数量{order.volume}超过可卖出{sellable}")
                return False

        # 应用滑点
        price = order.price
        if self.enable_slippage and self.slippage_model:
            price = self.slippage_model.apply(
                price,
                order.volume,
                order.direction,
                market_volume=self._get_market_volume(order.symbol)
            )

        # 成交
        order.status = Status.ALLTRADED
        order.traded = order.volume
        self.orders[order.vt_orderid] = order

        # 生成成交数据
        trade = TradeData(...)
        self.trades[trade.vt_tradeid] = trade

        # 扣除交易成本
        if self.enable_cost:
            cost = self.cost_calculator.calculate(
                price,
                order.volume,
                order.direction
            )
            self.total_cost += cost.total
            self.account.balance -= cost.total

        # 更新T+1记录
        if self.enable_t1:
            if order.direction == Direction.LONG:
                self.t1_simulator.record_buy(
                    order.symbol,
                    order.volume,
                    price,
                    order.datetime.date()
                )
            else:
                self.t1_simulator.record_sell(
                    order.symbol,
                    order.volume,
                    price,
                    order.datetime.date()
                )

        return True
```

---

## 3. 回测报告增强

### 3.1 指标计算

**文件**: `vnpy_china_backtest/report/metrics.py`

```python
"""
A股特有指标计算
"""

from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime


@dataclass
class EnhancedMetrics:
    """增强回测指标"""

    # 基础收益指标
    total_return: float           # 总收益率
    annual_return: float          # 年化收益率
    max_drawdown: float           # 最大回撤
    sharpe_ratio: float           # 夏普比率
    sortino_ratio: float          # 索提诺比率
    calmar_ratio: float            # 卡玛比率

    # A股特有指标
    win_rate: float               # 胜率
    profit_loss_ratio: float      # 盈亏比
    avg_holding_days: float       # 平均持股天数
    avg_positions: float          # 平均持仓数
    avg_capital_usage: float      # 平均资金使用率
    max_positions: int            # 最大持仓数

    # 交易统计
    total_trades: int             # 总交易次数
    buy_trades: int               # 买入次数
    sell_trades: int              # 卖出次数
    max_consecutive_wins: int     # 最大连续盈利
    max_consecutive_losses: int   # 最大连续亏损

    # 成本统计
    total_cost: float             # 总交易成本
    cost_rate: float              # 成本费率
    avg_cost_per_trade: float     # 笔均成本

    # 月度收益
    monthly_returns: Dict[str, float]  # 月度收益


class MetricsCalculator:
    """指标计算器"""

    def calculate(
        self,
        trades: List[TradeData],
        history: List[AccountData],
        initial_capital: float
    ) -> EnhancedMetrics:
        """计算所有指标"""
        # 基础指标
        metrics = self._calculate_basic_metrics(history, initial_capital)

        # A股特有指标
        metrics.win_rate = self._calculate_win_rate(trades)
        metrics.profit_loss_ratio = self._calculate_profit_loss_ratio(trades)
        metrics.avg_holding_days = self._calculate_avg_holding_days(trades)
        metrics.avg_positions = self._calculate_avg_positions(history)
        metrics.max_positions = self._calculate_max_positions(history)
        metrics.avg_capital_usage = self._calculate_avg_capital_usage(history, initial_capital)

        # 交易统计
        metrics.total_trades = len(trades)
        metrics.buy_trades = len([t for t in trades if t.direction == Direction.LONG])
        metrics.sell_trades = len([t for t in trades if t.direction == Direction.SHORT])
        metrics.max_consecutive_wins = self._calculate_max_consecutive(trades, is_win=True)
        metrics.max_consecutive_losses = self._calculate_max_consecutive(trades, is_win=False)

        return metrics

    def _calculate_win_rate(self, trades: List[TradeData]) -> float:
        """计算胜率"""
        if not trades:
            return 0.0

        # 按股票分组计算盈亏
        stock_pnl = {}
        for trade in trades:
            if trade.symbol not in stock_pnl:
                stock_pnl[trade.symbol] = 0.0
            # 简化计算
            if trade.direction == Direction.SHORT:
                stock_pnl[trade.symbol] += trade.volume * trade.price

        wins = sum(1 for pnl in stock_pnl.values() if pnl > 0)
        return wins / len(stock_pnl) if stock_pnl else 0.0
```

---

## 4. 开发计划

### 4.1 开发阶段

| 阶段 | 任务 | 工时 | 依赖 |
|-----|------|-----|------|
| **Phase 1** | 基础框架搭建 | 1天 | - |
| | - 目录结构创建 | 0.25天 | - |
| | - 交易成本计算器 | 0.5天 | - |
| | - 滑点模型基类 | 0.25天 | - |
| **Phase 2** | 交易规则模拟 | 2天 | Phase 1 |
| | - 涨跌停处理器 | 0.75天 | - |
| | - T+1模拟器 | 0.75天 | - |
| | - 交易限制规则 | 0.5天 | - |
| **Phase 3** | 增强回测引擎 | 1.5天 | Phase 1, 2 |
| | - EnhancedBacktestEngine | 1天 | - |
| | - 与现有回测系统集成 | 0.5天 | - |
| **Phase 4** | 报告增强 | 1天 | Phase 3 |
| | - 指标计算器 | 0.5天 | - |
| | - 报告生成器 | 0.5天 | - |
| **Phase 5** | 测试与文档 | 1天 | All |
| | - 单元测试 | 0.75天 | - |
| | - 集成测试 | 0.25天 | - |

### 4.2 总工时估算

| 阶段 | 工时 |
|-----|------|
| Phase 1 | 1天 |
| Phase 2 | 2天 |
| Phase 3 | 1.5天 |
| Phase 4 | 1天 |
| Phase 5 | 1天 |
| **总计** | **6.5天** |

---

## 5. 使用示例

### 5.1 基本使用

```python
from vnpy_china_backtest import EnhancedBacktestEngine
from vnpy_china_backtestConfig
from vn.cost import Costpy_china_backtest.slippage import PercentSlippage

# 创建增强回测引擎
engine = EnhancedBacktestEngine()

# 配置交易成本
cost_config = CostConfig(
    commission_rate=0.0003,
    min_commission=5.0,
    stamp_duty_rate=0.001,
)
engine.set_cost_config(cost_config)

# 配置滑点
engine.set_slippage("percent", percent=0.001)

# 启用各项功能
engine.enable_cost = True
engine.enable_slippage = True
engine.enable_price_limit = True
engine.enable_t1 = True

# 运行回测
engine.set_parameters(
    vt_symbol="000001.SZSE",
    interval="1d",
    start_date="2020-01-01",
    end_date="2023-12-31",
    capital=1000000,
)

# 加载策略
engine.add_strategy(MyStrategy)

# 运行
engine.run_backtesting()

# 获取结果
result = engine.get_result()
print(result)
```

### 5.2 自定义配置

```python
# 激进型配置（高滑点、高成本）
engine.set_slippage("impact", impact_factor=0.2)

# 保守型配置（低滑点、低成本）
engine.set_slippage("fixed", slippage=0.005)
cost_config = CostConfig(commission_rate=0.0001, min_commission=0)

# 禁用部分功能
engine.enable_price_limit = False  # 不模拟涨跌停
engine.enable_t1 = False          # 不模拟T+1
```

---

## 6. 测试策略

### 6.1 单元测试

| 测试类 | 测试内容 |
|-------|---------|
| TestCostCalculator | 交易成本计算（佣金、印花税、过户费） |
| TestSlippageModel | 滑点计算（固定、百分比、冲击成本） |
| TestPriceLimitHandler | 涨跌停判断和订单处理 |
| TestT1Simulator | T+1持仓计算和卖出限制 |
| TestMetricsCalculator | 指标计算 |

### 6.2 集成测试

- 完整回测流程测试
- 与现有回测引擎对比测试
- 边界条件测试（涨跌停、T+1边界）

---

## 7. 已知依赖

### 7.1 内部依赖

| 模块 | 依赖内容 |
|-----|---------|
| vnpy.backtesting | BacktestingEngine |
| vnpy.trader.object | OrderData, TradeData, AccountData |
| vnpy.trader.constant | Direction, Exchange |

### 7.2 外部依赖

| 包 | 用途 | 版本 |
|---|------|-----|
| pandas | 数据处理 | >=1.5.0 |

---

*文档结束*
