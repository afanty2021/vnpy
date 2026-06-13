# vnpy_china_backtest - A股增强回测模块

> 更新时间：2026-02-24
> 版本：1.0.0

## 模块概述

vnpy_china_backtest是A股增强回测模块，在VeighNa现有回测系统基础上增加A股特色交易模拟功能。

## 核心功能

### 1. 交易成本模拟
- 佣金：万3，最低5元
- 印花税：千1，仅卖出收取
- 过户费：万0.1，双向收取
- 经手费：万0.0685，双向收取

### 2. 滑点模型
- FixedSlippage：固定滑点
- PercentSlippage：百分比滑点
- ImpactCostSlippage：冲击成本滑点
- AdaptiveSlippage：自适应滑点

### 3. 涨跌停处理
- 主板：10%
- 创业板/科创板：20%
- 北交所：30%
- ST：5%
- 涨停无法买入，跌停无法卖出

### 4. T+1规则模拟
- 当日买入，次日才能卖出
- FIFO原则卖出

### 5. 指标计算
- 基础指标：总收益、年化收益、最大回撤、夏普比率
- A股特有：胜率、盈亏比、平均持股天数

## 模块结构

```
vnpy_china_backtest/
├── __init__.py                    # 模块入口
├── CLAUDE.md                     # 模块文档
├── engine.py                      # 增强回测引擎
├── cost.py                        # 交易成本计算
├── slippage.py                    # 滑点模型
├── config.py                      # 配置管理
├── rules/                         # 交易规则模拟
│   ├── __init__.py
│   ├── price_limit.py            # 涨跌停处理
│   └── t1_simulator.py           # T+1模拟
└── report/                        # 回测报告
    ├── __init__.py
    └── metrics.py                # 指标计算
```

## 快速开始

### 基本使用

```python
from vnpy_china_backtest import create_engine

# 创建引擎
engine = create_engine(
    capital=1_000_000,
    enable_cost=True,
    enable_slippage=True,
    enable_price_limit=True,
    enable_t1=True
)

# 设置昨日收盘价
from datetime import date
engine.pre_closes["000001.SZSE"] = 10.0

# 买入
success, reason = engine.buy("000001.SZSE", price=10.0, volume=1000)
print(f"买入结果: {success}, {reason}")

# 卖出（T+1规则：次日才能卖出）
success, reason = engine.sell("000001.SZSE", price=10.5, volume=1000)
print(f"卖出结果: {success}, {reason}")

# 获取权益
equity = engine.get_equity()
print(f"当前权益: {equity}")

# 计算指标
metrics = engine.calculate_metrics()
print(f"总收益: {metrics.total_return:.2%}")
print(f"胜率: {metrics.win_rate:.2%}")
```

### 自定义配置

```python
from vnpy_china_backtest import (
    EnhancedBacktestEngine,
    CostConfig,
    PercentSlippage
)

# 创建引擎
engine = EnhancedBacktestEngine()

# 设置成本配置
cost_config = CostConfig(
    commission_rate=0.0003,
    min_commission=5.0,
    stamp_duty_rate=0.001,
)
engine.set_cost_config(cost_config)

# 设置滑点
engine.set_slippage("percent", percent=0.002)

# 启用/禁用功能
engine.enable_cost = True
engine.enable_slippage = True
engine.enable_price_limit = True
engine.enable_t1 = True
```

## API参考

### CostCalculator

交易成本计算器

```python
from vnpy_china_backtest import CostCalculator, CostConfig
from vnpy.trader.constant import Direction, Exchange

config = CostConfig(commission_rate=0.0003)
calculator = CostCalculator(config)

# 计算买入成本
cost = calculator.calculate(price=10.0, volume=1000, direction=Direction.LONG, exchange=Exchange.SZSE)
print(f"佣金: {cost.commission}")
print(f"总成本: {cost.total}")

# 计算卖出成本（包含印花税）
cost = calculator.calculate(price=10.0, volume=1000, direction=Direction.SHORT, exchange=Exchange.SZSE)
print(f"印花税: {cost.stamp_duty}")
print(f"总成本: {cost.total}")
```

### SlippageModel

滑点模型

```python
from vnpy_china_backtest import PercentSlippage, FixedSlippage
from vnpy.trader.constant import Direction

# 百分比滑点
slippage = PercentSlippage(percent=0.001)  # 0.1%
adjusted_price = slippage.apply(price=10.0, volume=1000, direction=Direction.LONG)

# 固定滑点
slippage = FixedSlippage(slippage=0.01)  # 1分钱
adjusted_price = slippage.apply(price=10.0, volume=1000, direction=Direction.LONG)
```

### T1Simulator

T+1规则模拟器

```python
from vnpy_china_backtest import T1Simulator
from datetime import date

simulator = T1Simulator()

# 记录买入
simulator.record_buy("000001.SZSE", 1000, 10.0, date(2024, 1, 1))

# 当日不可卖出
sellable = simulator.get_sellable_volume("000001.SZSE", date(2024, 1, 1))
print(f"当日可卖出数量: {sellable}")  # 0

# 次日可卖出
sellable = simulator.get_sellable_volume("000001.SZSE", date(2024, 1, 2))
print(f"次日可卖出数量: {sellable}")  # 1000
```

### PriceLimitHandler

涨跌停处理器

```python
from vnpy_china_backtest import PriceLimitHandler
from vnpy.trader.constant import Direction
from datetime import date

handler = PriceLimitHandler()

# 处理订单
success, reason, price, volume = handler.process_order(
    symbol="000001.SZSE",
    direction=Direction.LONG,
    price=10.5,
    volume=1000,
    trade_date=date(2024, 1, 2),
    prev_close=10.0,
    current_price=10.5  # 当前价格
)

print(f"成交结果: {success}, {reason}")
print(f"成交价格: {price}")

# 涨停板无法买入
success, reason, price, volume = handler.process_order(
    symbol="000001.SZSE",
    direction=Direction.LONG,
    price=11.0,
    volume=1000,
    trade_date=date(2024, 1, 2),
    prev_close=10.0,
    current_price=11.0  # 涨停价
)
print(f"涨停板买入: {success}, {reason}")  # False, 涨停板无法买入
```

### EnhancedMetrics

回测指标

```python
from vnpy_china_backtest import MetricsCalculator

calculator = MetricsCalculator(annual_days=240)

metrics = calculator.calculate(
    trades=trades_list,
    equity_curve=[1000000, 1200000],
    trading_days=240,
    initial_capital=1000000,
    final_capital=1200000,
    total_cost=5000
)

# 基础指标
print(f"总收益率: {metrics.total_return:.2%}")
print(f"年化收益率: {metrics.annual_return:.2%}")
print(f"最大回撤: {metrics.max_drawdown:.2%}")
print(f"夏普比率: {metrics.sharpe_ratio:.2f}")

# A股特有指标
print(f"胜率: {metrics.win_rate:.2%}")
print(f"盈亏比: {metrics.profit_loss_ratio:.2f}")
print(f"平均持股天数: {metrics.avg_holding_days:.1f}")

# 成本统计
print(f"总交易成本: {metrics.total_cost:.2f}")
print(f"成本费率: {metrics.cost_rate:.4f}")
```

## 涨跌停规则

| 市场 | 代码前缀 | 涨跌幅 |
|------|---------|--------|
| 主板 | 000/001/002 | 10% |
| 创业板 | 300 | 20% |
| 科创板 | 688 | 20% |
| 北交所 | 4/8 | 30% |
| ST | ST/*ST | 5% |

## 变更记录

### 2026-06-13 v1.1.0
- 🔧 **回测可信度修复**：
  - `get_equity()` 改用回测当前市价计算持仓市值（此前用买入均价，导致日间未实现盈亏丢失）
  - 回测时钟取自 `bar.datetime`，替代 `datetime.now()`（此前导致 T+1 规则在回放中失效、所有卖出被阻止）
  - `calculate_metrics()` 接入完整权益曲线与真实回测天数（此前两点曲线导致夏普比率恒为 0、最大回撤失真、天数硬编码 240）
  - `t1_simulator` 卖出冻结量计算改用回测 `trade_date`，消除 `date.today()` 污染
  - 修复 `cost.py` 中 `CostCalculatorFactory("ETF")` 的 `min_commission` 拼写错误（原会抛 TypeError）
- 🏗️ **架构重构**：
  - 新增 `strategies.py`：`BaseStrategy` / `MaCrossStrategy` / `BuyHoldStrategy`，策略与 UI 解耦（新增策略无需改 Widget）
  - `widget.py` 复用数据服务单例 `get_data_service()`、统一使用 `extract_vt_symbol`、清理未用导入（`timedelta`/`defaultdict`/`QtGui`）

### 2026-02-24 v1.0.0
- 初始版本
- 实现交易成本计算（佣金、印花税、过户费、经手费）
- 实现滑点模型（固定、百分比、冲击成本、自适应）
- 实现涨跌停处理（主板10%/创业板20%/科创板20%/北交所30%/ST5%）
- 实现T+1模拟（FIFO原则）
- 实现指标计算（基础指标 + A股特有指标）


<claude-mem-context>
# Recent Activity

<!-- This section is auto-generated by claude-mem. Edit content outside the tags. -->

### Feb 24, 2026

| ID | Time | T | Title | Read |
|----|------|---|-------|------|
| #6615 | 9:28 PM | 🔵 | Checked vnpy_china_backtest CLAUDE.md documentation | ~207 |
| #6614 | 9:27 PM | 🔵 | Read vnpy_china_backtest/CLAUDE.md documentation file | ~156 |

### Feb 25, 2026

| ID | Time | T | Title | Read |
|----|------|---|-------|------|
| #7146 | 4:31 PM | 🔴 | vnpy_china_backtest __init__.py updated with App exports | ~153 |
| #7131 | 4:24 PM | 🟣 | ChinaBacktestApp created for vnpy_china_backtest GUI integration | ~146 |
</claude-mem-context>