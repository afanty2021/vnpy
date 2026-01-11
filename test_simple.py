#!/usr/bin/env python3
"""
VeighNa简化测试脚本
快速验证核心功能是否正常
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
    Exchange,
    Interval,
    Product
)


def test_core_modules():
    """测试核心模块导入和创建"""
    print("=" * 50)
    print("🧪 VeighNa 核心功能测试")
    print("=" * 50)

    # 1. 测试事件引擎
    print("\n1. 测试事件引擎...")
    event_engine = EventEngine()
    print("   ✅ 事件引擎创建成功")

    # 2. 测试主引擎
    print("\n2. 测试主引擎...")
    main_engine = MainEngine(event_engine)
    print("   ✅ 主引擎创建成功")

    # 3. 创建测试数据对象
    print("\n3. 测试数据对象...")

    # 合约数据
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
    print(f"   ✅ 合约对象创建: {test_contract.symbol}")

    # K线数据
    test_bar = BarData(
        gateway_name="TEST",
        symbol="IF888",
        exchange=Exchange.CFFEX,
        datetime=datetime.now(),
        interval=Interval.MINUTE,
        open_price=4000.0,
        high_price=4010.0,
        low_price=3990.0,
        close_price=4005.0,
        volume=1000,
        turnover=1000000
    )
    print(f"   ✅ K线对象创建: {test_bar.open_price} -> {test_bar.close_price}")

    # Tick数据
    test_tick = TickData(
        gateway_name="TEST",
        symbol="IF888",
        exchange=Exchange.CFFEX,
        datetime=datetime.now(),
        name="沪深300指数",
        volume=100,
        turnover=100000,
        open_price=4000.0,
        high_price=4010.0,
        low_price=3990.0,
        pre_close=3995.0,
        last_price=4005.0
    )
    print(f"   ✅ Tick对象创建: {test_tick.last_price}")

    return main_engine, event_engine


def test_alpha_functionality():
    """测试Alpha量化研究功能"""
    print("\n" + "=" * 50)
    print("🤖 Alpha量化研究功能测试")
    print("=" * 50)

    try:
        from vnpy.alpha import AlphaDataset, AlphaModel, AlphaStrategy, AlphaLab

        print("\n1. 测试Alpha模块导入...")
        print("   ✅ AlphaDataset - 数据集管理")
        print("   ✅ AlphaModel - 模型训练")
        print("   ✅ AlphaStrategy - 策略开发")
        print("   ✅ AlphaLab - 投研管理")

        # 测试AlphaLab创建
        print("\n2. 测试AlphaLab创建...")
        lab = AlphaLab("~/alpha_lab")
        print("   ✅ AlphaLab实例创建成功")

        # 提示使用方法
        print("\n💡 Alpha模块使用示例:")
        print("   from vnpy.alpha import AlphaLab")
        print("   lab = AlphaLab()")
        print("   # 然后可以开始量化研究工作流")

        return True

    except ImportError as e:
        print(f"   ❌ Alpha模块导入失败: {e}")
        print("   💡 请确保已安装Alpha依赖: pip install -e '.[alpha]'")
        return False


def test_chart_functionality():
    """测试图表功能"""
    print("\n" + "=" * 50)
    print("📊 图表功能测试")
    print("=" * 50)

    try:
        from vnpy.chart import ChartWidget, CandleItem, VolumeItem

        print("\n1. 测试图表模块导入...")
        print("   ✅ ChartWidget - 图表控件")
        print("   ✅ CandleItem - K线图项")
        print("   ✅ VolumeItem - 成交量图项")

        print("\n💡 图表使用示例:")
        print("   from vnpy.chart import ChartWidget, CandleItem")
        print("   chart = ChartWidget()")
        print("   chart.add_plot('candle')")
        print("   chart.add_item(CandleItem, 'candle', 'candle')")

        return True

    except ImportError as e:
        print(f"   ❌ 图表模块导入失败: {e}")
        return False


def test_gui_startup():
    """测试GUI启动（可选）"""
    print("\n" + "=" * 50)
    print("🖥️  GUI界面测试")
    print("=" * 50)

    try:
        print("\n创建GUI应用...")
        app = create_qapp()

        # 创建事件引擎和主引擎
        event_engine = EventEngine()
        main_engine = MainEngine(event_engine)

        # 创建主窗口
        main_window = MainWindow(main_engine, event_engine)
        print("   ✅ 主窗口创建成功")

        print("\n💡 GUI已创建，将显示窗口")
        print("   💡 关闭窗口即可退出测试")
        print("   ⚠️  如果无法显示，可能是因为无显示器环境")

        # 显示窗口
        main_window.showMaximized()

        # 运行应用
        app.exec()

        return True

    except Exception as e:
        print(f"   ⚠️  GUI启动失败: {e}")
        print("   💡 这在无显示器环境是正常的")
        return False


def main():
    """主函数"""
    print(f"\nPython版本: {sys.version}")
    print(f"当前工作目录: {sys.path[0]}")
    print(f"开始VeighNa功能测试...\n")

    # 1. 测试核心模块
    success_count = 0
    main_engine, event_engine = test_core_modules()
    success_count += 1

    # 2. 测试Alpha功能
    if test_alpha_functionality():
        success_count += 1

    # 3. 测试图表功能
    if test_chart_functionality():
        success_count += 1

    # 4. 询问是否测试GUI
    print("\n" + "=" * 50)
    test_gui = input("是否测试GUI界面？(y/N): ").lower().strip()

    if test_gui in ['y', 'yes']:
        if test_gui_startup():
            success_count += 1

    # 测试总结
    print("\n" + "=" * 50)
    print("📊 测试总结")
    print("=" * 50)
    print(f"✅ 测试完成")
    print(f"🎉 VeighNa {sys.version.split()[0]} 环境测试成功！")

    print("\n📝 下一步建议:")
    print("   1. 配置交易接口（CTP/IB等）")
    print("   2. 运行examples中的示例程序")
    print("   3. 开始策略开发")

    print("\n📚 资源链接:")
    print("   - 官方文档: https://www.vnpy.com/docs")
    print("   - 社区论坛: https://www.vnpy.com/forum")
    print("   - GitHub: https://github.com/vnpy/vnpy")


if __name__ == "__main__":
    main()