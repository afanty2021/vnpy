"""
CapitalFlowData 使用示例

演示如何创建和使用资金流水数据对象。
"""

import os
import sys
# 项目根目录（本文件上溯三级：examples -> vnpy_china_capital -> 项目根）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from vnpy.trader.constant import Direction, Offset, Exchange
from vnpy.trader.object import TradeData, AccountData
from vnpy_china_capital.objects import CapitalFlowData


def demo_basic_creation():
    """演示基本创建方式"""
    print("=" * 50)
    print("示例1: 直接创建资金流水")
    print("=" * 50)

    flow = CapitalFlowData(
        flow_id="flow_001",
        gateway_name="QMT",
        trade_id="trade_12345",
        symbol="000001",
        exchange="SZSE",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        price=12.50,
        volume=1000,
        amount=12500.0,
        balance=100000.0,
        available=87500.0,
        trade_time=datetime.now(),
        created_at=datetime.now(),
        flow_type="trade",
        description="买入平安银行"
    )

    print(f"流水ID: {flow.flow_id}")
    print(f"股票代码: {flow.symbol}")
    print(f"统一标识: {flow.vt_symbol}")
    print(f"方向: {flow.direction.value}")
    print(f"成交价格: {flow.price}")
    print(f"成交数量: {flow.volume}")
    print(f"成交金额: {flow.amount}")
    print(f"总资金: {flow.balance}")
    print(f"可用资金: {flow.available}")
    print()


def demo_auto_flow_id():
    """演示自动生成flow_id"""
    print("=" * 50)
    print("示例2: 自动生成流水ID")
    print("=" * 50)

    flow = CapitalFlowData(
        flow_id="",  # 留空，自动生成
        gateway_name="QMT",
        trade_id="trade_67890",
        symbol="600000",
        exchange="SSE",
        direction=Direction.SHORT,
        offset=Offset.CLOSE,
        price=10.00,
        volume=500,
        amount=5000.0,
        balance=100000.0,
        available=105000.0,
        trade_time=datetime.now(),
        created_at=datetime.now(),
        flow_type="trade",
        description="卖出浦发银行"
    )

    print(f"自动生成的流水ID: {flow.flow_id}")
    print(f"格式: gateway_name + '_' + trade_id")
    print()


def demo_from_trade_data():
    """演示从TradeData创建"""
    print("=" * 50)
    print("示例3: 从TradeData创建资金流水")
    print("=" * 50)

    # 创建模拟的成交数据
    trade_time = datetime.now()
    trade_data = TradeData(
        gateway_name="QMT",
        symbol="600519",
        exchange=Exchange.SSE,
        orderid="order_001",
        tradeid="trade_99999",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        price=1500.00,
        volume=100,
        datetime=trade_time,
    )

    # 创建模拟的账户数据
    account_data = AccountData(
        gateway_name="QMT",
        accountid="account_001",
        balance=500000.0,
        frozen=150000.0,
    )

    # 从成交数据创建资金流水
    flow = CapitalFlowData.from_trade_data(
        trade_data=trade_data,
        account_data=account_data,
        flow_type="trade",
        description="买入贵州茅台"
    )

    print(f"股票代码: {flow.symbol}")
    print(f"成交金额: {flow.amount:,.2f} 元")
    print(f"总资金: {flow.balance:,.2f} 元")
    print(f"可用资金: {flow.available:,.2f} 元")
    print(f"说明: {flow.description}")
    print()


def demo_db_conversion():
    """演示数据库转换"""
    print("=" * 50)
    print("示例4: 数据库转换")
    print("=" * 50)

    flow = CapitalFlowData(
        flow_id="flow_003",
        gateway_name="QMT",
        trade_id="trade_11111",
        symbol="000002",
        exchange="SZSE",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        price=25.00,
        volume=2000,
        amount=50000.0,
        balance=200000.0,
        available=150000.0,
        trade_time=datetime.now(),
        created_at=datetime.now(),
        flow_type="trade",
        description="买入万科A"
    )

    # 转换为数据库字典
    db_dict = flow.to_db_dict()
    print(f"转换为数据库字典，包含 {len(db_dict)} 个字段")
    print(f"数据库字典示例:")
    for key, value in list(db_dict.items())[:5]:
        print(f"  {key}: {value}")
    print("  ...")
    print()

    # 从数据库字典恢复对象
    restored_flow = CapitalFlowData.from_db_dict(db_dict)
    print(f"恢复对象成功!")
    print(f"流水ID匹配: {flow.flow_id == restored_flow.flow_id}")
    print(f"股票代码匹配: {flow.symbol == restored_flow.symbol}")
    print()


def demo_flow_types():
    """演示不同的流水类型"""
    print("=" * 50)
    print("示例5: 不同的流水类型")
    print("=" * 50)

    flow_types = {
        "trade": "交易成交",
        "transfer": "资金转账",
        "fee": "手续费",
        "withdraw": "出金",
        "deposit": "入金"
    }

    for flow_type, description in flow_types.items():
        print(f"{flow_type:10s} - {description}")

    print()


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("CapitalFlowData 使用示例")
    print("=" * 50 + "\n")

    demo_basic_creation()
    demo_auto_flow_id()
    demo_from_trade_data()
    demo_db_conversion()
    demo_flow_types()

    print("=" * 50)
    print("所有示例运行完成!")
    print("=" * 50)
