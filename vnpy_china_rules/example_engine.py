"""
规则引擎使用示例

演示如何使用A股交易规则引擎检查订单合规性。
"""

from datetime import datetime
from vnpy.trader.object import OrderData, TradeData
from vnpy.trader.constant import Direction, Exchange, Offset, Status
from vnpy.trader.engine import MainEngine
from vnpy.event import EventEngine

from vnpy_china_rules import (
    QMTDataSource,
    TushareDataSource,
    DataSourceManager,
    ChinaStockRulesEngine,
)


def main():
    """主函数"""
    print("=" * 60)
    print("A股交易规则引擎使用示例")
    print("=" * 60)

    # 1. 创建数据源管理器
    print("\n1. 初始化数据源管理器...")
    manager = DataSourceManager()

    # 2. 创建规则引擎
    print("2. 创建规则引擎...")
    rules_engine = ChinaStockRulesEngine(manager)

    # 3. 显示常量
    print("\n3. 规则引擎常量:")
    print(f"   上午交易时间: {rules_engine.TRADING_MORNING_START} - {rules_engine.TRADING_MORNING_END}")
    print(f"   下午交易时间: {rules_engine.TRADING_AFTERNOON_START} - {rules_engine.TRADING_AFTERNOON_END}")
    print(f"   主板涨跌停比例: {rules_engine.LIMIT_RATIO_MAIN * 100}%")
    print(f"   创业板涨跌停比例: {rules_engine.LIMIT_RATIO_SME * 100}%")
    print(f"   科创板涨跌停比例: {rules_engine.LIMIT_RATIO_SCI * 100}%")
    print(f"   北交所涨跌停比例: {rules_engine.LIMIT_RATIO_BSE * 100}%")
    print(f"   ST股票涨跌停比例: {rules_engine.LIMIT_RATIO_ST * 100}%")

    # 4. 创建测试订单
    print("\n4. 测试规则检查:")

    # 测试订单1: 合规的买入订单
    print("\n   测试1: 合规的买入订单")
    order1 = OrderData(
        gateway_name="TEST",
        symbol="000001",
        exchange=Exchange.SZSE,
        orderid="test001",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        price=10.50,
        volume=100,  # 100股的整数倍
        datetime=datetime(2024, 2, 24, 14, 0)  # 交易时间
    )

    can_submit, message = rules_engine.can_submit_order(order1)
    print(f"   结果: {'通过' if can_submit else '失败'} - {message}")

    # 测试订单2: 不合规的交易单位
    print("\n   测试2: 不合规的交易单位（150股）")
    order2 = OrderData(
        gateway_name="TEST",
        symbol="000001",
        exchange=Exchange.SZSE,
        orderid="test002",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        price=10.50,
        volume=150,  # 不是100的整数倍
        datetime=datetime(2024, 2, 24, 14, 0)
    )

    can_submit, message = rules_engine.can_submit_order(order2)
    print(f"   结果: {'通过' if can_submit else '失败'} - {message}")

    # 测试订单3: 非交易时间
    print("\n   测试3: 非交易时间（12:00）")
    order3 = OrderData(
        gateway_name="TEST",
        symbol="000001",
        exchange=Exchange.SZSE,
        orderid="test003",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        price=10.50,
        volume=100,
        datetime=datetime(2024, 2, 24, 12, 0)  # 非交易时间
    )

    can_submit, message = rules_engine.can_submit_order(order3)
    print(f"   结果: {'通过' if can_submit else '失败'} - {message}")

    # 测试T+1规则
    print("\n5. 测试T+1规则:")

    # 前日买入
    print("\n   记录前日买入: 000001 1000股")
    rules_engine.t1_rules.record_buy(
        "000001",
        1000,
        datetime(2024, 2, 23, 9, 30)
    )

    # 查询可卖数量
    sellable = rules_engine.t1_rules.get_sellable_volume(
        "000001",
        datetime(2024, 2, 24, 14, 0)
    )
    print(f"   可卖数量: {sellable}股")

    # 创建卖出订单
    print("\n   测试卖出订单（卖出500股）")
    sell_order = OrderData(
        gateway_name="TEST",
        symbol="000001",
        exchange=Exchange.SZSE,
        orderid="sell001",
        direction=Direction.SHORT,
        offset=Offset.CLOSE,
        price=11.00,
        volume=500,
        datetime=datetime(2024, 2, 24, 14, 0)
    )

    can_submit, message = rules_engine.can_submit_order(sell_order)
    print(f"   结果: {'通过' if can_submit else '失败'} - {message}")

    # 当日买入
    print("\n   记录当日买入: 000001 800股")
    rules_engine.t1_rules.record_buy(
        "000001",
        800,
        datetime(2024, 2, 24, 9, 30)
    )

    # 再次查询可卖数量
    sellable = rules_engine.t1_rules.get_sellable_volume(
        "000001",
        datetime(2024, 2, 24, 14, 0)
    )
    print(f"   可卖数量: {sellable}股（当日买入不可卖）")

    # 测试当日卖出
    print("\n   测试卖出当日买入的股票")
    sell_order2 = OrderData(
        gateway_name="TEST",
        symbol="000001",
        exchange=Exchange.SZSE,
        orderid="sell002",
        direction=Direction.SHORT,
        offset=Offset.CLOSE,
        price=11.00,
        volume=500,
        datetime=datetime(2024, 2, 24, 14, 0)
    )

    can_submit, message = rules_engine.can_submit_order(sell_order2)
    print(f"   结果: {'通过' if can_submit else '失败'} - {message}")

    print("\n" + "=" * 60)
    print("示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
