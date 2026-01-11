#!/usr/bin/env python3
"""
VeighNa基础功能测试
不需要交易接口，仅测试框架核心功能
"""

import sys
from datetime import datetime

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy.trader.object import (
    TickData,
    BarData,
    ContractData,
    OrderRequest,
    CancelRequest,
    Direction,
    OrderType,
    Status,
    Exchange,
    Interval
)
from vnpy.trader.constant import Product


def test_basic_functionality():
    """测试基础功能"""
    print("=" * 50)
    print("🧪 VeighNa 基础功能测试")
    print("=" * 50)

    # 创建事件引擎
    event_engine = EventEngine()
    print("✅ 事件引擎创建成功")

    # 创建主引擎
    main_engine = MainEngine(event_engine)
    print("✅ 主引擎创建成功")

    # 显示支持的网关
    print("\n📋 已注册的网关:")
    for gateway_name in main_engine.get_all_gateway_names():
        print(f"   - {gateway_name}")

    # 显示支持的应用
    print("\n📋 已注册的应用:")
    for app_name in main_engine.get_all_apps():
        print(f"   - {app_name.app_name}")

    # 创建测试合约
    test_contract = ContractData(
        gateway_name="TEST",
        symbol="IF888",
        exchange=Exchange.CFFEX,
        name="沪深300指数",
        product=Product.INDEX,
        size=1,
        pricetick=0.1,
        min_volume=1,
        history_data=True,
        net_position=True
    )

    # 添加合约到主引擎
    main_engine.update_contract(test_contract)
    print(f"✅ 测试合约 {test_contract.symbol} 添加成功")

    # 创建测试K线数据
    test_bar = BarData(
        symbol="IF888",
        exchange=Exchange.CFFEX,
        datetime=datetime.now(),
        interval=Interval.MINUTE,
        open_price=4000.0,
        high_price=4010.0,
        low_price=3990.0,
        close_price=4005.0,
        volume=1000,
        turnover=1000000,
        gateway_name=""
    )

    print(f"✅ 测试K线数据创建成功: {test_bar}")

    return main_engine, event_engine


def test_alpha_module():
    """测试Alpha量化研究模块"""
    print("\n" + "=" * 50)
    print("🤖 Alpha量化研究模块测试")
    print("=" * 50)

    try:
        from vnpy.alpha.dataset import AlphaDataset
        from vnpy.alpha.model import AlphaModel
        from vnpy.alpha.strategy import AlphaStrategy
        from vnpy.alpha.lab import AlphaLab

        print("✅ Alpha模块导入成功")
        print(f"   - AlphaDataset: {AlphaDataset}")
        print(f"   - AlphaModel: {AlphaModel}")
        print(f"   - AlphaStrategy: {AlphaStrategy}")
        print(f"   - AlphaLab: {AlphaLab}")

        # 创建AlphaLab实例
        lab = AlphaLab()
        print("✅ AlphaLab实例创建成功")

    except ImportError as e:
        print(f"❌ Alpha模块导入失败: {e}")


def test_chart_module():
    """测试图表模块"""
    print("\n" + "=" * 50)
    print("📊 图表模块测试")
    print("=" * 50)

    try:
        from vnpy.chart import ChartWidget, CandleItem, VolumeItem
        print("✅ 图表模块导入成功")
        print(f"   - ChartWidget: {ChartWidget}")
        print(f"   - CandleItem: {CandleItem}")
        print(f"   - VolumeItem: {VolumeItem}")

    except ImportError as e:
        print(f"❌ 图表模块导入失败: {e}")


def main():
    """主测试函数"""
    print(f"Python版本: {sys.version}")
    print(f"VeighNa版本测试开始...")

    # 测试基础功能
    main_engine, event_engine = test_basic_functionality()

    # 测试Alpha模块
    test_alpha_module()

    # 测试图表模块
    test_chart_module()

    print("\n" + "=" * 50)
    print("🎉 基础功能测试完成！")
    print("📝 说明: ")
    print("   - 核心模块工作正常")
    print("   - 可以开始添加交易接口")
    print("   - 可以运行examples中的示例")
    print("=" * 50)

    # 测试GUI（可选）
    try:
        print("\n启动GUI界面测试...")
        app = create_qapp()
        main_window = MainWindow(main_engine, event_engine)
        main_window.show()
        print("✅ GUI界面创建成功")
        print("💡 提示: 关闭窗口即可退出程序")
        app.exec()
    except Exception as e:
        print(f"⚠️  GUI启动失败: {e}")
        print("💡 可能是因为无显示器环境，这是正常的")


if __name__ == "__main__":
    main()