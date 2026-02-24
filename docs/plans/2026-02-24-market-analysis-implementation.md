# 行情数据分析系统实施方案

> 文档版本：v1.0
> 创建日期：2026-02-24
> 需求编号：REQ-008
> 优先级：P1
> 预计工时：8人天
> 实施周期：2周

---

## 1. 方案概述

### 1.1 项目背景

A股市场具有独特的微观结构特征，如Level-2行情、资金流向、集合竞价等。本方案旨在为VeighNa A股交易系统构建专业的行情数据分析能力，为策略决策提供丰富的市场微观结构信息。

### 1.2 实施目标

| 目标类别 | 具体目标 | 成功标准 |
|---------|---------|---------|
| Level-2分析 | 实现十档行情、逐笔成交、主力动向分析 | 支持QMT Level-2数据 |
| 资金流向 | 超大单/大单/中单/小单分类统计 | 分类准确率≥95% |
| 技术指标增强 | 涨跌停统计、连板天数、板块指数 | 实时计算延迟<100ms |
| 集合竞价 | 竞价数据分析、开盘预测 | 预测准确率≥60% |

### 1.3 交付物清单

| 序号 | 交付物 | 类型 | 说明 |
|------|--------|------|------|
| 1 | vnpy_china_analysis模块 | 代码 | 行情分析核心模块 |
| 2 | 单元测试 | 代码 | pytest测试套件 |
| 3 | 数据源适配器 | 代码 | QMT/Tushare数据适配 |
| 4 | 使用示例 | 代码 | 示例策略和脚本 |
| 5 | API文档 | 文档 | 接口说明文档 |
| 6 | 实施报告 | 文档 | 开发过程总结 |

---

## 2. 技术架构设计

### 2.1 模块结构

```
vnpy_china_analysis/
├── __init__.py                     # 模块入口
├── level2/                         # Level-2行情分析
│   ├── __init__.py
│   ├── analyzer.py                 # Level-2分析器
│   ├── order_queue.py              # 委托队列分析
│   ├── tick_flow.py                # 逐笔成交分析
│   └── main_force.py               # 主力动向分析
├── money_flow/                     # 资金流向分析
│   ├── __init__.py
│   ├── analyzer.py                 # 资金流向分析器
│   ├── classifier.py               # 资金分类器
│   └── indicator.py                # 资金指标计算
├── technical/                      # 技术指标增强
│   ├── __init__.py
│   ├── analyzer.py                 # 技术指标分析器
│   ├── limit_stats.py              # 涨跌停统计
│   └── sector_index.py             # 板块指数计算
├── auction/                        # 集合竞价分析
│   ├── __init__.py
│   ├── analyzer.py                 # 竞价分析器
│   ├── volume_ratio.py             # 量比计算
│   └── open_predict.py             # 开盘预测
├── objects/                        # 数据对象定义
│   ├── __init__.py
│   └── types.py                    # 类型定义
├── adapters/                       # 数据源适配器
│   ├── __init__.py
│   ├── qmt_adapter.py              # QMT数据适配
│   └── tushare_adapter.py          # Tushare数据适配
└── utils/                          # 工具函数
    ├── __init__.py
    └── helpers.py                  # 辅助函数
```

### 2.2 类图设计

```
┌─────────────────────────────────────────────────────────────────┐
│                     Level2Analyzer                              │
│                   (Level-2行情分析器)                            │
├─────────────────────────────────────────────────────────────────┤
│ -order_queue_data: Dict[str, OrderQueueData]                   │
│ -tick_flow_history: List[TickFlowData]                         │
├─────────────────────────────────────────────────────────────────┤
│ +analyze_order_queue(tick) -> OrderQueueData                   │
│ +analyze_tick_flow(ticks) -> List[TickFlowData]                │
│ +detect_large_order(flow, threshold) -> bool                   │
│ +calculate_main_force(flows) -> MainForceData                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    MoneyFlowAnalyzer                            │
│                     (资金流向分析器)                             │
├─────────────────────────────────────────────────────────────────┤
│ -thresholds: Dict[MoneyFlowLevel, float]                       │
│ -flow_history: Dict[str, List[MoneyFlowData]]                 │
├─────────────────────────────────────────────────────────────────┤
│ +classify_order(price, volume) -> MoneyFlowLevel              │
│ +analyze_money_flow(tick_flows) -> MoneyFlowData               │
│ +get_main_inflow(symbol) -> float                             │
│ +get_net_inflow(symbol) -> float                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  LimitStatsAnalyzer                             │
│                    (涨跌停统计分析器)                            │
├─────────────────────────────────────────────────────────────────┤
│ -limit_up_days: Dict[str, int]                                 │
│ -limit_down_days: Dict[str, int]                               │
├─────────────────────────────────────────────────────────────────┤
│ +update(symbol, is_limit_up, is_limit_down) -> None           │
│ +get_limit_stats(symbol) -> LimitStats                        │
│ +get_continuous_limit_up(symbol) -> int                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   AuctionAnalyzer                               │
│                    (集合竞价分析器)                              │
├─────────────────────────────────────────────────────────────────┤
│ -auction_history: Dict[str, List[AuctionData]]                │
├─────────────────────────────────────────────────────────────────┤
│ +analyze(symbol, date) -> AuctionData                         │
│ +predict_open_price(auction_data) -> float                    │
│ +get_volume_ratio(symbol, date) -> float                      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 数据流设计

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  数据源层     │ ──>  │  适配器层     │ ──>  │  分析引擎层   │
├──────────────┤      ├──────────────┤      ├──────────────┤
│ • QMT Gateway│      │ • QMT Adapter │      │ • Level2     │
│ • Tushare    │      │ • Ts Adapter  │      │ • MoneyFlow  │
│ • 本地数据   │      │ • Cache       │      │ • Technical  │
└──────────────┘      └──────────────┘      │ • Auction    │
                                              └──────────────┘
                                                     │
                                                     v
                                              ┌──────────────┐
                                              │  应用层      │
                                              ├──────────────┤
                                              │ • 策略调用   │
                                              │ • 监控展示   │
                                              │ • 报表生成   │
                                              └──────────────┘
```

---

## 3. 详细实施计划

### 3.1 第一阶段：基础框架（0.5人天）

#### 任务1.1：创建目录结构

```bash
# 创建模块根目录
mkdir -p vnpy_china_analysis

# 创建子目录
mkdir -p vnpy_china_analysis/level2
mkdir -p vnpy_china_analysis/money_flow
mkdir -p vnpy_china_analysis/technical
mkdir -p vnpy_china_analysis/auction
mkdir -p vnpy_china_analysis/objects
mkdir -p vnpy_china_analysis/adapters
mkdir -p vnpy_china_analysis/utils

# 创建测试目录
mkdir -p tests/analysis
```

#### 任务1.2：定义核心数据类型

**文件位置**：`vnpy_china_analysis/objects/types.py`

```python
from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Dict, Optional
from enum import Enum


class MoneyFlowLevel(Enum):
    """资金流向级别"""
    SUPER_LARGE = "super_large"    # 超大单 > 100万
    LARGE = "large"                # 大单 20-100万
    MEDIUM = "medium"              # 中单 5-20万
    SMALL = "small"                # 小单 < 5万


class LimitType(Enum):
    """涨跌停类型"""
    LIMIT_UP = "limit_up"          # 涨停
    LIMIT_DOWN = "limit_down"      # 跌停
    NORMAL = "normal"              # 正常


@dataclass
class OrderQueueData:
    """委托队列数据"""
    symbol: str
    datetime: datetime

    # 卖盘队列（10档）
    ask_prices: List[float]        # 卖价 [ask1...ask10]
    ask_volumes: List[int]         # 卖量
    ask_queue: List[List[int]]     # 各档位委托明细

    # 买盘队列（10档）
    bid_prices: List[float]        # 买价 [bid1...bid10]
    bid_volumes: List[int]         # 买量
    bid_queue: List[List[int]]     # 各档位委托明细


@dataclass
class TickFlowData:
    """逐笔成交数据"""
    symbol: str
    datetime: datetime
    price: float
    volume: int
    amount: float                  # 成交金额
    direction: str                 # buy/sell
    function_code: int             # 成交性质


@dataclass
class MainForceData:
    """主力动向数据"""
    symbol: str
    datetime: datetime
    buy_volume: float              # 买入成交量
    sell_volume: float             # 卖出成交量
    net_volume: float              # 凑成交量
    main_force_ratio: float        # 主力净流入比例
    direction: str                 # 主力方向 buy/sell/neutral


@dataclass
class MoneyFlowData:
    """资金流向数据"""
    symbol: str
    datetime: datetime

    # 分类资金流向（元）
    super_large_inflow: float      # 超大单净流入
    large_inflow: float            # 大单净流入
    medium_inflow: float           # 中单净流入
    small_inflow: float            # 小单净流入

    # 汇总指标
    main_inflow: float             # 主力净流入 (超大+大单)
    retail_inflow: float           # 散户净流入 (中+小单)
    net_inflow: float              # 总净流入


@dataclass
class LimitStats:
    """涨跌停统计"""
    symbol: str
    date: date
    limit_up_days: int             # 连续涨停天数
    limit_down_days: int           # 连续跌停天数
    is_limit_up: bool              # 今日涨停
    is_limit_down: bool            # 今日跌停
    limit_up_count: int            # 历史涨停次数
    limit_down_count: int          # 历史跌停次数


@dataclass
class SectorIndexData:
    """板块指数数据"""
    sector_code: str               # 板块代码
    sector_name: str               # 板块名称
    datetime: datetime
    index_value: float             # 指数值
    change_pct: float              # 涨跌幅
    volume: float                  # 成交量
    turnover: float                # 换手率
    leading_stocks: List[str]      # 领涨股票


@dataclass
class AuctionData:
    """集合竞价数据"""
    symbol: str
    date: date

    # 基础数据
    pre_close: float               # 昨收
    auction_price: float           # 竞价成交价
    auction_volume: int            # 竞价成交量
    auction_amount: float          # 竞价成交额

    # 委托数据
    total_buy_volume: int          # 总买委托量
    total_sell_volume: int         # 总卖委托量
    buy_orders: int                # 买委托笔数
    sell_orders: int               # 卖委托笔数

    # 计算指标
    volume_ratio: float            # 量比（竞价量/平均量）
    amplitude: float               # 竞价振幅
    buy_sell_ratio: float          # 买卖比
    open_prediction: float         # 开盘价预测


@dataclass
class AnalysisSignal:
    """分析信号"""
    symbol: str
    datetime: datetime
    signal_type: str               # 信号类型
    signal_value: float            # 信号值
    confidence: float              # 信号置信度
    reason: str                    # 信号原因
```

#### 任务1.3：创建分析器基类

**文件位置**：`vnpy_china_analysis/base.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime


class BaseAnalyzer(ABC):
    """
    分析器基类

    所有行情分析器应继承此类，实现统一的接口。
    """

    def __init__(self) -> None:
        """构造函数"""
        self.data_cache: Dict[str, List] = {}

    @abstractmethod
    def analyze(self, symbol: str, data: dict) -> dict:
        """
        分析行情数据

        Args:
            symbol: 股票代码
            data: 原始行情数据

        Returns:
            分析结果字典
        """
        pass

    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """
        清理缓存

        Args:
            symbol: 指定股票代码，None表示清理全部
        """
        if symbol:
            self.data_cache.pop(symbol, None)
        else:
            self.data_cache.clear()

    def get_cached_data(self, symbol: str) -> List:
        """获取缓存数据"""
        return self.data_cache.get(symbol, [])

    def update_cache(self, symbol: str, data: dict, max_size: int = 1000) -> None:
        """更新缓存"""
        if symbol not in self.data_cache:
            self.data_cache[symbol] = []

        self.data_cache[symbol].append(data)

        # 限制缓存大小
        if len(self.data_cache[symbol]) > max_size:
            self.data_cache[symbol] = self.data_cache[symbol][-max_size:]
```

**验收标准**：
- [ ] 目录结构完整
- [ ] 数据类型定义完整
- [ ] 基类接口清晰
- [ ] 通过类型检查

---

### 3.2 第二阶段：Level-2行情分析（2人天）

#### 任务2.1：委托队列分析器

**文件位置**：`vnpy_china_analysis/level2/order_queue.py`

```python
from typing import List, Dict
from datetime import datetime
from ..objects.types import OrderQueueData
from ..base import BaseAnalyzer


class OrderQueueAnalyzer(BaseAnalyzer):
    """
    委托队列分析器

    分析十档买卖盘的委托队列变化，识别支撑阻力位。
    """

    def __init__(self) -> None:
        super().__init__()
        self.queue_history: Dict[str, List[OrderQueueData]] = {}

    def analyze(self, symbol: str, data: dict) -> OrderQueueData:
        """
        分析委托队列

        Args:
            symbol: 股票代码
            data: 包含十档行情的字典

        Returns:
            OrderQueueData对象
        """
        order_queue = OrderQueueData(
            symbol=symbol,
            datetime=datetime.now(),
            ask_prices=data.get("ask_prices", []),
            ask_volumes=data.get("ask_volumes", []),
            ask_queue=data.get("ask_queue", []),
            bid_prices=data.get("bid_prices", []),
            bid_volumes=data.get("bid_volumes", []),
            bid_queue=data.get("bid_queue", [])
        )

        # 更新历史
        if symbol not in self.queue_history:
            self.queue_history[symbol] = []
        self.queue_history[symbol].append(order_queue)

        return order_queue

    def get_support_level(self, symbol: str) -> Dict:
        """
        识别支撑位

        通过分析买盘委托量，识别强支撑价位。

        Returns:
            {"price": 支撑价位, "strength": 强度}
        """
        if symbol not in self.queue_history or not self.queue_history[symbol]:
            return {}

        latest = self.queue_history[symbol][-1]

        # 计算各档位的委托强度
        max_strength = 0
        support_price = 0

        for i, (price, volume) in enumerate(zip(latest.bid_prices, latest.bid_volumes)):
            if volume <= 0:
                continue

            # 计算强度（价格越接近现价，权重越高）
            strength = volume * (1 - i * 0.1)

            if strength > max_strength:
                max_strength = strength
                support_price = price

        return {
            "price": support_price,
            "strength": max_strength
        }

    def get_resistance_level(self, symbol: str) -> Dict:
        """
        识别阻力位

        通过分析卖盘委托量，识别强阻力价位。
        """
        if symbol not in self.queue_history or not self.queue_history[symbol]:
            return {}

        latest = self.queue_history[symbol][-1]

        max_strength = 0
        resistance_price = 0

        for i, (price, volume) in enumerate(zip(latest.ask_prices, latest.ask_volumes)):
            if volume <= 0:
                continue

            strength = volume * (1 - i * 0.1)

            if strength > max_strength:
                max_strength = strength
                resistance_price = price

        return {
            "price": resistance_price,
            "strength": max_strength
        }

    def detect_queue_anomaly(self, symbol: str) -> Dict:
        """
        检测委托队列异常

        识别突然的大单挂单或撤单。
        """
        if symbol not in self.queue_history or len(self.queue_history[symbol]) < 2:
            return {}

        current = self.queue_history[symbol][-1]
        previous = self.queue_history[symbol][-2]

        anomalies = []

        # 检测买盘异常
        for i in range(min(5, len(current.bid_volumes))):
            change = current.bid_volumes[i] - previous.bid_volumes[i]
            if abs(change) > 1000:  # 变化超过1000手
                anomalies.append({
                    "side": "buy",
                    "level": i + 1,
                    "change": change,
                    "current_volume": current.bid_volumes[i]
                })

        # 检测卖盘异常
        for i in range(min(5, len(current.ask_volumes))):
            change = current.ask_volumes[i] - previous.ask_volumes[i]
            if abs(change) > 1000:
                anomalies.append({
                    "side": "sell",
                    "level": i + 1,
                    "change": change,
                    "current_volume": current.ask_volumes[i]
                })

        return {"anomalies": anomalies}
```

**测试用例**：
```python
def test_order_queue_analyzer():
    """测试委托队列分析器"""
    analyzer = OrderQueueAnalyzer()

    # 构造测试数据
    data = {
        "ask_prices": [10.05, 10.06, 10.07],
        "ask_volumes": [1000, 2000, 1500],
        "bid_prices": [10.00, 9.99, 9.98],
        "bid_volumes": [5000, 3000, 2000]
    }

    result = analyzer.analyze("000001", data)

    assert result.symbol == "000001"
    assert len(result.bid_prices) == 3

    # 测试支撑位识别
    support = analyzer.get_support_level("000001")
    assert support["price"] == 10.00  # 最强支撑在买一
```

#### 任务2.2：逐笔成交分析器

**文件位置**：`vnpy_china_analysis/level2/tick_flow.py`

```python
from typing import List, Dict
from datetime import datetime
from ..objects.types import TickFlowData
from ..base import BaseAnalyzer


class TickFlowAnalyzer(BaseAnalyzer):
    """
    逐笔成交分析器

    分析逐笔成交数据，识别大单交易和主力行为。
    """

    def __init__(self, large_threshold: int = 500) -> None:
        """
        Args:
            large_threshold: 大单阈值（手）
        """
        super().__init__()
        self.large_threshold = large_threshold
        self.tick_history: Dict[str, List[TickFlowData]] = {}

    def analyze(self, symbol: str, data: dict) -> TickFlowData:
        """分析逐笔成交"""
        tick_flow = TickFlowData(
            symbol=symbol,
            datetime=datetime.fromtimestamp(data.get("time", 0)),
            price=data.get("price", 0.0),
            volume=data.get("volume", 0),
            amount=data.get("amount", 0.0),
            direction=data.get("direction", "buy"),
            function_code=data.get("function_code", 0)
        )

        # 更新历史
        if symbol not in self.tick_history:
            self.tick_history[symbol] = []
        self.tick_history[symbol].append(tick_flow)

        return tick_flow

    def detect_large_orders(self, symbol: str, minutes: int = 5) -> List[TickFlowData]:
        """
        检测近期大单

        Args:
            symbol: 股票代码
            minutes: 统计时间窗口（分钟）

        Returns:
            大单列表
        """
        if symbol not in self.tick_history:
            return []

        now = datetime.now()
        cutoff_time = now.timestamp() - minutes * 60

        large_orders = [
            tick for tick in self.tick_history[symbol]
            if tick.datetime.timestamp() >= cutoff_time
            and tick.volume >= self.large_threshold
        ]

        return large_orders

    def analyze_tick_pattern(self, symbol: str) -> Dict:
        """
        分析成交模式

        识别主动买入/卖出、扫单等模式。
        """
        if symbol not in self.tick_history or len(self.tick_history[symbol]) < 10:
            return {}

        recent_ticks = self.tick_history[symbol][-100:]

        # 统计主动买卖
        aggressive_buy = sum(
            t.volume for t in recent_ticks
            if t.direction == "buy" and t.function_code in [1, 3]  # 主动买/扫单
        )
        aggressive_sell = sum(
            t.volume for t in recent_ticks
            if t.direction == "sell" and t.function_code in [2, 4]  # 主动卖/扫单
        )

        # 计算主动性比率
        total = aggressive_buy + aggressive_sell
        aggressive_ratio = aggressive_buy / total if total > 0 else 0.5

        return {
            "aggressive_buy": aggressive_buy,
            "aggressive_sell": aggressive_sell,
            "aggressive_ratio": aggressive_ratio,
            "pattern": "strong_buy" if aggressive_ratio > 0.6 else
                      "strong_sell" if aggressive_ratio < 0.4 else
                      "neutral"
        }
```

#### 任务2.3：主力动向分析器

**文件位置**：`vnpy_china_analysis/level2/main_force.py`

```python
from typing import List, Dict
from datetime import datetime, timedelta
from ..objects.types import MainForceData, TickFlowData
from ..base import BaseAnalyzer


class MainForceAnalyzer(BaseAnalyzer):
    """
    主力动向分析器

    通过分析大单交易，判断主力资金的进出方向。
    """

    def __init__(self) -> None:
        super().__init__()
        self.main_force_history: Dict[str, List[MainForceData]] = {}

    def analyze(
        self,
        symbol: str,
        tick_flows: List[TickFlowData],
        window_minutes: int = 5
    ) -> MainForceData:
        """
        分析主力动向

        Args:
            symbol: 股票代码
            tick_flows: 逐笔成交列表
            window_minutes: 时间窗口（分钟）

        Returns:
            MainForceData对象
        """
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=window_minutes)

        # 筛选时间窗口内的成交
        window_flows = [
            t for t in tick_flows
            if t.datetime >= cutoff_time
        ]

        if not window_flows:
            return MainForceData(
                symbol=symbol,
                datetime=now,
                buy_volume=0,
                sell_volume=0,
                net_volume=0,
                main_force_ratio=0,
                direction="neutral"
            )

        # 分别统计买卖（只统计大单）
        large_threshold = 200  # 200手以上为大单

        buy_volume = sum(
            t.amount for t in window_flows
            if t.direction == "buy" and t.volume >= large_threshold
        )
        sell_volume = sum(
            t.amount for t in window_flows
            if t.direction == "sell" and t.volume >= large_threshold
        )

        net_volume = buy_volume - sell_volume
        total_volume = buy_volume + sell_volume

        main_force_ratio = net_volume / total_volume if total_volume > 0 else 0

        # 判断方向
        if main_force_ratio > 0.1:
            direction = "buy"
        elif main_force_ratio < -0.1:
            direction = "sell"
        else:
            direction = "neutral"

        main_force = MainForceData(
            symbol=symbol,
            datetime=now,
            buy_volume=buy_volume,
            sell_volume=sell_volume,
            net_volume=net_volume,
            main_force_ratio=main_force_ratio,
            direction=direction
        )

        # 更新历史
        if symbol not in self.main_force_history:
            self.main_force_history[symbol] = []
        self.main_force_history[symbol].append(main_force)

        return main_force

    def get_main_force_trend(self, symbol: str, periods: int = 5) -> Dict:
        """
        获取主力趋势

        Args:
            symbol: 股票代码
            periods: 统计周期数

        Returns:
            {"trend": "up/down/neutral", "strength": 强度}
        """
        if symbol not in self.main_force_history:
            return {}

        history = self.main_force_history[symbol][-periods:]
        if len(history) < periods:
            return {}

        # 计算趋势
        net_volumes = [h.net_volume for h in history]

        if sum(net_volumes) > 0 and all(v >= 0 for v in net_volumes[-3:]):
            return {"trend": "up", "strength": "strong"}
        elif sum(net_volumes) < 0 and all(v <= 0 for v in net_volumes[-3:]):
            return {"trend": "down", "strength": "strong"}
        elif sum(net_volumes) > 0:
            return {"trend": "up", "strength": "weak"}
        elif sum(net_volumes) < 0:
            return {"trend": "down", "strength": "weak"}
        else:
            return {"trend": "neutral", "strength": "none"}
```

**验收标准**：
- [ ] 所有分析器实现完整
- [ ] 测试用例通过
- [ ] 性能满足要求（<100ms）

---

### 3.3 第三阶段：资金流向分析（2人天）

#### 任务3.1：资金分类器

**文件位置**：`vnpy_china_analysis/money_flow/classifier.py`

```python
from ..objects.types import MoneyFlowLevel


class MoneyFlowClassifier:
    """
    资金流向分类器

    根据成交金额将订单分类为超大单、大单、中单、小单。
    """

    # 默认阈值（元）
    DEFAULT_THRESHOLDS = {
        MoneyFlowLevel.SUPER_LARGE: 1_000_000,   # 100万
        MoneyFlowLevel.LARGE: 200_000,           # 20万
        MoneyFlowLevel.MEDIUM: 50_000,           # 5万
    }

    def __init__(self, thresholds: dict = None) -> None:
        """
        Args:
            thresholds: 自定义阈值
        """
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS

    def classify(self, price: float, volume: int) -> MoneyFlowLevel:
        """
        分类订单

        Args:
            price: 成交价格
            volume: 成交数量（手）

        Returns:
            资金级别
        """
        amount = price * volume * 100  # 转换为元

        if amount >= self.thresholds[MoneyFlowLevel.SUPER_LARGE]:
            return MoneyFlowLevel.SUPER_LARGE
        elif amount >= self.thresholds[MoneyFlowLevel.LARGE]:
            return MoneyFlowLevel.LARGE
        elif amount >= self.thresholds[MoneyFlowLevel.MEDIUM]:
            return MoneyFlowLevel.MEDIUM
        else:
            return MoneyFlowLevel.SMALL

    def classify_batch(self, trades: List[dict]) -> Dict[MoneyFlowLevel, List[dict]]:
        """
        批量分类

        Args:
            trades: 交易列表

        Returns:
            {级别: 交易列表}
        """
        result = {
            MoneyFlowLevel.SUPER_LARGE: [],
            MoneyFlowLevel.LARGE: [],
            MoneyFlowLevel.MEDIUM: [],
            MoneyFlowLevel.SMALL: [],
        }

        for trade in trades:
            level = self.classify(trade["price"], trade["volume"])
            result[level].append(trade)

        return result
```

#### 任务3.2：资金流向分析器

**文件位置**：`vnpy_china_analysis/money_flow/analyzer.py`

```python
from typing import List, Dict
from datetime import datetime, timedelta
from ..objects.types import MoneyFlowData, TickFlowData, MoneyFlowLevel
from .classifier import MoneyFlowClassifier
from ..base import BaseAnalyzer


class MoneyFlowAnalyzer(BaseAnalyzer):
    """
    资金流向分析器

    分析各层级的资金进出情况。
    """

    def __init__(self, thresholds: dict = None) -> None:
        super().__init__()
        self.classifier = MoneyFlowClassifier(thresholds)
        self.flow_history: Dict[str, List[MoneyFlowData]] = {}

    def analyze(
        self,
        symbol: str,
        tick_flows: List[TickFlowData],
        window_minutes: int = 5
    ) -> MoneyFlowData:
        """
        分析资金流向

        Args:
            symbol: 股票代码
            tick_flows: 逐笔成交列表
            window_minutes: 时间窗口

        Returns:
            MoneyFlowData对象
        """
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=window_minutes)

        # 筛选时间窗口内的成交
        window_flows = [
            t for t in tick_flows
            if t.datetime >= cutoff_time
        ]

        # 初始化各层级资金流向
        flows = {
            MoneyFlowLevel.SUPER_LARGE: 0.0,
            MoneyFlowLevel.LARGE: 0.0,
            MoneyFlowLevel.MEDIUM: 0.0,
            MoneyFlowLevel.SMALL: 0.0,
        }

        # 统计各层级资金
        for flow in window_flows:
            level = self.classifier.classify(flow.price, flow.volume)
            amount = flow.price * flow.volume * 100

            if flow.direction == "buy":
                flows[level] += amount
            else:
                flows[level] -= amount

        # 汇总
        main_inflow = flows[MoneyFlowLevel.SUPER_LARGE] + flows[MoneyFlowLevel.LARGE]
        retail_inflow = flows[MoneyFlowLevel.MEDIUM] + flows[MoneyFlowLevel.SMALL]
        net_inflow = sum(flows.values())

        money_flow = MoneyFlowData(
            symbol=symbol,
            datetime=now,
            super_large_inflow=flows[MoneyFlowLevel.SUPER_LARGE],
            large_inflow=flows[MoneyFlowLevel.LARGE],
            medium_inflow=flows[MoneyFlowLevel.MEDIUM],
            small_inflow=flows[MoneyFlowLevel.SMALL],
            main_inflow=main_inflow,
            retail_inflow=retail_inflow,
            net_inflow=net_inflow
        )

        # 更新历史
        if symbol not in self.flow_history:
            self.flow_history[symbol] = []
        self.flow_history[symbol].append(money_flow)

        return money_flow

    def get_cumulative_flow(
        self,
        symbol: str,
        days: int = 1
    ) -> Dict[str, float]:
        """
        获取累计资金流向

        Args:
            symbol: 股票代码
            days: 统计天数

        Returns:
            {"super_large": ..., "large": ..., ...}
        """
        if symbol not in self.flow_history:
            return {}

        cutoff = datetime.now() - timedelta(days=days)

        flows = [
            f for f in self.flow_history[symbol]
            if f.datetime >= cutoff
        ]

        if not flows:
            return {}

        return {
            "super_large": sum(f.super_large_inflow for f in flows),
            "large": sum(f.large_inflow for f in flows),
            "medium": sum(f.medium_inflow for f in flows),
            "small": sum(f.small_inflow for f in flows),
            "main": sum(f.main_inflow for f in flows),
            "net": sum(f.net_inflow for f in flows),
        }

    def detect_flow_anomaly(self, symbol: str) -> Dict:
        """
        检测资金异常

        识别突然的大额资金进出。
        """
        if symbol not in self.flow_history or len(self.flow_history[symbol]) < 10:
            return {}

        recent = self.flow_history[symbol][-5:]
        previous = self.flow_history[symbol][-10:-5]

        if not previous:
            return {}

        # 计算平均值
        avg_main_flow = sum(f.main_inflow for f in previous) / len(previous)

        # 检测异常
        anomalies = []
        for flow in recent:
            change = flow.main_inflow - avg_main_flow
            if abs(change) > abs(avg_main_flow) * 2:  # 变化超过2倍
                anomalies.append({
                    "datetime": flow.datetime,
                    "main_inflow": flow.main_inflow,
                    "change": change,
                    "type": "inflow" if change > 0 else "outflow"
                })

        return {"anomalies": anomalies}
```

#### 任务3.3：资金指标计算器

**文件位置**：`vnpy_china_analysis/money_flow/indicator.py`

```python
from typing import List, Dict
from ..objects.types import MoneyFlowData


class MoneyFlowIndicator:
    """
    资金流向指标计算器

    计算各种资金流向相关的技术指标。
    """

    def calculate_mfi(
        self,
        flow_history: List[MoneyFlowData],
        period: int = 14
    ) -> float:
        """
        计算资金流量指标 (Money Flow Index)

        MFI = 100 - 100 / (1 + 资金流量比率)

        资金流量比率 = 正资金流量 / 负资金流量

        Args:
            flow_history: 资金流向历史
            period: 周期

        Returns:
            MFI值 (0-100)
        """
        if len(flow_history) < period:
            return 50.0

        recent = flow_history[-period:]

        positive_flow = 0.0
        negative_flow = 0.0

        for flow in recent:
            if flow.net_inflow > 0:
                positive_flow += flow.net_inflow
            else:
                negative_flow += abs(flow.net_inflow)

        if negative_flow == 0:
            return 100.0

        money_ratio = positive_flow / negative_flow
        mfi = 100 - (100 / (1 + money_ratio))

        return mfi

    def calculate_flow_strength(
        self,
        flow_history: List[MoneyFlowData],
        period: int = 5
    ) -> Dict[str, float]:
        """
        计算资金强度

        Args:
            flow_history: 资金流向历史
            period: 周期

        Returns:
            {"main_strength": ..., "retail_strength": ...}
        """
        if len(flow_history) < period:
            return {}

        recent = flow_history[-period:]

        avg_main = sum(abs(f.main_inflow) for f in recent) / period
        avg_retail = sum(abs(f.retail_inflow) for f in recent) / period
        total = avg_main + avg_retail

        if total == 0:
            return {"main_strength": 0, "retail_strength": 0}

        return {
            "main_strength": avg_main / total,
            "retail_strength": avg_retail / total
        }

    def get_flow_signal(
        self,
        current_flow: MoneyFlowData,
        mfi: float,
        strength: Dict[str, float]
    ) -> Dict:
        """
        生成资金流向信号

        Args:
            current_flow: 当前资金流向
            mfi: 资金流量指标
            strength: 资金强度

        Returns:
            {"signal": "buy/sell/neutral", "confidence": 置信度}
        """
        signals = []

        # MFI信号
        if mfi > 80:
            signals.append(("sell", 0.7))  # 超买
        elif mfi < 20:
            signals.append(("buy", 0.7))   # 超卖

        # 主力资金信号
        if current_flow.main_inflow > 1_000_000:  # 主力净流入>100万
            signals.append(("buy", 0.8))
        elif current_flow.main_inflow < -1_000_000:
            signals.append(("sell", 0.8))

        # 资金强度信号
        if strength.get("main_strength", 0) > 0.7:  # 主力占主导
            if current_flow.main_inflow > 0:
                signals.append(("buy", 0.6))
            else:
                signals.append(("sell", 0.6))

        # 汇总信号
        if not signals:
            return {"signal": "neutral", "confidence": 0.5}

        buy_score = sum(s[1] for s in signals if s[0] == "buy")
        sell_score = sum(s[1] for s in signals if s[0] == "sell")

        if buy_score > sell_score * 1.5:
            return {"signal": "buy", "confidence": min(buy_score / 2, 1.0)}
        elif sell_score > buy_score * 1.5:
            return {"signal": "sell", "confidence": min(sell_score / 2, 1.0)}
        else:
            return {"signal": "neutral", "confidence": 0.5}
```

**验收标准**：
- [ ] 资金分类准确
- [ ] 资金流向计算正确
- [ ] 指标计算符合标准
- [ ] 信号生成合理

---

### 3.4 第四阶段：技术指标增强（1.5人天）

#### 任务4.1：涨跌停统计器

**文件位置**：`vnpy_china_analysis/technical/limit_stats.py`

```python
from typing import Dict, List
from datetime import date, datetime
from ..objects.types import LimitStats, LimitType
from ..base import BaseAnalyzer


class LimitStatsAnalyzer(BaseAnalyzer):
    """
    涨跌停统计分析器

    统计股票的涨跌停情况，计算连续涨跌停天数。
    """

    def __init__(self) -> None:
        super().__init__()
        self.limit_records: Dict[str, List[LimitStats]] = {}
        self.current_status: Dict[str, Dict] = {}

    def analyze(
        self,
        symbol: str,
        data: dict
    ) -> LimitStats:
        """
        更新涨跌停统计

        Args:
            symbol: 股票代码
            data: {"date", "pre_close", "current_price", "limit_up", "limit_down"}

        Returns:
            LimitStats对象
        """
        today = date.fromisoformat(data["date"])
        pre_close = data["pre_close"]
        current_price = data["current_price"]
        limit_up = data["limit_up"]
        limit_down = data["limit_down"]

        # 判断涨跌停
        is_limit_up = abs(current_price - limit_up) < 0.01
        is_limit_down = abs(current_price - limit_down) < 0.01

        # 获取前一状态
        prev_status = self.current_status.get(symbol, {})
        limit_up_days = prev_status.get("limit_up_days", 0)
        limit_down_days = prev_status.get("limit_down_days", 0)
        limit_up_count = prev_status.get("limit_up_count", 0)
        limit_down_count = prev_status.get("limit_down_count", 0)

        # 更新连续天数
        if is_limit_up:
            limit_up_days += 1
            limit_down_days = 0
            limit_up_count += 1
        elif is_limit_down:
            limit_down_days += 1
            limit_up_days = 0
            limit_down_count += 1
        else:
            limit_up_days = 0
            limit_down_days = 0

        # 创建统计记录
        stats = LimitStats(
            symbol=symbol,
            date=today,
            limit_up_days=limit_up_days,
            limit_down_days=limit_down_days,
            is_limit_up=is_limit_up,
            is_limit_down=is_limit_down,
            limit_up_count=limit_up_count,
            limit_down_count=limit_down_count
        )

        # 更新状态
        self.current_status[symbol] = {
            "limit_up_days": limit_up_days,
            "limit_down_days": limit_down_days,
            "limit_up_count": limit_up_count,
            "limit_down_count": limit_down_count
        }

        # 保存历史
        if symbol not in self.limit_records:
            self.limit_records[symbol] = []
        self.limit_records[symbol].append(stats)

        return stats

    def get_limit_stocks(
        self,
        all_symbols: List[str],
        limit_type: LimitType = LimitType.LIMIT_UP
    ) -> List[str]:
        """
        获取涨跌停股票列表

        Args:
            all_symbols: 所有股票代码
            limit_type: 涨跌停类型

        Returns:
            股票代码列表
        """
        result = []

        for symbol in all_symbols:
            status = self.current_status.get(symbol)
            if not status:
                continue

            if limit_type == LimitType.LIMIT_UP and status.get("limit_up_days", 0) > 0:
                result.append(symbol)
            elif limit_type == LimitType.LIMIT_DOWN and status.get("limit_down_days", 0) > 0:
                result.append(symbol)

        return result

    def get_continuous_limit_stocks(
        self,
        min_days: int = 3
    ) -> Dict[str, List[str]]:
        """
        获取连续涨跌停股票

        Args:
            min_days: 最小连续天数

        Returns:
            {"limit_up": [...], "limit_down": [...]}
        """
        limit_up = []
        limit_down = []

        for symbol, status in self.current_status.items():
            if status.get("limit_up_days", 0) >= min_days:
                limit_up.append(symbol)
            if status.get("limit_down_days", 0) >= min_days:
                limit_down.append(symbol)

        return {
            "limit_up": limit_up,
            "limit_down": limit_down
        }

    def calculate_limit_strength(
        self,
        symbol: str,
        limit_type: LimitType
    ) -> float:
        """
        计算涨跌停强度

        基于封单量和封单时间计算强度。
        """
        # TODO: 需要Level-2数据支持
        # 强度 = 封单量 / 流通盘 * 时间权重
        return 0.0
```

#### 任务4.2：板块指数计算器

**文件位置**：`vnpy_china_analysis/technical/sector_index.py`

```python
from typing import List, Dict
from datetime import datetime
from ..objects.types import SectorIndexData
from ..base import BaseAnalyzer


class SectorIndexCalculator(BaseAnalyzer):
    """
    板块指数计算器

    根据板块成分股计算板块指数。
    """

    def __init__(self) -> None:
        super().__init__()
        self.sector_stocks: Dict[str, List[str]] = {}
        self.stock_prices: Dict[str, float] = {}
        self.stock_returns: Dict[str, float] = {}
        self.base_values: Dict[str, float] = {}

    def set_sector_stocks(
        self,
        sector_code: str,
        stocks: List[str]
    ) -> None:
        """
        设置板块成分股

        Args:
            sector_code: 板块代码
            stocks: 成分股列表
        """
        self.sector_stocks[sector_code] = stocks

    def update_stock_price(
        self,
        symbol: str,
        price: float,
        pre_close: float
    ) -> None:
        """
        更新股票价格

        Args:
            symbol: 股票代码
            price: 当前价
            pre_close: 昨收价
        """
        self.stock_prices[symbol] = price

        if pre_close > 0:
            self.stock_returns[symbol] = (price - pre_close) / pre_close

    def calculate_index(
        self,
        sector_code: str,
        method: str = "equal_weight"
    ) -> SectorIndexData:
        """
        计算板块指数

        Args:
            sector_code: 板块代码
            method: 计算方法 (equal_weight/market_cap)

        Returns:
            SectorIndexData对象
        """
        if sector_code not in self.sector_stocks:
            raise ValueError(f"Unknown sector: {sector_code}")

        stocks = self.sector_stocks[sector_code]

        if method == "equal_weight":
            return self._calculate_equal_weight(sector_code, stocks)
        else:
            return self._calculate_market_cap(sector_code, stocks)

    def _calculate_equal_weight(
        self,
        sector_code: str,
        stocks: List[str]
    ) -> SectorIndexData:
        """等权重计算"""
        returns = []
        leading_stocks = []

        for symbol in stocks:
            if symbol in self.stock_returns:
                returns.append(self.stock_returns[symbol])

                # 找出领涨股
                if self.stock_returns[symbol] > 0.05:  # 涨幅>5%
                    leading_stocks.append(symbol)

        if not returns:
            return SectorIndexData(
                sector_code=sector_code,
                sector_name="",
                datetime=datetime.now(),
                index_value=1000.0,
                change_pct=0.0,
                volume=0.0,
                turnover=0.0,
                leading_stocks=[]
            )

        # 计算平均收益率
        avg_return = sum(returns) / len(returns)

        # 更新基准值
        if sector_code not in self.base_values:
            self.base_values[sector_code] = 1000.0

        base_value = self.base_values[sector_code]
        index_value = base_value * (1 + avg_return)

        # 更新基准
        self.base_values[sector_code] = index_value

        return SectorIndexData(
            sector_code=sector_code,
            sector_name="",
            datetime=datetime.now(),
            index_value=index_value,
            change_pct=avg_return,
            volume=0.0,
            turnover=0.0,
            leading_stocks=leading_stocks[:5]  # 前5只领涨股
        )

    def _calculate_market_cap(
        self,
        sector_code: str,
        stocks: List[str]
    ) -> SectorIndexData:
        """市值加权计算"""
        # TODO: 需要市值数据支持
        pass

    def get_sector_ranking(
        self,
        method: str = "change_pct"
    ) -> List[tuple]:
        """
        获取板块排名

        Args:
            method: 排序方法 (change_pct/volume/turnover)

        Returns:
            [(sector_code, value), ...]
        """
        rankings = []

        for sector_code in self.sector_stocks.keys():
            if sector_code in self.base_values:
                if method == "change_pct":
                    # 从base_values推算涨跌幅
                    pass
                rankings.append((sector_code, 0.0))

        return sorted(rankings, key=lambda x: x[1], reverse=True)
```

**验收标准**：
- [ ] 涨跌停统计准确
- [ ] 连板天数计算正确
- [ ] 板块指数计算合理
- [ ] 领涨股识别准确

---

### 3.5 第五阶段：集合竞价分析（1.5人天）

#### 任务5.1：集合竞价分析器

**文件位置**：`vnpy_china_analysis/auction/analyzer.py`

```python
from typing import Dict, List
from datetime import date, datetime
from ..objects.types import AuctionData
from ..base import BaseAnalyzer


class AuctionAnalyzer(BaseAnalyzer):
    """
    集合竞价分析器

    分析9:15-9:25的集合竞价数据。
    """

    def __init__(self) -> None:
        super().__init__()
        self.auction_history: Dict[str, List[AuctionData]] = {}
        self.avg_volumes: Dict[str, float] = {}

    def analyze(
        self,
        symbol: str,
        data: dict
    ) -> AuctionData:
        """
        分析集合竞价

        Args:
            symbol: 股票代码
            data: {
                "date", "pre_close", "auction_price",
                "auction_volume", "auction_amount",
                "buy_volume", "sell_volume",
                "buy_orders", "sell_orders"
            }

        Returns:
            AuctionData对象
        """
        today = date.fromisoformat(data["date"])
        pre_close = data["pre_close"]
        auction_price = data.get("auction_price", pre_close)
        auction_volume = data.get("auction_volume", 0)
        auction_amount = data.get("auction_amount", 0.0)
        buy_volume = data.get("buy_volume", 0)
        sell_volume = data.get("sell_volume", 0)
        buy_orders = data.get("buy_orders", 0)
        sell_orders = data.get("sell_orders", 0)

        # 计算量比
        avg_volume = self._get_avg_volume(symbol, days=5)
        volume_ratio = auction_volume / avg_volume if avg_volume > 0 else 0

        # 计算振幅
        amplitude = abs(auction_price - pre_close) / pre_close if pre_close > 0 else 0

        # 计算买卖比
        total_volume = buy_volume + sell_volume
        buy_sell_ratio = buy_volume / total_volume if total_volume > 0 else 0.5

        auction = AuctionData(
            symbol=symbol,
            date=today,
            pre_close=pre_close,
            auction_price=auction_price,
            auction_volume=auction_volume,
            auction_amount=auction_amount,
            total_buy_volume=buy_volume,
            total_sell_volume=sell_volume,
            buy_orders=buy_orders,
            sell_orders=sell_orders,
            volume_ratio=volume_ratio,
            amplitude=amplitude,
            buy_sell_ratio=buy_sell_ratio,
            open_prediction=auction_price  # 初始预测为竞价价
        )

        # 更新历史
        if symbol not in self.auction_history:
            self.auction_history[symbol] = []
        self.auction_history[symbol].append(auction)

        # 更新平均量
        self._update_avg_volume(symbol, auction_volume)

        return auction

    def _get_avg_volume(self, symbol: str, days: int = 5) -> float:
        """获取历史平均竞价量"""
        if symbol not in self.auction_history:
            return 0.0

        history = self.auction_history[symbol][-days:]
        if not history:
            return 0.0

        return sum(a.auction_volume for a in history) / len(history)

    def _update_avg_volume(self, symbol: str, volume: int) -> None:
        """更新平均量"""
        if symbol not in self.avg_volumes:
            self.avg_volumes[symbol] = volume
        else:
            # 指数移动平均
            self.avg_volumes[symbol] = (
                self.avg_volumes[symbol] * 0.8 + volume * 0.2
            )

    def detect_auction_anomaly(
        self,
        auction: AuctionData
    ) -> Dict:
        """
        检测竞价异常

        识别高开、低开、异常放量等情况。
        """
        anomalies = []

        # 高开/低开检测
        if auction.amplitude > 0.05:  # 振幅>5%
            direction = "high_open" if auction.auction_price > auction.pre_close else "low_open"
            anomalies.append({
                "type": direction,
                "amplitude": auction.amplitude,
                "price": auction.auction_price
            })

        # 异常放量检测
        if auction.volume_ratio > 3:  # 量比>3
            anomalies.append({
                "type": "high_volume",
                "volume_ratio": auction.volume_ratio,
                "auction_volume": auction.auction_volume
            })

        # 买卖失衡检测
        if auction.buy_sell_ratio > 0.8 or auction.buy_sell_ratio < 0.2:
            direction = "buy_dominant" if auction.buy_sell_ratio > 0.5 else "sell_dominant"
            anomalies.append({
                "type": direction,
                "buy_sell_ratio": auction.buy_sell_ratio
            })

        return {"anomalies": anomalies}
```

#### 任务5.2：开盘价预测器

**文件位置**：`vnpy_china_analysis/auction/open_predict.py`

```python
from typing import Dict, List
from datetime import date
from ..objects.types import AuctionData
import numpy as np


class OpenPricePredictor:
    """
    开盘价预测器

    基于集合竞价数据预测开盘价。
    """

    def __init__(self) -> None:
        self.prediction_history: Dict[str, List[tuple]] = {}

    def predict(
        self,
        auction: AuctionData,
        method: str = "simple"
    ) -> float:
        """
        预测开盘价

        Args:
            auction: 竞价数据
            method: 预测方法 (simple/machine_learning)

        Returns:
            预测开盘价
        """
        if method == "simple":
            return self._simple_predict(auction)
        elif method == "ml":
            return self._ml_predict(auction)
        else:
            return auction.auction_price

    def _simple_predict(self, auction: AuctionData) -> float:
        """
        简单预测模型

        基于买卖盘力量预测开盘价。
        """
        # 买卖盘力量对比
        total_volume = auction.total_buy_volume + auction.total_sell_volume

        if total_volume == 0:
            return auction.auction_price

        buy_ratio = auction.total_buy_volume / total_volume

        # 计算调整幅度
        # 买盘越强，开盘越高（最多+2%）
        # 卖盘越强，开盘越低（最多-2%）
        adjustment = (buy_ratio - 0.5) * 0.04  # ±2%

        # 考虑量比因素
        # 放量情况下，竞价价更可能维持
        volume_weight = min(auction.volume_ratio / 5, 1.0)  # 最多权重1

        predicted_change = auction.amplitude * (buy_ratio - 0.5) * 2
        predicted_price = auction.pre_close * (1 + predicted_change)

        # 限制涨跌停范围
        limit_up = auction.pre_close * 1.1  # 假设10%涨停
        limit_down = auction.pre_close * 0.9

        return max(limit_down, min(limit_up, predicted_price))

    def _ml_predict(self, auction: AuctionData) -> float:
        """
        机器学习预测模型

        使用历史数据训练模型预测开盘价。
        """
        # TODO: 实现ML模型
        # 特征：竞价价、竞价量、买卖比、量比、振幅
        # 标签：实际开盘价
        return auction.auction_price

    def evaluate_prediction(
        self,
        symbol: str,
        predicted: float,
        actual: float
    ) -> Dict:
        """
        评估预测准确率

        Args:
            symbol: 股票代码
            predicted: 预测价
            actual: 实际开盘价

        Returns:
            评估指标
        """
        error = abs(predicted - actual)
        error_pct = error / actual if actual > 0 else 0

        # 更新历史
        if symbol not in self.prediction_history:
            self.prediction_history[symbol] = []

        self.prediction_history[symbol].append((predicted, actual, error_pct))

        return {
            "error": error,
            "error_pct": error_pct,
            "is_accurate": error_pct < 0.01  # 误差<1%算准确
        }

    def get_accuracy(self, symbol: str) -> Dict:
        """
        获取预测准确率统计
        """
        if symbol not in self.prediction_history:
            return {}

        history = self.prediction_history[symbol]

        accurate_count = sum(1 for _, _, e in history if e < 0.01)
        avg_error = sum(e for _, _, e in history) / len(history)

        return {
            "total_predictions": len(history),
            "accurate_count": accurate_count,
            "accuracy": accurate_count / len(history),
            "avg_error_pct": avg_error
        }
```

**验收标准**：
- [ ] 竞价数据解析正确
- [ ] 量比计算准确
- [ ] 异常检测有效
- [ ] 开盘预测准确率≥60%

---

### 3.6 第六阶段：集成测试与文档（0.5人天）

#### 任务6.1：集成测试

**文件位置**：`tests/analysis/test_integration.py`

```python
import pytest
from vnpy_china_analysis.level2 import Level2Analyzer
from vnpy_china_analysis.money_flow import MoneyFlowAnalyzer
from vnpy_china_analysis.auction import AuctionAnalyzer
from vnpy_china_analysis.objects.types import TickFlowData, AuctionData
from datetime import datetime


def test_full_analysis_workflow():
    """测试完整分析流程"""
    # 1. Level-2分析
    level2_analyzer = Level2Analyzer()

    # 模拟逐笔成交
    tick_flows = []
    for i in range(100):
        tick = TickFlowData(
            symbol="000001",
            datetime=datetime.now(),
            price=10.0 + i * 0.01,
            volume=500,
            amount=500000,
            direction="buy" if i % 2 == 0 else "sell",
            function_code=1
        )
        tick_flows.append(tick)

    # 分析主力动向
    main_force = level2_analyzer.analyze_main_force("000001", tick_flows)
    assert main_force is not None
    assert main_force.symbol == "000001"

    # 2. 资金流向分析
    money_flow_analyzer = MoneyFlowAnalyzer()
    money_flow = money_flow_analyzer.analyze("000001", tick_flows)
    assert money_flow is not None
    assert money_flow.symbol == "000001"

    # 3. 集合竞价分析
    auction_analyzer = AuctionAnalyzer()

    auction_data = {
        "date": "2026-02-24",
        "pre_close": 10.0,
        "auction_price": 10.2,
        "auction_volume": 10000,
        "buy_volume": 6000,
        "sell_volume": 4000,
        "buy_orders": 100,
        "sell_orders": 80
    }

    auction = auction_analyzer.analyze("000001", auction_data)
    assert auction is not None
    assert auction.volume_ratio > 0


def test_cross_module_integration():
    """测试跨模块集成"""
    # 综合使用多个分析器生成交易信号

    tick_flows = [
        TickFlowData(
            symbol="000001",
            datetime=datetime.now(),
            price=10.5,
            volume=1000,  # 大单
            amount=1050000,
            direction="buy",
            function_code=1
        )
    ]

    # 主力分析
    level2 = Level2Analyzer()
    main_force = level2.analyze_main_force("000001", tick_flows)

    # 资金流向
    money_flow = MoneyFlowAnalyzer()
    flow = money_flow.analyze("000001", tick_flows)

    # 综合判断
    if (main_force.direction == "buy" and
        flow.main_inflow > 0):
        signal = "buy"
    else:
        signal = "neutral"

    assert signal == "buy"
```

#### 任务6.2：使用文档

**文件位置**：`docs/analysis_usage.md`

```markdown
# 行情分析模块使用指南

## 1. 快速开始

### 1.1 Level-2行情分析

```python
from vnpy_china_analysis.level2 import Level2Analyzer

# 创建分析器
analyzer = Level2Analyzer()

# 分析主力动向
main_force = analyzer.analyze_main_force(
    symbol="000001",
    tick_flows=tick_flows,
    window_minutes=5
)

print(f"主力方向: {main_force.direction}")
print(f"主力净流入: {main_force.net_volume:.2f}元")
```

### 1.2 资金流向分析

```python
from vnpy_china_analysis.money_flow import MoneyFlowAnalyzer

# 创建分析器
analyzer = MoneyFlowAnalyzer()

# 分析资金流向
money_flow = analyzer.analyze(
    symbol="000001",
    tick_flows= tick_flows
)

print(f"主力净流入: {money_flow.main_inflow:.2f}元")
print(f"散户净流入: {money_flow.retail_inflow:.2f}元")
```

### 1.3 集合竞价分析

```python
from vnpy_china_analysis.auction import AuctionAnalyzer

# 创建分析器
analyzer = AuctionAnalyzer()

# 分析集合竞价
auction = analyzer.analyze("000001", auction_data)

# 预测开盘价
from vnpy_china_analysis.auction import OpenPricePredictor
predictor = OpenPricePredictor()
predicted_open = predictor.predict(auction)

print(f"预测开盘价: {predicted_open:.2f}")
```

## 2. 策略集成示例

```python
from vnpy_ctastrategy import CtaTemplate
from vnpy_china_analysis.level2 import Level2Analyzer
from vnpy_china_analysis.money_flow import MoneyFlowAnalyzer


class AnalysisStrategy(CtaTemplate):
    """基于行情分析的策略"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.level2_analyzer = Level2Analyzer()
        self.money_flow_analyzer = MoneyFlowAnalyzer()

    def on_tick(self, tick: TickData):
        """Tick行情回调"""

        # 分析主力动向
        main_force = self.level2_analyzer.analyze_main_force(
            tick.symbol,
            self.get_tick_flows(tick.symbol)
        )

        # 分析资金流向
        money_flow = self.money_flow_analyzer.analyze(
            tick.symbol,
            self.get_tick_flows(tick.symbol)
        )

        # 生成交易信号
        if (main_force.direction == "buy" and
            money_flow.main_inflow > 500000 and
            main_force.main_force_ratio > 0.3):

            self.buy(tick.symbol, price=tick.ask_price_1, volume=100)
```
```

**验收标准**：
- [ ] 集成测试通过
- [ ] 文档完整清晰
- [ ] 示例代码可运行

---

## 4. 测试计划

### 4.1 单元测试矩阵

| 模块 | 测试文件 | 用例数 | 覆盖目标 |
|------|---------|--------|---------|
| level2/order_queue | test_order_queue.py | 6 | 90% |
| level2/tick_flow | test_tick_flow.py | 5 | 85% |
| level2/main_force | test_main_force.py | 5 | 85% |
| money_flow/classifier | test_classifier.py | 4 | 95% |
| money_flow/analyzer | test_money_flow.py | 6 | 90% |
| money_flow/indicator | test_indicator.py | 5 | 85% |
| technical/limit_stats | test_limit_stats.py | 6 | 90% |
| technical/sector_index | test_sector_index.py | 4 | 80% |
| auction/analyzer | test_auction.py | 5 | 85% |
| auction/open_predict | test_predict.py | 4 | 80% |
| **合计** | | **50** | **87%** |

### 4.2 性能测试

```python
def test_analysis_performance():
    """测试分析性能"""
    import time

    # 构造测试数据
    tick_flows = [
        TickFlowData(
            symbol=f"{i:06d}.SZ",
            datetime=datetime.now(),
            price=10.0,
            volume=500,
            amount=500000,
            direction="buy",
            function_code=1
        )
        for i in range(1000)
    ]

    # 测试主力分析性能
    analyzer = Level2Analyzer()

    start = time.time()
    for tick in tick_flows:
        analyzer.analyze_main_force(tick.symbol, [tick])

    elapsed = time.time() - start

    # 1000只股票分析应在1秒内完成
    assert elapsed < 1.0
```

---

## 5. 数据源适配

### 5.1 QMT数据适配器

**文件位置**：`vnpy_china_analysis/adapters/qmt_adapter.py`

```python
from typing import List, Dict
from vnpy.trader.object import TickData
from ..objects.types import TickFlowData, OrderQueueData


class QMTDataAdapter:
    """
    QMT数据适配器

    将QMT的Tick数据转换为分析器可用的格式。
    """

    def convert_tick_to_flow(
        self,
        tick: TickData,
        direction: str,
        function_code: int
    ) -> TickFlowData:
        """
        转换Tick到TickFlow

        QMT提供逐笔成交数据，需要正确解析方向。
        """
        return TickFlowData(
            symbol=tick.symbol,
            datetime=tick.datetime,
            price=tick.last_price,
            volume=tick.volume,  # 该笔成交量
            amount=tick.volume * tick.last_price,
            direction=direction,
            function_code=function_code
        )

    def convert_order_queue(
        self,
        tick: TickData
    ) -> OrderQueueData:
        """
        转换十档行情数据

        QMT提供level2十档数据。
        """
        return OrderQueueData(
            symbol=tick.symbol,
            datetime=tick.datetime,
            ask_prices=[
                tick.ask_price_1, tick.ask_price_2,
                tick.ask_price_3, tick.ask_price_4,
                tick.ask_price_5
            ],
            ask_volumes=[
                tick.ask_volume_1, tick.ask_volume_2,
                tick.ask_volume_3, tick.ask_volume_4,
                tick.ask_volume_5
            ],
            ask_queue=[],  # QMT可能不提供明细
            bid_prices=[
                tick.bid_price_1, tick.bid_price_2,
                tick.bid_price_3, tick.bid_price_4,
                tick.bid_price_5
            ],
            bid_volumes=[
                tick.bid_volume_1, tick.bid_volume_2,
                tick.bid_volume_3, tick.bid_volume_4,
                tick.bid_volume_5
            ],
            bid_queue=[]
        )
```

### 5.2 Tushare数据适配器

**文件位置**：`vnpy_china_analysis/adapters/tushare_adapter.py`

```python
class TushareDataAdapter:
    """
    Tushare数据适配器

    用于回测场景，获取历史Level-2数据。
    """

    def __init__(self, api_token: str):
        import tushare as ts
        self.ts = ts.pro_api(api_token)

    def get_tick_flow(
        self,
        symbol: str,
        trade_date: str
    ) -> List[TickFlowData]:
        """
        获取历史逐笔成交

        Tushare API: tushare.get_ticks()
        """
        # TODO: 调用Tushare API获取数据
        pass

    def get_auction_data(
        self,
        symbol: str,
        trade_date: str
    ) -> Dict:
        """
        获取集合竞价数据

        Tushare API: 需要Level-2权限
        """
        pass
```

---

## 6. 时间安排

### 6.1 日程计划

| 日期 | 任务 | 工时 |
|------|------|------|
| Day 1-2 | 基础框架+Level-2分析 | 16h |
| Day 3-4 | 资金流向分析 | 16h |
| Day 5-6 | 技术指标增强 | 12h |
| Day 7 | 集合竞价分析 | 12h |
| Day 8 | 测试+文档 | 8h |
| **合计** | | **80h (8人天)** |

### 6.2 里程碑

| 里程碑 | 时间 | 交付内容 |
|--------|------|---------|
| M1 | Day 2结束 | Level-2分析完成 |
| M2 | Day 4结束 | 资金流向分析完成 |
| M3 | Day 6结束 | 技术指标增强完成 |
| M4 | Day 7结束 | 集合竞价分析完成 |
| M5 | Day 8结束 | 测试+文档完成 |

---

## 7. 风险管理

### 7.1 技术风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| QMT Level-2数据不完整 | 高 | 高 | 使用Tushare数据补充 |
| 性能问题 | 中 | 中 | 使用缓存和异步处理 |
| 数据解析错误 | 中 | 低 | 充分的单元测试 |

### 7.2 数据风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| Level-2数据收费 | 高 | 中 | 使用免费数据源 |
| 数据延迟 | 中 | 中 | 设计容错机制 |
| 数据缺失 | 低 | 低 | 历史数据备份 |

---

## 8. 验收标准

### 8.1 功能验收

- [ ] Level-2行情分析准确
- [ ] 资金流向分类准确率≥95%
- [ ] 技术指标计算正确
- [ ] 集合竞价分析有效
- [ ] 开盘预测准确率≥60%

### 8.2 性能验收

- [ ] 分析延迟<100ms
- [ ] 1000只股票分析<1s
- [ ] 内存占用<200MB

### 8.3 质量验收

- [ ] 单元测试覆盖率≥85%
- [ ] 所有测试通过
- [ ] 代码通过类型检查
- [ ] 文档完整

---

## 9. 后续计划

### 9.1 功能扩展

- [ ] 支持更多数据源（同花顺、东方财富）
- [ ] 实现机器学习预测模型
- [ ] 支持实时行情推送
- [ ] 添加可视化图表

### 9.2 优化方向

- [ ] 使用Cython加速计算
- [ ] 支持分布式计算
- [ ] 实现增量计算
- [ ] 添加数据压缩

---

**文档版本**：v1.0
**创建日期**：2026-02-24
**维护者**：AI Assistant
**下次更新**：实施完成后更新
