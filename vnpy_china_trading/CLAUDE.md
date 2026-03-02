# vnpy_china_trading - A股交易引擎

> 更新时间：2026-03-02
> 版本：1.0.0

## 模块概述

vnpy_china_trading 模块提供 A 股半自动实盘交易引擎，支持信号生成→风险检查→人工确认→手动下单的完整流程。

## 核心功能

### 1. 信号引擎 (SignalEngine)
- 收集多策略产生的交易信号
- 信号状态管理（PENDING → RISK_CHECKING → RISK_PASSED/RISK_REJECTED → CONFIRMED → EXECUTED）
- 信号回调机制，支持实时通知
- 线程安全设计

### 2. 风控引擎 (RiskEngine)
- 涨跌停检查
- T+1 交易限制检查
- 资金余额检查
- 持仓数量限制检查
- 支持自定义规则扩展

### 3. 策略调度器 (StrategyScheduler)
- 多策略并行调度
- 时间窗口控制
- 策略运行间隔配置
- 异常隔离

### 4. UI 组件
- SignalMonitor：信号监控窗口
- RiskAlertPanel：风险告警面板

## 快速开始

### 1. 基本使用

```python
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_china_trading import ChinaTradingApp

# 初始化
event_engine = EventEngine()
main_engine = MainEngine(event_engine)

# 添加交易引擎
app = main_engine.add_app(ChinaTradingApp)
app.start()

# 获取信号引擎
signal_engine = app.get_signal_engine()
risk_engine = app.get_risk_engine()
```

### 2. 添加交易信号

```python
from vnpy_china_trading.object import (
    TradingSignal, SignalSource, SignalDirection, SignalStatus
)
from datetime import datetime

# 方式1：直接创建信号对象
signal = TradingSignal(
    signal_id="SIGNAL-001",
    symbol="000001",
    exchange="SZSE",
    direction=SignalDirection.LONG,
    strength=0.8,
    source=SignalSource.ALPHA158,
    model_name="alpha158_lgb",
    predicted_return=0.02,
    confidence=0.75,
    created_time=datetime.now(),
    status=SignalStatus.PENDING,
)
signal_engine.add_signal(signal)

# 方式2：通过引擎方法添加
signal_engine.add_signal(
    symbol="600000",
    exchange="SHSE",
    direction=SignalDirection.SHORT,
    source=SignalSource.MANUAL,
    strength=0.6,
    model_name="manual",
    predicted_return=-0.01,
    confidence=0.8,
)
```

### 3. 风控检查

```python
# 获取待处理信号
pending_signals = signal_engine.get_pending_signals()

# 对每个信号进行风控检查
for signal in pending_signals:
    # 更新状态为检查中
    signal_engine.update_signal_status(
        signal.signal_id,
        SignalStatus.RISK_CHECKING
    )

    # 执行风控检查
    result = risk_engine.check_signal(signal)

    if result.passed:
        # 风控通过
        signal_engine.update_signal_status(
            signal.signal_id,
            SignalStatus.RISK_PASSED
        )
    else:
        # 风控拒绝
        print(f"风控拒绝: {signal.symbol}, 原因: {result.reasons}")
        signal_engine.update_signal_status(
            signal.signal_id,
            SignalStatus.RISK_REJECTED
        )
```

### 4. 人工确认与执行

```python
# 人工确认后更新状态
signal_engine.confirm_signal(signal_id)

# 执行下单（标记为已执行）
signal_engine.execute_signal(signal_id)

# 或者取消信号
signal_engine.cancel_signal(signal_id)
```

### 5. 策略调度

```python
from vnpy_china_trading.scheduler import StrategyScheduler, StrategyConfig
from datetime import time

def my_strategy_callback():
    """策略回调函数"""
    # 获取行情、计算信号、添加到信号引擎
    pass

# 创建调度器
scheduler = StrategyScheduler()

# 添加策略
config = StrategyConfig(
    name="Alpha158策略",
    enabled=True,
    run_interval=300,  # 5分钟执行一次
    run_time_start=time(9, 30),  # 交易时间开始
    run_time_end=time(15, 0),   # 交易时间结束
    callback=my_strategy_callback,
)
scheduler.add_strategy(config)

# 启动调度器
scheduler.start()

# ... 交易时间结束 ...

# 停止调度器
scheduler.stop()
```

## 与 run_qmt_client.py 集成

在现有的 `run_qmt_client.py` 中添加交易引擎：

```python
# examples/client_server/run_qmt_client.py

from vnpy_china_trading import ChinaTradingApp

def start_gui_with_rpc():
    # ... 现有代码 ...

    # 添加交易引擎模块
    trading_app = main_engine.add_app(ChinaTradingApp)
    trading_app.start()
    print("  ✓ A股交易引擎模块")

    # ... 现有代码 ...
```

## 测试

### 单元测试

```bash
# 运行所有单元测试
pytest vnpy_china_trading/tests/ -v

# 运行单个测试
pytest vnpy_china_trading/tests/test_signal_engine.py -v
```

### 集成测试

```bash
# 运行基本集成测试
python examples/test_trading_flow.py

# 运行QMT环境集成测试（需要RPC服务运行）
python examples/test_qmt_integration.py
```

## 模块结构

```
vnpy_china_trading/
├── __init__.py           # 模块入口
├── app.py                # ChinaTradingApp 应用类
├── object.py             # 数据对象定义
├── signal_engine.py      # 信号引擎
├── risk_engine.py        # 风控引擎
├── scheduler.py          # 策略调度器
├── ui/
│   ├── __init__.py
│   └── widget.py        # UI组件
├── rules/
│   ├── __init__.py
│   ├── base.py          # 规则基类
│   ├── limit_rule.py    # 涨跌停规则
│   ├── t1_rule.py       # T+1规则
│   ├── capital_rule.py  # 资金规则
│   └── position_limit_rule.py  # 持仓限制
└── tests/
    ├── test_signal_engine.py
    ├── test_risk_engine.py
    └── test_scheduler.py
```

## 配置说明

### 风控规则配置

风控引擎默认初始化以下规则：

| 规则 | 默认值 | 说明 |
|------|--------|------|
| LimitUpDownRule | 启用 | 检查涨跌停 |
| T1RestrictionRule | 启用 | T+1交易限制 |
| CapitalRule | min_balance=10000 | 最低资金余额 |
| PositionLimitRule | max_positions=10 | 最大持仓数量 |

### 自定义规则

```python
from vnpy_china_trading.rules.base import RiskRule, RiskCheckResult

class MyCustomRule(RiskRule):
    """自定义风控规则"""

    def __init__(self):
        super().__init__("自定义规则")

    def check(self, signal, main_engine) -> RiskCheckResult:
        reasons = []
        warnings = []

        # 实现自定义检查逻辑
        if some_condition:
            reasons.append("不满足自定义条件")

        return RiskCheckResult(
            passed=len(reasons) == 0,
            reasons=reasons,
            warnings=warnings,
        )

# 添加自定义规则
risk_engine.add_rule(MyCustomRule())
```

## 变更记录

### 2026-03-02
- 初始化模块
- 实现信号引擎、风控引擎、策略调度器
- 添加 UI 组件
- 添加单元测试和集成测试
