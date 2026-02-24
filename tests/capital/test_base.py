"""
资金管理系统基础框架测试

测试核心数据类型和仓位管理器基类的功能。
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from vnpy_china_capital.objects.types import (
    PositionType,
    OrderBatchType,
    OrderBatch,
    PositionAllocation,
    EquityPoint,
    RiskMetrics,
)
from vnpy_china_capital.position.base import PositionSizer
from datetime import datetime


def test_position_type_enum():
    """测试仓位类型枚举"""
    assert PositionType.EQUAL_WEIGHT.value == "equal_weight"
    assert PositionType.VALUE_WEIGHT.value == "value_weight"
    assert PositionType.RISK_PARITY.value == "risk_parity"
    assert PositionType.DYNAMIC.value == "dynamic"
    print("[PASS] PositionType enum test")


def test_order_batch_type_enum():
    """测试订单批次类型枚举"""
    assert OrderBatchType.EQUAL.value == "equal"
    assert OrderBatchType.PYRAMID_BUY.value == "pyramid_buy"
    assert OrderBatchType.PYRAMID_SELL.value == "pyramid_sell"
    assert OrderBatchType.TWAP.value == "twap"
    assert OrderBatchType.VWAP.value == "vwap"
    print("[PASS] OrderBatchType enum test")


def test_order_batch_dataclass():
    """测试委托批次数据类"""
    batch = OrderBatch(
        price=10.5,
        volume=1000,
        delay=5,
        batch_type=OrderBatchType.EQUAL
    )
    assert batch.price == 10.5
    assert batch.volume == 1000
    assert batch.delay == 5
    assert batch.batch_type == OrderBatchType.EQUAL
    print("[PASS] OrderBatch dataclass test")


def test_position_allocation_dataclass():
    """测试仓位分配结果数据类"""
    allocation = PositionAllocation(
        symbol="600000.SH",
        target_volume=10000,
        target_value=105000.0,
        weight=0.25,
        reason="等权重分配"
    )
    assert allocation.symbol == "600000.SH"
    assert allocation.target_volume == 10000
    assert allocation.target_value == 105000.0
    assert allocation.weight == 0.25
    assert allocation.reason == "等权重分配"
    print("[PASS] PositionAllocation dataclass test")


def test_equity_point_dataclass():
    """测试资金曲线点数据类"""
    point = EquityPoint(
        datetime=datetime(2024, 1, 1, 9, 30),
        equity=1000000.0,
        drawdown=0.05,
        daily_return=0.02,
        cumulative_return=0.10
    )
    assert point.datetime == datetime(2024, 1, 1, 9, 30)
    assert point.equity == 1000000.0
    assert point.drawdown == 0.05
    assert point.daily_return == 0.02
    assert point.cumulative_return == 0.10
    print("[PASS] EquityPoint dataclass test")


def test_risk_metrics_dataclass():
    """测试风险指标数据类"""
    metrics = RiskMetrics(
        max_drawdown=0.15,
        current_drawdown=0.05,
        sharpe_ratio=1.8,
        sortino_ratio=2.2,
        calmar_ratio=1.5,
        volatility=0.12
    )
    assert metrics.max_drawdown == 0.15
    assert metrics.current_drawdown == 0.05
    assert metrics.sharpe_ratio == 1.8
    assert metrics.sortino_ratio == 2.2
    assert metrics.calmar_ratio == 1.5
    assert metrics.volatility == 0.12
    print("[PASS] RiskMetrics dataclass test")


def test_position_sizer_base():
    """测试仓位管理器基类"""
    # 创建测试用的 PositionSizer 子类
    class TestPositionSizer(PositionSizer):
        def calculate_positions(
            self,
            symbols,
            total_capital,
            prices,
            **kwargs
        ):
            result = {}
            price_per_share = total_capital / len(symbols)
            for symbol in symbols:
                volume = int(price_per_share / prices[symbol] / 100) * 100
                result[symbol] = volume
            return result

    # 测试基本功能
    sizer = TestPositionSizer()
    symbols = ["600000.SH", "600001.SH"]
    prices = {"600000.SH": 10.0, "600001.SH": 20.0}
    total_capital = 100000.0

    positions = sizer.calculate_positions(symbols, total_capital, prices)

    assert "600000.SH" in positions

    # 测试验证方法
    assert sizer.validate_position("600000.SH", 1000, 10.0) is True   # 1000是100的倍数
    assert sizer.validate_position("600000.SH", 100, 10.0) is True   # 100是100的倍数
    assert sizer.validate_position("600000.SH", 50, 10.0) is False   # 50不是100的倍数
    assert sizer.validate_position("600000.SH", 0, 10.0) is False    # 股数为0
    assert sizer.validate_position("600000.SH", 1000, 0) is False    # 价格为0

    # 测试摘要
    summary = sizer.get_allocation_summary()
    assert summary["total_positions"] == 0  # 基类默认allocations为空

    print("[PASS] PositionSizer base class test")


def test_all():
    """运行所有测试"""
    print("=" * 50)
    print("开始运行资金管理系统基础框架测试")
    print("=" * 50)

    test_position_type_enum()
    test_order_batch_type_enum()
    test_order_batch_dataclass()
    test_position_allocation_dataclass()
    test_equity_point_dataclass()
    test_risk_metrics_dataclass()
    test_position_sizer_base()

    print("=" * 50)
    print("所有测试通过!")
    print("=" * 50)


if __name__ == "__main__":
    test_all()
