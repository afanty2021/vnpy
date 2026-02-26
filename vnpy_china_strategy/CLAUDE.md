# vnpy_china_strategy - A股特色策略库

> 更新时间：2026-02-26
> 版本：1.0.0
> 需求编号：REQ-005
> 优先级：P1

## 模块概述

vnpy_china_strategy 是 VeighNa 量化交易框架的 A股特色策略库模块，提供 5 大类 A 股特有策略的完整实现。

## 策略分类

### 1. 龙虎榜策略
- **InstitutionTrackerStrategy**: 机构席位追踪策略
- **BrokerMoneyStrategy**: 游资策略
- **FollowStrategy**: 跟随策略

### 2. 北向资金策略
- **NorthboundFlowStrategy**: 资金流向策略
- **HoldingChangeStrategy**: 持股变化策略
- **SectorPreferenceStrategy**: 板块偏好策略

### 3. 板块轮动策略
- **SectorStrengthStrategy**: 板块强度轮动策略
- **RotationSignalStrategy**: 轮动信号策略

### 4. 事件驱动策略
- **EarningsForecastStrategy**: 业绩预告策略
- **PolicyEventStrategy**: 政策事件策略

### 5. 可转债套利策略
- **ConvertibleArbitrageStrategy**: 转股套利策略

## 目录结构

```
vnpy_china_strategy/
├── __init__.py                 # 模块入口
├── template.py                 # 策略模板基类
├── base.py                     # 策略基础类
├── config.py                   # 策略配置管理
├── data_service.py             # 数据服务接口
├── dragon_tiger/               # 龙虎榜策略
│   ├── __init__.py
│   ├── models.py              # 数据模型
│   ├── institution.py         # 机构席位策略
│   ├── broker.py              # 游资策略
│   └── follow.py              # 跟随策略
├── northbound/                 # 北向资金策略
│   ├── __init__.py
│   ├── models.py              # 数据模型
│   ├── flow.py                # 资金流向策略
│   ├── holding.py             # 持股变化策略
│   └── sector.py              # 板块偏好策略
├── sector_rotation/            # 板块轮动策略
│   ├── __init__.py
│   ├── models.py              # 数据模型
│   ├── strength.py            # 板块强度策略
│   └── signal.py              # 轮动信号策略
├── event_driven/               # 事件驱动策略
│   ├── __init__.py
│   ├── models.py              # 数据模型
│   ├── earnings.py             # 业绩预告策略
│   └── policy.py              # 政策事件策略
├── convertible/                # 可转债套利策略
│   ├── __init__.py
│   ├── models.py              # 数据模型
│   └── arbitrage.py           # 套利策略
├── indicators/                 # 公共指标库
│   └── __init__.py
└── tests/                      # 测试
    ├── __init__.py
    ├── test_dragon_tiger.py
    ├── test_northbound.py
    ├── test_sector_rotation.py
    ├── test_event_driven.py
    └── test_convertible.py
```

## 快速开始

### 基本使用

```python
from vnpy_china_strategy import (
    InstitutionTrackerStrategy,
    ChinaStrategyDataService,
    get_data_service,
)
from vnpy_china_data import ChinaDataService

# 创建数据服务
data_service = ChinaDataService()
data_service.connect()

# 创建策略数据服务
strategy_data_service = get_data_service(data_service)

# 创建CTA引擎（需要vnpy_ctastrategy）
# cta_engine = CtaEngine(...)

# 创建策略
strategy = InstitutionTrackerStrategy(
    cta_engine=cta_engine,
    strategy_name="institution_tracker",
    vt_symbol="000001.SZSE",
    setting={
        "institution_threshold": 1000,  # 1000万
        "min_institution_count": 3,
        "holding_days": 5,
    }
)

# 注入数据服务
strategy.set_data_service(strategy_data_service)
```

### 独立使用

```python
from vnpy_china_strategy.base import ChinaStrategyBase, PositionManager

class MyStrategy(ChinaStrategyBase):
    def __init__(self):
        super().__init__("my_strategy")
        self.position_manager = PositionManager()

    def on_bar(self, bar):
        # 策略逻辑
        pass
```

## 策略基类

### ChinaStrategyTemplate

策略模板基类，继承自 vnpy_ctastrategy 的 CtaTemplate，提供：

- `set_data_service()`: 设置数据服务
- `get_bar_data()`: 获取K线数据
- `get_current_price()`: 获取当前价格
- `calculate_position_size()`: 计算仓位
- `is_tradeable()`: 检查是否可交易

### RiskControlMixin

风控混入类，提供：

- `check_risk_limits()`: 检查风控限制
- `check_daily_loss_limit()`: 检查日止损
- `check_position_limit()`: 检查持仓限制
- `check_st_stock()`: 检查ST股票
- `check_limit_up_down()`: 检查涨跌停

### PositionManager

持仓管理器，提供：

- `add_position()`: 添加持仓
- `update_position()`: 更新持仓
- `remove_position()`: 移除持仓
- `get_position()`: 获取持仓
- `check_holding_expired()`: 检查持仓过期

## 策略配置

### DragonTigerConfig

```python
from vnpy_china_strategy.config import DragonTigerConfig

config = DragonTigerConfig()
config.institution_threshold = 1000  # 机构买入阈值(万)
config.min_institution_count = 3
```

### NorthboundConfig

```python
from vnpy_china_strategy.config import NorthboundConfig

config = NorthboundConfig()
config.net_inflow_threshold = 10  # 净流入阈值(亿)
```

## 数据模型

### DragonTigerRecord

龙虎榜记录，包含机构席位和游资数据。

### NorthboundFlow

北向资金流向数据。

### SectorStrength

板块强度数据，包含动量指标。

### ConvertibleBond

可转债数据，包含转股溢价率等信息。

### EarningsForecast

业绩预告数据。

## 公共指标库

提供各类技术指标计算函数：

- `calculate_ma()`: 移动平均线
- `calculate_ema()`: 指数移动平均线
- `calculate_rsi()`: RSI 指标
- `calculate_macd()`: MACD 指标
- `calculate_bollinger_bands()`: 布林带
- `calculate_momentum()`: 动量指标
- `calculate_atr()`: ATR 指标
- `calculate_volume_ratio()`: 量比

## 依赖项

- vnpy (核心框架)
- vnpy_ctastrategy (CTA策略)
- vnpy_china_data (A股数据服务)
- pandas (数据处理)
- numpy (数值计算)

## 相关模块

- [vnpy_china_data](../vnpy_china_data/) - A股数据服务
- [vnpy_china_interface](../vnpy_china_interface/) - 数据接口定义
- [vnpy_china_config](../vnpy_china_config/) - 配置管理

---

*提示：本模块需要结合 vnpy_ctastrategy 和 vnpy_china_data 使用。*

## 变更记录

### 2026-02-26
- 🔴 **Bug修复**：修复数据服务未初始化错误
  - 修正 `gui_engine.py` 中的依赖注入逻辑
  - 从 `vnpy_china_data.get_data_service()` 获取底层数据服务
  - 正确传递给 `ChinaStrategyDataService` 初始化


<claude-mem-context>
# Recent Activity

<!-- This section is auto-generated by claude-mem. Edit content outside the tags. -->

### Feb 25, 2026

| ID | Time | T | Title | Read |
|----|------|---|-------|------|
| #7151 | 4:39 PM | 🔴 | ChinaStrategyEngine constructor fixed to pass engine_name | ~219 |
| #7108 | 4:17 PM | ✅ | vnpy_china_strategy/__init__.py updated with GUI imports | ~149 |
| #7103 | 4:15 PM | 🟣 | ChinaStrategyApp BaseApp subclass created | ~197 |
| #7088 | 4:13 PM | 🔵 | vnpy_china_strategy module API surface identified | ~318 |
</claude-mem-context>