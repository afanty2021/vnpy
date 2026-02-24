# 行情数据分析设计文档

> 文档版本：v1.1
> 创建日期：2026-02-24
> 更新日期：2026-02-24
> 需求编号：REQ-011
> 优先级：P1
> 预计工时：8人天
>
> **变更记录**: 修正REQ编号（原REQ-007）

---

## 1. 设计目标

构建A股特色行情数据分析模块：

1. **Level-2行情分析**：买卖盘队列、逐笔成交、大单追踪、主力动向
2. **资金流向分析**：超大单、大单、中单、小单净流入
3. **技术指标增强**：涨跌停统计、连板天数、板块指数
4. **集合竞价分析**：竞价数据、量比、开盘预测

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     行情数据分析架构                               │
├─────────────────────────────────────────────────────────────────┤
│  【分析引擎】                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │Level2Analyzer│  │MoneyFlow    │  │Technical    │        │
│  │(Level-2分析) │  │Analyzer     │  │Analyzer     │        │
│  │              │  │(资金流向)    │  │(技术指标)    │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│  【指标计算】                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ OrderQueue   │  │ TickFlow    │  │ StockStats   │        │
│  │(委托队列)    │  │ (逐笔成交)   │  │ (股票统计)   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│  【集合竞价分析】                                                │
│  ┌──────────────┐  ┌──────────────┐                          │
│  │ AuctionData  │  │OpenPredict  │                          │
│  │(竞价数据)    │  │(开盘预测)   │                          │
│  └──────────────┘  └──────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块结构

```
vnpy_china_analysis/
├── __init__.py
├── level2/
│   ├── __init__.py
│   ├── analyzer.py           # Level-2分析器
│   ├── order_queue.py        # 委托队列分析
│   ├── tick_flow.py          # 逐笔成交分析
│   └── main_force.py         # 主力动向分析
├── money_flow/
│   ├── __init__.py
│   ├── analyzer.py           # 资金流向分析器
│   ├── classifier.py         # 资金分类
│   └── indicator.py          # 资金指标
├── technical/
│   ├── __init__.py
│   ├── analyzer.py           # 技术指标分析器
│   ├── limit_stats.py       # 涨跌停统计
│   └── sector_index.py      # 板块指数
└── auction/
    ├── __init__.py
    ├── analyzer.py           # 集合竞价分析器
    ├── volume_ratio.py       # 量比计算
    └── open_predict.py      # 开盘预测
```

---

## 3. 核心类设计

### 3.1 Level-2行情分析

```python
from vnpy.trader.object import TickData
from dataclasses import dataclass
from typing import List


@dataclass
class OrderQueueData:
    """委托队列数据"""
    symbol: str
    datetime: datetime

    # 卖盘委托队列 (10档)
    ask_price_1: float
    ask_volume_1: int
    ask_queue_1: List[int]  # 各档位委托数量

    # 买盘委托队列 (10档)
    bid_price_1: float
    bid_volume_1: int
    bid_queue_1: List[int]


@dataclass
class TickFlowData:
    """逐笔成交数据"""
    symbol: str
    datetime: datetime
    price: float
    volume: int
    direction: str   # buy/sell
    order_type: str  # market/limit


class Level2Analyzer:
    """Level-2行情分析器"""

    def __init__(self):
        self.order_queues: List[OrderQueueData] = []
        self.tick_flows: List[TickFlowData] = []

    def analyze_order_queue(self, tick: TickData) -> OrderQueueData:
        """分析委托队列"""
        # 计算委托队列变化
        pass

    def detect_large_order(self, tick_flow: TickFlowData, threshold: int = 500) -> bool:
        """检测大单"""
        return tick_flow.volume >= threshold

    def calculate_main_force(self, tick_flows: List[TickFlowData]) -> dict:
        """计算主力动向"""
        buy_volume = sum(t.volume for t in tick_flows if t.direction == "buy")
        sell_volume = sum(t.volume for t in tick_flows if t.direction == "sell")

        net_volume = buy_volume - sell_volume
        main_force_ratio = net_volume / (buy_volume + sell_volume) if (buy_volume + sell_volume) > 0 else 0

        return {
            "buy_volume": buy_volume,
            "sell_volume": sell_volume,
            "net_volume": net_volume,
            "main_force_ratio": main_force_ratio,
            "direction": "buy" if net_volume > 0 else "sell"
        }
```

### 3.2 资金流向分析

```python
from enum import Enum


class MoneyFlowLevel(Enum):
    """资金流向级别"""
    SUPER_LARGE = "super_large"  # 超大单 > 100万
    LARGE = "large"              # 大单 20-100万
    MEDIUM = "medium"            # 中单 5-20万
    SMALL = "small"              # 小单 < 5万


@dataclass
class MoneyFlowData:
    """资金流向数据"""
    symbol: str
    datetime: datetime

    # 分类资金
    super_large_inflow: float   # 超大单净流入
    large_inflow: float        # 大单净流入
    medium_inflow: float       # 中单净流入
    small_inflow: float        # 小单净流入

    # 汇总
    main_inflow: float         # 主力净流入 (超大+大单)
    net_inflow: float          # 总净流入


class MoneyFlowAnalyzer:
    """资金流向分析器"""

    def __init__(self):
        self.thresholds = {
            MoneyFlowLevel.SUPER_LARGE: 1_000_000,  # 100万
            MoneyFlowLevel.LARGE: 200_000,          # 20万
            MoneyFlowLevel.MEDIUM: 50_000,           # 5万
        }

    def classify_order(self, price: float, volume: int) -> MoneyFlowLevel:
        """分类订单"""
        amount = price * volume

        if amount >= self.thresholds[MoneyFlowLevel.SUPER_LARGE]:
            return MoneyFlowLevel.SUPER_LARGE
        elif amount >= self.thresholds[MoneyFlowLevel.LARGE]:
            return MoneyFlowLevel.LARGE
        elif amount >= self.thresholds[MoneyFlowLevel.MEDIUM]:
            return MoneyFlowLevel.MEDIUM
        else:
            return MoneyFlowLevel.SMALL

    def analyze_money_flow(
        self,
        tick_flows: List[TickFlowData]
    ) -> MoneyFlowData:
        """分析资金流向"""

        flows = {
            MoneyFlowLevel.SUPER_LARGE: 0,
            MoneyFlowLevel.LARGE: 0,
            MoneyFlowLevel.MEDIUM: 0,
            MoneyFlowLevel.SMALL: 0,
        }

        for flow in tick_flows:
            level = self.classify_order(flow.price, flow.volume)
            amount = flow.price * flow.volume

            if flow.direction == "buy":
                flows[level] += amount
            else:
                flows[level] -= amount

        return MoneyFlowData(
            symbol=tick_flows[0].symbol if tick_flows else "",
            datetime=datetime.now(),
            super_large_inflow=flows[MoneyFlowLevel.SUPER_LARGE],
            large_inflow=flows[MoneyFlowLevel.LARGE],
            medium_inflow=flows[MoneyFlowLevel.MEDIUM],
            small_inflow=flows[MoneyFlowLevel.SMALL],
            main_inflow=flows[MoneyFlowLevel.SUPER_LARGE] + flows[MoneyFlowLevel.LARGE],
            net_inflow=sum(flows.values())
        )
```

### 3.3 技术指标增强

```python
class LimitStatsAnalyzer:
    """涨跌停统计分析器"""

    def __init__(self):
        self.limit_up_days: dict[str, int] = {}   # 连续涨停天数
        self.limit_down_days: dict[str, int] = {}  # 连续跌停天数

    def update(self, symbol: str, is_limit_up: bool, is_limit_down: bool):
        """更新涨跌停状态"""

        if is_limit_up:
            self.limit_up_days[symbol] = self.limit_up_days.get(symbol, 0) + 1
            self.limit_down_days[symbol] = 0
        elif is_limit_down:
            self.limit_down_days[symbol] = self.limit_down_days.get(symbol, 0) + 1
            self.limit_up_days[symbol] = 0
        else:
            self.limit_up_days[symbol] = 0
            self.limit_down_days[symbol] = 0

    def get_limit_stats(self, symbol: str) -> dict:
        """获取涨跌停统计"""
        return {
            "limit_up_days": self.limit_up_days.get(symbol, 0),
            "limit_down_days": self.limit_down_days.get(symbol, 0),
            "is_in_limit_up": self.limit_up_days.get(symbol, 0) > 0,
            "is_in_limit_down": self.limit_down_days.get(symbol, 0) > 0,
        }


class SectorIndexCalculator:
    """板块指数计算器"""

    def calculate_index(
        self,
        stocks: List[str],
        weights: List[float] = None
    ) -> float:
        """计算板块指数"""
        if not stocks:
            return 0

        weights = weights or [1.0 / len(stocks)] * len(stocks)

        total_return = 0
        for stock, weight in zip(stocks, weights):
            returns = self.get_stock_return(stock)
            total_return += returns * weight

        return total_return
```

### 3.4 集合竞价分析

```python
@dataclass
class AuctionData:
    """集合竞价数据"""
    symbol: str
    date: date

    # 竞价数据
    pre_close: float         # 昨日收盘价
    auction_price: float     # 竞价成交价
    auction_volume: int     # 竞价成交量

    # 委托数据
    total_buy_volume: int    # 总买委托量
    total_sell_volume: int  # 总卖委托量

    # 计算指标
    volume_ratio: float     # 量比
    amplitude: float        # 竞价振幅


class AuctionAnalyzer:
    """集合竞价分析器"""

    def __init__(self):
        self.history_data: Dict[str, List[AuctionData]] = {}

    def analyze(self, symbol: str, date: date) -> AuctionData:
        """分析集合竞价"""

        # 获取竞价数据
        auction_price = self.get_auction_price(symbol, date)
        auction_volume = self.get_auction_volume(symbol, date)
        pre_close = self.get_pre_close(symbol, date)

        # 计算量比
        avg_volume = self.get_avg_volume(symbol, days=5)
        volume_ratio = auction_volume / avg_volume if avg_volume > 0 else 0

        # 计算振幅
        amplitude = abs(auction_price - pre_close) / pre_close if pre_close > 0 else 0

        return AuctionData(
            symbol=symbol,
            date=date,
            pre_close=pre_close,
            auction_price=auction_price,
            auction_volume=auction_volume,
            volume_ratio=volume_ratio,
            amplitude=amplitude
        )

    def predict_open_price(
        self,
        auction_data: AuctionData
    ) -> float:
        """预测开盘价"""

        # 基于竞价量和竞价价格预测
        # 如果买盘委托量大，开盘可能高开
        # 如果卖盘委托量大，开盘可能低开

        buy_ratio = auction_data.total_buy_volume / (
            auction_data.total_buy_volume + auction_data.total_sell_volume
        ) if auction_data.total_buy_volume + auction_data.total_sell_volume > 0 else 0.5

        # 简单预测模型
        predicted_price = auction_data.pre_close * (
            1 + (buy_ratio - 0.5) * 0.02  # 最大2%波动
        )

        return predicted_price
```

---

## 4. 实施计划

| 阶段 | 任务 | 预估工时 |
|------|------|---------|
| 1 | 创建目录结构 | 0.5人天 |
| 2 | 实现Level-2行情分析 | 2人天 |
| 3 | 实现资金流向分析 | 2人天 |
| 4 | 实现技术指标增强 | 1.5人天 |
| 5 | 实现集合竞价分析 | 1.5人天 |
| 6 | 集成测试 | 0.5人天 |
| 合计 | | **8人天** |

---

## 5. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-02-24 | 初始版本 |
