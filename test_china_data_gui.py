"""
A股数据模块GUI功能测试

测试龙虎榜和北向资金数据的查询和显示功能。
"""

from datetime import date


def test_data_models():
    """测试数据模型"""
    print("=" * 50)
    print("测试数据模型...")
    print("=" * 50)

    from vnpy_china_data.models.dragon_tiger import DragonTigerData
    from vnpy_china_data.models.northbound import NorthboundFlowData

    # 创建测试数据
    dt_data = DragonTigerData(
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
    )
    print(f"龙虎榜数据: {dt_data.name} - {dt_data.total_net_buy:+.2f}万元")

    nb_data = NorthboundFlowData(
        trade_date=date(2026, 2, 20),
        sh_net_inflow=25.5,
        sh_buy_volume=100.0,
        sh_sell_volume=74.5,
        sz_net_inflow=15.3,
        sz_buy_volume=80.0,
        sz_sell_volume=64.7,
    )
    print(f"北向资金: 总净流入 {nb_data.total_net_inflow:+.2f}亿元")


def test_gui_engine():
    """测试GUI引擎"""
    print("\n" + "=" * 50)
    print("测试GUI引擎...")
    print("=" * 50)

    from vnpy.event import EventEngine
    from vnpy.trader.engine import MainEngine
    from vnpy_china_data.app import ChinaDataApp

    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    gui_engine = main_engine.add_app(ChinaDataApp)

    print(f"GUI引擎名称: {gui_engine.engine_name}")
    print(f"数据服务状态: {gui_engine.get_data_service_status()}")

    # 测试查询方法（使用当前日期）
    from datetime import date
    try:
        result = gui_engine.query_dragon_tiger(date.today())
        print(f"龙虎榜查询测试：返回{len(result)}条记录")
    except Exception as e:
        print(f"龙虎榜查询测试：失败 - {e}")

    event_engine.stop()


def test_table_components():
    """测试表格组件"""
    print("\n" + "=" * 50)
    print("测试表格组件导入...")
    print("=" * 50)

    try:
        from vnpy_china_data.ui.table import DragonTigerTable, NorthboundTable
        print("DragonTigerTable: 导入成功")
        print("NorthboundTable: 导入成功")
    except ImportError as e:
        print(f"导入失败: {e}")


def test_widget_components():
    """测试主组件"""
    print("\n" + "=" * 50)
    print("测试主组件导入...")
    print("=" * 50)

    try:
        from vnpy_china_data.ui.widget import ChinaDataWidget
        print("ChinaDataWidget: 导入成功")
    except ImportError as e:
        print(f"导入失败: {e}")


if __name__ == "__main__":
    test_data_models()
    test_gui_engine()
    test_table_components()
    test_widget_components()

    print("\n" + "=" * 50)
    print("所有测试完成！")
    print("=" * 50)
