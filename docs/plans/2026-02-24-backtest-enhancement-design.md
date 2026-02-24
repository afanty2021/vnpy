# 增强回测系统设计文档

> 文档版本：v1.0
> 创建日期：2026-02-24
> 需求编号：REQ-006
> 优先级：P1
> 预计工时：6人天

---

## 1. 设计目标

增强VeighNa回测系统，实现A股特色交易模拟：

1. **交易成本模拟**：佣金、印花税、过户费、经手费
2. **滑点模拟**：固定、百分比、冲击成本
3. **涨跌停处理**：涨停无法买入、跌停无法卖出
4. **T+1规则模拟**：当日买入次日才能卖出
5. **回测报告增强**：A股特有指标

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      增强回测系统架构                              │
├─────────────────────────────────────────────────────────────────┤
│  【核心引擎】                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ BacktestEngine│  │ CostCalculator│  │ SlippageModel│          │
│  │   (回测引擎)  │  │  (成本计算)   │  │  (滑点模型)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│  【规则模拟】                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │PriceLimit    │  │   T1Sim      │  │  TradeLimit  │          │
│  │(涨跌停处理)  │  │  (T+1模拟)   │  │ (交易限制)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│  【报告增强】                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ReportGenerator│  │MetricsCalc   │  │  Analyzer   │          │
│  │ (报告生成)   │  │  (指标计算)   │  │  (归因分析)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块结构

```
vnpy_china_backtest/
├── __init__.py
├── engine.py                 # 增强回测引擎
├── cost.py                  # 交易成本计算
├── slippage.py              # 滑点模型
├── rules/
│   ├── __init__.py
│   ├── price_limit.py       # 涨跌停处理
│   ├── t1_simulator.py     # T+1模拟
│   └── trade_limit.py       # 交易限制
├── report/
│   ├── __init__.py
│   ├── generator.py        # 报告生成器
│   ├── metrics.py          # 指标计算
│   └── analyzer.py          # 归因分析
└── config.py               # 配置
```

---

## 3. 核心类设计

### 3.1 交易成本计算

```python
from dataclasses import dataclass
from vnpy.trader.constant import Direction


@dataclass
class TradingCost:
    """交易成本"""
    commission: float      # 佣金
    stamp_duty: float    # 印花税
    transfer_fee: float   # 过户费
    handling_fee: float   # 经手费
    total: float         # 总成本


class CostCalculator:
    """交易成本计算器"""

    def __init__(self):
        # 默认费率配置
        self.commission_rate = 0.0003    # 万3佣金
        self.min_commission = 5.0         # 最低5元
        self.stamp_duty = 0.001          # 印花税0.1%（仅卖出）
        self.transfer_fee = 0.00001      # 过户费0.001%
        self.handling_fee = 0.00000685   # 经手费0.000685%

    def calculate(
        self,
        price: float,
        volume: int,
        direction: Direction
    ) -> TradingCost:
        """计算交易成本"""

        # 1. 佣金计算
        turnover = price * volume  # 成交金额
        commission = turnover * self.commission_rate
        commission = max(commission, self.min_commission)

        # 2. 印花税（仅卖出收取）
        stamp_duty = 0.0
        if direction == Direction.SHORT:
            stamp_duty = turnover * self.stamp_duty

        # 3. 过户费（双向收取）
        transfer_fee = turnover * self.transfer_fee

        # 4. 经手费（双向收取）
        handling_fee = turnover * self.handling_fee

        total = commission + stamp_duty + transfer_fee + handling_fee

        return TradingCost(
            commission=commission,
            stamp_duty=stamp_duty,
            transfer_fee=transfer_fee,
            handling_fee=handling_fee,
            total=total
        )

    def calculate_rate(self, price: float, volume: int, direction: Direction) -> float:
        """计算成本费率"""
        cost = self.calculate(price, volume, direction)
        turnover = price * volume
        return cost.total / turnover if turnover > 0 else 0
```

### 3.2 滑点模型

```python
from abc import ABC, abstractmethod
import random


class SlippageModel(ABC):
    """滑点模型基类"""

    @abstractmethod
    def apply(
        self,
        price: float,
        volume: int,
        direction: Direction
    ) -> float:
        """应用滑点，返回调整后的价格"""
        pass


class FixedSlippage(SlippageModel):
    """固定滑点"""

    def __init__(self, slippage: float = 0.01):
        self.slippage = slippage

    def apply(self, price: float, volume: int, direction: Direction) -> float:
        if direction == Direction.LONG:
            return price + self.slippage
        return price - self.slippage


class PercentSlippage(SlippageModel):
    """百分比滑点"""

    def __init__(self, percent: float = 0.001):
        self.percent = percent

    def apply(self, price: float, volume: int, direction: Direction) -> float:
        slippage = price * self.percent
        if direction == Direction.LONG:
            return price + slippage
        return price - slippage


class ImpactCostSlippage(SlippageModel):
    """冲击成本滑点模型"""

    def __init__(self, impact_factor: float = 0.1):
        self.impact_factor = impact_factor

    def apply(self, price: float, volume: int, direction: Direction) -> float:
        # 冲击成本与成交量相关
        # 大订单冲击成本更高
        volume_factor = min(1.0, volume / 10000)  # 最多1万手
        slippage = price * self.impact_factor * volume_factor

        if direction == Direction.LONG:
            return price + slippage
        return price - slippage
```

### 3.3 涨跌停处理

```python
class PriceLimitHandler:
    """涨跌停处理器"""

    def __init__(self, price_limit_engine):
        self.price_limit_engine = price_limit_engine

    def check_order(
        self,
        symbol: str,
        direction: Direction,
        price: float,
        volume: int
    ) -> tuple[bool, str, float]:
        """
        检查订单是否可执行

        返回: (是否可执行, 原因, 调整后的价格)
        """
        # 获取涨跌停价格
        limit_prices = self.price_limit_engine.get_limit_price(symbol)

        if direction == Direction.LONG:
            # 买入检查：价格不能超过涨停价
            if price > limit_prices.upper:
                return False, f"买入价格超过涨停价{limit_prices.upper}", limit_prices.upper
            # 涨停时不能买入
            if limit_prices.is_limit_up:
                return False, "涨停板无法买入", price

        else:
            # 卖出检查：价格不能低于跌停价
            if price < limit_prices.lower:
                return False, f"卖出价格低于跌停价{limit_prices.lower}", limit_prices.lower
            # 跌停时不能卖出
            if limit_prices.is_limit_down:
                return False, "跌停板无法卖出", price

        return True, "可执行", price


@dataclass
class LimitPrices:
    """涨跌停价格"""
    upper: float
    lower: float
    is_limit_up: bool = False
    is_limit_down: bool = False
```

### 3.4 T+1模拟

```python
class T1Simulator:
    """T+1规则模拟器"""

    def __init__(self):
        # 持仓流水: {symbol: [BuyRecord, ...]}
        self.buy_records: dict[str, list[BuyRecord]] = {}

    def record_buy(self, symbol: str, volume: int, price: float, datetime: datetime):
        """记录买入"""
        if symbol not in self.buy_records:
            self.buy_records[symbol] = []

        self.buy_records[symbol].append(BuyRecord(
            volume=volume,
            price=price,
            buy_date=datetime.date()
        ))

    def get_sellable_volume(self, symbol: str, current_date: date) -> int:
        """获取可卖出数量"""
        if symbol not in self.buy_records:
            return 0

        total = 0
        for record in self.buy_records[symbol]:
            # T+1: 必须是前一天及之前买入的
            if record.buy_date < current_date:
                total += record.volume - record.sold_volume

        return total

    def record_sell(self, symbol: str, volume: int, current_date: date):
        """记录卖出"""
        if symbol not in self.buy_records:
            return

        remaining = volume
        for record in self.buy_records[symbol]:
            if remaining <= 0:
                break
            if record.buy_date < current_date:
                available = record.volume - record.sold_volume
                sold = min(remaining, available)
                record.sold_volume += sold
                remaining -= sold


@dataclass
class BuyRecord:
    """买入记录"""
    volume: int
    price: float
    buy_date: date
    sold_volume: int = 0
```

### 3.5 增强回测报告

```python
@dataclass
class EnhancedBacktestResult:
    """增强回测结果"""

    # 基础指标
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float

    # A股特有指标
    win_rate: float                    # 胜率
    profit_loss_ratio: float          # 盈亏比
    avg_holding_days: float          # 平均持股天数
    avg_positions: int               # 平均持仓数
    avg_capital_usage: float         # 平均资金使用率

    # 交易统计
    total_trades: int
    buy_trades: int
    sell_trades: int
    max_consecutive_wins: int        # 最大连续盈利
    max_consecutive_losses: int      # 最大连续亏损

    # 成本统计
    total_cost: float
    cost_rate: float                # 成本费率

    # 月度收益
    monthly_returns: dict[str, float]


class ReportGenerator:
    """回测报告生成器"""

    def generate(self, backtest_result: EnhancedBacktestResult) -> str:
        """生成回测报告"""

        report = f"""
========================================
           A股增强回测报告
========================================

一、收益指标
-----------
总收益率: {backtest_result.total_return:.2%}
年化收益率: {backtest_result.annual_return:.2%}
最大回撤: {backtest_result.max_drawdown:.2%}
夏普比率: {backtest_result.sharpe_ratio:.2f}

二、交易统计
-----------
总交易次数: {backtest_result.total_trades}
买入次数: {backtest_result.buy_trades}
卖出次数: {backtest_result.sell_trades}
胜率: {backtest_result.win_rate:.2%}
盈亏比: {backtest_result.profit_loss_ratio:.2f}

三、持仓统计
-----------
平均持股天数: {backtest_result.avg_holding_days:.1f}
平均持仓数: {backtest_result.avg_positions}
平均资金使用率: {backtest_result.avg_capital_usage:.2%}

四、成本统计
-----------
总交易成本: {backtest_result.total_cost:.2f}
成本费率: {backtest_result.cost_rate:.3%}

========================================
"""
        return report
```

---

## 4. 实施计划

| 阶段 | 任务 | 预估工时 |
|------|------|---------|
| 1 | 创建目录结构和基础类 | 0.5人天 |
| 2 | 实现交易成本计算器 | 1人天 |
| 3 | 实现滑点模型 | 1人天 |
| 4 | 实现涨跌停处理和T+1模拟 | 1.5人天 |
| 5 | 实现增强回测报告 | 1人天 |
| 6 | 集成测试 | 1人天 |
| 合计 | | **6人天** |

---

## 5. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-02-24 | 初始版本 |
