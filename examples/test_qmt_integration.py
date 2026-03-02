# -*- coding: utf-8 -*-
"""
QMT环境集成测试

测试A股交易引擎在真实QMT环境下的完整流程：
1. RPC连接测试
2. 行情数据获取测试
3. 风险控制规则测试
4. 信号生成与确认流程测试

运行方式：
    python examples/test_qmt_integration.py

环境要求：
    - Windows服务端已运行 run_qmt_server.py
    - RPC地址已配置在 .vntrader_china/config/config.yaml
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 尝试导入依赖，如果失败则跳过相关测试
try:
    from vnpy.event import EventEngine
    from vnpy.trader.engine import MainEngine
    from vnpy_rpcservice.rpc_gateway import RpcGateway
    HAS_RPC = True
except ImportError as e:
    HAS_RPC = False
    print(f"警告: RPC模块未安装，跳过RPC相关测试: {e}")

from vnpy_china_trading import ChinaTradingApp
from vnpy_china_trading.object import (
    TradingSignal,
    SignalSource,
    SignalDirection,
    SignalStatus,
)


class QMTIntegrationTest:
    """QMT环境集成测试类"""

    def __init__(self):
        self.main_engine: Optional[MainEngine] = None
        self.event_engine: Optional[EventEngine] = None
        self.app: Optional[ChinaTradingApp] = None
        self.test_results = []

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("QMT环境集成测试")
        print("=" * 60)
        print(f"RPC模块可用: {HAS_RPC}")
        print()

        tests = [
            ("1. RPC连接测试", self.test_rpc_connection),
            ("2. 账户数据获取", self.test_account_data),
            ("3. 持仓数据获取", self.test_position_data),
            ("4. 行情数据获取", self.test_market_data),
            ("5. 风控规则测试", self.test_risk_rules),
            ("6. 信号流程测试", self.test_signal_flow),
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests:
            print(f"\n{test_name}")
            print("-" * 40)
            try:
                test_func()
                print(f"  [PASS]")
                passed += 1
            except AssertionError as e:
                print(f"  [FAIL]: {e}")
                failed += 1
            except Exception as e:
                print(f"  [ERROR]: {e}")
                failed += 1

        print("\n" + "=" * 60)
        print(f"测试完成: 通过 {passed}, 失败 {failed}")
        print("=" * 60)

        return failed == 0

    def test_rpc_connection(self):
        """测试1: RPC连接测试"""
        if not HAS_RPC:
            raise AssertionError("RPC模块不可用")

        # 创建事件引擎和主引擎
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)

        # 添加RPC网关
        rpc_gateway = self.main_engine.add_gateway(RpcGateway, "RPC")

        # 尝试连接
        from vnpy_china_config import ConfigManager
        config_manager = ConfigManager()
        config = config_manager.load_config()

        # 连接RPC
        rpc_setting = {
            "主动请求地址": config.rpc.rep_address,
            "推送订阅地址": config.rpc.pub_address,
        }

        self.main_engine.connect(rpc_setting, "RPC")

        # 等待连接建立
        import time
        time.sleep(2)

        # 检查连接状态
        gateway = self.main_engine.get_gateway("RPC")
        if gateway and hasattr(gateway, 'connected'):
            print(f"  - RPC连接状态: {gateway.connected}")
        else:
            print("  - RPC网关已添加")

        print("  - RPC连接测试完成")

    def test_account_data(self):
        """测试2: 账户数据获取"""
        if not HAS_RPC or not self.main_engine:
            raise AssertionError("RPC未连接")

        account = self.main_engine.get_account("RPC")
        if account:
            print(f"  - 账户余额: {account.balance}")
            print(f"  - 可用资金: {account.available}")
            print(f"  - 冻结资金: {account.frozen}")
        else:
            print("  - 账户数据: 暂未获取")

    def test_position_data(self):
        """测试3: 持仓数据获取"""
        if not HAS_RPC or not self.main_engine:
            raise AssertionError("RPC未连接")

        positions = self.main_engine.get_all_positions()
        print(f"  - 持仓数量: {len(positions)}")
        for pos in positions[:3]:  # 只显示前3个
            print(f"    - {pos.vt_symbol}: {pos.volume}股")

    def test_market_data(self):
        """测试4: 行情数据获取"""
        if not HAS_RPC or not self.main_engine:
            raise AssertionError("RPC未连接")

        # 获取常用股票行情
        test_symbols = ["000001.SZ", "600000.SH"]
        for symbol in test_symbols:
            tick = self.main_engine.get_tick(symbol)
            if tick:
                print(f"  - {symbol}: 最新价={tick.last_price}, 卖一={tick.ask_price_1}, 买一={tick.bid_price_1}")
            else:
                print(f"  - {symbol}: 暂无行情")

    def test_risk_rules(self):
        """测试5: 风控规则测试"""
        from vnpy_china_trading.risk_engine import RiskEngine

        if not self.main_engine:
            # 使用Mock
            from unittest.mock import Mock
            self.main_engine = Mock()

        # 创建风控引擎
        risk_engine = RiskEngine(self.main_engine)

        # 获取规则列表
        rules = risk_engine.get_all_rules()
        print(f"  - 已加载风控规则数量: {len(rules)}")
        for rule in rules:
            print(f"    - {rule.name}: {'启用' if rule.enabled else '禁用'}")

    def test_signal_flow(self):
        """测试6: 信号流程测试"""
        # 创建测试应用
        if not self.event_engine:
            from vnpy.event import EventEngine
            from unittest.mock import Mock
            self.event_engine = EventEngine()
            self.main_engine = Mock()

        self.app = ChinaTradingApp(self.main_engine, self.event_engine)
        self.app.start()

        # 验证引擎初始化
        assert self.app.signal_engine is not None, "信号引擎未初始化"
        assert self.app.risk_engine is not None, "风控引擎未初始化"

        print("  - 信号引擎初始化成功")
        print("  - 风控引擎初始化成功")

        # 创建测试信号
        signal = TradingSignal(
            signal_id=f"QMT-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            symbol="000001",
            exchange="SZSE",
            direction=SignalDirection.LONG,
            strength=0.8,
            source=SignalSource.MANUAL,
            model_name="manual_test",
            predicted_return=0.02,
            confidence=0.9,
            status=SignalStatus.PENDING,
        )

        # 添加信号
        self.app.signal_engine.add_signal(
            symbol=signal.symbol,
            exchange=signal.exchange,
            direction=signal.direction,
            source=signal.source,
            strength=signal.strength,
            model_name=signal.model_name,
            predicted_return=signal.predicted_return,
            confidence=signal.confidence,
        )

        print("  - 测试信号添加成功")

        # 获取待处理信号
        pending = self.app.signal_engine.get_pending_signals()
        print(f"  - 待处理信号数量: {len(pending)}")

    def cleanup(self):
        """清理资源"""
        if self.main_engine:
            self.main_engine.close()


def main():
    """主函数"""
    test = QMTIntegrationTest()
    try:
        success = test.run_all_tests()
        return 0 if success else 1
    finally:
        test.cleanup()


if __name__ == "__main__":
    sys.exit(main())
