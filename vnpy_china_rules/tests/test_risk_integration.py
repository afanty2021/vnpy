"""A股风控规则注册 vnpy_riskmanager 集成测试

默认跳过。启用方式（需 vnpy_riskmanager 已安装）：
    RUN_INTEGRATION=1 D:/Scoop/apps/miniconda3/current/envs/quant-3.11/python.exe \
        -m pytest vnpy_china_rules/tests/test_risk_integration.py -v
"""

import os
import unittest

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine

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
        # hasattr 双重保护：main_engine 存在且支持 close（vnpy BaseEngine 惯例提供）
        if hasattr(self, "main_engine") and hasattr(self.main_engine, "close"):
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
        self.assertIn(self.risk_engine.process_trade_event, trade_handlers)
        self.assertEqual(
            trade_handlers.count(self.risk_engine.process_trade_event), 1
        )


if __name__ == "__main__":
    unittest.main()
