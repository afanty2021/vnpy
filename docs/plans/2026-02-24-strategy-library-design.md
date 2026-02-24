# A股特色策略库设计文档

> 文档版本：v1.1
> 创建日期：2026-02-24
> 更新日期：2026-02-24
> 需求编号：REQ-005
> 优先级：P1
> 预计工时：10人天
>
> **变更记录**:
> - v1.1: 使用vnpy_china_data作为统一数据源，通过接口访问数据
> - v1.0: 初始版本

---

## 1. 设计目标

构建A股特色策略库，实现：

1. **龙虎榜策略**：机构席位追踪、营业部游资追踪、跟随交易
2. **北向资金策略**：资金流向、个股持股变化、板块偏好
3. **板块轮动策略**：板块强度、资金流向、轮动信号
4. **事件驱动策略**：业绩预告、重大事项、政策事件
5. **可转债套利策略**：转股价值、溢价率、套利信号

### 1.1 数据源集成

**本模块的所有数据需求均通过vnpy_china_data模块获取**：

| 策略类型 | 数据需求 | 接口 |
|---------|---------|------|
| 龙虎榜策略 | 龙虎榜数据 | `IDragonTigerProvider` |
| 北向资金策略 | 北向资金流向 | `INorthboundProvider` |
| 板块轮动策略 | 板块数据、板块指数 | `ISectorProvider` |
| 事件驱动策略 | 公告数据、业绩预告 | `IDataProvider.get_stock_info()` |
| 可转债套利 | 可转债行情、转股价 | `IDataProvider.get_bar_data()` |

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    A股特色策略库架构                              │
├─────────────────────────────────────────────────────────────────┤
│  【策略基类层】                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ChinaStrategy │  │MultiFactor   │  │  Timing     │          │
│  │ Template     │  │ Strategy     │  │  Strategy   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│  【策略实现层】                                                  │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │
│  │龙虎榜  │ │北向资金│ │板块轮动│ │事件驱动│ │可转债  │       │
│  │策略    │ │策略    │ │策略    │ │策略    │ │套利    │       │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘       │
├─────────────────────────────────────────────────────────────────┤
│  【数据支持层】                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  龙虎榜数据  │  │ 北向资金数据  │  │  板块数据    │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块结构

```
vnpy_china_strategy/
├── __init__.py
├── template.py                 # 策略基类
├── base.py                    # 基础策略类
├── dragon_tiger/
│   ├── data.py               # 龙虎榜数据
│   ├── institution.py        # 机构席位策略
│   ├── broker.py             # 游资策略
│   └── follow.py             # 跟随策略
├── northbound/
│   ├── data.py               # 北向资金数据
│   ├── flow.py               # 资金流向策略
│   ├── holding.py             # 持股变化策略
│   └── sector.py              # 板块偏好策略
├── sector_rotation/
│   ├── data.py               # 板块数据
│   ├── strength.py            # 板块强度策略
│   ├── fund_flow.py          # 资金流向策略
│   └── signal.py              # 轮动信号策略
├── event_driven/
│   ├── data.py               # 事件数据
│   ├── earnings.py            # 业绩预告策略
│   ├── mna.py                 # 并购重组策略
│   └── policy.py              # 政策事件策略
└── convertible/
    ├── data.py                # 可转债数据
    ├── arbitrage.py           # 套利策略
    └── pricing.py             # 定价模型
```

---

## 3. 核心策略设计

### 3.1 龙虎榜策略基类

```python
from vnpy.trader.object import BarData, TickData
from vnpy_ctastrategy import CtaTemplate
from vnpy_china_interface import IDragonTigerProvider, DragonTigerData
from vnpy_china_config import ConfigManager
from vnpy_china_data import ChinaDataService


class DragonTigerStrategy(CtaTemplate):
    """龙虎榜策略基类"""

    parameters = [
        "institution_threshold",  # 机构买入阈值
        "broker_threshold",       # 游资买入阈值
        "follow_days",           # 跟随天数
        "position_ratio",        # 仓位比例
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 获取数据服务（通过接口）
        self.data_provider: IDragonTigerProvider = ChinaDataService()

        # 获取策略配置
        config_manager = ConfigManager()
        self.strategy_config = config_manager.get_config("strategy")

        # 默认参数
        self.institution_threshold = 1000_000  # 机构买入1000万
        self.broker_threshold = 500_000        # 游资买入500万
        self.follow_days = 5                   # 跟随5天
        self.position_ratio = 0.1             # 10%仓位

    def on_bar(self, bar: BarData):
        """K线推送"""
        # 通过接口获取当日龙虎榜数据
        dragon_tiger_data = self.data_provider.get_dragon_tiger_data(
            bar.datetime.date()
        )

        if not dragon_tiger_data:
            return

        # 筛选符合条件的股票
        for stock in dragon_tiger_data:
            if self.check_buy_signal(stock):
                self.buy_stock(stock, self.position_ratio)


class InstitutionTrackerStrategy(DragonTigerStrategy):
    """机构席位追踪策略"""

    name = "机构席位追踪"

    def check_buy_signal(self, data: DragonTigerData) -> bool:
        """检查买入信号"""
        return (
            data.institution_net_buy > self.institution_threshold
            and data.buy_ratio > 0.6
        )
```

### 3.2 北向资金策略

```python
class NorthboundStrategy(CtaTemplate):
    """北向资金策略基类"""

    parameters = [
        "net_inflow_threshold",   # 净流入阈值
        "holding_change_ratio",   # 持股变化比例
        "sector_weight",          # 板块权重
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.net_inflow_threshold = 1_000_000_000  # 10亿
        self.holding_change_ratio = 0.05           # 5%

    def on_bar(self, bar: BarData):
        """K线推送"""
        # 获取北向资金流向
        flow_data = self.get_northbound_flow(bar.datetime.date())

        # 获取持股变化
        holding_changes = self.get_holding_changes(
            bar.symbol,
            days=5
        )

        # 生成信号
        if self.check_signal(flow_data, holding_changes):
            self.execute_trade(bar)


class SectorPreferenceStrategy(NorthboundStrategy):
    """北向资金板块偏好策略"""

    name = "北向资金板块偏好"

    def get_sector_preference(self) -> dict[str, float]:
        """获取板块偏好"""
        # 计算各行业北向资金净流入
        sector_flow = {}
        for stock in self.get_all_stocks():
            flow = self.get_northbound_flow(stock, days=20)
            sector = self.get_stock_sector(stock)
            sector_flow[sector] = sector_flow.get(sector, 0) + flow.net_inflow

        return sector_flow
```

### 3.3 板块轮动策略

```python
class SectorRotationStrategy(CtaTemplate):
    """板块轮动策略"""

    parameters = [
        "rotation_period",       # 轮动周期
        "top_n",                 # 选取前N个板块
        "momentum_days",         # 动量天数
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.rotation_period = 20      # 20个交易日
        self.top_n = 3                 # 前3个板块
        self.momentum_days = 60        # 60天动量


class StrengthRotationStrategy(SectorRotationStrategy):
    """板块强度轮动策略"""

    name = "板块强度轮动"

    def calculate_sector_strength(self, sector: str) -> float:
        """计算板块强度"""
        # 相对强弱 = 板块涨幅 / 大盘涨幅
        sector_return = self.get_sector_return(sector, self.momentum_days)
        market_return = self.get_market_return(self.momentum_days)

        return sector_return / market_return if market_return != 0 else 0
```

### 3.4 事件驱动策略

```python
class EventDrivenStrategy(CtaTemplate):
    """事件驱动策略基类"""

    parameters = [
        "event_types",           # 事件类型
        "position_limit",       # 仓位限制
        "holding_days",         # 持有天数
    ]


class EarningsForecastStrategy(EventDrivenStrategy):
    """业绩预告事件策略"""

    name = "业绩预告事件"

    def on_bar(self, bar: BarData):
        """检查事件"""
        # 获取即将发布的业绩预告
        upcoming = self.get_upcoming_earnings(bar.symbol)

        if upcoming and self.is_buy_signal(upcoming):
            self.buy(bar.close_price, self.get_position_size())


class PolicyEventStrategy(EventDrivenStrategy):
    """政策事件策略"""

    name = "政策事件驱动"

    # 关注的政策关键词
    POLICY_KEYWORDS = [
        "新能源", "半导体", "人工智能", "医药",
        "房地产", "金融", "消费", "出口"
    ]
```

### 3.5 可转债套利策略

```python
class ConvertibleArbitrageStrategy(CtaTemplate):
    """可转债套利策略"""

    parameters = [
        "premium_threshold",    # 溢价率阈值
        "conversion_ratio",     # 转股价值阈值
        "position_size",        # 仓位大小
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.premium_threshold = -5  # 溢价率-5%以下
        self.conversion_ratio = 1.0  # 转股价值接近正股
        self.position_size = 10000   # 1万面额


class BondArbitrageStrategy(ConvertibleArbitrageStrategy):
    """可转债转股套利策略"""

    name = "可转债转股套利"

    def check_arbitrage_opportunity(self, cb: ConvertibleBond) -> bool:
        """检查套利机会"""
        # 计算转股溢价率
        premium = (cb.price / cb.conversion_value - 1) * 100

        # 溢价率为负且绝对值大于阈值
        if premium < self.premium_threshold:
            # 同时满足正股处于上升趋势
            if self.is_stock_uptrend(cb.stock_symbol):
                return True

        return False
```

---

## 4. 实施计划

| 阶段 | 任务 | 预估工时 |
|------|------|---------|
| 1 | 创建目录结构和基类 | 1人天 |
| 2 | 实现龙虎榜策略 | 2人天 |
| 3 | 实现北向资金策略 | 2人天 |
| 4 | 实现板块轮动策略 | 2人天 |
| 5 | 实现事件驱动策略 | 1.5人天 |
| 6 | 实现可转债套利策略 | 1.5人天 |
| 合计 | | **10人天** |

---

## 5. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-02-24 | 初始版本 |
