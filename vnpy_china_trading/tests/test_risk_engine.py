# -*- coding: utf-8 -*-
"""
风险控制引擎测试

测试风控引擎和各个风控规则的功能。
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from typing import Any

from vnpy_china_trading.risk_engine import RiskEngine
from vnpy_china_trading.rules import (
    RiskRule,
    RiskCheckResult,
    LimitUpDownRule,
    T1RestrictionRule,
    CapitalRule,
    PositionLimitRule,
)
from vnpy_china_trading.object import (
    TradingSignal,
    SignalDirection,
    SignalSource,
    SignalStatus,
)


class MockMainEngine:
    """模拟主引擎"""

    def __init__(self):
        self.ticks: dict = {}
        self.accounts: dict = {}
        self.positions: dict = {}
        self.trades: list = []

    def get_tick(self, vt_symbol: str) -> Any:
        return self.ticks.get(vt_symbol)

    def get_all_accounts(self) -> dict:
        return self.accounts

    def get_account(self, gateway_name: str) -> Any:
        return self.accounts.get(gateway_name)

    def get_all_positions(self) -> dict:
        return self.positions

    def get_all_trades(self) -> list:
        return self.trades


class MockTickData:
    """模拟Tick数据"""

    def __init__(self, last_price: float = 10.0, limit_up: float = 11.0, limit_down: float = 9.0):
        self.symbol = "000001"
        self.exchange = "SZSE"
        self.vt_symbol = "000001.SZSE"
        self.last_price = last_price
        self.limit_up = limit_up
        self.limit_down = limit_down
        self.datetime = datetime.now()


class MockTradeData:
    """模拟成交数据"""

    def __init__(self, symbol: str, vt_symbol: str, direction: str, datetime_obj: datetime):
        self.symbol = symbol
        self.vt_symbol = vt_symbol
        self.direction = direction
        self.datetime = datetime_obj


class MockPositionData:
    """模拟持仓数据"""

    def __init__(self, symbol: str, vt_symbol: str, volume: float = 100):
        self.symbol = symbol
        self.vt_symbol = vt_symbol
        self.volume = volume
        self.direction = None


class MockAccountData:
    """模拟账户数据"""

    def __init__(self, balance: float = 100000, available: float = 80000):
        self.accountid = "test_account"
        self.balance = balance
        self.available = available


def create_test_signal(
    symbol: str = "000001",
    exchange: str = "SZSE",
    direction: SignalDirection = SignalDirection.LONG,
) -> TradingSignal:
    """创建测试信号"""
    return TradingSignal(
        signal_id="TEST-001",
        symbol=symbol,
        exchange=exchange,
        direction=direction,
        strength=1.0,
        source=SignalSource.CUSTOM,
    )


class TestRiskEngine(unittest.TestCase):
    """风险引擎测试"""

    def setUp(self):
        self.main_engine = MockMainEngine()
        self.risk_engine = RiskEngine(self.main_engine)

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.risk_engine.main_engine)
        self.assertEqual(len(self.risk_engine.rules), 4)

    def test_add_rule(self):
        """测试添加规则"""
        # 创建一个自定义规则
        class CustomRule(RiskRule):
            def __init__(self):
                super().__init__("自定义规则", enabled=True)

            def check(self, signal, main_engine):
                return RiskCheckResult(passed=True)

        rule = CustomRule()
        self.risk_engine.add_rule(rule)
        self.assertEqual(len(self.risk_engine.rules), 5)

    def test_remove_rule(self):
        """测试移除规则"""
        result = self.risk_engine.remove_rule("涨跌停规则")
        self.assertTrue(result)
        self.assertEqual(len(self.risk_engine.rules), 3)

    def test_enable_rule(self):
        """测试启用规则"""
        self.risk_engine.disable_rule("涨跌停规则")
        self.assertFalse(self.risk_engine.get_rule("涨跌停规则").enabled)
        self.risk_engine.enable_rule("涨跌停规则")
        self.assertTrue(self.risk_engine.get_rule("涨跌停规则").enabled)

    def test_disable_rule(self):
        """测试禁用规则"""
        result = self.risk_engine.disable_rule("涨跌停规则")
        self.assertTrue(result)
        self.assertFalse(self.risk_engine.get_rule("涨跌停规则").enabled)

    def test_check_signal(self):
        """测试信号检查"""
        signal = create_test_signal()
        result = self.risk_engine.check_signal(signal)
        self.assertIsInstance(result, RiskCheckResult)

    def test_check_invalid_signal(self):
        """测试无效信号"""
        result = self.risk_engine.check_signal("invalid")
        self.assertFalse(result.passed)


class TestLimitRule(unittest.TestCase):
    """涨跌停规则测试"""

    def test_limit_up(self):
        """测试涨停检查"""
        main_engine = MockMainEngine()
        main_engine.ticks["000001.SZSE"] = MockTickData(
            last_price=11.0, limit_up=11.0, limit_down=9.0
        )

        rule = LimitUpDownRule()
        signal = create_test_signal(direction=SignalDirection.LONG)
        result = rule.check(signal, main_engine)

        self.assertFalse(result.passed)
        self.assertTrue(result.limit_up)
        self.assertIn("已涨停", result.reasons[0])

    def test_limit_down(self):
        """测试跌停检查"""
        main_engine = MockMainEngine()
        main_engine.ticks["000001.SZSE"] = MockTickData(
            last_price=9.0, limit_up=11.0, limit_down=9.0
        )

        rule = LimitUpDownRule()
        signal = create_test_signal(direction=SignalDirection.SHORT)
        result = rule.check(signal, main_engine)

        self.assertFalse(result.passed)
        self.assertTrue(result.limit_down)
        self.assertIn("已跌停", result.reasons[0])

    def test_normal(self):
        """测试正常情况"""
        main_engine = MockMainEngine()
        main_engine.ticks["000001.SZSE"] = MockTickData(
            last_price=10.0, limit_up=11.0, limit_down=9.0
        )

        rule = LimitUpDownRule()
        signal = create_test_signal(direction=SignalDirection.LONG)
        result = rule.check(signal, main_engine)

        self.assertTrue(result.passed)

    def test_disabled(self):
        """测试禁用规则"""
        main_engine = MockMainEngine()
        main_engine.ticks["000001.SZSE"] = MockTickData(
            last_price=11.0, limit_up=11.0, limit_down=9.0
        )

        rule = LimitUpDownRule(enabled=False)
        signal = create_test_signal(direction=SignalDirection.LONG)
        result = rule.check(signal, main_engine)

        self.assertTrue(result.passed)


class TestT1Rule(unittest.TestCase):
    """T+1规则测试"""

    def test_t1_restriction(self):
        """测试T+1限制"""
        main_engine = MockMainEngine()
        today = datetime.now()
        trade = MockTradeData(
            symbol="000001",
            vt_symbol="000001.SZSE",
            direction="Direction.LONG",
            datetime_obj=today,
        )
        main_engine.trades = [trade]

        rule = T1RestrictionRule()
        signal = create_test_signal(direction=SignalDirection.LONG)
        result = rule.check(signal, main_engine)

        self.assertFalse(result.passed)
        self.assertTrue(result.t1_restriction)
        self.assertIn("T+1", result.reasons[0])

    def test_no_t1_restriction(self):
        """测试无T+1限制"""
        main_engine = MockMainEngine()
        main_engine.trades = []

        rule = T1RestrictionRule()
        signal = create_test_signal(direction=SignalDirection.LONG)
        result = rule.check(signal, main_engine)

        self.assertTrue(result.passed)

    def test_ignore_close_direction(self):
        """测试平仓方向忽略T+1检查"""
        main_engine = MockMainEngine()
        today = datetime.now()
        trade = MockTradeData(
            symbol="000001",
            vt_symbol="000001.SZSE",
            direction="Direction.LONG",
            datetime_obj=today,
        )
        main_engine.trades = [trade]

        rule = T1RestrictionRule()
        signal = create_test_signal(direction=SignalDirection.CLOSE)
        result = rule.check(signal, main_engine)

        self.assertTrue(result.passed)


class TestCapitalRule(unittest.TestCase):
    """资金规则测试"""

    def test_insufficient_capital(self):
        """测试资金不足"""
        main_engine = MockMainEngine()
        main_engine.accounts["test"] = MockAccountData(balance=10000, available=5000)

        rule = CapitalRule(min_balance=10000)
        signal = create_test_signal(direction=SignalDirection.LONG)
        result = rule.check(signal, main_engine)

        self.assertFalse(result.passed)
        self.assertTrue(result.insufficient_capital)
        self.assertIn("资金不足", result.reasons[0])

    def test_sufficient_capital(self):
        """测试资金充足"""
        main_engine = MockMainEngine()
        main_engine.accounts["test"] = MockAccountData(balance=100000, available=80000)

        rule = CapitalRule(min_balance=10000)
        signal = create_test_signal(direction=SignalDirection.LONG)
        result = rule.check(signal, main_engine)

        self.assertTrue(result.passed)

    def test_warning_threshold(self):
        """测试警告阈值"""
        main_engine = MockMainEngine()
        main_engine.accounts["test"] = MockAccountData(balance=20000, available=15000)

        rule = CapitalRule(min_balance=10000)
        signal = create_test_signal(direction=SignalDirection.LONG)
        result = rule.check(signal, main_engine)

        self.assertTrue(result.passed)
        self.assertTrue(len(result.warnings) > 0)


class TestPositionLimitRule(unittest.TestCase):
    """持仓限制规则测试"""

    def test_position_limit_exceeded(self):
        """测试持仓超限"""
        main_engine = MockMainEngine()
        # 创建10个持仓
        positions = {}
        for i in range(10):
            symbol = f"00000{i}"
            positions[f"{symbol}.SZSE"] = MockPositionData(
                symbol=symbol, vt_symbol=f"{symbol}.SZSE", volume=100
            )
        main_engine.positions = positions

        rule = PositionLimitRule(max_positions=10)
        signal = create_test_signal(direction=SignalDirection.LONG)
        result = rule.check(signal, main_engine)

        self.assertFalse(result.passed)
        self.assertTrue(result.position_limit)

    def test_position_available(self):
        """测试有可用持仓额度"""
        main_engine = MockMainEngine()
        # 创建5个持仓
        positions = {}
        for i in range(5):
            symbol = f"00000{i}"
            positions[f"{symbol}.SZSE"] = MockPositionData(
                symbol=symbol, vt_symbol=f"{symbol}.SZSE", volume=100
            )
        main_engine.positions = positions

        rule = PositionLimitRule(max_positions=10)
        signal = create_test_signal(direction=SignalDirection.LONG)
        result = rule.check(signal, main_engine)

        self.assertTrue(result.passed)

    def test_warning_threshold(self):
        """测试接近上限警告"""
        main_engine = MockMainEngine()
        # 创建8个持仓（80%）
        positions = {}
        for i in range(8):
            symbol = f"00000{i}"
            positions[f"{symbol}.SZSE"] = MockPositionData(
                symbol=symbol, vt_symbol=f"{symbol}.SZSE", volume=100
            )
        main_engine.positions = positions

        rule = PositionLimitRule(max_positions=10)
        signal = create_test_signal(direction=SignalDirection.LONG)
        result = rule.check(signal, main_engine)

        self.assertTrue(result.passed)
        self.assertTrue(len(result.warnings) > 0)


if __name__ == "__main__":
    unittest.main()
