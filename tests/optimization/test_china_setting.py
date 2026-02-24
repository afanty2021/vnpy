"""
测试A股优化设置
"""
import pytest
from vnpy_china_optimize.setting.china_setting import (
    ChinaTradingCost,
    ChinaOptimizerSetting,
    calculate_china_trading_cost,
)


def test_trading_cost_calculate_buy():
    """测试买入成本计算"""
    cost_config = ChinaTradingCost()

    # 买入100手，价格10元
    buy_cost = cost_config.calculate_buy_cost(price=10.0, volume=100)

    # 金额 = 10 * 100 * 100 = 100,000
    # 佣金 = max(100000 * 0.0003, 5) = 30
    # 过户费 = 100000 * 0.00001 = 1
    # 经手费 = 100000 * 0.00000685 = 0.685
    # 总成本约 100,031.685
    assert buy_cost > 100000
    assert buy_cost < 101000


def test_trading_cost_calculate_sell():
    """测试卖出成本计算"""
    cost_config = ChinaTradingCost()

    # 卖出100手，价格10元
    sell_income = cost_config.calculate_sell_cost(price=10.0, volume=100)

    # 金额 = 10 * 100 * 100 = 100,000
    # 佣金 = 30
    # 印花税 = 100000 * 0.001 = 100
    # 过户费 = 1
    # 经手费 = 0.685
    # 净收入 = 100,000 - 30 - 100 - 1 - 0.685 = 99,868.315
    assert sell_income < 100000
    assert sell_income > 99000


def test_trading_cost_round_trip():
    """测试往返成本"""
    cost_config = ChinaTradingCost()

    cost_rate = cost_config.calculate_round_trip_cost(price=10.0, volume=100)

    # 往返成本率应该在0.1%到0.3%之间
    assert 0.001 < cost_rate < 0.003


def test_min_commission():
    """测试最低佣金"""
    cost_config = ChinaTradingCost()

    # 小额交易，佣金应该按最低5元收取
    buy_cost = cost_config.calculate_buy_cost(price=1.0, volume=1)

    # 金额 = 1 * 1 * 100 = 100
    # 佣金 = max(100 * 0.0003, 5) = 5（触发最低佣金）
    assert buy_cost > 100
    # 佣金至少5元
    assert buy_cost >= 105


def test_custom_trading_cost():
    """测试自定义交易成本"""
    cost_config = ChinaTradingCost(
        commission_rate=0.0002,  # 万2
        min_commission=10.0,     # 最低10元
        stamp_duty=0.0015        # 印花税0.15%
    )

    buy_cost = cost_config.calculate_buy_cost(price=10.0, volume=100)
    sell_income = cost_config.calculate_sell_cost(price=10.0, volume=100)

    assert buy_cost > 0
    assert sell_income > 0


def test_china_optimizer_setting():
    """测试A股优化设置"""
    setting = ChinaOptimizerSetting()

    # 检查默认值
    assert setting.t1_rule is True
    assert setting.price_limit is True
    assert setting.min_trading_unit == 100

    # 设置交易成本
    setting.set_trading_cost(
        commission_rate=0.0003,
        min_commission=5.0,
        stamp_duty=0.001
    )

    assert setting.trading_cost.commission_rate == 0.0003


def test_calculate_total_cost():
    """测试完整交易成本计算"""
    setting = ChinaOptimizerSetting()

    total_cost = setting.calculate_total_cost(
        entry_price=10.0,
        exit_price=11.0,  # 卖出价格更高，有利润
        volume=100
    )

    # 总成本是买入成本减去卖出收入（正值表示成本）
    # 由于卖出价格更高，总体可能是负的（表示盈利）
    # 只验证计算能正常完成
    assert isinstance(total_cost, float)


def test_calculate_china_trading_cost_function():
    """测试便捷函数"""
    # 买入
    buy_cost = calculate_china_trading_cost(
        price=10.0,
        volume=100,
        is_buy=True
    )
    assert buy_cost > 0

    # 卖出
    sell_income = calculate_china_trading_cost(
        price=10.0,
        volume=100,
        is_buy=False
    )
    assert sell_income > 0


def test_slippage():
    """测试滑点"""
    cost_config = ChinaTradingCost(slippage=0.001)  # 0.1%滑点

    buy_cost = cost_config.calculate_buy_cost(price=10.0, volume=100)

    # 有滑点时成本应该更高
    assert buy_cost > 100000


def test_compare_buy_sell():
    """对比买入和卖出成本"""
    cost_config = ChinaTradingCost()

    buy_cost = cost_config.calculate_buy_cost(price=10.0, volume=100)
    sell_income = cost_config.calculate_sell_cost(price=10.0, volume=100)

    # 卖出收入应该小于买入成本（因为有印花税）
    assert sell_income < buy_cost

    # 计算价差比例
    spread = (buy_cost - sell_income) / buy_cost
    # 价差比例应该在0.15%左右（主要是印花税）
    assert 0.001 < spread < 0.002
