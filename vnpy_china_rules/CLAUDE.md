# A股交易规则适配模块

> 更新时间：2026-02-24
> 版本：0.1.0
> 开发状态：已完成

## 模块概述

`vnpy_china_rules` 是为VeighNa框架开发的A股交易规则适配模块，提供A股T+1、涨跌停等特有交易规则的适配功能。

## 模块架构

```
vnpy_china_rules/
├── __init__.py           # 模块入口
├── datasource.py         # 数据源管理层 (已完成)
├── engine.py             # 规则引擎核心 (已完成)
├── filter.py             # 风控过滤器 (已完成)
├── strategy.py           # 策略基类 (已完成)
├── tests/
│   ├── __init__.py
│   ├── test_datasource.py  # 数据源测试
│   ├── test_engine.py      # 规则引擎测试
│   ├── test_filter.py      # 风控过滤器测试
│   └── test_strategy.py    # 策略基类测试
└── CLAUDE.md            # 本文档
```

## 数据源管理层 (datasource.py)

### 核心类

#### StockInfo
股票信息数据类，包含：
- `symbol`: 股票代码
- `exchange`: 交易所
- `name`: 股票名称
- `market_type`: 市场类型（主板/创业板/科创板/北交所）
- `is_st`: 是否ST股票
- `list_date`: 上市日期
- `limit_ratio`: 涨跌停比例

#### DataSource (抽象基类)
数据源抽象基类，定义了：
- `get_stock_info()`: 获取股票基本信息
- `get_market_data()`: 获取实时行情数据

#### QMTDataSource
QMT数据源实现：
- 从QMT网关获取实时行情数据
- 自动识别ST股票
- 根据交易所判断市场类型

#### TushareDataSource
Tushare数据源实现：
- 使用Tushare API获取离线补充数据
- 自动解析市场类型和涨跌停比例
- 支持日线数据查询

#### DataSourceManager
数据源管理器，提供：
- 多数据源注册
- 主数据源优先
- 自动降级机制
- LRU缓存支持

## 规则引擎核心 (engine.py)

### 核心类

#### RuleResult
规则检查结果数据类，包含：
- `passed`: 是否通过规则检查
- `rule_name`: 规则名称
- `message`: 详细消息

#### PositionRecord
持仓记录数据类（用于T+1规则），包含：
- `symbol`: 股票代码
- `volume`: 买入数量
- `buy_datetime`: 买入时间
- `available`: 可用数量（卖出后减少）

#### ChinaStockRulesEngine
A股交易规则引擎主类，提供：
- 统一的规则检查接口
- 协调各子规则引擎
- 成交回调处理

**常量定义：**
- `TRADING_MORNING_START`: 上午交易开始时间 9:15
- `TRADING_MORNING_END`: 上午交易结束时间 11:30
- `TRADING_AFTERNOON_START`: 下午交易开始时间 13:00
- `TRADING_AFTERNOON_END`: 下午交易结束时间 15:00
- `LIMIT_RATIO_MAIN`: 主板涨跌停比例 10%
- `LIMIT_RATIO_SME`: 创业板涨跌停比例 20%
- `LIMIT_RATIO_SCI`: 科创板涨跌停比例 20%
- `LIMIT_RATIO_BSE`: 北交所涨跌停比例 30%
- `LIMIT_RATIO_ST`: ST股票涨跌停比例 5%

#### T1RulesEngine
T+1规则引擎，实现：
- 持仓流水记录
- 可卖数量计算
- 卖出订单检查

**实现原理：**
1. 维护持仓流水记录，记录每次买入的时间、数量
2. 计算可卖数量：遍历持仓，计算当日之前买入的股数
3. 卖出时扣减：卖出成交后，使用FIFO原则扣减对应买入记录的可用数量

**核心方法：**
- `record_buy(symbol, volume, datetime)`: 记录买入成交
- `record_sell(symbol, volume, datetime)`: 记录卖出成交
- `get_sellable_volume(symbol, current_datetime)`: 获取可卖出数量
- `check(order)`: 检查卖出订单

#### PriceLimitRulesEngine
涨跌停规则引擎，实现：
- 涨跌停价格计算
- 委托价格检查

**核心方法：**
- `calculate_limit_price(symbol, prev_close, limit_ratio)`: 计算涨跌停价格
- `check(order, prev_close)`: 检查委托价格

**价格计算：**
- 使用Decimal确保精度
- 支持不同市场类型的涨跌停比例
- 自动从数据源获取股票信息

#### TimeRulesEngine
交易时间规则引擎，实现：
- 交易时间判断
- 可委托时间检查

**交易时间：**
- 集合竞价：9:15-9:25
- 上午交易：9:30-11:30
- 下午交易：13:00-15:00

**核心方法：**
- `is_trading_time(dt)`: 判断是否在交易时间
- `can_submit_order(dt)`: 判断是否可委托
- `check(order)`: 检查委托时间

#### UnitRulesEngine
交易单位规则引擎，实现：
- 最小交易单位检查（100股）
- 整数倍检查

**核心方法：**
- `check(order)`: 检查委托数量

#### IpoRulesEngine
新股申购规则引擎，实现：
- 申购额度计算

**核心方法：**
- `calculate_subs_quota(account_data)`: 计算申购额度
- `check(order)`: 检查申购订单

### 策略基类 (strategy.py)

#### ChinaStockStrategy
A股策略基类，提供A股特有的交易规则检查功能：

- `buy(price, volume, lock)`: 买入开仓
- `sell(price, volume, lock)`: 卖出平仓
- `short(price, volume)`: 卖空开仓（A股不支持）
- `cover(price, volume)`: 买空平仓（A股不支持）
- `check_buy(symbol, price, volume)`: 检查是否可买入
- `check_sell(symbol, price, volume)`: 检查是否可卖出
- `get_sellable_volume(symbol)`: 获取可卖出数量
- `on_init()`: 策略初始化回调
- `on_start()`: 策略启动回调
- `on_stop()`: 策略停止回调
- `on_trade(trade)`: 成交推送回调
- `on_order(order)`: 委托推送回调
- `on_bar(bar)`: K线推送回调
- `write_log(msg)`: 写日志

**便捷函数：**
- `create_strategy_base(cta_engine, strategy_name, vt_symbol, setting, rules_engine)`: 创建带规则引擎的策略实例

**使用示例：**
```python
from vnpy_china_rules.strategy import ChinaStockStrategy
from vnpy_china_rules import ChinaStockRulesEngine, DataSourceManager


class MyStockStrategy(ChinaStockStrategy):
    parameters = ["max_position", "stop_loss"]
    variables = ["pos", "avg_price"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.max_position = setting.get("max_position", 10000)
        self.stop_loss = setting.get("stop_loss", 0.02)
        self.avg_price = 0.0

    def on_bar(self, bar):
        if self.pos == 0:
            can_buy, msg = self.check_buy(self.vt_symbol, bar.close_price, 1000)
            if can_buy:
                self.buy(bar.close_price, 1000)


# 创建策略
strategy = MyStockStrategy(
    cta_engine=cta_engine,
    strategy_name="my_strategy",
    vt_symbol="000001.SZSE",
    setting={"max_position": 20000}
)

# 绑定规则引擎
strategy.rules_engine = rules_engine
```

#### TradingRuleMixin
交易规则混入类，用于不想继承ChinaStockStrategy的场景：

- `check_buy(symbol, price, volume)`: 检查是否可买入
- `check_sell(symbol, price, volume)`: 检查是否可卖出
- `get_sellable_volume(symbol)`: 获取可卖出数量

**使用示例：**
```python
from vnpy_china_rules.strategy import TradingRuleMixin


class MyExistingStrategy(MyBaseStrategy, TradingRuleMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rules_engine = None

    def some_method(self):
        can_buy, msg = self.check_buy("000001.SZSE", 10.0, 1000)
        if can_buy:
            # 执行买入
            pass
```

### 风控过滤器 (filter.py)

#### ChinaStockRiskFilter
A股交易风控过滤器，提供VeighNa框架集成接口：

- `check_order(order)`: 订单检查回调，返回(是否通过, 原因)
- `on_trade(trade)`: 成交回调，更新T+1持仓记录
- `enabled`: 启用/禁用过滤器

**便捷函数：**
- `create_risk_filter(rules_engine)`: 创建风控过滤器实例

**使用示例：**
```python
from vnpy_china_rules import (
    create_rules_engine,
    ChinaStockRiskFilter,
)

# 创建规则引擎
rules_engine = create_rules_engine(qmt_gateway=gateway)

# 创建风控过滤器
risk_filter = ChinaStockRiskFilter(rules_engine)

# 订单检查
passed, message = risk_filter.check_order(order)
if not passed:
    print(f"订单被拦截: {message}")

# 成交回调（更新T+1记录）
risk_filter.on_trade(trade)
```

### 使用示例

```python
from vnpy_china_rules import (
    QMTDataSource,
    TushareDataSource,
    DataSourceManager,
    ChinaStockRulesEngine,
)

# 创建数据源管理器
manager = DataSourceManager()

# 注册QMT数据源（主数据源）
qmt_source = QMTDataSource(main_engine)
manager.register_source("qmt", qmt_source, primary=True)

# 注册Tushare数据源（备用）
tushare_source = TushareDataSource(token="your_token")
manager.register_source("tushare", tushare_source)

# 创建规则引擎
rules_engine = ChinaStockRulesEngine(manager)

# 检查订单
order = OrderData(...)
results = rules_engine.check_order(order)

for result in results:
    print(f"{result.rule_name}: {result.message}")

# 或者直接判断是否可提交
can_submit, message = rules_engine.can_submit_order(order)
if can_submit:
    print("订单可以提交")
else:
    print(f"订单不能提交: {message}")

# 成交回调
rules_engine.on_trade(trade)
```

## 测试

运行测试：
```bash
# 运行所有测试
pytest vnpy_china_rules/tests/ -v

# 只运行数据源测试
pytest vnpy_china_rules/tests/test_datasource.py -v

# 只运行规则引擎测试
pytest vnpy_china_rules/tests/test_engine.py -v
```

测试覆盖：
- **数据源测试**（25个测试用例）：
  - StockInfo数据类测试
  - QMTDataSource功能测试
  - TushareDataSource功能测试
  - DataSourceManager多数据源测试
  - 降级机制测试

- **规则引擎测试**（33个测试用例）：
  - RuleResult和PositionRecord数据类测试
  - T1RulesEngine测试（9个测试）
  - PriceLimitRulesEngine测试（6个测试）
  - TimeRulesEngine测试（9个测试）
  - UnitRulesEngine测试（3个测试）
  - IpoRulesEngine测试（2个测试）
  - ChinaStockRulesEngine集成测试（4个测试）

- **风控过滤器测试**（8个测试用例）
- **策略基类测试**（25个测试用例）

**总计：91个测试用例全部通过**

## 开发计划

### 已完成
- [x] 数据源管理层
  - [x] StockInfo数据类
  - [x] DataSource抽象基类
  - [x] QMTDataSource实现
  - [x] TushareDataSource实现
  - [x] DataSourceManager实现
  - [x] 单元测试（25个测试用例）

- [x] 规则引擎核心
  - [x] ChinaStockRulesEngine
  - [x] T1RulesEngine
  - [x] PriceLimitRulesEngine
  - [x] TimeRulesEngine
  - [x] UnitRulesEngine
  - [x] IpoRulesEngine
  - [x] 单元测试（33个测试用例）

- [x] 风控过滤器 (filter.py)
  - [x] ChinaStockRiskFilter类
  - [x] 单元测试（8个测试用例）

- [x] 策略基类 (strategy.py)
  - [x] ChinaStockStrategy基类
  - [x] TradingRuleMixin混入类
  - [x] create_strategy_base便捷函数
  - [x] 单元测试（25个测试用例）

## 技术要点

### 涨跌停比例
- 主板：10%
- 创业板：20%
- 科创板：20%
- 北交所：30%
- ST股票：5%

### 交易所映射
- SSE（上海证券交易所）：主板、科创板
- SZSE（深圳证券交易所）：主板、创业板
- BSE（北京证券交易所）：北交所

### 数据源优先级
1. 主数据源（QMT实时数据）
2. 备用数据源（Tushare离线数据）

### T+1规则实现
- 持仓流水记录：记录每次买入的时间、数量
- 可卖数量计算：只计算当前日期之前买入的股数
- FIFO扣减：卖出时按时间顺序扣减可用数量

### 代码质量
- 严格遵循PEP 8编码规范
- 完整的类型注解
- 详细的docstring文档
- 使用loguru进行日志记录
- 使用Decimal确保价格计算精度

## 变更记录

### 2026-02-24 (第四版)
- ✨ 实现策略基类
- 📊 实现ChinaStockStrategy基类
- 📊 实现TradingRuleMixin混入类
- 🔧 实现买入/卖出/卖空/平仓方法
- 🔧 实现规则检查便捷方法（check_buy/check_sell/get_sellable_volume）
- 🔧 实现回调方法（on_init/on_start/on_stop/on_trade/on_order/on_bar/on_tick）
- 🔧 实现create_strategy_base便捷函数
- ✅ 完成所有单元测试（25个测试用例全部通过）
- 📈 总计91个测试用例全部通过

### 2026-02-24 (第三版)
- ✨ 实现风控过滤器
- 📊 实现ChinaStockRiskFilter类
- 🔧 实现check_order订单检查回调
- 🔧 实现on_trade成交回调（T+1持仓更新）
- 🔧 添加create_risk_filter便捷函数
- ✅ 完成所有单元测试（8个测试用例全部通过）
- 📈 总计61个测试用例全部通过（5个Tushare测试跳过）

### 2026-02-24 (第二版)
- ✨ 实现规则引擎核心
- 📊 实现RuleResult和PositionRecord数据类
- 🔧 实现ChinaStockRulesEngine主引擎
- 🔧 实现T1RulesEngine（T+1规则）
- 🔧 实现PriceLimitRulesEngine（涨跌停规则）
- 🔧 实现TimeRulesEngine（交易时间规则）
- 🔧 实现UnitRulesEngine（交易单位规则）
- 🔧 实现IpoRulesEngine（新股申购规则）
- ✅ 完成所有单元测试（33个测试用例全部通过）
- 📈 总计58个测试用例全部通过

### 2026-02-24 (第一版)
- ✨ 创建数据源管理层
- 📊 实现StockInfo数据类
- 🔧 实现QMTDataSource
- 🔧 实现TushareDataSource
- 🔧 实现DataSourceManager
- ✅ 完成所有单元测试（25个测试用例全部通过）


<claude-mem-context>
# Recent Activity

<!-- This section is auto-generated by claude-mem. Edit content outside the tags. -->

### Feb 24, 2026

| ID | Time | T | Title | Read |
|----|------|---|-------|------|
| #6274 | 2:29 PM | ⚖️ | Designed comprehensive data service and monitoring architecture for A-share trading system | ~626 |
| #6273 | " | 🔵 | Found comprehensive A股数据服务 design document from earlier session | ~468 |
| #6271 | " | 🟣 | Design Documents Completed for REQ-003 and REQ-004 | ~331 |
| #6260 | 2:21 PM | 🔵 | DataSource Implementation Verified in Main Repository | ~379 |
| #6252 | 2:15 PM | 🔵 | vnpy_riskmanager uses RuleTemplate pattern with dynamic callback registration and send_order patching | ~522 |
</claude-mem-context>