# -*- coding: utf-8 -*-
"""
完整交易流程集成测试

测试A股交易引擎的完整交易流程，包括：
1. 初始化测试
2. 信号生成测试
3. 风控检查测试
4. 信号状态转换测试
5. 取消流程测试
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from vnpy_china_trading import ChinaTradingApp
from vnpy_china_trading.object import (
    TradingSignal,
    SignalSource,
    SignalDirection,
    SignalStatus,
    RiskCheckResult,
)
from vnpy_china_trading.signal_engine import SignalEngine
from vnpy_china_trading.risk_engine import RiskEngine


class TestTradingFlow:
    """完整交易流程测试类"""

    def __init__(self):
        """初始化测试"""
        self.main_engine = Mock()
        self.event_engine = Mock()
        self.app = None
        self.signal_engine = None
        self.risk_engine = None
        self.test_results = []

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("开始完整交易流程集成测试")
        print("=" * 60)

        # 执行所有测试
        tests = [
            ("1. 初始化测试", self.test_initialization),
            ("2. 信号生成测试", self.test_signal_generation),
            ("3. 风控检查测试", self.test_risk_check),
            ("4. 信号状态转换测试", self.test_status_transitions),
            ("5. 取消流程测试", self.test_cancel_flow),
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests:
            print(f"\n{test_name}")
            print("-" * 40)
            try:
                test_func()
                print(f"  [PASS] {test_name}")
                passed += 1
            except AssertionError as e:
                print(f"  [FAIL] {test_name}: {e}")
                failed += 1
            except Exception as e:
                print(f"  [ERROR] {test_name}: {e}")
                failed += 1

        # 输出测试结果
        print("\n" + "=" * 60)
        print(f"测试完成: 通过 {passed}, 失败 {failed}")
        print("=" * 60)

        return failed == 0

    def test_initialization(self):
        """测试1: 初始化测试"""
        # 创建 Mock MainEngine 和 EventEngine
        self.main_engine = Mock()
        self.event_engine = Mock()

        # 配置 main_engine 的基本属性 - 使用 return_value 方式
        mock_account = MagicMock()
        mock_account.balance = 100000
        mock_account.available = 80000
        mock_account.frozen = 20000
        self.main_engine.get_account = Mock(return_value=mock_account)
        self.main_engine.get_position = Mock(return_value=None)

        # 初始化 ChinaTradingApp
        self.app = ChinaTradingApp(self.main_engine, self.event_engine)
        self.app.start()

        # 验证初始化结果
        assert self.app is not None, "ChinaTradingApp 初始化失败"
        assert self.app.signal_engine is not None, "信号引擎未初始化"
        assert isinstance(self.app.signal_engine, SignalEngine), "信号引擎类型错误"

        # 保存引用
        self.signal_engine = self.app.signal_engine
        self.risk_engine = RiskEngine(self.main_engine)

        print("  - MainEngine 和 EventEngine 创建成功")
        print("  - ChinaTradingApp 初始化成功")
        print("  - SignalEngine 初始化成功")
        print("  - RiskEngine 初始化成功")

    def test_signal_generation(self):
        """测试2: 信号生成测试"""
        # 创建测试信号
        signal = TradingSignal(
            signal_id="TEST-001",
            symbol="000001",
            exchange="SZSE",
            direction=SignalDirection.LONG,
            strength=0.8,
            source=SignalSource.ALPHA158,
            model_name="alpha158_lgb",
            predicted_return=0.05,
            confidence=0.75,
            status=SignalStatus.PENDING,
        )

        # 验证信号创建
        assert signal.signal_id == "TEST-001", "信号ID不匹配"
        assert signal.symbol == "000001", "股票代码不匹配"
        assert signal.exchange == "SZSE", "交易所不匹配"
        assert signal.direction == SignalDirection.LONG, "方向不匹配"
        assert signal.status == SignalStatus.PENDING, "初始状态应为PENDING"

        # 添加信号到信号引擎
        added_signal = self.signal_engine.add_signal(
            symbol="000001",
            exchange="SZSE",
            direction=SignalDirection.LONG,
            source=SignalSource.ALPHA158,
            strength=0.8,
            model_name="alpha158_lgb",
            predicted_return=0.05,
            confidence=0.75,
        )

        # 验证信号状态
        assert added_signal is not None, "信号添加失败"
        assert added_signal.status == SignalStatus.PENDING, "信号状态应为PENDING"

        # 验证信号存在于引擎中
        retrieved_signal = self.signal_engine.get_signal(added_signal.signal_id)
        assert retrieved_signal is not None, "无法获取添加的信号"
        assert retrieved_signal.symbol == "000001", "信号数据不匹配"

        print(f"  - 信号创建成功: {signal.signal_id}")
        print(f"  - 信号状态: {signal.status.value}")
        print(f"  - 信号添加到引擎成功")

    def test_risk_check(self):
        """测试3: 风控检查测试"""
        # 创建一个新的测试信号
        signal = self.signal_engine.add_signal(
            symbol="600000",
            exchange="SHSE",
            direction=SignalDirection.LONG,
            source=SignalSource.ML_MODEL,
            strength=0.9,
            model_name="lgb_model",
            predicted_return=0.03,
        )

        # 运行风险检查
        result = self.risk_engine.check_signal(signal)

        # 验证风控结果
        assert result is not None, "风控检查返回None"
        assert isinstance(result, RiskCheckResult), "返回结果类型错误"
        assert hasattr(result, 'passed'), "结果缺少passed属性"
        assert hasattr(result, 'reasons'), "结果缺少reasons属性"
        assert hasattr(result, 'warnings'), "结果缺少warnings属性"

        print(f"  - 风控检查完成")
        print(f"  - 检查结果: {'通过' if result.passed else '拒绝'}")
        if result.reasons:
            print(f"  - 拒绝原因: {result.reasons}")
        if result.warnings:
            print(f"  - 警告信息: {result.warnings}")

    def test_status_transitions(self):
        """测试4: 信号状态转换测试"""
        # 创建测试信号
        signal = self.signal_engine.add_signal(
            symbol="000001",
            exchange="SZSE",
            direction=SignalDirection.LONG,
            source=SignalSource.CUSTOM,
        )

        signal_id = signal.signal_id

        # 状态转换 1: PENDING -> RISK_CHECKING
        print(f"  - 初始状态: {signal.status.value}")
        success = self.signal_engine.update_signal_status(
            signal_id, SignalStatus.RISK_CHECKING
        )
        assert success, "状态转换 PENDING -> RISK_CHECKING 失败"
        signal = self.signal_engine.get_signal(signal_id)
        assert signal.status == SignalStatus.RISK_CHECKING, "状态转换未生效"
        print(f"  - 转换到 RISK_CHECKING: 成功")

        # 状态转换 2: RISK_CHECKING -> RISK_PASSED
        risk_result = RiskCheckResult(passed=True, warnings=["资金使用率较高"])
        success = self.signal_engine.update_signal_status(
            signal_id, SignalStatus.RISK_PASSED, risk_result
        )
        assert success, "状态转换 RISK_CHECKING -> RISK_PASSED 失败"
        signal = self.signal_engine.get_signal(signal_id)
        assert signal.status == SignalStatus.RISK_PASSED, "状态转换未生效"
        assert signal.risk_check_result is not None, "风控结果未保存"
        print(f"  - 转换到 RISK_PASSED: 成功")

        # 状态转换 3: RISK_PASSED -> CONFIRMED
        success = self.signal_engine.confirm_signal(signal_id)
        assert success, "状态转换 RISK_PASSED -> CONFIRMED 失败"
        signal = self.signal_engine.get_signal(signal_id)
        assert signal.status == SignalStatus.CONFIRMED, "状态转换未生效"
        print(f"  - 转换到 CONFIRMED: 成功")

        # 状态转换 4: CONFIRMED -> EXECUTED
        success = self.signal_engine.execute_signal(signal_id)
        assert success, "状态转换 CONFIRMED -> EXECUTED 失败"
        signal = self.signal_engine.get_signal(signal_id)
        assert signal.status == SignalStatus.EXECUTED, "状态转换未生效"
        print(f"  - 转换到 EXECUTED: 成功")

        print("  - 完整状态转换流程测试通过")

    def test_risk_rejected_flow(self):
        """测试4.1: 风控拒绝流程测试"""
        # 创建测试信号
        signal = self.signal_engine.add_signal(
            symbol="999999",
            exchange="SHSE",
            direction=SignalDirection.SHORT,
            source=SignalSource.MANUAL,
        )

        signal_id = signal.signal_id

        # 模拟风控拒绝
        risk_result = RiskCheckResult(
            passed=False,
            reasons=["资金不足", "持仓超限"]
        )

        # 状态转换: PENDING -> RISK_CHECKING -> RISK_REJECTED
        self.signal_engine.update_signal_status(signal_id, SignalStatus.RISK_CHECKING)
        signal = self.signal_engine.get_signal(signal_id)
        assert signal.status == SignalStatus.RISK_CHECKING

        success = self.signal_engine.update_signal_status(
            signal_id, SignalStatus.RISK_REJECTED, risk_result
        )
        assert success, "状态转换到RISK_REJECTED失败"
        signal = self.signal_engine.get_signal(signal_id)
        assert signal.status == SignalStatus.RISK_REJECTED, "状态转换未生效"
        assert signal.risk_check_result is not None
        assert not signal.risk_check_result.passed

        print("  - 风控拒绝流程测试通过")

    def test_cancel_flow(self):
        """测试5: 取消流程测试"""
        # 创建测试信号
        signal = self.signal_engine.add_signal(
            symbol="300001",
            exchange="SZSE",
            direction=SignalDirection.CLOSE,
            source=SignalSource.CUSTOM,
        )

        signal_id = signal.signal_id
        initial_status = signal.status
        assert initial_status == SignalStatus.PENDING, "初始状态应为PENDING"

        # 取消信号: PENDING -> CANCELLED
        success = self.signal_engine.cancel_signal(signal_id)
        assert success, "取消信号失败"

        # 验证取消结果
        cancelled_signal = self.signal_engine.get_signal(signal_id)
        assert cancelled_signal is not None, "无法获取取消的信号"
        assert cancelled_signal.status == SignalStatus.CANCELLED, "信号状态未变为CANCELLED"

        print(f"  - 初始状态: {initial_status.value}")
        print(f"  - 取消后状态: {cancelled_signal.status.value}")
        print("  - 取消流程测试通过")


def test_trading_flow():
    """主测试函数"""
    tester = TestTradingFlow()
    success = tester.run_all_tests()

    if success:
        print("\n所有集成测试通过!")
        return 0
    else:
        print("\n部分集成测试失败!")
        return 1


if __name__ == "__main__":
    exit_code = test_trading_flow()
    sys.exit(exit_code)
