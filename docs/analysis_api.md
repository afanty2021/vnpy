# vnpy_china_analysis API文档

> 版本: 1.0.0
> 更新日期: 2026-02-25

## 模块结构

```
vnpy_china_analysis/
├── level2/          # Level-2行情分析
├── money_flow/      # 资金流向分析
├── technical/       # 技术指标增强
├── auction/         # 集合竞价分析
├── adapters/        # 数据适配器
└── objects/         # 数据对象
```

## 核心类

### Level2Analyzer

Level-2行情综合分析器。

```python
class Level2Analyzer:
    def __init__(self) -> None
```

**方法:**

- `update(symbol: str, data: Dict) -> Dict`: 更新实时数据
- `get_main_force(symbol: str) -> MainForceData`: 获取主力动向
- `get_order_queue(symbol: str) -> OrderQueueData`: 获取委托队列

### MoneyFlowAnalyzer

资金流向综合分析器。

```python
class MoneyFlowAnalyzer:
    def __init__(self, thresholds: Optional[Dict] = None) -> None
```

**方法:**

- `analyze(symbol: str, tick_flows: List[TickFlowData], window_minutes: int = 5) -> MoneyFlowData`: 分析资金流向
- `get_main_inflow(symbol: str) -> float`: 获取主力净流入
- `get_net_inflow(symbol: str) -> float`: 获取总净流入
- `get_flow_summary(symbol: str, minutes: int = 5) -> Dict`: 获取资金流向汇总

### AuctionAnalyzer

集合竞价分析器。

```python
class AuctionAnalyzer(RealtimeAnalyzer):
    def __init__(self, cache_size: int = 1000) -> None
```

**方法:**

- `analyze(symbol: str, data: Dict) -> AuctionData`: 分析竞价数据
- `predict_open_price(auction_data: AuctionData) -> float`: 预测开盘价
- `get_volume_ratio(symbol: str) -> float`: 获取量比

## 数据对象

### TickFlowData

逐笔成交数据。

```python
@dataclass
class TickFlowData:
    symbol: str              # 股票代码
    datetime: datetime       # 成交时间
    price: float             # 成交价格
    volume: int              # 成交数量（手）
    amount: float            # 成交金额（元）
    direction: str           # 方向: buy/sell
    function_code: int       # 成交性质
```

### MoneyFlowData

资金流向数据。

```python
@dataclass
class MoneyFlowData:
    symbol: str                      # 股票代码
    datetime: datetime               # 时间
    super_large_inflow: float        # 超大单净流入
    large_inflow: float              # 大单净流入
    medium_inflow: float             # 中单净流入
    small_inflow: float              # 小单净流入
    main_inflow: float               # 主力净流入
    retail_inflow: float             # 散户净流入
    net_inflow: float                # 总净流入
```

### MainForceData

主力动向数据。

```python
@dataclass
class MainForceData:
    symbol: str              # 股票代码
    datetime: datetime       # 时间
    buy_volume: float        # 买入成交量
    sell_volume: float       # 卖出成交量
    net_volume: float        # 净成交量
    main_force_ratio: float  # 主力净流入比例
    direction: str           # 方向: buy/sell/neutral
```

### AuctionData

集合竞价数据。

```python
@dataclass
class AuctionData:
    symbol: str                  # 股票代码
    date: date                   # 日期
    pre_close: float             # 昨收
    auction_price: float         # 竞价成交价
    auction_volume: int          # 竞价成交量
    auction_amount: float        # 竞价成交额
    total_buy_volume: int        # 总买委托量
    total_sell_volume: int       # 总卖委托量
    buy_orders: int              # 买委托笔数
    sell_orders: int             # 卖委托笔数
    volume_ratio: float          # 量比
    amplitude: float             # 竞价振幅
    buy_sell_ratio: float        # 买卖比
    open_prediction: float       # 开盘价预测
```

## 枚举类型

### MoneyFlowLevel

资金流向级别。

```python
class MoneyFlowLevel(Enum):
    SUPER_LARGE = "super_large"    # 超大单 > 100万
    LARGE = "large"                # 大单 20-100万
    MEDIUM = "medium"              # 中单 5-20万
    SMALL = "small"                # 小单 < 5万
```

## 适配器

### QMTDataAdapter

QMT数据适配器。

```python
class QMTDataAdapter:
    def convert_to_analysis_format(self, data: Dict, data_type: str) -> Dict
```

### TushareDataAdapter

Tushare数据适配器。

```python
class TushareDataAdapter:
    def __init__(self, api_token: str)
    def get_tick_flow(self, symbol: str, trade_date: str) -> List[TickFlowData]
```
