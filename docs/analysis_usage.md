# 行情分析模块使用指南

> vnpy_china_analysis 模块使用文档
> 版本: 1.0.0

## 1. 快速开始

### 1.1 Level-2行情分析

```python
from vnpy_china_analysis.level2 import Level2Analyzer

# 创建分析器
analyzer = Level2Analyzer()

# 更新实时数据
tick_data = {
    "datetime": datetime.now(),
    "price": 10.5,
    "volume": 1000,
    "amount": 10500,
    "direction": "buy",
    "function_code": 1
}
analyzer.update("000001", tick_data)

# 获取主力动向
main_force = analyzer.get_main_force("000001")
print(f"主力方向: {main_force.direction}")
print(f"主力净流入: {main_force.net_volume:.2f}元")

# 获取支撑阻力位
support = analyzer.analyzer_order_queue.get_support_level("000001")
resistance = analyzer.analyzer_order_queue.get_resistance_level("000001")
```

### 1.2 资金流向分析

```python
from vnpy_china_analysis.money_flow import MoneyFlowAnalyzer
from vnpy_china_analysis.objects.types import TickFlowData
from datetime import datetime

# 创建分析器
analyzer = MoneyFlowAnalyzer()

# 准备逐笔成交数据
tick_flows = [
    TickFlowData(
        symbol="000001",
        datetime=datetime.now(),
        price=10.5,
        volume=1000,
        amount=105000,
        direction="buy",
        function_code=1
    )
]

# 分析资金流向
money_flow = analyzer.analyze("000001", tick_flows)

print(f"主力净流入: {money_flow.main_inflow:.2f}元")
print(f"散户净流入: {money_flow.retail_inflow:.2f}元")
print(f"总净流入: {money_flow.net_inflow:.2f}元")
```

### 1.3 集合竞价分析

```python
from vnpy_china_analysis.auction import AuctionAnalyzer

# 创建分析器
analyzer = AuctionAnalyzer()

# 竞价数据
auction_data = {
    "datetime": datetime.now(),
    "pre_close": 10.0,
    "auction_price": 10.2,
    "auction_volume": 10000,
    "total_buy_volume": 6000,
    "total_sell_volume": 4000,
    "buy_orders": 100,
    "sell_orders": 80
}

# 分析竞价
auction = analyzer.analyze("000001", auction_data)

print(f"量比: {auction.volume_ratio:.2f}")
print(f"开盘预测: {auction.open_prediction:.2f}")
```

## 2. 数据适配器

### 2.1 QMT数据适配

```python
from vnpy_china_analysis.adapters import QMTDataAdapter

# 创建适配器
adapter = QMTDataAdapter()

# 转换QMT tick数据
level2_data = adapter.convert_to_analysis_format(qmt_tick_data, "level2")

# 使用转换后的数据
analyzer.update(symbol, level2_data)
```

### 2.2 Tushare数据适配

```python
from vnpy_china_analysis.adapters import TushareDataAdapter

# 创建适配器（需要API token）
adapter = TushareDataAdapter(api_token="your_token")

# 获取历史数据
tick_flows = adapter.get_tick_flow("000001.SZ", "20260224")
```

## 3. 策略示例

### 3.1 主力流入策略

```python
from vnpy_china_analysis import Level2Analyzer, MoneyFlowAnalyzer

class MainInflowStrategy:
    def __init__(self):
        self.level2 = Level2Analyzer()
        self.money_flow = MoneyFlowAnalyzer()

    def on_tick(self, symbol, tick_data):
        # 更新数据
        self.level2.update(symbol, tick_data)

        # 获取分析结果
        main_force = self.level2.get_main_force(symbol)

        # 判断条件
        if (main_force.direction == "buy" and
            main_force.main_force_ratio > 0.5):
            return "BUY"
        elif main_force.direction == "sell":
            return "SELL"

        return "HOLD"
```

## 4. API参考

### 4.1 Level2Analyzer

| 方法 | 说明 |
|------|------|
| `update(symbol, data)` | 更新实时数据 |
| `get_main_force(symbol)` | 获取主力动向 |
| `get_order_queue(symbol)` | 获取委托队列 |

### 4.2 MoneyFlowAnalyzer

| 方法 | 说明 |
|------|------|
| `analyze(symbol, tick_flows)` | 分析资金流向 |
| `get_main_inflow(symbol)` | 获取主力净流入 |
| `get_net_inflow(symbol)` | 获取总净流入 |

### 4.3 AuctionAnalyzer

| 方法 | 说明 |
|------|------|
| `analyze(symbol, data)` | 分析竞价数据 |
| `predict_open_price(data)` | 预测开盘价 |
| `get_volume_ratio(symbol)` | 获取量比 |

## 5. 注意事项

1. **时间窗口**：分析器默认使用5分钟时间窗口，可通过参数调整
2. **数据精度**：成交量单位为"手"，每手100股
3. **缓存管理**：定期清理缓存以释放内存
4. **线程安全**：当前版本非线程安全，多线程使用需加锁
