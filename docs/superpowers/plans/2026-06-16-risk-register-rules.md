# 补完 _register_custom_rules 规则注册 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `AStockRiskManager` 的 4 个 A股风控规则在 vnpy_riskmanager 已安装时完整注册生效（下单拦截 + 状态更新 + 告警联动）。

**Architecture:** `manager.py` 顶部 try/except 导入 4 个规则类（降级 None，与 `risk/__init__.py` 一致）；重写 `_register_custom_rules` 为 `add_rule` + 收集实例 + 调 `_register_rule_events` + `set_risk_manager` 告警联动；新增 `_register_rule_events` 手动补注册事件回调（每事件类型显式 register 一次，不依赖 `EventEngine.register` 内部幂等性）。

**Tech Stack:** Python 3.11 / unittest + unittest.mock / pytest 运行器

**Spec:** `docs/superpowers/specs/2026-06-16-risk-register-rules-design.md`

**实现细化（对 spec §1）：** 规则类改在 `manager.py` **顶部** try/except 导入（非方法内 import），以便单测 `patch.object` 模块属性；前置条件不变（`_init_risk_manager` 成功后调用，运行时规则类非 None）。

**测试运行命令（统一）：**
```bash
D:/Scoop/apps/miniconda3/current/envs/quant-3.11/python.exe -m pytest <path> -v
```
（conda run 在 subagent 环境偶发 plugin 异常，用解释器绝对路径）

**提交约定：** 遵循项目 conventional commit + emoji 风格。**注意：output style 要求未获用户明确指示不主动 git 提交**——计划中的 commit 步骤在执行时由用户授权后进行。

---

## 文件结构

| 文件 | 责任 | 动作 |
|---|---|---|
| `vnpy_china_rules/risk/manager.py` | 顶部 try/except 导入规则类；重写 `_register_custom_rules`；新增 `_register_rule_events`；删除原 `importlib`/`pathlib` 死 import | 修改 |
| `vnpy_china_rules/tests/test_risk_manager.py` | `_register_rule_events` + `_register_custom_rules` 单测（mock，不需 vnpy_riskmanager） | 新建 |
| `vnpy_china_rules/tests/test_risk_integration.py` | 真实 vnpy_riskmanager 集成测试（默认 `@skipUnless RUN_INTEGRATION`） | 新建 |

---

## Task 1: `_register_rule_events`（事件回调补注册）

**Files:**
- Modify: `vnpy_china_rules/risk/manager.py`（新增 `_register_rule_events` 方法）
- Test: `vnpy_china_rules/tests/test_risk_manager.py`（新建）

- [ ] **Step 1: 写失败测试**

创建 `vnpy_china_rules/tests/test_risk_manager.py`：

```python
"""AStockRiskManager 单元测试（mock，不依赖 vnpy_riskmanager）"""

import unittest
from unittest.mock import MagicMock

from vnpy_china_rules.risk.manager import AStockRiskManager


class FakeRule:
    """Fake 规则实例，_callbacks 标记重写了哪些回调方法"""

    def __init__(self, name, callbacks=None):
        self.name = name
        self._callbacks = set(callbacks or [])


def make_mock_risk_engine():
    """构造 mock RiskEngine，needs_callback 按 rule._callbacks 判定"""
    re = MagicMock()
    re.tick_rules = []
    re.order_rules = []
    re.trade_rules = []
    re.timer_rules = []
    re.needs_callback = lambda rule, method: method in getattr(rule, "_callbacks", set())
    re.process_tick_event = MagicMock(name="process_tick_event")
    re.process_order_event = MagicMock(name="process_order_event")
    re.process_trade_event = MagicMock(name="process_trade_event")
    re.process_timer_event = MagicMock(name="process_timer_event")
    re.event_engine = MagicMock()
    return re


class TestRegisterRuleEvents(unittest.TestCase):
    """_register_rule_events：事件回调补注册"""

    def setUp(self):
        self.manager = AStockRiskManager(MagicMock(), MagicMock())

    def test_registers_callback_to_correct_bucket(self):
        """重写 on_trade 的规则加入 trade_rules，其他 bucket 不含"""
        rule = FakeRule("rule1", ["on_trade"])
        re = make_mock_risk_engine()
        self.manager.risk_engine = re

        self.manager._register_rule_events([rule])

        self.assertIn(rule, re.trade_rules)
        self.assertNotIn(rule, re.tick_rules)
        self.assertNotIn(rule, re.order_rules)
        self.assertNotIn(rule, re.timer_rules)

    def test_each_event_registered_once(self):
        """多个规则重写同一回调，该事件 handler 只 register 一次"""
        rule1 = FakeRule("r1", ["on_trade"])
        rule2 = FakeRule("r2", ["on_trade", "on_tick"])
        re = make_mock_risk_engine()
        self.manager.risk_engine = re

        self.manager._register_rule_events([rule1, rule2])

        trade_registers = [
            c for c in re.event_engine.register.call_args_list
            if c.args[1] is re.process_trade_event
        ]
        self.assertEqual(len(trade_registers), 1)
        tick_registers = [
            c for c in re.event_engine.register.call_args_list
            if c.args[1] is re.process_tick_event
        ]
        self.assertEqual(len(tick_registers), 1)

    def test_no_callback_no_register(self):
        """规则无重写回调，不 append 不 register"""
        rule = FakeRule("r1", [])
        re = make_mock_risk_engine()
        self.manager.risk_engine = re

        self.manager._register_rule_events([rule])

        self.assertEqual(re.tick_rules, [])
        self.assertEqual(re.order_rules, [])
        self.assertEqual(re.trade_rules, [])
        self.assertEqual(re.timer_rules, [])
        re.event_engine.register.assert_not_called()

    def test_already_in_bucket_no_dup(self):
        """规则已在 bucket，不重复 append"""
        rule = FakeRule("r1", ["on_trade"])
        re = make_mock_risk_engine()
        re.trade_rules.append(rule)  # 预置已在
        self.manager.risk_engine = re

        self.manager._register_rule_events([rule])

        self.assertEqual(re.trade_rules.count(rule), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试，确认失败**

```bash
D:/Scoop/apps/miniconda3/current/envs/quant-3.11/python.exe -m pytest vnpy_china_rules/tests/test_risk_manager.py -v
```
Expected: FAIL（`AttributeError: _register_rule_events`）

- [ ] **Step 3: 实现 `_register_rule_events`**

在 `vnpy_china_rules/risk/manager.py` 的 `_register_custom_rules` 方法**之后**插入新方法：

```python
    def _register_rule_events(self, rules):
        """为新注册的规则补注册事件回调

        register_events 已在 RiskEngine.__init__ 跑完，后 add_rule 的规则需手动补。
        needs_callback 在 add_rule（实例化）后调用，规则方法已绑定子类重写版本。
        每事件类型显式 register 一次（不依赖 EventEngine.register 内部幂等性）。
        """
        from vnpy.trader.event import (
            EVENT_TICK, EVENT_ORDER, EVENT_TRADE, EVENT_TIMER,
        )

        re = self.risk_engine
        buckets = [
            ("on_tick", re.tick_rules, EVENT_TICK, re.process_tick_event),
            ("on_order", re.order_rules, EVENT_ORDER, re.process_order_event),
            ("on_trade", re.trade_rules, EVENT_TRADE, re.process_trade_event),
            ("on_timer", re.timer_rules, EVENT_TIMER, re.process_timer_event),
        ]

        events_to_register = []
        for method_name, bucket, event_type, handler in buckets:
            added = False
            for rule in rules:
                if re.needs_callback(rule, method_name) and rule not in bucket:
                    bucket.append(rule)
                    added = True
            if added:
                events_to_register.append((event_type, handler))

        for event_type, handler in events_to_register:
            re.event_engine.register(event_type, handler)
```

- [ ] **Step 4: 跑测试，确认通过**

```bash
D:/Scoop/apps/miniconda3/current/envs/quant-3.11/python.exe -m pytest vnpy_china_rules/tests/test_risk_manager.py -v
```
Expected: PASS（4 个测试）

- [ ] **Step 5: 提交**（待用户授权）

```bash
git add vnpy_china_rules/risk/manager.py vnpy_china_rules/tests/test_risk_manager.py
git commit -m "✨ feat(vnpy_china_rules): 新增_register_rule_events补注册风控规则事件回调"
```

---

## Task 2: `_register_custom_rules` 重写（注册主流程 + 告警联动 + 删 importlib）

**Files:**
- Modify: `vnpy_china_rules/risk/manager.py`（顶部 try/except 导入规则类 + 重写 `_register_custom_rules`）
- Test: `vnpy_china_rules/tests/test_risk_manager.py`（追加测试类）

- [ ] **Step 1: 顶部 try/except 导入规则类**

在 `vnpy_china_rules/risk/manager.py` 顶部 import 区（`from vnpy_china_rules.datasource import DataSourceManager` 之后）插入：

```python
try:
    from vnpy_china_rules.risk.rules import (
        CapitalRiskRule,
        PositionControlRule,
        StopProfitLossRule,
        TradingLimitRule,
    )
except ImportError:
    # vnpy_riskmanager 缺失时降级为 None；_register_custom_rules 仅在
    # _init_risk_manager 成功后调用（vnpy_riskmanager 已安装），运行时非 None。
    CapitalRiskRule = None
    PositionControlRule = None
    StopProfitLossRule = None
    TradingLimitRule = None
```

- [ ] **Step 2: 追加失败测试**

在 `vnpy_china_rules/tests/test_risk_manager.py` 顶部 import 区追加：

```python
from unittest.mock import MagicMock, patch
from vnpy_china_rules.risk import manager as manager_module
```
（`patch` 替换原 `from unittest.mock import MagicMock` 行）

在文件末尾（`if __name__` 之前）追加测试类：

```python
class FakeRuleClass:
    """Fake 规则类（含 name 类属性），add_rule 后产生 FakeRuleInstance"""

    def __init__(self, name, alertable=False):
        self.name = name
        self.__name__ = name
        self._alertable = alertable


class FakeRuleInstance:
    """Fake 规则实例，alertable 决定是否有 set_risk_manager"""

    def __init__(self, name, alertable=False):
        self.name = name
        if alertable:
            self.set_risk_manager = MagicMock(name="set_risk_manager")


class TestRegisterCustomRules(unittest.TestCase):
    """_register_custom_rules：注册主流程 + 告警联动"""

    # 4 个规则类：前两个 alertable（CapitalRiskRule/PositionControlRule）
    RULE_SPECS = [
        ("CapitalRiskRule", True),
        ("PositionControlRule", True),
        ("StopProfitLossRule", False),
        ("TradingLimitRule", False),
    ]

    def setUp(self):
        self.manager = AStockRiskManager(MagicMock(), MagicMock())
        self.re = MagicMock()
        self.re.rules = {}

        def fake_add_rule(rule_class):
            alertable = rule_class._alertable
            instance = FakeRuleInstance(rule_class.name, alertable=alertable)
            self.re.rules[rule_class.name] = instance

        self.re.add_rule = MagicMock(side_effect=fake_add_rule)
        self.re.tick_rules = []
        self.re.order_rules = []
        self.re.trade_rules = []
        self.re.timer_rules = []
        self.re.needs_callback = lambda rule, method: method == "on_trade"
        self.re.process_tick_event = MagicMock()
        self.re.process_order_event = MagicMock()
        self.re.process_trade_event = MagicMock()
        self.re.process_timer_event = MagicMock()
        self.re.event_engine = MagicMock()
        self.manager.risk_engine = self.re
        self.manager.write_log = MagicMock()

    def _patches(self):
        classes = [FakeRuleClass(name, alertable) for name, alertable in self.RULE_SPECS]
        return [
            patch.object(manager_module, "CapitalRiskRule", classes[0]),
            patch.object(manager_module, "PositionControlRule", classes[1]),
            patch.object(manager_module, "StopProfitLossRule", classes[2]),
            patch.object(manager_module, "TradingLimitRule", classes[3]),
        ]

    def test_calls_add_rule_for_each_rule_class(self):
        """4 个规则类各调 add_rule 一次"""
        patches = self._patches()
        for p in patches:
            p.start()
        try:
            self.manager._register_custom_rules()
        finally:
            for p in patches:
                p.stop()

        self.assertEqual(self.re.add_rule.call_count, 4)

    def test_collects_instances_and_registers_events(self):
        """收集 4 个实例并调 _register_rule_events"""
        patches = self._patches()
        for p in patches:
            p.start()
        try:
            self.manager._register_custom_rules()
        finally:
            for p in patches:
                p.stop()

        # _register_rule_events 把 on_trade 规则加入 trade_rules
        # （setUp 中 needs_callback 仅对 on_trade 返回 True）
        self.assertEqual(len(self.re.trade_rules), 4)
        # EVENT_TRADE 注册一次
        trade_registers = [
            c for c in self.re.event_engine.register.call_args_list
            if c.args[1] is self.re.process_trade_event
        ]
        self.assertEqual(len(trade_registers), 1)

    def test_set_risk_manager_for_alertable_rules_only(self):
        """仅 alertable 规则（CapitalRiskRule/PositionControlRule）调 set_risk_manager"""
        patches = self._patches()
        for p in patches:
            p.start()
        try:
            self.manager._register_custom_rules()
        finally:
            for p in patches:
                p.stop()

        capital = self.re.rules["CapitalRiskRule"]
        position = self.re.rules["PositionControlRule"]
        stop = self.re.rules["StopProfitLossRule"]
        trading = self.re.rules["TradingLimitRule"]

        capital.set_risk_manager.assert_called_once_with(self.manager)
        position.set_risk_manager.assert_called_once_with(self.manager)
        self.assertFalse(hasattr(stop, "set_risk_manager"))
        self.assertFalse(hasattr(trading, "set_risk_manager"))

    def test_add_rule_exception_falls_back(self):
        """单个 add_rule 抛异常，降级日志，继续其他规则"""
        classes = [FakeRuleClass(n, a) for n, a in self.RULE_SPECS]
        call_count = [0]

        def add_rule_with_failure(rule_class):
            call_count[0] += 1
            if rule_class.name == "PositionControlRule":
                raise RuntimeError("db down")
            instance = FakeRuleInstance(rule_class.name, alertable=rule_class._alertable)
            self.re.rules[rule_class.name] = instance

        self.re.add_rule = MagicMock(side_effect=add_rule_with_failure)

        with patch.object(manager_module, "CapitalRiskRule", classes[0]), \
             patch.object(manager_module, "PositionControlRule", classes[1]), \
             patch.object(manager_module, "StopProfitLossRule", classes[2]), \
             patch.object(manager_module, "TradingLimitRule", classes[3]):
            self.manager._register_custom_rules()  # 不抛异常

        # PositionControlRule 缺失，其余 3 个注册
        self.assertIn("CapitalRiskRule", self.re.rules)
        self.assertNotIn("PositionControlRule", self.re.rules)
        self.assertIn("StopProfitLossRule", self.re.rules)
        self.assertIn("TradingLimitRule", self.re.rules)
        self.manager.write_log.assert_any_call(
            "注册风控规则失败 PositionControlRule: db down"
        )

    def test_empty_registered_rules_logs(self):
        """全部 add_rule 失败时，记录告警日志（非静默）"""
        self.re.add_rule = MagicMock(side_effect=RuntimeError("all fail"))

        with patch.object(manager_module, "CapitalRiskRule", FakeRuleClass("CapitalRiskRule")), \
             patch.object(manager_module, "PositionControlRule", FakeRuleClass("PositionControlRule")), \
             patch.object(manager_module, "StopProfitLossRule", FakeRuleClass("StopProfitLossRule")), \
             patch.object(manager_module, "TradingLimitRule", FakeRuleClass("TradingLimitRule")):
            self.manager._register_custom_rules()

        # 4 个失败日志 + 1 个汇总告警
        fail_logs = [c for c in self.manager.write_log.call_args_list
                     if "注册风控规则失败" in c.args[0]]
        self.assertEqual(len(fail_logs), 4)
        summary_logs = [c for c in self.manager.write_log.call_args_list
                        if "全部风控规则注册失败" in c.args[0]]
        self.assertEqual(len(summary_logs), 1)
```

- [ ] **Step 3: 跑测试，确认失败**

```bash
D:/Scoop/apps/miniconda3/current/envs/quant-3.11/python.exe -m pytest vnpy_china_rules/tests/test_risk_manager.py::TestRegisterCustomRules -v
```
Expected: FAIL（`_register_custom_rules` 仍是旧 importlib 实现，行为不符）

- [ ] **Step 4: 重写 `_register_custom_rules`**

替换 `vnpy_china_rules/risk/manager.py` 中整个 `_register_custom_rules` 方法（原 105-124 行的 importlib 动态加载实现）。新方法（用 Step 1 的模块级规则类引用，删除原 `from pathlib import Path` / `import importlib.util` 死 import）：

```python
    def _register_custom_rules(self):
        """注册 A股自定义风控规则到 vnpy_riskmanager 引擎

        前置：仅 _init_risk_manager 成功后调用（vnpy_riskmanager 已安装），
        故顶部导入的 4 个规则类必非 None。
        add_rule 用 rule_class.name（类属性）作 setting key 与 rules 字典 key，
        与实例 rule.name（继承类属性）一致——隐含契约：规则不在 on_init 中
        动态修改 self.name（当前 4 个规则均无此行为）。
        """
        rule_classes = [
            CapitalRiskRule, PositionControlRule,
            StopProfitLossRule, TradingLimitRule,
        ]

        registered_rules = []
        for rule_class in rule_classes:
            try:
                self.risk_engine.add_rule(rule_class)
                rule = self.risk_engine.rules.get(rule_class.name)
                if rule is not None:
                    registered_rules.append(rule)
                else:
                    self.write_log(f"注册风控规则未找到实例: {rule_class.name}")
            except Exception as e:
                self.write_log(f"注册风控规则失败 {rule_class.__name__}: {e}")

        if not registered_rules:
            self.write_log("全部风控规则注册失败，请检查 vnpy_riskmanager 与规则类")

        self._register_rule_events(registered_rules)

        # 告警联动：仅 CapitalRiskRule/PositionControlRule 有 set_risk_manager
        for rule in registered_rules:
            if hasattr(rule, "set_risk_manager"):
                rule.set_risk_manager(self)
            self.write_log(f"成功注册风控规则: {rule.name}")
```

> **删除 importlib 残留**：原方法体内的 `from pathlib import Path` 与 `import importlib.util` 随方法体整体替换被移除（它们在原方法内，不在模块顶部）。

- [ ] **Step 5: 跑测试，确认通过**

```bash
D:/Scoop/apps/miniconda3/current/envs/quant-3.11/python.exe -m pytest vnpy_china_rules/tests/test_risk_manager.py -v
```
Expected: PASS（Task 1 的 4 个 + Task 2 的 5 个 = 9 个测试）

- [ ] **Step 6: 全量回归，确认无破坏**

```bash
D:/Scoop/apps/miniconda3/current/envs/quant-3.11/python.exe -m pytest vnpy_china_rules/tests/ -v
```
Expected: 新增 9 个测试全绿；既有失败仍是 pre-existing 10 个（test_filter/strategy/gui_integration，与本次无关）

- [ ] **Step 7: 提交**（待用户授权）

```bash
git add vnpy_china_rules/risk/manager.py vnpy_china_rules/tests/test_risk_manager.py
git commit -m "✨ feat(vnpy_china_rules): _register_custom_rules完整注册规则(告警联动+降级+删importlib残留)"
```

---

## Task 3: 集成测试（默认跳过）

**Files:**
- Create: `vnpy_china_rules/tests/test_risk_integration.py`

- [ ] **Step 1: 创建集成测试文件**

创建 `vnpy_china_rules/tests/test_risk_integration.py`：

```python
"""A股风控规则注册 MySQL/vnpy_riskmanager 集成测试

默认跳过。启用方式（需 vnpy_riskmanager 已安装）：
    RUN_INTEGRATION=1 D:/Scoop/apps/miniconda3/current/envs/quant-3.11/python.exe \
        -m pytest vnpy_china_rules/tests/test_risk_integration.py -v
"""

import os
import unittest

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.object import OrderRequest
from vnpy.trader.constant import Direction, OrderType, Exchange

from vnpy_china_rules.risk.manager import AStockRiskManager


@unittest.skipUnless(os.getenv("RUN_INTEGRATION"), "需 RUN_INTEGRATION=1 及 vnpy_riskmanager")
class TestRiskRuleRegistrationIntegration(unittest.TestCase):
    """端到端：真实 vnpy_riskmanager + 4 规则注册"""

    def setUp(self):
        try:
            from vnpy_riskmanager import RiskManagerApp
            from vnpy_riskmanager.engine import RiskEngine
        except ImportError as e:
            self.skipTest(f"vnpy_riskmanager 不可用，跳过: {e}")

        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)
        self.main_engine.add_app(RiskManagerApp)
        self.risk_engine = self.main_engine.get_engine(RiskEngine)

        self.manager = AStockRiskManager(self.main_engine, self.event_engine)
        self.manager.risk_engine = self.risk_engine
        self.manager._register_custom_rules()

    def tearDown(self):
        if hasattr(self, "main_engine"):
            self.main_engine.close()

    def test_four_rules_registered(self):
        """4 个 A股规则注册到 risk_engine.rules"""
        from vnpy_china_rules.risk.rules import (
            CapitalRiskRule, PositionControlRule,
            StopProfitLossRule, TradingLimitRule,
        )
        names = {CapitalRiskRule.name, PositionControlRule.name,
                 StopProfitLossRule.name, TradingLimitRule.name}
        self.assertTrue(names.issubset(set(self.risk_engine.rules.keys())))

    def test_alertable_rules_have_risk_manager(self):
        """CapitalRiskRule/PositionControlRule 实例的 _risk_manager 已注入"""
        from vnpy_china_rules.risk.rules import CapitalRiskRule, PositionControlRule
        capital = self.risk_engine.rules[CapitalRiskRule.name]
        position = self.risk_engine.rules[PositionControlRule.name]
        self.assertIs(capital._risk_manager, self.manager)
        self.assertIs(position._risk_manager, self.manager)

    def test_event_handlers_registered_once(self):
        """EVENT_TRADE 等事件 handler 只注册一次（不重复）"""
        from vnpy.trader.event import EVENT_TRADE
        trade_handlers = self.event_engine._handlers.get(EVENT_TRADE, [])
        # process_trade_event 应在 handler 列表中
        self.assertIn(self.risk_engine.process_trade_event, trade_handlers)
        # 只出现一次
        self.assertEqual(
            trade_handlers.count(self.risk_engine.process_trade_event), 1
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 确认默认跳过**

```bash
D:/Scoop/apps/miniconda3/current/envs/quant-3.11/python.exe -m pytest vnpy_china_rules/tests/test_risk_integration.py -v
```
Expected: 3 SKIPPED（无 RUN_INTEGRATION）

- [ ] **Step 3: 提交**（待用户授权）

```bash
git add vnpy_china_rules/tests/test_risk_integration.py
git commit -m "✅ test(vnpy_china_rules): 新增风控规则注册集成测试(默认跳过)"
```

---

## 验收检查（实现完成后）

- [ ] 4 规则通过 `add_rule` 注册到 `risk_engine.rules`（单测 `test_calls_add_rule_for_each_rule_class`）
- [ ] 事件回调补注册，每事件 handler 只 register 一次（单测 `test_each_event_registered_once`）
- [ ] `CapitalRiskRule`/`PositionControlRule` 的 `set_risk_manager` 被调用（单测 `test_set_risk_manager_for_alertable_rules_only`）
- [ ] 单规则异常降级、全部失败有汇总日志（单测 `test_add_rule_exception_falls_back` / `test_empty_registered_rules_logs`）
- [ ] 集成测试默认跳过、启用后验证 4 规则注册 + handler 不重复（Task 3）
- [ ] `importlib`/`pathlib` 死 import 已删除（Task 2 Step 4）
- [ ] 全量回归无新增失败（既有 10 个 pre-existing 不变）
