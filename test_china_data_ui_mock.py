"""
A股数据模块UI组件模拟测试

不依赖外部服务，使用模拟数据测试UI组件功能。
"""

import sys
from datetime import date


def test_table_with_mock_data():
    """测试表格组件处理模拟数据"""
    print("=" * 50)
    print("测试表格组件...")
    print("=" * 50)

    from vnpy_china_data.models.dragon_tiger import DragonTigerData
    from vnpy_china_data.models.northbound import NorthboundFlowData

    # 创建模拟龙虎榜数据
    mock_dt_data = [
        DragonTigerData(
            symbol="000001",
            name="平安银行",
            trade_date=date(2026, 2, 20),
            close_price=10.50,
            change_pct=5.2,
            turnover_rate=8.5,
            institution_net_buy=1500.0,
            institution_buy=2000.0,
            institution_sell=500.0,
            broker_net_buy=500.0,
            broker_buy=1000.0,
            broker_sell=500.0,
            reason="涨幅偏离值达7%"
        ),
        DragonTigerData(
            symbol="600519",
            name="贵州茅台",
            trade_date=date(2026, 2, 20),
            close_price=1850.00,
            change_pct=-3.5,
            turnover_rate=2.1,
            institution_net_buy=-2000.0,
            institution_buy=1000.0,
            institution_sell=3000.0,
            broker_net_buy=-800.0,
            broker_buy=200.0,
            broker_sell=1000.0,
            reason="跌幅偏离值达7%"
        ),
    ]

    print(f"模拟龙虎榜数据：{len(mock_dt_data)}条")
    for data in mock_dt_data:
        print(f"  {data.symbol} {data.name}: {data.change_pct:+.2f}%, 净买入: {data.total_net_buy:+.2f}万元")

    # 创建模拟北向资金数据
    mock_nb_data = NorthboundFlowData(
        trade_date=date(2026, 2, 20),
        sh_net_inflow=25.5,
        sh_buy_volume=100.0,
        sh_sell_volume=74.5,
        sz_net_inflow=15.3,
        sz_buy_volume=80.0,
        sz_sell_volume=64.7,
    )

    print(f"\n模拟北向资金数据:")
    print(f"  交易日期: {mock_nb_data.trade_date}")
    print(f"  沪股通净流入: {mock_nb_data.sh_net_inflow:+.2f}亿元")
    print(f"  深股通净流入: {mock_nb_data.sz_net_inflow:+.2f}亿元")
    print(f"  总净流入: {mock_nb_data.total_net_inflow:+.2f}亿元")


def test_widget_creation():
    """测试组件创建（不启动GUI）"""
    print("\n" + "=" * 50)
    print("测试组件导入...")
    print("=" * 50)

    try:
        from vnpy_china_data.ui.widget import ChinaDataWidget
        print("ChinaDataWidget: 导入成功")

        # 检查方法是否存在
        methods = [
            "init_ui",
            "create_dragon_tiger_tab",
            "create_northbound_tab",
            "query_dragon_tiger",
            "refresh_dragon_tiger",
            "query_northbound",
            "refresh_northbound",
            "show_status",
        ]

        for method in methods:
            if hasattr(ChinaDataWidget, method):
                print(f"  ✓ {method}")
            else:
                print(f"  ✗ {method} 缺失")

    except ImportError as e:
        print(f"导入失败: {e}")


def test_table_creation():
    """测试表格组件创建"""
    print("\n" + "=" * 50)
    print("测试表格组件导入...")
    print("=" * 50)

    try:
        from vnpy_china_data.ui.table import DragonTigerTable, NorthboundTable, PnlCell, DateCell
        print("DragonTigerTable: 导入成功")
        print("NorthboundTable: 导入成功")
        print("PnlCell: 导入成功")
        print("DateCell: 导入成功")

        # 检查方法
        if hasattr(DragonTigerTable, "update_data"):
            print("  ✓ DragonTigerTable.update_data")
        if hasattr(NorthboundTable, "update_data"):
            print("  ✓ NorthboundTable.update_data")

    except ImportError as e:
        print(f"导入失败: {e}")


def test_gui_engine():
    """测试GUI引擎"""
    print("\n" + "=" * 50)
    print("测试GUI引擎...")
    print("=" * 50)

    try:
        from vnpy_china_data.gui_engine import ChinaDataGuiEngine
        print("ChinaDataGuiEngine: 导入成功")

        # 检查方法
        methods = [
            "query_dragon_tiger",
            "query_northbound_flow",
            "get_data_service_status",
            "_init_data_service",
        ]

        for method in methods:
            if hasattr(ChinaDataGuiEngine, method):
                print(f"  ✓ {method}")
            else:
                print(f"  ✗ {method} 缺失")

    except ImportError as e:
        print(f"导入失败: {e}")


if __name__ == "__main__":
    test_table_with_mock_data()
    test_widget_creation()
    test_table_creation()
    test_gui_engine()

    print("\n" + "=" * 50)
    print("所有测试完成！")
    print("=" * 50)
