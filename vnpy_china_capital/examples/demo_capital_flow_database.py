"""
资金流水数据库操作演示

演示如何使用 CapitalFlowDatabase 进行资金流水的保存和查询。
"""

import sys
sys.path.insert(0, '/Users/berton/Github/vnpy')

from datetime import datetime, date, timedelta

from vnpy.trader.constant import Direction, Offset, Exchange
from vnpy.trader.object import TradeData, AccountData

from vnpy_china_capital import CapitalFlowDatabase, CapitalFlowData
from vnpy_china_data.database import MySQLDatabaseLayer


def create_mock_database_layer():
    """创建模拟数据库层（用于演示）"""
    from unittest.mock import Mock

    mock_db = Mock()
    mock_db.create_capital_flow_table = Mock(return_value=True)
    mock_db.save_capital_flow = Mock(return_value=True)
    mock_db.query_capital_flow = Mock(return_value=[])
    # 模拟 _execute_sql 返回结果
    mock_db._execute_sql = Mock(side_effect=lambda sql, params=None, fetch_all=False: (
        [] if fetch_all else True
    ))
    return mock_db


def demo_create_flow():
    """演示创建资金流水"""
    print("=" * 60)
    print("演示 1: 创建资金流水数据")
    print("=" * 60)

    flow = CapitalFlowData(
        flow_id="DEMO_trade_001",
        gateway_name="DEMO",
        trade_id="trade_001",
        symbol="000001",
        exchange="SZSE",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        price=10.50,
        volume=1000.0,
        amount=10500.0,
        balance=50000.0,
        available=39500.0,
        trade_time=datetime.now(),
        created_at=datetime.now(),
        flow_type="trade",
        description="买入平安银行"
    )

    print(f"流水ID: {flow.flow_id}")
    print(f"股票: {flow.vt_symbol}")
    print(f"方向: {flow.direction.value}")
    print(f"价格: {flow.price}, 数量: {flow.volume}")
    print(f"金额: {flow.amount}, 总资金: {flow.balance}")
    print(f"类型: {flow.flow_type}, 说明: {flow.description}")
    print()


def demo_from_trade_data():
    """演示从成交数据创建流水"""
    print("=" * 60)
    print("演示 2: 从成交数据创建资金流水")
    print("=" * 60)

    # 创建成交数据
    trade = TradeData(
        gateway_name="DEMO",
        symbol="600000",
        exchange=Exchange.SSE,
        orderid="order_001",
        tradeid="trade_002",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        price=10.50,
        volume=1000,
        datetime=datetime.now(),
    )

    # 创建账户数据
    account = AccountData(
        gateway_name="DEMO",
        accountid="account_001",
        balance=50000.0,
        frozen=500.0,
    )

    # 创建流水
    flow = CapitalFlowData.from_trade_data(
        trade_data=trade,
        account_data=account,
        flow_type="trade",
        description="买入浦发银行"
    )

    print(f"自动生成的流水ID: {flow.flow_id}")
    print(f"股票: {flow.vt_symbol}")
    print(f"成交金额: {flow.amount}")
    print(f"可用资金: {flow.available} (总资金 {flow.balance} - 冻结 {account.frozen})")
    print()


def demo_database_operations():
    """演示数据库操作"""
    print("=" * 60)
    print("演示 3: 数据库操作")
    print("=" * 60)

    # 创建数据库层（使用模拟）
    db_layer = create_mock_database_layer()
    db = CapitalFlowDatabase(db_layer)

    # 1. 初始化表
    print("1. 初始化数据库表...")
    db.init_tables()
    print("   ✓ 数据库表初始化成功")

    # 2. 创建并保存流水
    print("\n2. 保存资金流水...")
    flow = CapitalFlowData(
        flow_id="DEMO_trade_001",
        gateway_name="DEMO",
        trade_id="trade_001",
        symbol="000001",
        exchange="SZSE",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        price=10.50,
        volume=1000.0,
        amount=10500.0,
        balance=50000.0,
        available=39500.0,
        trade_time=datetime.now(),
        created_at=datetime.now(),
        flow_type="trade",
        description="买入平安银行"
    )
    db.save_capital_flow(flow)
    print(f"   ✓ 流水 {flow.flow_id} 保存成功")

    # 3. 查询流水
    print("\n3. 查询资金流水...")
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    flows = db.query_capital_flow(start_date=start_date, end_date=end_date)
    print(f"   ✓ 查询到 {len(flows)} 条记录")

    # 4. 获取最新流水
    print("\n4. 获取最新流水...")
    latest = db.get_latest_capital_flow(symbol="000001")
    if latest:
        print(f"   ✓ 最新流水: {latest.flow_id}")

    # 5. 统计信息
    print("\n5. 获取统计信息...")
    stats = db.get_flow_statistics()
    for flow_type, stat in stats.items():
        print(f"   {flow_type}: {stat['count']} 笔, 总额 {stat['total_amount']:.2f}")

    print()


def demo_advanced_features():
    """演示高级功能"""
    print("=" * 60)
    print("演示 4: 高级功能")
    print("=" * 60)

    db_layer = create_mock_database_layer()
    db = CapitalFlowDatabase(db_layer)

    # 1. 按股票查询
    print("1. 按股票查询最近30天流水...")
    flows = db.query_capital_flow_by_symbol(symbol="000001", days=30)
    print(f"   ✓ 查询到 {len(flows)} 条记录")

    # 2. 按类型查询
    print("\n2. 按类型查询交易流水...")
    flows = db.query_capital_flow(flow_type="trade")
    print(f"   ✓ 查询到 {len(flows)} 条记录")

    # 3. 每日汇总
    print("\n3. 获取今日流水汇总...")
    summary = db.get_daily_flow_summary()
    print(f"   ✓ 今日汇总包含 {len(summary)} 个股票")

    # 4. 删除重复记录
    print("\n4. 删除重复流水记录...")
    count = db.delete_duplicate_flows()
    print(f"   ✓ 删除了 {count} 条重复记录")

    print()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("资金流水数据库操作演示")
    print("=" * 60 + "\n")

    demo_create_flow()
    demo_from_trade_data()
    demo_database_operations()
    demo_advanced_features()

    print("=" * 60)
    print("演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
