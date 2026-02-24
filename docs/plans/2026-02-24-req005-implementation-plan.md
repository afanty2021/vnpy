# REQ-005 A股特色策略库实施方案

> 文档版本：v1.0
> 创建日期：2026-02-24
> 需求编号：REQ-005
> 优先级：P1
> 状态：待实施

---

## 1. 模块概述

### 1.1 模块定位

`vnpy_china_strategy` 是A股特色策略库模块，提供5大类A股特有策略：
- 龙虎榜策略（机构席位追踪、游资追踪、跟随交易）
- 北向资金策略（资金流向、持股变化、板块偏好）
- 板块轮动策略（板块强度、资金流向、轮动信号）
- 事件驱动策略（业绩预告、并购重组、政策事件）
- 可转债套利策略（转股套利、定价模型）

### 1.2 模块位置

```
vnpy_china_strategy/
├── __init__.py                    # 模块入口
├── CLAUDE.md                      # 模块文档
├── template.py                    # 策略模板基类
├── base.py                        # 策略基础类
├── config.py                      # 策略配置管理
├── dragon_tiger/                  # 龙虎榜策略
│   ├── __init__.py
│   ├── data.py                   # 龙虎榜数据获取
│   ├── models.py                 # 数据模型
│   ├── institution.py            # 机构席位策略
│   ├── broker.py                 # 游资策略
│   ├── follow.py                 # 跟随策略
│   └── __init__.py
├── northbound/                    # 北向资金策略
│   ├── __init__.py
│   ├── data.py                   # 北向资金数据获取
│   ├── models.py                 # 数据模型
│   ├── flow.py                   # 资金流向策略
│   ├── holding.py                # 持股变化策略
│   └── sector.py                 # 板块偏好策略
├── sector_rotation/               # 板块轮动策略
│   ├── __init__.py
│   ├── data.py                   # 板块数据获取
│   ├── models.py                 # 数据模型
│   ├── strength.py               # 板块强度策略
│   ├── fund_flow.py              # 资金流向策略
│   └── signal.py                 # 轮动信号策略
├── event_driven/                 # 事件驱动策略
│   ├── __init__.py
│   ├── data.py                   # 事件数据获取
│   ├── models.py                 # 数据模型
│   ├── earnings.py                # 业绩预告策略
│   ├── mna.py                    # 并购重组策略
│   └── policy.py                 # 政策事件策略
├── convertible/                  # 可转债套利策略
│   ├── __init__.py
│   ├── data.py                   # 可转债数据获取
│   ├── models.py                 # 数据模型
│   ├── arbitrage.py              # 套利策略
│   └── pricing.py                # 定价模型
├── indicators/                    # 公共指标库
│   ├── __init__.py
│   ├── momentum.py               # 动量指标
│   ├── volatility.py             # 波动率指标
│   └── volume.py                # 成交量指标
└── tests/                        # 测试
    ├── __init__.py
    ├── test_dragon_tiger.py
    ├── test_northbound.py
    ├── test_sector_rotation.py
    ├── test_event_driven.py
    └── test_convertible.py
```

---

## 2. 数据模型设计

### 2.1 龙虎榜数据模型

**文件**: `vnpy_china_strategy/dragon_tiger/models.py`

```python
from dataclasses import dataclass
from datetime import date
from typing import List, Optional
from decimal import Decimal

@dataclass
class DragonTigerRecord:
    """龙虎榜记录"""
    trade_date: date              # 交易日期
    symbol: str                   # 股票代码
    name: str                     # 股票名称
    close_price: float            # 收盘价
    change_pct: float            # 涨跌幅

    # 机构席位数据
    institution_buy: Decimal     # 机构买入金额
    institution_sell: Decimal    # 机构卖出金额
    institution_net: Decimal      # 机构净买入
    institution_count: int       # 机构买入家数

    # 营业部游资数据
    broker_buy: Decimal          # 游资买入金额
    broker_sell: Decimal         # 游资卖出金额
    broker_net: Decimal          # 游资净买入

    # 合计
    total_buy: Decimal           # 总买入
    total_sell: Decimal          # 总卖出
    net_buy: Decimal             # 净买入

    # 成交额
    turnover: Decimal            # 成交额
    turnover_rate: float         # 换手率

@dataclass
class InstitutionDetail:
    """机构席位详情"""
    name: str                    # 席位名称
    buy_amount: Decimal          # 买入金额
    sell_amount: Decimal         # 卖出金额
    net_amount: Decimal           # 净买入
    rank: int                    # 排名

@dataclass
class BrokerDetail:
    """营业部游资详情"""
    broker_name: str             # 营业部名称
    buy_amount: Decimal          # 买入金额
    sell_amount: Decimal         # 卖出金额
    net_amount: Decimal           # 净买入
```

### 2.2 北向资金数据模型

**文件**: `vnpy_china_strategy/northbound/models.py`

```python
@dataclass
class NorthboundFlow:
    """北向资金流向"""
    trade_date: date             # 交易日期
    net_inflow: Decimal          # 净流入
    inflow: Decimal              # 买入额
    outflow: Decimal             # 卖出额
    balance: Decimal             # 余额

@dataclass
class StockHoldingChange:
    """个股持股变化"""
    symbol: str                  # 股票代码
    trade_date: date             # 交易日期
    holding_shares: int         # 持股数
    holding_ratio: float         # 持股比例
    change_shares: int           # 变化股数
    change_ratio: float          # 变化比例
    net_inflow: Decimal          # 净流入

@dataclass
class SectorNorthboundFlow:
    """板块北向资金流向"""
    sector: str                  # 板块名称
                # 交易日期
    net_inflow: Decimal trade_date: date         # 净流入
    stock_count: int             # 流入股票数
    avg_change: float            # 平均涨幅
```

### 2.3 板块数据模型

**文件**: `vnpy_china_strategy/sector_rotation/models.py`

```python
@dataclass
class SectorData:
    """板块数据"""
    sector: str                  # 板块名称
    trade_date: date             # 交易日期
    close_index: float          # 收盘点位
    change_pct: float          # 涨跌幅
    turnover_rate: float        # 换手率
    pe: float                   # 市盈率
    volume: Decimal              # 成交量
    amount: Decimal              # 成交额

@dataclass
class SectorStrength:
    """板块强度"""
    sector: str                  # 板块
    strength: float             # 强度值 (相对大盘)
    momentum_5d: float          # 5日动量
    momentum_20d: float         # 20日动量
    momentum_60d: float         # 60日动量
    fund_flow: Decimal           # 资金净流入
    rank: int                   # 强度排名

@dataclass
class RotationSignal:
    """轮动信号"""
    from_sector: str            # 轮出板块
    to_sector: str              # 轮入板块
    signal_date: date           # 信号日期
    confidence: float           # 置信度
    reason: str                 # 轮动原因
```

### 2.4 事件数据模型

**文件**: `vnpy_china_strategy/event_driven/models.py`

```python
@dataclass
class EarningsForecast:
    """业绩预告"""
    symbol: str                  # 股票代码
    name: str                   # 公司名称
    forecast_date: date         # 预告日期
    report_date: date            # 报告期
    earnings_type: str          # 业绩类型 (预增/预减/扭亏/...)
    earnings_range_low: Optional[Decimal]  # 业绩下限
    earnings_range_high: Optional[Decimal] # 业绩上限
    YoY_change: Optional[float]  # 同比变化

@dataclass
class CorporateAction:
    """重大事项"""
    symbol: str                  # 股票代码
    name: str                   # 公司名称
    announcement_date: date      # 公告日期
    action_type: str            # 事项类型 (并购/重组/增减持/...)
    title: str                  # 公告标题
    content: str                # 摘要内容
    impact: str                 # 影响分析

@dataclass
class PolicyEvent:
    """政策事件"""
    event_date: date            # 事件日期
    policy_title: str           # 政策标题
    related_sectors: List[str]  # 相关板块
    impact_level: str           # 影响级别 (正面/中性/负面)
    keywords: List[str]         # 关键词
```

### 2.5 可转债数据模型

**文件**: `vnpy_china_strategy/convertible/models.py`

```python
@dataclass
class ConvertibleBond:
    """可转债"""
    symbol: str                  # 转债代码
    name: str                   # 转债名称
    stock_symbol: str           # 正股代码
    stock_name: str             # 正股名称

    # 价格数据
    cb_price: float             # 转债价格
    stock_price: float          # 正股价格

    # 转股数据
    conversion_price: float      # 转股价
    conversion_value: float     # 转股价值
    conversion_ratio: float     # 转股比例

    # 溢价率
    premium_rate: float          # 转股溢价率
    pure_bond_value: float      # 纯债价值
    yield_to_maturity: float    # 到期收益率

    # 其他
    maturity_date: date         # 到期日
    rating: str                 # 评级
    call_price: float          # 强赎价
```

---

## 3. 策略基类设计

### 3.1 策略模板基类

**文件**: `vnpy_china_strategy/template.py`

```python
from vnpy_ctastrategy import CtaTemplate
from vnpy.trader.object import BarData, TickData
from typing import Optional, List, Dict
from datetime import datetime

class ChinaStrategyTemplate(CtaTemplate):
    """A股策略模板基类"""

    # 策略参数
    parameters: List[str] = []

    # 策略变量
    variables: List[str] = []

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 数据服务接口（由子类注入）
        self.data_service = None

    def get_bar_data(self, symbol: str, days: int) -> List[BarData]:
        """获取K线数据"""
        if self.data_service:
            return self.data_service.get_bar_data(symbol, days)
        return []

    def get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前价格"""
        tick = self.get_tick(symbol)
        return tick.last_price if tick else None

    def calculate_position_size(
        self,
        price: float,
        risk_amount: float
    ) -> int:
        """计算仓位数量"""
        # 固定风险金额/每手价值 = 持仓手数
        per_lot_value = price * 100  # 股票1手=100股
        return int(risk_amount / per_lot_value)

    def is_tradeable(self, symbol: str) -> bool:
        """检查是否可交易"""
        # 检查ST股票
        stock_info = self.data_service.get_stock_info(symbol) if self.data_service else None
        if stock_info and stock_info.is_st:
            return False

        # 检查涨跌停
        price = self.get_current_price(symbol)
        if price:
            tick = self.get_tick(symbol)
            if tick:
                if price >= tick.limit_up or price <= tick.limit_down:
                    return False
        return True
```

---

## 4. 策略实现详情

### 4.1 龙虎榜策略

#### 4.1.1 机构席位追踪策略

**文件**: `vnpy_china_strategy/dragon_tiger/institution.py`

```python
from vnpy_china_strategy.template import ChinaStrategyTemplate
from vnpy_china_strategy.dragon_tiger.models import DragonTigerRecord

class InstitutionTrackerStrategy(ChinaStrategyTemplate):
    """机构席位追踪策略

    逻辑：
    1. 每日收盘后获取当日龙虎榜数据
    2. 筛选机构净买入 > 阈值的股票
    3. 机构买入家数 >= 3家
    4. 买入后持有 N 天卖出
    """

    parameters = [
        "institution_threshold",   # 机构买入阈值(万)
        "min_institution_count",   # 最少机构数
        "holding_days",           # 持有天数
        "position_ratio",         # 仓位比例
    ]

    variables = [
        "signal_count",
        "positions",
    ]

    def on_init(self):
        self.institution_threshold = 1000  # 1000万
        self.min_institution_count = 3
        self.holding_days = 5
        self.position_ratio = 0.1

        self.signal_count = 0
        self.positions: Dict[str, int] = {}  # symbol -> entry_day

    def on_bar(self, bar: BarData):
        """K线推送"""
        # 获取当日龙虎榜
        dt_data = self.get_dragon_tiger_data(bar.datetime.date())

        if not dt_data:
            return

        # 筛选机构买入信号
        for record in dt_data:
            if self.check_buy_signal(record):
                self.execute_buy(record)

        # 检查卖出信号
        self.check_sell_signals(bar.datetime)

    def check_buy_signal(self, record: DragonTigerRecord) -> bool:
        """检查买入信号"""
        # 机构净买入 > 阈值
        if record.institution_net < self.institution_threshold * 10000:
            return False

        # 机构买入家数 >= 阈值
        if record.institution_count < self.min_institution_count:
            return False

        # 排除ST股票
        if not self.is_tradeable(record.symbol):
            return False

        return True

    def execute_buy(self, record: DragonTigerRecord):
        """执行买入"""
        if record.symbol in self.positions:
            return

        # 获取开盘价或市价买入
        price = self.get_current_price(record.symbol)
        if not price:
            return

        # 计算仓位
        size = self.calculate_position_size(
            price,
            self.cta_engine.get_account().available * self.position_ratio
        )

        if size > 0:
            self.buy(price, size)
            self.positions[record.symbol] = 0
            self.signal_count += 1

    def check_sell_signals(self, current_time: datetime):
        """检查卖出信号"""
        to_close = []

        for symbol, days in self.positions.items():
            # 持有天数达到
            if days >= self.holding_days:
                to_close.append(symbol)
            # 止损
            elif self.check_stop_loss(symbol):
                to_close.append(symbol)

        for symbol in to_close:
            self.close_position(symbol)
            del self.positions[symbol]
```

#### 4.1.2 游资策略

**文件**: `vnpy_china_strategy/dragon_tiger/broker.py`

```python
class BrokerMoneyStrategy(ChinaStrategyTemplate):
    """游资策略

    逻辑：
    1. 筛选游资净买入 > 阈值的股票
    2. 游资买入占比 > 60%
    3. 短期持有 (2-3天)
    """

    parameters = [
        "broker_threshold",       # 游资买入阈值
        "broker_ratio",          # 游资买入占比
        "holding_days",         # 持有天数
    ]

    def check_buy_signal(self, record: DragonTigerRecord) -> bool:
        # 游资净买入 > 阈值
        if record.broker_net < self.broker_threshold * 10000:
            return False

        # 游资买入占比 > 阈值
        if record.total_buy > 0:
            ratio = record.broker_buy / record.total_buy
            if ratio < self.broker_ratio:
                return False

        return True
```

#### 4.1.3 跟随策略

**文件**: `vnpy_china_strategy/dragon_tiger/follow.py`

```python
class FollowStrategy(ChinaStrategyTemplate):
    """龙虎榜跟随策略

    逻辑：
    1. 获取近期多次上榜的股票
    2. 上榜后持续跟踪
    3. 在回调时买入
    """

    parameters = [
        "appear_count",          # 上榜次数
        "follow_days",           # 跟随天数
        "pullback_ratio",       # 回调买入比例
    ]

    def on_bar(self, bar: BarData):
        # 获取近期龙虎榜
        recent_data = self.get_recent_dragon_tiger(days=10)

        # 统计上榜次数
        stock_appears = {}
        for record in recent_data:
            stock_appears[record.symbol] = stock_appears.get(record.symbol, 0) + 1

        # 筛选多次上榜且回调的股票
        for symbol, count in stock_appears.items():
            if count >= self.appear_count:
                if self.is_pullback Opportunity(symbol):
                    self.execute_buy(symbol)
```

### 4.2 北向资金策略

#### 4.2.1 资金流向策略

**文件**: `vnpy_china_strategy/northbound/flow.py`

```python
class NorthboundFlowStrategy(ChinaStrategyTemplate):
    """北向资金流向策略

    逻辑：
    1. 监控北向资金整体净流入
    2. 净流入放大时买入大盘股
    3. 净流出时减仓
    """

    parameters = [
        "net_inflow_threshold", # 净流入阈值(亿)
        "market_filter",        # 市场筛选 (沪深300/中证500/全部)
        "position_ratio",       # 仓位比例
    ]

    variables = [
        "daily_net_inflow",
        "signal",
    ]

    def on_bar(self, bar: BarData):
        # 获取北向资金流向
        flow = self.get_northbound_flow(bar.datetime.date())

        if not flow:
            return

        # 判断信号
        if flow.net_inflow > self.net_inflow_threshold * 1e8:
            self.signal = "BUY"
            # 买入ETF或大盘股
        elif flow.net_inflow < -self.net_inflow_threshold * 1e8:
            self.signal = "SELL"
            # 卖出
        else:
            self.signal = "HOLD"

        self.daily_net_inflow = float(flow.net_inflow)
```

#### 4.2.2 持股变化策略

**文件**: `vnpy_china_strategy/northbound/holding.py`

```python
class HoldingChangeStrategy(ChinaStrategyTemplate):
    """北向资金持股变化策略

    逻辑：
    1. 监控北向资金持股变化
    2. 持股比例增加 > 阈值
    3. 连续增持效果更好
    """

    parameters = [
        "change_threshold",      # 变化阈值
        "consecutive_days",      # 连续天数
        "min_shares",           # 最少持股数
    ]

    def check_buy_signal(self, symbol: str) -> bool:
        # 获取持股变化
        changes = self.get_holding_changes(symbol, days=self.consecutive_days)

        if len(changes) < self.consecutive_days:
            return False

        # 检查是否连续增持
        for change in changes:
            if change.change_ratio < self.change_threshold:
                return False

        return True
```

### 4.3 板块轮动策略

#### 4.3.1 板块强度策略

**文件**: `vnpy_china_strategy/sector_rotation/strength.py`

```python
class SectorStrengthStrategy(ChinaStrategyTemplate):
    """板块强度轮动策略

    逻辑：
    1. 计算各板块相对强度 (板块涨幅/大盘涨幅)
    2. 选取强度最高的 N 个板块
    3. 每月轮动一次
    """

    parameters = [
        "rotation_period",      # 轮动周期(交易日)
        "top_n",                # 选取板块数
        "momentum_days",        # 动量计算天数
        "min_strength",         # 最小强度阈值
    ]

    variables = [
        "current_sectors",
        "rotation_day",
    ]

    def on_bar(self, bar: BarData):
        # 轮动周期判断
        if self.rotation_day >= self.rotation_period:
            self.rotate_sectors()
            self.rotation_day = 0
        else:
            self.rotation_day += 1

    def rotate_sectors(self):
        """轮动板块"""
        # 计算各板块强度
        strengths = self.calculate_all_sector_strength()

        # 排序选取top N
        sorted_sectors = sorted(
            strengths,
            key=lambda x: x.strength,
            reverse=True
        )[:self.top_n]

        # 轮出弱板块，轮入强板块
        self.current_sectors = [s.sector for s in sorted_sectors]
```

### 4.4 事件驱动策略

#### 4.4.1 业绩预告策略

**文件**: `vnpy_china_strategy/event_driven/earnings.py`

```python
class EarningsForecastStrategy(ChinaStrategyTemplate):
    """业绩预告事件策略

    逻辑：
    1. 获取即将发布的业绩预告
    2. 预增/扭亏类型的股票可能上涨
    3. 预告发布后卖出
    """

    parameters = [
        "event_types",          # 关注的业绩类型
        "min_yoy_change",       # 最少同比变化
        "holding_days",         # 持有天数
    ]

    EVENT_TYPES = ["预增", "扭亏", "续盈"]

    def on_bar(self, bar: BarData):
        # 获取近期业绩预告
        forecasts = self.get_upcoming_earnings(
            days_ahead=7
        )

        for forecast in forecasts:
            if self.check_signal(forecast):
                self.execute_buy(forecast.symbol)
```

#### 4.4.2 政策事件策略

**文件**: `vnpy_china_strategy/event_driven/policy.py`

```python
class PolicyEventStrategy(ChinaStrategyTemplate):
    """政策事件驱动策略

    逻辑：
    1. 监控政策发布
    2. 识别相关板块
    3. 事件发生后买入相关板块
    """

    parameters = [
        "keywords",             # 关注关键词
        "impact_threshold",     # 影响阈值
        "sector_exposure",     # 板块暴露度
    ]

    # 政策关键词映射到板块
    KEYWORD_SECTOR_MAP = {
        "新能源": ["电气设备", "汽车", "有色"],
        "半导体": ["电子", "计算机"],
        "医药": ["医药生物"],
        "房地产": ["房地产", "建筑装饰"],
    }

    def on_bar(self, bar: BarData):
        # 获取近期政策事件
        events = self.get_recent_policy_events(days=30)

        for event in events:
            if event.impact_level == "正面":
                sectors = self.get_related_sectors(event)
                for sector in sectors:
                    self.buy_sector_etf(sector)
```

### 4.5 可转债套利策略

#### 4.5.1 转股套利策略

**文件**: `vnpy_china_strategy/convertible/arbitrage.py`

```python
class ConvertibleArbitrageStrategy(ChinaStrategyTemplate):
    """可转债转股套利策略

    逻辑：
    1. 筛选转股溢价率为负的转债
    2. 正股处于上升趋势
    3. 买入转债+融券正股
    4. 执行转股后平仓
    """

    parameters = [
        "premium_threshold",    # 溢价率阈值 (负数)
        "min_conversion_value", # 最小转股价值
        "trend_days",           # 趋势判断天数
    ]

    variables = [
        "positions",
    ]

    def on_bar(self, bar: BarData):
        # 获取全部可转债
        cb_list = self.get_all_convertible_bonds()

        for cb in cb_list:
            if self.check_arbitrage_opportunity(cb):
                self.execute_arbitrage(cb)

    def check_arbitrage_opportunity(self, cb: ConvertibleBond) -> bool:
        # 转股溢价率为负
        if cb.premium_rate >= self.premium_threshold:
            return False

        # 转股价值足够
        if cb.conversion_value < self.min_conversion_value:
            return False

        # 正股上升趋势
        if not self.is_stock_uptrend(cb.stock_symbol):
            return False

        return True

    def execute_arbitrage(self, cb: ConvertibleBond):
        """执行套利"""
        # 1. 买入可转债
        self.buy(cb.cb_price, self.position_size, cb.symbol)

        # 2. 融券卖出正股
        self.short(cb.stock_price, self.position_size * cb.conversion_ratio, cb.stock_symbol)

        # 3. 记录套利持仓
        self.positions[cb.symbol] = {
            "stock_symbol": cb.stock_symbol,
            "entry_date": datetime.now(),
        }
```

---

## 5. 数据获取层

### 5.1 数据服务接口

**文件**: `vnpy_china_strategy/data_service.py`

```python
from typing import Optional, List
from datetime import date
from abc import ABC, abstractmethod

class IDataProvider(ABC):
    """数据提供接口"""

    @abstractmethod
    def get_dragon_tiger_data(self, trade_date: date) -> List[DragonTigerRecord]:
        """获取龙虎榜数据"""

    @abstractmethod
    def get_northbound_flow(self, trade_date: date) -> NorthboundFlow:
        """获取北向资金流向"""

    @abstractmethod
    def get_stock_holding(self, symbol: str, trade_date: date) -> StockHoldingChange:
        """获取个股持股变化"""

    @abstractmethod
    def get_sector_data(self, sector: str, trade_date: date) -> SectorData:
        """获取板块数据"""

    @abstractmethod
    def get_convertible_bonds(self) -> List[ConvertibleBond]:
        """获取可转债列表"""

    @abstractmethod
    def get_earnings_forecast(self, symbol: str, days: int) -> List[EarningsForecast]:
        """获取业绩预告"""
```

### 5.2 数据服务实现

**文件**: `vnpy_china_strategy/data_service.py`

```python
class ChinaStrategyDataService(IDataProvider):
    """策略数据服务实现

    集成 vnpy_china_data 模块获取数据
    """

    def __init__(self, data_service=None):
        self.data_service = data_service

    def get_dragon_tiger_data(self, trade_date: date) -> List[DragonTigerRecord]:
        """获取龙虎榜数据"""
        # 通过数据服务接口获取
        if self.data_service:
            return self.data_service.get_dragon_tiger_data(trade_date)
        return []

    def get_northbound_flow(self, trade_date: date) -> NorthboundFlow:
        """获取北向资金流向"""
        if self.data_service:
            return self.data_service.get_northbound_flow(trade_date)
        return None
```

---

## 6. 开发计划

### 6.1 开发阶段

| 阶段 | 任务 | 工时 | 依赖 |
|-----|------|-----|------|
| **Phase 1** | 基础框架搭建 | 1.5天 | - |
| | - 目录结构创建 | 0.25天 | - |
| | - 策略基类 ChinaStrategyTemplate | 0.5天 | - |
| | - 数据模型定义 | 0.5天 | - |
| | - 数据服务接口 | 0.25天 | - |
| **Phase 2** | 龙虎榜策略 | 2天 | Phase 1 |
| | - DragonTigerRecord模型 | 0.25天 | - |
| | - 数据获取层 | 0.5天 | - |
| | - InstitutionTrackerStrategy | 0.75天 | - |
| | - BrokerMoneyStrategy | 0.25天 | - |
| | - FollowStrategy | 0.25天 | - |
| **Phase 3** | 北向资金策略 | 1.5天 | Phase 1 |
| | - NorthboundFlow模型 | 0.25天 | - |
| | - 数据获取层 | 0.25天 | - |
| | - NorthboundFlowStrategy | 0.5天 | - |
| | - HoldingChangeStrategy | 0.5天 | - |
| **Phase 4** | 板块轮动策略 | 1.5天 | Phase 1 |
| | - SectorData模型 | 0.25天 | - |
| | - 数据获取层 | 0.25天 | - |
| | - SectorStrengthStrategy | 0.75天 | - |
| | - RotationSignalStrategy | 0.25天 | - |
| **Phase 5** | 事件驱动策略 | 1.5天 | Phase 1 |
| | - 事件数据模型 | 0.25天 | - |
| | - EarningsForecastStrategy | 0.5天 | - |
| | - PolicyEventStrategy | 0.5天 | - |
| | - CorporateActionStrategy | 0.25天 | - |
| **Phase 6** | 可转债套利策略 | 1.5天 | Phase 1 |
| | - ConvertibleBond模型 | 0.25天 | - |
| | - 数据获取层 | 0.25天 | - |
| | - ConvertibleArbitrageStrategy | 0.75天 | - |
| | - BondPricingModel | 0.25天 | - |
| **Phase 7** | 测试与文档 | 1.5天 | All |
| | - 单元测试 | 1天 | - |
| | - 文档完善 | 0.5天 | - |

### 6.2 总工时估算

| 阶段 | 工时 |
|-----|------|
| Phase 1 | 1.5天 |
| Phase 2 | 2天 |
| Phase 3 | 1.5天 |
| Phase 4 | 1.5天 |
| Phase 5 | 1.5天 |
| Phase 6 | 1.5天 |
| Phase 7 | 1.5天 |
| **总计** | **11人天** |

---

## 7. 配置管理

### 7.1 策略配置

```python
# vnpy_china_strategy/config.py
from vnpy_china_config import ConfigManager

class StrategyConfig:
    """策略配置"""

    # 龙虎榜策略配置
    DRAGON_TIGER_CONFIG = {
        "institution_threshold": 1000,  # 机构买入阈值(万)
        "min_institution_count": 3,
        "broker_threshold": 500,        # 游资买入阈值(万)
        "follow_days": 5,
    }

    # 北向资金策略配置
    NORTHBOUND_CONFIG = {
        "net_inflow_threshold": 10,   # 亿
        "change_threshold": 0.05,     # 5%
    }

    # 板块轮动策略配置
    SECTOR_ROTATION_CONFIG = {
        "rotation_period": 20,         # 交易日
        "top_n": 3,
        "momentum_days": 60,
    }

    # 可转债策略配置
    CONVERTIBLE_CONFIG = {
        "premium_threshold": -5,       # -5%
        "min_conversion_value": 100,   # 100元
    }
```

---

## 8. 使用示例

### 8.1 加载策略

```python
from vnpy_ctastrategy import CtaEngine
from vnpy_china_strategy.dragon_tiger import InstitutionTrackerStrategy
from vnpy_china_strategy.data_service import ChinaStrategyDataService
from vnpy_china_data import ChinaDataService

# 创建数据服务
data_service = ChinaDataService()
strategy_data_service = ChinaStrategyDataService(data_service)

# 创建CTA引擎
cta_engine = CtaEngine(main_engine, event_engine)

# 创建策略实例
strategy = InstitutionTrackerStrategy(
    cta_engine=cta_engine,
    strategy_name="institution_tracker",
    vt_symbol="000001.SZSE",
    setting={
        "institution_threshold": 1000,
        "holding_days": 5,
    }
)

# 注入数据服务
strategy.data_service = strategy_data_service

# 初始化并启动
cta_engine.add_strategy(strategy)
strategy.inited = True
strategy.trading = True
```

### 8.2 策略参数配置

```python
# 策略参数
strategy_params = {
    # 机构席位策略
    "institution_threshold": 1000,  # 1000万
    "min_institution_count": 3,
    "holding_days": 5,
    "position_ratio": 0.1,

    # 北向资金策略
    "net_inflow_threshold": 10,     # 10亿
    "change_threshold": 0.05,        # 5%

    # 板块轮动
    "rotation_period": 20,
    "top_n": 3,

    # 可转债
    "premium_threshold": -5,
}
```

---

## 9. 风险控制

### 9.1 策略风控

```python
class RiskControlMixin:
    """风控混入类"""

    def check_risk_limits(self) -> bool:
        """检查风控限制"""
        # 检查单日最大亏损
        if self.check_daily_loss_limit():
            return False

        # 检查最大持仓
        if self.check_position_limit():
            return False

        # 检查ST股票
        if self.check_st_stock():
            return False

        # 检查涨跌停
        if self.check_limit_up_down():
            return False

        return True

    def check_daily_loss_limit(self) -> bool:
        """检查日止损"""
        account = self.cta_engine.get_account()
        if account:
            daily_pnl = account.balance - account.pre_balance
            if daily_pnl < -self.max_daily_loss:
                self.write_log(f"触发日止损: {daily_pnl}")
                return True
        return False

    def check_st_stock(self) -> bool:
        """检查ST股票"""
        # 实现ST股票检查逻辑
        pass

    def check_limit_up_down(self) -> bool:
        """检查涨跌停"""
        # 实现涨跌停检查逻辑
        pass
```

---

## 10. 已知依赖

### 10.1 内部依赖

| 模块 | 依赖内容 |
|-----|---------|
| vnpy_ctastrategy | CtaTemplate, CtaEngine |
| vnpy.trader.object | BarData, TickData, OrderRequest |
| vnpy_china_data | 数据服务接口 |
| vnpy_china_config | 配置管理 |

### 10.2 外部依赖

| 包 | 用途 | 版本 |
|---|------|-----|
| pandas | 数据处理 | >=1.5.0 |
| numpy | 数值计算 | >=1.21.0 |

---

## 11. 测试策略

### 11.1 单元测试

| 测试类 | 测试内容 |
|-------|---------|
| TestDragonTigerStrategy | 龙虎榜策略逻辑测试 |
| TestNorthboundStrategy | 北向资金策略逻辑测试 |
| TestSectorRotationStrategy | 板块轮动策略逻辑测试 |
| TestEventDrivenStrategy | 事件驱动策略逻辑测试 |
| TestConvertibleStrategy | 可转债策略逻辑测试 |

### 11.2 回测验证

- 使用历史数据进行回测
- 验证策略逻辑正确性
- 评估策略绩效指标

---

*文档结束*
