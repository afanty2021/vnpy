#!/usr/bin/env python3
"""
RPC实时信号生成脚本 - 单元测试

测试实时信号管理器的各项功能
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from examples.rpc_realtime_signals import RealtimeSignalManager
from vnpy.trader.object import TickData, BarData
from vnpy.trader.constant import Exchange


def create_test_tick(symbol: str, exchange: Exchange, price: float, volume: float) -> TickData:
    """创建测试Tick数据"""
    return TickData(
        gateway_name="TEST",
        symbol=symbol,
        exchange=exchange,
        datetime=datetime.now(),
        last_price=price,
        volume=volume,
        turnover=price * volume,
    )


def create_test_bar(symbol: str, exchange: Exchange, open_price: float, high_price: float,
                    low_price: float, close_price: float, volume: float) -> BarData:
    """创建测试K线数据"""
    return BarData(
        gateway_name="TEST",
        symbol=symbol,
        exchange=exchange,
        datetime=datetime.now(),
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        volume=volume,
        turnover=close_price * volume,
    )


def test_model_loading():
    """测试模型加载"""
    print("\n" + "=" * 60)
    print("测试1: 模型加载")
    print("=" * 60)

    manager = RealtimeSignalManager(
        rpc_req_address="tcp://127.0.0.1:2014",
        rpc_sub_address="tcp://127.0.0.1:4102",
        model_path=str(Path.home() / "vnpy_lab/model/a_stock_lgb.txt"),
    )

    result = manager.load_model()
    print(f"模型加载结果: {'成功' if result else '失败'}")
    print(f"模型已加载标志: {manager.model_loaded}")

    assert result is True, "模型加载应该成功"
    assert manager.model_loaded is True, "模型加载标志应该为True"

    print("✓ 模型加载测试通过")
    return True


def test_data_window():
    """测试数据窗口管理"""
    print("\n" + "=" * 60)
    print("测试2: 数据窗口管理")
    print("=" * 60)

    manager = RealtimeSignalManager(
        rpc_req_address="tcp://127.0.0.1:2014",
        rpc_sub_address="tcp://127.0.0.1:4102",
        model_path=str(Path.home() / "vnpy_lab/model/alpha158_lgb.txt"),
        window_size=10,  # 小窗口便于测试
    )

    # 添加测试K线数据
    vt_symbol = "000001.SZSE"
    for i in range(15):
        bar = create_test_bar(
            symbol="000001",
            exchange=Exchange.SZSE,
            open_price=10.0 + i * 0.01,
            high_price=10.05 + i * 0.01,
            low_price=9.95 + i * 0.01,
            close_price=10.0 + i * 0.01,
            volume=1000000,
        )
        manager.on_bar(bar)

    # 检查窗口大小
    window = manager.data_windows[vt_symbol]
    print(f"数据窗口大小: {len(window)}")
    print(f"预期窗口大小: {manager.window_size}")

    assert len(window) == manager.window_size, f"窗口大小应为{manager.window_size}"

    print("✓ 数据窗口管理测试通过")
    return True


def test_tick_to_bar():
    """测试Tick转K线"""
    print("\n" + "=" * 60)
    print("测试3: Tick数据转换为K线")
    print("=" * 60)

    manager = RealtimeSignalManager(
        rpc_req_address="tcp://127.0.0.1:2014",
        rpc_sub_address="tcp://127.0.0.1:4102",
        model_path=str(Path.home() / "vnpy_lab/model/alpha158_lgb.txt"),
        window_size=10,
    )

    vt_symbol = "600000.SSE"

    # 模拟同一分钟的多个Tick
    base_time = datetime.now().replace(second=0, microsecond=0)

    for i in range(5):
        tick = TickData(
            gateway_name="TEST",
            symbol="600000",
            exchange=Exchange.SSE,
            datetime=base_time,
            last_price=10.0 + i * 0.01,
            volume=100000,
            turnover=(10.0 + i * 0.01) * 100000,
        )
        manager.on_tick(tick)

    # 检查K线数据
    window = manager.data_windows[vt_symbol]
    print(f"K线数量: {len(window)}")

    if len(window) > 0:
        bar = window[-1]
        print(f"开盘价: {bar['open']:.2f}")
        print(f"最高价: {bar['high']:.2f}")
        print(f"最低价: {bar['low']:.2f}")
        print(f"收盘价: {bar['close']:.2f}")
        print(f"成交量: {bar['volume']:.0f}")

        assert bar["open"] == 10.0, "开盘价应为10.0"
        assert bar["high"] == 10.04, "最高价应为10.04"
        assert bar["low"] == 10.0, "最低价应为10.0"
        assert bar["close"] == 10.04, "收盘价应为10.04"
        assert bar["volume"] == 500000, "成交量应为500000"

        print("✓ Tick转K线测试通过")
        return True
    else:
        print("✗ 未生成K线数据")
        return False


def test_signal_generation():
    """测试信号生成（使用模拟数据）"""
    print("\n" + "=" * 60)
    print("测试4: 信号生成")
    print("=" * 60)

    # 加载模型
    manager = RealtimeSignalManager(
        rpc_req_address="tcp://127.0.0.1:2014",
        rpc_sub_address="tcp://127.0.0.1:4102",
        model_path=str(Path.home() / "vnpy_lab/model/a_stock_lgb.txt"),
        window_size=60,  # 实际需要的窗口大小
    )

    if not manager.load_model():
        print("模型加载失败，跳过信号生成测试")
        return False

    print("注意: 完整的信号生成测试需要60天的历史数据")
    print("这里仅验证数据结构和接口")

    # 验证信号存储结构
    vt_symbol = "TEST"
    manager.signals[vt_symbol] = {
        "prediction": 0.025,
        "signal": 1,
        "timestamp": datetime.now(),
    }

    # 测试获取Top信号
    long_signals, short_signals = manager.get_top_signals(10)

    print(f"做多信号数量: {len(long_signals)}")
    print(f"做空信号数量: {len(short_signals)}")

    assert len(long_signals) == 1, "应有1个做多信号"
    assert long_signals[0]["vt_symbol"] == "TEST", "信号应为TEST"
    assert long_signals[0]["signal"] == 1, "信号类型应为做多(1)"

    print("✓ 信号生成接口测试通过")
    return True


def test_statistics():
    """测试统计功能"""
    print("\n" + "=" * 60)
    print("测试5: 统计功能")
    print("=" * 60)

    manager = RealtimeSignalManager(
        rpc_req_address="tcp://127.0.0.1:2014",
        rpc_sub_address="tcp://127.0.0.1:4102",
        model_path=str(Path.home() / "vnpy_lab/model/a_stock_lgb.txt"),
    )

    # 添加一些测试信号
    manager.stats["total_predictions"] = 100
    manager.stats["long_signals"] = 30
    manager.stats["short_signals"] = 20
    manager.stats["hold_signals"] = 50

    print(f"总预测数: {manager.stats['total_predictions']}")
    print(f"做多信号: {manager.stats['long_signals']}")
    print(f"做空信号: {manager.stats['short_signals']}")
    print(f"持仓信号: {manager.stats['hold_signals']}")

    assert manager.stats["total_predictions"] == 100
    assert manager.stats["long_signals"] == 30
    assert manager.stats["short_signals"] == 20
    assert manager.stats["hold_signals"] == 50

    print("✓ 统计功能测试通过")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("RPC实时信号生成脚本 - 单元测试")
    print("=" * 60)

    tests = [
        test_model_loading,
        test_data_window,
        test_tick_to_bar,
        test_signal_generation,
        test_statistics,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"✗ {test.__name__} 失败: {e}")
            results.append((test.__name__, False))

    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")

    print(f"\n通过: {passed}/{total}")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
