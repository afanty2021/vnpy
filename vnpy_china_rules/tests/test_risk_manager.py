"""AStockRiskManager 单元测试（mock，不依赖 vnpy_riskmanager）"""

import unittest
from unittest.mock import MagicMock, patch

from vnpy_china_rules.risk.manager import AStockRiskManager
from vnpy_china_rules.risk import manager as manager_module


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
        """收集 4 个实例并触发事件注册"""
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

        def add_rule_with_failure(rule_class):
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

        self.assertIn("CapitalRiskRule", self.re.rules)
        self.assertNotIn("PositionControlRule", self.re.rules)
        self.assertIn("StopProfitLossRule", self.re.rules)
        self.assertIn("TradingLimitRule", self.re.rules)
        self.manager.write_log.assert_any_call(
            "注册风控规则失败 PositionControlRule: db down"
        )

    def test_empty_registered_rules_logs(self):
        """全部 add_rule 失败时，记录汇总告警日志（非静默）"""
        self.re.add_rule = MagicMock(side_effect=RuntimeError("all fail"))

        with patch.object(manager_module, "CapitalRiskRule", FakeRuleClass("CapitalRiskRule")), \
             patch.object(manager_module, "PositionControlRule", FakeRuleClass("PositionControlRule")), \
             patch.object(manager_module, "StopProfitLossRule", FakeRuleClass("StopProfitLossRule")), \
             patch.object(manager_module, "TradingLimitRule", FakeRuleClass("TradingLimitRule")):
            self.manager._register_custom_rules()

        fail_logs = [c for c in self.manager.write_log.call_args_list
                     if "注册风控规则失败" in c.args[0]]
        self.assertEqual(len(fail_logs), 4)
        summary_logs = [c for c in self.manager.write_log.call_args_list
                        if "全部风控规则注册失败" in c.args[0]]
        self.assertEqual(len(summary_logs), 1)

    def test_register_rule_events_failure_falls_back(self):
        """_register_rule_events 抛异常时降级日志，不阻断"""
        patches = self._patches()
        for p in patches:
            p.start()
        self.manager._register_rule_events = MagicMock(
            side_effect=RuntimeError("event register failed"))
        try:
            self.manager._register_custom_rules()  # 不抛异常
        finally:
            for p in patches:
                p.stop()

        self.manager.write_log.assert_any_call(
            "风控规则事件回调注册失败: event register failed"
        )

    def test_set_risk_manager_failure_falls_back(self):
        """单个规则 set_risk_manager 抛异常时降级，继续其他规则"""
        classes = [FakeRuleClass(n, a) for n, a in self.RULE_SPECS]

        def add_rule_with_failing_alert(rule_class):
            instance = FakeRuleInstance(rule_class.name, alertable=rule_class._alertable)
            if rule_class.name == "PositionControlRule":
                instance.set_risk_manager = MagicMock(
                    side_effect=RuntimeError("alert failed"))
            self.re.rules[rule_class.name] = instance

        self.re.add_rule = MagicMock(side_effect=add_rule_with_failing_alert)

        with patch.object(manager_module, "CapitalRiskRule", classes[0]), \
             patch.object(manager_module, "PositionControlRule", classes[1]), \
             patch.object(manager_module, "StopProfitLossRule", classes[2]), \
             patch.object(manager_module, "TradingLimitRule", classes[3]):
            self.manager._register_custom_rules()  # 不抛异常

        # CapitalRiskRule 的 set_risk_manager 仍调用（不被 PositionControlRule 失败阻断）
        capital = self.re.rules["CapitalRiskRule"]
        capital.set_risk_manager.assert_called_once_with(self.manager)
        # PositionControlRule 失败降级日志
        self.manager.write_log.assert_any_call(
            "风控规则告警联动失败 PositionControlRule: alert failed"
        )


if __name__ == "__main__":
    unittest.main()
