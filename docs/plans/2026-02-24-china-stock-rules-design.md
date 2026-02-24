# A股交易规则适配模块设计文档

> 文档版本：v1.0
> 创建日期：2026-02-24
> 状态：已设计

---

## 1. 设计目标

为VeighNa框架开发A股交易规则适配模块，解决A股T+1、涨跌停等特有交易规则与量化策略的集成问题。

### 1.1 核心目标

1. **策略层面集成**：提供A股策略基类，在策略执行前自动检查交易规则
2. **网关层面拦截**：提供风控过滤器，作为兜底机制拦截不合规订单
3. **数据源管理**：统一管理QMT、Tushare等多数据源，便于未来扩展

### 1.2 功能范围

| 规则 | 说明 |
|------|------|
| T+1交易规则 | 当日买入，次日才能卖出 |
| 涨跌停板 | 主板10%、创业板20%、科创板20%、北交所30%、ST 5% |
| 交易时间 | 集合竞价、上午盘、下午盘 |
| 交易单位 | 最小100股（1手） |
| 新股申购 | 额度计算、时间限制 |

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                 A股交易规则适配引擎 (ChinaStockRules)            │
├─────────────────────────────────────────────────────────────────┤
│  【策略层面】                                                    │
│  ┌─────────────────┐    ┌─────────────────┐                   │
│  │ ChinaStockStrategy │    │ TradingRuleMixin  │               │
│  │    (策略基类)     │    │    (混入类)      │               │
│  └────────┬────────┘    └────────┬────────┘                   │
│           │                      │                              │
│           └──────────┬───────────┘                              │
│                      ▼                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              RulesEngine (规则引擎)                      │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │   │
│  │  │T1Rules │ │PriceLimit│ │TimeRules│ │UnitRules│      │   │
│  │  │        │ │  Rules   │ │         │ │         │      │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘      │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  【网关层面】                                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           RiskCheckFilter (风控过滤器)                    │   │
│  │     (订单发送前自动拦截不合规委托)                         │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  【数据层】                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ QMTDataSource│  │TushareSource │  │  LocalCache  │      │
│  │  (实时行情)  │  │ (离线补充)   │  │ (持仓流水)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块职责

| 模块 | 职责 |
|------|------|
| `ChinaStockStrategy` | A股策略基类，提供规则检查便捷方法 |
| `TradingRuleMixin` | 交易规则混入类，非继承方式集成规则 |
| `ChinaStockRulesEngine` | 规则引擎主入口，协调各子规则 |
| `T1RulesEngine` | T+1规则：持仓流水管理、可卖数量计算 |
| `PriceLimitRulesEngine` | 涨跌停规则：价格计算、涨停判断 |
| `TimeRulesEngine` | 交易时间规则：时段判断、可委托检查 |
| `UnitRulesEngine` | 交易单位规则：最小数量检查 |
| `IpoRulesEngine` | 新股申购规则：额度计算 |
| `DataSourceManager` | 数据源管理器，支持多数据源 |
| `ChinaStockRiskFilter` | 风控过滤器，集成到现有风控体系 |

---

## 3. 核心类设计

### 3.1 数据源层

```python
# datasource.py

class DataSource(ABC):
    """数据源抽象基类"""

    @abstractmethod
    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        pass

    @abstractmethod
    def get_market_data(self, symbol: str) -> Optional[MarketData]:
        pass


class QMTDataSource(DataSource):
    """QMT数据源 - 实时行情"""

    def __init__(self, gateway):
        self.gateway = gateway


class TushareDataSource(DataSource):
    """Tushare数据源 - 离线补充"""

    def __init__(self, token: str):
        self.pro = ts.pro_api(token)


class DataSourceManager:
    """数据源管理器"""

    def register_source(self, name: str, source: DataSource, primary: bool = False):
        pass

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        pass

    def get_market_data(self, symbol: str) -> Optional[MarketData]:
        pass
```

### 3.2 规则引擎

```python
# engine.py

class ChinaStockRulesEngine:
    """A股交易规则引擎"""

    TRADING_MORNING_START = time(9, 15)
    TRADING_MORNING_END = time(11, 30)
    TRADING_AFTERNOON_START = time(13, 0)
    TRADING_AFTERNOON_END = time(15, 0)

    LIMIT_RATIO_MAIN = 0.10
    LIMIT_RATIO_SME_START = 0.20
    LIMIT_RATIO_SCI = 0.20
    LIMIT_RATIO_BSE = 0.30
    LIMIT_RATIO_ST = 0.05

    def __init__(self, datasource_manager: DataSourceManager):
        self.dm = datasource_manager
        self.t1_rules = T1RulesEngine(self)
        self.price_limit_rules = PriceLimitRulesEngine(self)
        self.time_rules = TimeRulesEngine(self)
        self.unit_rules = UnitRulesEngine(self)
        self.ipo_rules = IpoRulesEngine(self)

    def check_order(self, order: OrderData) -> List[RuleResult]:
        """全面检查订单合规性"""

    def can_submit_order(self, order: OrderData) -> tuple[bool, str]:
        """判断订单是否可提交"""


class T1RulesEngine:
    """T+1规则引擎"""

    def record_buy(self, symbol: str, volume: int, datetime: datetime):
        """记录买入成交"""

    def record_sell(self, symbol: str, volume: int, datetime: datetime):
        """记录卖出成交"""

    def get_sellable_volume(self, symbol: str, current_datetime: datetime) -> int:
        """获取可卖出数量"""

    def check(self, order: OrderData) -> RuleResult:
        """检查卖出订单"""


class PriceLimitRulesEngine:
    """涨跌停规则引擎"""

    def calculate_limit_price(self, symbol: str, prev_close: float) -> tuple[float, float]:
        """计算涨跌停价格"""

    def check(self, order: OrderData) -> RuleResult:
        """检查委托价格"""
```

### 3.3 风控过滤器

```python
# filter.py

class ChinaStockRiskFilter:
    """A股交易风控过滤器"""

    def __init__(self, rules_engine: ChinaStockRulesEngine):
        self.rules_engine = rules_engine
        self.enabled = True

    def check_order(self, order: OrderData) -> tuple[bool, str]:
        """订单检查回调 - 被风控系统调用"""

    def on_trade(self, trade: TradeData):
        """成交回调 - 更新T+1持仓记录"""
```

---

## 4. 使用示例

### 4.1 策略中使用

```python
from vnpy_china_rules.strategy import ChinaStockStrategy


class MyStockStrategy(ChinaStockStrategy):
    """我的A股策略"""

    parameters = [
        "max_position",
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.max_position = setting.get("max_position", 10000)

    def on_trade(self, trade):
        # 成交后自动更新T+1记录
        pass

    def on_bar(self, bar):
        # 买入示例
        symbol = "000001.SZSE"
        price = bar.close_price
        volume = 1000

        # 检查是否可买入
        can_buy, msg = self.check_buy(symbol, price, volume)
        if can_buy:
            self.buy(symbol, price, volume)
        else:
            self.write_log(f"买入检查失败: {msg}")

        # 卖出示例 - 检查T+1
        can_sell, msg = self.check_sell(symbol, price, 100)
        if can_sell:
            self.sell(symbol, price, 100)
        else:
            self.write_log(f"卖出检查失败: {msg}")

        # 查询可卖数量
        sellable = self.get_sellable_volume(symbol)
        self.write_log(f"可卖出数量: {sellable}")
```

### 4.2 风控过滤器集成

```python
from vnpy_china_rules import create_rules_engine, ChinaStockRiskFilter

# 在MainEngine初始化后
def setup_risk_filter(main_engine, qmt_gateway):
    # 创建规则引擎
    rules_engine = create_rules_engine(qmt_gateway=qmt_gateway)

    # 创建风控过滤器
    risk_filter = ChinaStockRiskFilter(rules_engine)

    # 注册到vnpy风控系统
    main_engine.add_risk_filter(risk_filter)

    return rules_engine
```

---

## 5. 技术要点

### 5.1 T+1实现原理

1. **持仓流水记录**：每次成交记录买入时间、数量
2. **可卖数量计算**：遍历持仓，计算当日之前买入的股数
3. **卖出时扣减**：卖出成交后，减少对应买入记录的可用数量

### 5.2 涨跌停计算

1. **获取股票信息**：从数据源获取股票所属市场、是否ST
2. **获取昨日收盘价**：从行情数据获取prev_close
3. **计算涨跌停价**：`prev_close * (1 ± 涨跌幅比例)`
4. **价格校验**：买入价≤涨停价，卖出价≥跌停价

### 5.3 数据源设计原则

1. **优先使用实时数据**：QMT实时行情优先
2. **降级处理**：实时数据不可用时，使用Tushare补充
3. **缓存机制**：热门数据本地缓存，减少API调用

---

## 6. 实施计划

| 阶段 | 任务 | 预估工时 |
|------|------|---------|
| 1 | 数据源管理层开发 | 1人天 |
| 2 | 规则引擎核心开发 | 2人天 |
| 3 | 风控过滤器开发 | 1人天 |
| 4 | 策略基类开发 | 1人天 |
| 5 | 单元测试 | 1人天 |
| **合计** | | **6人天** |

---

## 7. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-02-24 | 初始版本 |
