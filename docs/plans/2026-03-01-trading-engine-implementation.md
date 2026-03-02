# A股实盘交易引擎实现规划

> **For Claude:** REQUIRED SUB-SKILL: 使用 superpowers:subagent-driven-development 执行本计划

**目标：** 在现有 run_qmt_client.py 基础上构建半自动实盘交易引擎，支持信号生成→风险检查→人工确认→手动下单的完整流程

**架构概述：**
- 基于现有 RPC-QMT 连接（已有）
- 新增信号引擎模块：收集并聚合多策略信号
- 新增风控引擎模块：下单前风险检查（涨跌停、T+1、资金校验）
- 新增信号确认 UI：半自动交易界面，信号标注风险等级，人工确认后跳转手动下单
- 多策略调度器：并行运行多个策略，产生信号后统一汇总

**技术栈：**
- Python 3.11+
- PySide6 (GUI)
- VeighNa 事件引擎
- RPC-QMT 连接（现有）
- SQLite (信号/风控规则存储)

---

## 现有基础设施

### run_qmt_client.py (已实现)
- RPC Gateway 连接 QMT
- 持仓/资金同步显示
- 手动下单/撤单功能
- 7个A股增强模块集成

### rpc_realtime_signals.py (已实现)
- RPC 实时行情获取
- Alpha158 因子计算
- 模型信号生成
- 终端 UI 信号展示

---

## 待实现功能模块

### Task 1: 信号引擎模块 (vnpy_china_trading/signal_engine)

**文件：**
- 创建: `vnpy_china_trading/__init__.py`
- 创建: `vnpy_china_trading/signal_engine.py`
- 创建: `vnpy_china_trading/object.py`

**Step 1: 创建模块结构和基础对象**

```python
# vnpy_china_trading/object.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class SignalSource(Enum):
    ALPHA158 = "alpha158"
    CUSTOM = "custom"

class SignalDirection(Enum):
    LONG = "long"      # 做多
    SHORT = "short"    # 做空
    CLOSE = "close"    # 平仓
    HOLD = "hold"      # 持仓不动

class SignalStatus(Enum):
    PENDING = "pending"      # 待处理
    RISK_CHECKING = "risk_checking"  # 风控检查中
    RISK_PASSED = "risk_passed"       # 风控通过
    RISK_REJECTED = "risk_rejected"  # 风控拒绝
    CONFIRMED = "confirmed"    # 已确认（待下单）
    EXECUTED = "executed"      # 已执行
    CANCELLED = "cancelled"    # 已取消

@dataclass
class TradingSignal:
    """交易信号"""
    signal_id: str
    symbol: str
    exchange: str
    direction: SignalDirection
    strength: float  # 信号强度 0-1
    source: SignalSource
    model_name: str
    predicted_return: Optional[float]  # 预测收益率
    confidence: float  # 置信度 0-1
    created_time: datetime
    status: SignalStatus = SignalStatus.PENDING

    # 风控结果
    risk_check_result: Optional[dict] = None

@dataclass
class RiskCheckResult:
    """风控检查结果"""
    passed: bool
    reasons: list[str]  # 拒绝原因
    warnings: list[str]  # 警告信息
    limit_up: bool = False      # 是否涨停
    limit_down: bool = False    # 是否跌停
    t1_restriction: bool = False  # T+1限制
    insufficient_capital: bool = False  # 资金不足
    position_limit: bool = False  # 仓位超限
```

**Step 2: 实现信号引擎核心类**

```python
# vnpy_china_trading/signal_engine.py
from collections import defaultdict
from datetime import datetime
from threading import Lock
from typing import Callable, Optional

from .object import TradingSignal, SignalSource, SignalDirection, SignalStatus

class SignalEngine:
    """信号引擎 - 收集和聚合多策略信号"""

    def __init__(self, main_engine, event_engine):
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.signals: dict[str, TradingSignal] = {}
        self.lock = Lock()

        # 信号回调
        self.signal_callbacks: list[Callable] = []

    def add_signal(self, signal: TradingSignal) -> None:
        """添加新信号"""
        with self.lock:
            self.signals[signal.signal_id] = signal

        # 触发回调
        for callback in self.signal_callbacks:
            callback(signal)

    def get_pending_signals(self) -> list[TradingSignal]:
        """获取待处理信号"""
        with self.lock:
            return [s for s in self.signals.values()
                    if s.status == SignalStatus.PENDING]

    def update_signal_status(self, signal_id: str, status: SignalStatus) -> bool:
        """更新信号状态"""
        with self.lock:
            if signal_id in self.signals:
                self.signals[signal_id].status = status
                return True
        return False

    def register_callback(self, callback: Callable) -> None:
        """注册信号回调"""
        self.signal_callbacks.append(callback)
```

**Step 3: 创建 App 基类**

```python
# vnpy_china_trading/app.py
from vnpy.app import BaseApp

class ChinaTradingApp(BaseApp):
    """A股交易引擎应用"""

    app_name = "china_trading"
    app_display_name = "A股交易引擎"
    app_version = "1.0.0"

    def __init__(self, main_engine, event_engine):
        super().__init__(main_engine, event_engine)
        self.signal_engine = None
        self.risk_engine = None

    def start(self):
        # 初始化信号引擎和风控引擎
        pass

    def close(self):
        pass
```

**Step 4: 编写测试用例验证模块创建**

```bash
# 运行测试验证
python -c "from vnpy_china_trading import ChinaTradingApp; print('模块导入成功')"
```

**Step 5: 提交代码**

```bash
git add vnpy_china_trading/
git commit -m "feat(trading): 添加A股交易引擎基础模块"
```

---

### Task 2: 风险控制引擎 (vnpy_china_trading/risk_engine)

**文件：**
- 创建: `vnpy_china_trading/risk_engine.py`
- 创建: `vnpy_china_trading/rules/`

**Step 1: 创建风控规则基类**

```python
# vnpy_china_trading/rules/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class RiskCheckResult:
    passed: bool
    reasons: list[str]
    warnings: list[str]

class RiskRule(ABC):
    """风控规则基类"""

    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled

    @abstractmethod
    def check(self, signal, main_engine) -> RiskCheckResult:
        """执行风控检查"""
        pass
```

**Step 2: 实现核心风控规则**

```python
# vnpy_china_trading/rules/limit_rule.py
from .base import RiskRule, RiskCheckResult

class LimitUpDownRule(RiskRule):
    """涨跌停规则"""

    def __init__(self):
        super().__init__("涨跌停检查")

    def check(self, signal, main_engine) -> RiskCheckResult:
        reasons = []
        warnings = []

        # 获取当前价格和涨跌停状态
        tick = main_engine.get_tick(signal.symbol)
        if not tick:
            warnings.append("无法获取行情数据")
            return RiskCheckResult(True, [], warnings)

        # 检查是否涨停/跌停
        if tick.limit_up:
            reasons.append("股票已涨停")
            return RiskCheckResult(False, reasons, warnings)

        if tick.limit_down:
            reasons.append("股票已跌停")
            return RiskCheckResult(False, reasons, warnings)

        return RiskCheckResult(True, [], warnings)


# vnpy_china_trading/rules/t1_rule.py
class T1RestrictionRule(RiskRule):
    """T+1 交易规则"""

    def __init__(self):
        super().__init__("T+1检查")

    def check(self, signal, main_engine) -> RiskCheckResult:
        reasons = []
        warnings = []

        # 检查今日是否已买入过该股票
        # A股市场：当日买入不能当日卖出
        if signal.direction.value in ["long", "short"]:
            # 查询今日是否有买入成交
            trades = main_engine.get_trades()
            today_buys = [t for t in trades
                         if t.symbol == signal.symbol
                         and t.direction.value == "long"
                         and t.datetime.date() == datetime.now().date()]

            if today_buys:
                # 检查持仓情况
                position = main_engine.get_position(signal.symbol)
                if position and position.volume > 0:
                    reasons.append("T+1限制：当日买入后不能卖出")
                    return RiskCheckResult(False, reasons, warnings)

        return RiskCheckResult(True, [], warnings)


# vnpy_china_trading/rules/capital_rule.py
class CapitalRule(RiskRule):
    """资金检查规则"""

    def __init__(self, min_balance: float = 10000):
        super().__init__("资金检查")
        self.min_balance = min_balance

    def check(self, signal, main_engine) -> RiskCheckResult:
        reasons = []
        warnings = []

        # 获取账户资金
        account = main_engine.get_account("RPC")
        if not account:
            reasons.append("无法获取账户信息")
            return RiskCheckResult(False, reasons, warnings)

        # 估算所需资金（假设买入1手）
        tick = main_engine.get_tick(signal.signal_symbol)
        if tick:
            estimated_cost = tick.ask_price_1 * 100
            if account.balance < estimated_cost:
                reasons.append(f"资金不足：账户余额 {account.balance:.2f}，预估需要 {estimated_cost:.2f}")
                return RiskCheckResult(False, reasons, warnings)

        # 检查最低余额
        if account.balance < self.min_balance:
            warnings.append(f"账户余额低于最低要求 {self.min_balance}")

        return RiskCheckResult(True, [], warnings)


# vnpy_china_trading/rules/position_limit_rule.py
class PositionLimitRule(RiskRule):
    """持仓数量限制规则"""

    def __init__(self, max_positions: int = 10):
        super().__init__("持仓数量限制")
        self.max_positions = max_positions

    def check(self, signal, main_engine) -> RiskCheckResult:
        reasons = []
        warnings = []

        # 检查总持仓数量
        positions = main_engine.get_all_positions()
        if len(positions) >= self.max_positions:
            reasons.append(f"持仓数量已达上限 {self.max_positions}")
            return RiskCheckResult(False, reasons, warnings)

        return RiskCheckResult(True, [], warnings)
```

**Step 3: 实现风控引擎主类**

```python
# vnpy_china_trading/risk_engine.py
from .rules.base import RiskRule, RiskCheckResult
from .rules.limit_rule import LimitUpDownRule
from .rules.t1_rule import T1RestrictionRule
from .rules.capital_rule import CapitalRule
from .rules.position_limit_rule import PositionLimitRule

class RiskEngine:
    """风险控制引擎"""

    def __init__(self, main_engine):
        self.main_engine = main_engine
        self.rules: list[RiskRule] = []
        self._init_default_rules()

    def _init_default_rules(self):
        """初始化默认风控规则"""
        self.add_rule(LimitUpDownRule())
        self.add_rule(T1RestrictionRule())
        self.add_rule(CapitalRule(min_balance=10000))
        self.add_rule(PositionLimitRule(max_positions=10))

    def add_rule(self, rule: RiskRule) -> None:
        """添加风控规则"""
        self.rules.append(rule)

    def remove_rule(self, rule_name: str) -> bool:
        """移除风控规则"""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                self.rules.pop(i)
                return True
        return False

    def check_signal(self, signal) -> RiskCheckResult:
        """检查信号是否通过风控"""
        all_reasons = []
        all_warnings = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            result = rule.check(signal, self.main_engine)

            if not result.passed:
                all_reasons.extend(result.reasons)

            all_warnings.extend(result.warnings)

        passed = len(all_reasons) == 0

        # 添加风控结果到信号
        signal.risk_check_result = {
            "passed": passed,
            "reasons": all_reasons,
            "warnings": all_warnings
        }

        return RiskCheckResult(passed, all_reasons, all_warnings)
```

**Step 4: 编写测试用例**

```python
# tests/test_risk_engine.py
import pytest
from unittest.mock import Mock, MagicMock
from vnpy_china_trading.risk_engine import RiskEngine
from vnpy_china_trading.rules.base import RiskRule, RiskCheckResult
from vnpy_china_trading.object import TradingSignal, SignalDirection

class TestRiskEngine:
    def test_add_rule(self):
        engine = RiskEngine(Mock())
        rule = RiskRule("测试规则")
        engine.add_rule(rule)
        assert len(engine.rules) == 1

    def test_check_signal_pass(self):
        mock_engine = Mock()
        mock_engine.get_tick.return_value = MagicMock(limit_up=False, limit_down=False)
        mock_engine.get_account.return_value = MagicMock(balance=100000)
        mock_engine.get_all_positions.return_value = []

        engine = RiskEngine(mock_engine)
        signal = TradingSignal(...)
        result = engine.check_signal(signal)
        assert result.passed

    def test_limit_up_reject(self):
        mock_engine = Mock()
        mock_engine.get_tick.return_value = MagicMock(limit_up=True, limit_down=False)

        engine = RiskEngine(mock_engine)
        signal = TradingSignal(...)
        result = engine.check_signal(signal)
        assert not result.passed
        assert any("涨停" in r for r in result.reasons)
```

**Step 5: 运行测试**

```bash
pytest vnpy_china_trading/tests/test_risk_engine.py -v
```

**Step 6: 提交代码**

```bash
git add vnpy_china_trading/
git commit -m "feat(trading): 添加风险控制引擎和规则"
```

---

### Task 3: 信号确认 UI (vnpy_china_trading/ui/widget.py)

**文件：**
- 创建: `vnpy_china_trading/ui/__init__.py`
- 创建: `vnpy_china_trading/ui/widget.py`

**Step 1: 创建信号监控窗口**

```python
# vnpy_china_trading/ui/widget.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QTextEdit
)
from PySide6.QtCore import Qt, QTimer
from vnpy.trader.ui.widget import BaseCell, EnumCell
from vnpy.trader.object import TickData, TradeData

class SignalMonitor(QWidget):
    """信号监控窗口"""

    def __init__(self, signal_engine, risk_engine):
        super().__init__()
        self.signal_engine = signal_engine
        self.risk_engine = risk_engine
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("交易信号监控")
        self.resize(1000, 600)

        layout = QVBoxLayout()

        # 工具栏
        toolbar = QHBoxLayout()
        self.btn_refresh = QPushButton("刷新")
        self.btn_confirm = QPushButton("确认下单")
        self.btn_cancel = QPushButton("取消")
        toolbar.addWidget(self.btn_refresh)
        toolbar.addWidget(self.btn_confirm)
        toolbar.addWidget(self.btn_cancel)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 信号表格
        self.signal_table = QTableWidget()
        self.signal_table.setColumnCount(10)
        self.signal_table.setHorizontalHeaderLabels([
            "时间", "股票", "方向", "强度", "来源", "预测收益",
            "风控状态", "拒绝原因", "确认", "操作"
        ])
        self.signal_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.signal_table)

        # 详情面板
        detail_layout = QHBoxLayout()
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        detail_layout.addWidget(QLabel("信号详情:"))
        detail_layout.addWidget(self.detail_text)
        layout.addLayout(detail_layout)

        self.setLayout(layout)

        # 定时刷新
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_signals)
        self.timer.start(2000)  # 每2秒刷新

    def refresh_signals(self):
        """刷新信号列表"""
        signals = self.signal_engine.get_pending_signals()
        self.signal_table.setRowCount(len(signals))

        for row, signal in enumerate(signals):
            # 填充表格...
            pass
```

**Step 2: 添加风险告警窗口**

```python
class RiskAlertPanel(QWidget):
    """风险告警面板"""

    def __init__(self, risk_engine):
        super().__init__()
        self.risk_engine = risk_engine
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 告警列表
        self.alert_list = QTableWidget()
        self.alert_list.setColumnCount(4)
        self.alert_list.setHorizontalHeaderLabels(["时间", "类型", "股票", "描述"])
        layout.addWidget(self.alert_list)

        self.setLayout(layout)

    def add_alert(self, alert_type: str, symbol: str, message: str):
        """添加告警"""
        row = self.alert_list.rowCount()
        self.alert_list.insertRow(row)
        # 填充告警信息...
```

**Step 3: 集成到 run_qmt_client.py**

```python
# examples/client_server/run_qmt_client.py

# 添加新的导入
from vnpy_china_trading import ChinaTradingApp

def start_gui_with_rpc():
    # ... 现有代码 ...

    # 添加交易引擎模块
    trading_app = main_engine.add_app(ChinaTradingApp)
    print("  ✓ A股交易引擎模块")

    # 启动交易引擎
    trading_app.start()

    # ... 现有代码 ...
```

**Step 4: 提交代码**

```bash
git add vnpy_china_trading/ examples/client_server/run_qmt_client.py
git commit -m "feat(trading): 添加信号确认UI和风险告警面板"
```

---

### Task 4: 多策略调度器 (vnpy_china_trading/scheduler.py)

**文件：**
- 创建: `vnpy_china_trading/scheduler.py`

**Step 1: 实现策略调度器**

```python
# vnpy_china_trading/scheduler.py
from dataclasses import dataclass
from datetime import datetime, time
from threading import Thread, Event
from typing import Callable, Optional
import schedule
import time as time_module

@dataclass
class StrategyConfig:
    """策略配置"""
    name: str
    enabled: bool
    run_interval: int  # 运行间隔（秒）
    run_time_start: Optional[time]  # 开始时间
    run_time_end: Optional[time]  # 结束时间
    callback: Callable  # 回调函数

class StrategyScheduler:
    """多策略调度器"""

    def __init__(self):
        self.strategies: dict[str, StrategyConfig] = {}
        self.running = Event()
        self.threads: list[Thread] = []

    def add_strategy(self, config: StrategyConfig) -> None:
        """添加策略"""
        self.strategies[config.name] = config

    def remove_strategy(self, name: str) -> bool:
        """移除策略"""
        if name in self.strategies:
            del self.strategies[name]
            return True
        return False

    def start(self) -> None:
        """启动调度器"""
        self.running.set()

        for name, config in self.strategies.items():
            if not config.enabled:
                continue

            thread = Thread(target=self._run_strategy, args=(config,))
            thread.daemon = True
            thread.start()
            self.threads.append(thread)

    def stop(self) -> None:
        """停止调度器"""
        self.running.clear()
        for thread in self.threads:
            thread.join(timeout=5)
        self.threads.clear()

    def _run_strategy(self, config: StrategyConfig) -> None:
        """运行策略"""
        while self.running.is_set():
            # 检查交易时间
            now = datetime.now().time()
            if config.run_time_start and now < config.run_time_start:
                time_module.sleep(60)
                continue

            if config.run_time_end and now > config.run_time_end:
                break

            try:
                config.callback()
            except Exception as e:
                print(f"策略 {config.name} 执行错误: {e}")

            time_module.sleep(config.run_interval)
```

**Step 2: 集成 Alpha158 信号生成**

```python
# 在信号引擎中添加策略调用示例

def register_alpha158_strategy(signal_engine: SignalEngine, scheduler: StrategyScheduler):
    """注册 Alpha158 策略"""

    def generate_signals():
        # 1. 获取实时行情
        # 2. 计算 Alpha158 因子
        # 3. 使用模型预测
        # 4. 生成信号
        signal_engine.add_signal(signal)

    config = StrategyConfig(
        name="Alpha158",
        enabled=True,
        run_interval=300,  # 5分钟
        run_time_start=time(9, 30),
        run_time_end=time(15, 0),
        callback=generate_signals
    )

    scheduler.add_strategy(config)
```

**Step 3: 提交代码**

```bash
git add vnpy_china_trading/scheduler.py
git commit -m "feat(trading): 添加多策略调度器"
```

---

### Task 5: 集成测试 - 完整交易流程

**文件：**
- 创建: `examples/test_trading_flow.py`

**Step 1: 实现端到端测试**

```python
# examples/test_trading_flow.py
"""
完整交易流程测试：
1. 模拟信号生成
2. 风控检查
3. 人工确认
4. 下单执行
"""

def test_trading_flow():
    """测试完整交易流程"""

    # 1. 初始化
    from vnpy_china_trading import ChinaTradingApp
    from unittest.mock import Mock

    main_engine = Mock()
    event_engine = Mock()

    app = ChinaTradingApp(main_engine, event_engine)
    app.start()

    # 2. 生成测试信号
    signal = TradingSignal(
        signal_id="test_001",
        symbol="000001",
        exchange="SSE",
        direction=SignalDirection.LONG,
        strength=0.8,
        source=SignalSource.ALPHA158,
        model_name="alpha158_lgb",
        predicted_return=0.02,
        confidence=0.75,
        created_time=datetime.now()
    )

    # 3. 添加信号
    app.signal_engine.add_signal(signal)
    assert len(app.signal_engine.get_pending_signals()) == 1

    # 4. 风控检查
    result = app.risk_engine.check_signal(signal)
    print(f"风控检查结果: {result}")

    # 5. 验证信号状态更新
    updated_signal = app.signal_engine.signals[signal.signal_id]
    assert updated_signal.risk_check_result is not None

    print("✓ 完整交易流程测试通过")

if __name__ == "__main__":
    test_trading_flow()
```

**Step 2: 运行测试**

```bash
python examples/test_trading_flow.py
```

**Step 3: 提交代码**

```bash
git add examples/test_trading_flow.py
git commit -m "test(trading): 添加完整交易流程测试"
```

---

## 实施顺序总结

| 任务 | 描述 | 依赖 |
|------|------|------|
| Task 1 | 信号引擎模块基础 | 无 |
| Task 2 | 风险控制引擎 | Task 1 |
| Task 3 | 信号确认 UI | Task 1, Task 2 |
| Task 4 | 多策略调度器 | Task 1 |
| Task 5 | 集成测试 | Task 1-4 |

---

## 与现有代码的集成

### 复用 rpc_realtime_signals.py

现有的 `rpc_realtime_signals.py` 已经实现了：
- RPC 实时行情获取
- Alpha158 因子计算
- 模型信号生成

可以将信号输出改为发送到 SignalEngine：
```python
# 修改 rpc_realtime_signals.py
from vnpy_china_trading import ChinaTradingApp

# 在生成信号后
signal_engine.add_signal(signal)
```

### 复用现有风控规则

现有的 `vnpy_china_rules` 模块已有：
- T+1 规则检查
- 涨跌停检查
- 交易时间检查

可以直接复用这些规则到 RiskEngine。

---

## 文件结构

```
vnpy_china_trading/
├── __init__.py
├── app.py                    # App 基类
├── object.py                # 数据对象定义
├── signal_engine.py         # 信号引擎
├── risk_engine.py           # 风控引擎
├── scheduler.py             # 多策略调度器
├── ui/
│   ├── __init__.py
│   └── widget.py            # GUI 组件
├── rules/
│   ├── __init__.py
│   └── base.py              # 规则基类
└── tests/
    ├── __init__.py
    ├── test_signal_engine.py
    └── test_risk_engine.py

examples/
└── test_trading_flow.py     # 集成测试
```
