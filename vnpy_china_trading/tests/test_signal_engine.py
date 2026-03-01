# -*- coding: utf-8 -*-
"""
信号引擎测试

测试SignalEngine类的各项功能。
"""

import unittest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from vnpy_china_trading.object import (
    SignalSource,
    SignalDirection,
    SignalStatus,
    TradingSignal,
    RiskCheckResult,
)
from vnpy_china_trading.signal_engine import SignalEngine


class TestSignalEngine(unittest.TestCase):
    """测试SignalEngine信号引擎"""

    def setUp(self):
        """测试前准备"""
        self.main_engine = Mock()
        self.event_engine = Mock()
        self.signal_engine = SignalEngine(self.main_engine, self.event_engine)

    def test_add_signal(self):
        """测试添加信号"""
        # 添加做多信号
        signal = self.signal_engine.add_signal(
            symbol="000001",
            exchange="SZSE",
            direction=SignalDirection.LONG,
            source=SignalSource.ALPHA158,
            strength=0.8,
            model_name="alpha158_lgb",
            predicted_return=0.05,
            confidence=0.75,
        )

        # 验证信号创建
        self.assertIsNotNone(signal.signal_id)
        self.assertEqual(signal.symbol, "000001")
        self.assertEqual(signal.exchange, "SZSE")
        self.assertEqual(signal.direction, SignalDirection.LONG)
        self.assertEqual(signal.source, SignalSource.ALPHA158)
        self.assertEqual(signal.strength, 0.8)
        self.assertEqual(signal.model_name, "alpha158_lgb")
        self.assertEqual(signal.predicted_return, 0.05)
        self.assertEqual(signal.confidence, 0.75)
        self.assertEqual(signal.status, SignalStatus.PENDING)

    def test_add_signal_with_minimal_params(self):
        """测试使用最小参数添加信号"""
        signal = self.signal_engine.add_signal(
            symbol="600000",
            exchange="SHSE",
            direction=SignalDirection.SHORT,
        )

        # 验证默认参数
        self.assertEqual(signal.source, SignalSource.CUSTOM)
        self.assertEqual(signal.strength, 1.0)
        self.assertIsNone(signal.model_name)
        self.assertIsNone(signal.predicted_return)
        self.assertIsNone(signal.confidence)

    def test_get_pending_signals(self):
        """测试获取待处理信号"""
        # 添加多个信号
        self.signal_engine.add_signal(
            symbol="000001", exchange="SZSE", direction=SignalDirection.LONG
        )
        self.signal_engine.add_signal(
            symbol="600000", exchange="SHSE", direction=SignalDirection.SHORT
        )

        # 获取待处理信号
        pending = self.signal_engine.get_pending_signals()

        # 验证
        self.assertEqual(len(pending), 2)
        self.assertTrue(all(s.status == SignalStatus.PENDING for s in pending))

    def test_update_signal_status(self):
        """测试更新信号状态"""
        # 添加信号
        signal = self.signal_engine.add_signal(
            symbol="000001", exchange="SZSE", direction=SignalDirection.LONG
        )
        signal_id = signal.signal_id

        # 创建风控结果
        risk_result = RiskCheckResult(
            passed=True,
            warnings=["资金使用率较高"],
        )

        # 更新状态为风控通过
        result = self.signal_engine.update_signal_status(
            signal_id, SignalStatus.RISK_PASSED, risk_result
        )

        # 验证
        self.assertTrue(result)
        updated_signal = self.signal_engine.get_signal(signal_id)
        self.assertEqual(updated_signal.status, SignalStatus.RISK_PASSED)
        self.assertIsNotNone(updated_signal.risk_check_result)
        self.assertTrue(updated_signal.risk_check_result.passed)

    def test_update_nonexistent_signal(self):
        """测试更新不存在的信号"""
        result = self.signal_engine.update_signal_status(
            "NONEXISTENT", SignalStatus.CANCELLED
        )
        self.assertFalse(result)

    def test_cancel_signal(self):
        """测试取消信号"""
        signal = self.signal_engine.add_signal(
            symbol="000001", exchange="SZSE", direction=SignalDirection.LONG
        )

        # 取消信号
        result = self.signal_engine.cancel_signal(signal.signal_id)

        # 验证
        self.assertTrue(result)
        cancelled_signal = self.signal_engine.get_signal(signal.signal_id)
        self.assertEqual(cancelled_signal.status, SignalStatus.CANCELLED)

    def test_confirm_signal(self):
        """测试确认信号"""
        signal = self.signal_engine.add_signal(
            symbol="000001", exchange="SZSE", direction=SignalDirection.LONG
        )

        # 先通过风控
        self.signal_engine.update_signal_status(
            signal.signal_id, SignalStatus.RISK_PASSED
        )

        # 确认信号
        result = self.signal_engine.confirm_signal(signal.signal_id)

        # 验证
        self.assertTrue(result)
        confirmed_signal = self.signal_engine.get_signal(signal.signal_id)
        self.assertEqual(confirmed_signal.status, SignalStatus.CONFIRMED)

    def test_execute_signal(self):
        """测试执行信号"""
        signal = self.signal_engine.add_signal(
            symbol="000001", exchange="SZSE", direction=SignalDirection.LONG
        )

        # 执行信号
        result = self.signal_engine.execute_signal(signal.signal_id)

        # 验证
        self.assertTrue(result)
        executed_signal = self.signal_engine.get_signal(signal.signal_id)
        self.assertEqual(executed_signal.status, SignalStatus.EXECUTED)

    def test_register_callback(self):
        """测试注册回调函数"""
        callback_called = []

        def callback(signal: TradingSignal) -> None:
            callback_called.append(signal)

        # 注册回调
        self.signal_engine.register_callback(callback)

        # 添加信号触发回调
        self.signal_engine.add_signal(
            symbol="000001", exchange="SZSE", direction=SignalDirection.LONG
        )

        # 验证回调被调用
        self.assertEqual(len(callback_called), 1)

    def test_unregister_callback(self):
        """测试注销回调函数"""
        callback_called = []

        def callback(signal: TradingSignal) -> None:
            callback_called.append(signal)

        # 注册回调
        self.signal_engine.register_callback(callback)

        # 注销回调
        self.signal_engine.unregister_callback(callback)

        # 添加信号
        self.signal_engine.add_signal(
            symbol="000001", exchange="SZSE", direction=SignalDirection.LONG
        )

        # 验证回调未被调用
        self.assertEqual(len(callback_called), 0)

    def test_get_signals_by_status(self):
        """测试根据状态获取信号"""
        # 添加并更新信号
        s1 = self.signal_engine.add_signal(
            symbol="000001", exchange="SZSE", direction=SignalDirection.LONG
        )
        s2 = self.signal_engine.add_signal(
            symbol="600000", exchange="SHSE", direction=SignalDirection.SHORT
        )

        # 取消第二个信号
        self.signal_engine.cancel_signal(s2.signal_id)

        # 获取已取消的信号
        cancelled = self.signal_engine.get_signals_by_status(SignalStatus.CANCELLED)

        # 验证
        self.assertEqual(len(cancelled), 1)
        self.assertEqual(cancelled[0].symbol, "600000")

    def test_clear_history(self):
        """测试清理历史信号"""
        # 添加多个信号
        s1 = self.signal_engine.add_signal(
            symbol="000001", exchange="SZSE", direction=SignalDirection.LONG
        )
        s2 = self.signal_engine.add_signal(
            symbol="600000", exchange="SHSE", direction=SignalDirection.SHORT
        )

        # 执行第一个信号
        self.signal_engine.execute_signal(s1.signal_id)

        # 清理历史
        count = self.signal_engine.clear_history()

        # 验证
        self.assertEqual(count, 1)
        remaining = self.signal_engine.get_all_signals()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].symbol, "600000")

    def test_signal_id_unique(self):
        """测试信号ID唯一性"""
        # 添加多个信号
        signals = []
        for i in range(10):
            signal = self.signal_engine.add_signal(
                symbol=f"00000{i}", exchange="SZSE", direction=SignalDirection.LONG
            )
            signals.append(signal)

        # 验证所有ID唯一
        signal_ids = [s.signal_id for s in signals]
        self.assertEqual(len(signal_ids), len(set(signal_ids)))


class TestTradingSignal(unittest.TestCase):
    """测试TradingSignal数据类"""

    def test_create_signal(self):
        """测试创建信号"""
        signal = TradingSignal(
            signal_id="TEST001",
            symbol="000001",
            exchange="SZSE",
            direction=SignalDirection.LONG,
            strength=0.8,
            source=SignalSource.ALPHA158,
        )

        self.assertEqual(signal.signal_id, "TEST001")
        self.assertEqual(signal.vt_symbol, "000001.SZSE")

    def test_invalid_strength(self):
        """测试无效的信号强度"""
        with self.assertRaises(ValueError):
            TradingSignal(
                signal_id="TEST001",
                symbol="000001",
                exchange="SZSE",
                direction=SignalDirection.LONG,
                strength=1.5,  # 无效：超过1
            )

    def test_empty_symbol(self):
        """测试空股票代码"""
        with self.assertRaises(ValueError):
            TradingSignal(
                signal_id="TEST001",
                symbol="",
                exchange="SZSE",
                direction=SignalDirection.LONG,
            )


class TestRiskCheckResult(unittest.TestCase):
    """测试RiskCheckResult数据类"""

    def test_create_passed_result(self):
        """测试创建通过的风控结果"""
        result = RiskCheckResult(
            passed=True,
            warnings=["资金使用率较高"],
        )

        self.assertTrue(result.passed)
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("通过", result.message)

    def test_create_rejected_result(self):
        """测试创建拒绝的风控结果"""
        result = RiskCheckResult(
            passed=False,
            reasons=["资金不足", "持仓超限"],
        )

        self.assertFalse(result.passed)
        self.assertEqual(len(result.reasons), 2)
        self.assertIn("资金不足", result.message)


if __name__ == "__main__":
    unittest.main()
