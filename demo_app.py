#!/usr/bin/env python3
"""
VeighNa 4.2.0 功能演示应用
展示核心功能，无需交易接口或历史数据
"""

import sys
from datetime import datetime, timedelta
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy.trader.object import (
    TickData,
    BarData,
    ContractData,
    OrderRequest,
    Direction,
    OrderType,
    Exchange,
    Interval,
    Product
)
from vnpy.chart import ChartWidget, CandleItem, VolumeItem
from vnpy.trader.ui import QtCore


class DemoApp:
    """VeighNa功能演示应用"""

    def __init__(self):
        """初始化"""
        print("=" * 60)
        print("🚀 VeighNa 4.2.0 功能演示")
        print("=" * 60)

        # 创建事件引擎和主引擎
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)

        print("\n✅ 事件引擎和主引擎初始化完成")

        # 注册事件处理器
        self.register_event_handlers()

        # 创建示例数据
        self.create_sample_data()

    def register_event_handlers(self):
        """注册事件处理器"""
        # 订阅所有事件
        self.event_engine.register_general_handler(self.on_event)

        print("✅ 事件处理器注册完成")

    def on_event(self, event):
        """通用事件处理器"""
        # 这里可以处理所有事件
        pass

    def create_sample_data(self):
        """创建示例数据"""
        print("\n📊 创建示例数据...")

        # 创建示例合约
        self.contract = ContractData(
            gateway_name="DEMO",
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

        # 生成示例K线数据
        self.bars = []
        base_price = 4000.0
        base_volume = 1000

        for i in range(200):
            dt = datetime.now() - timedelta(minutes=200-i)

            # 生成更真实的价格波动
            trend = i % 20 - 10  # -10 到 10 的趋势
            volatility = 20  # 波动幅度

            open_price = base_price + trend * 0.5
            high_price = open_price + volatility
            low_price = open_price - volatility
            close_price = open_price + (i % 7 - 3) * 5

            bar = BarData(
                symbol="IF888",
                exchange=Exchange.CFFEX,
                datetime=dt,
                interval=Interval.MINUTE,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=base_volume + (i % 100) * 10,
                turnover=close_price * (base_volume + (i % 100) * 10),
                gateway_name="DEMO"
            )
            self.bars.append(bar)
            base_price = close_price

        print(f"   生成了 {len(self.bars)} 根K线数据")

        # 生成示例Tick数据
        self.ticks = []
        for i in range(10):
            tick = TickData(
                symbol="IF888",
                exchange=Exchange.CFFEX,
                datetime=datetime.now(),
                name="沪深300指数",
                volume=100 + i * 10,
                turnover=1000000 + i * 10000,
                open_price=4000.0,
                high_price=4010.0,
                low_price=3990.0,
                pre_close=3995.0,
                last_price=4005.0 + i,
                gateway_name="DEMO"
            )
            self.ticks.append(tick)

        print(f"   生成了 {len(self.ticks)} 个Tick数据")

    def test_trading_functions(self):
        """测试交易功能"""
        print("\n💼 测试交易功能...")

        # 测试下单请求
        order_request = OrderRequest(
            symbol="IF888",
            exchange=Exchange.CFFEX,
            direction=Direction.LONG,
            type=OrderType.LIMIT,
            volume=1,
            price=4000.0,
            reference="测试订单",
            gateway_name="DEMO"
        )
        print(f"   创建测试订单: {order_request}")

    def test_alpha_features(self):
        """测试Alpha量化研究功能"""
        print("\n🤖 测试Alpha量化研究功能...")

        try:
            from vnpy.alpha.dataset import AlphaDataset
            from vnpy.alpha.model import AlphaModel
            from vnpy.alpha.strategy import AlphaStrategy
            from vnpy.alpha.lab import AlphaLab

            print("   ✅ Alpha模块导入成功")
            print("   - AlphaDataset: 数据集管理")
            print("   - AlphaModel: 模型训练")
            print("   - AlphaStrategy: 策略开发")
            print("   - AlphaLab: 投研管理")

            # 注意：这里只是导入测试，不实际创建实例
            print("   💡 Alpha量化研究功能已准备就绪")

        except ImportError as e:
            print(f"   ❌ Alpha模块导入失败: {e}")

    def show_chart_window(self):
        """显示图表窗口"""
        print("\n📈 显示K线图表...")

        # 创建图表
        chart = ChartWidget()
        chart.setWindowTitle("VeighNa 4.2.0 - 演示图表")

        # 添加K线和成交量子图
        chart.add_plot("candle", hide_x_axis=True)
        chart.add_plot("volume", maximum_height=200)

        # 添加图项
        chart.add_item(CandleItem, "candle", "candle")
        chart.add_item(VolumeItem, "volume", "volume")

        # 添加十字光标
        chart.add_cursor()

        # 加载历史数据
        chart.update_history(self.bars[:100])

        # 模拟实时更新
        self.chart = chart
        self.update_index = 100

        # 设置定时器
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_chart)
        self.timer.start(1000)  # 每秒更新

        chart.show()
        print("   ✅ 图表窗口已打开（显示100根历史K线）")
        print("   💡 正在模拟实时数据更新...")

    def update_chart(self):
        """更新图表数据"""
        if self.update_index < len(self.bars):
            bar = self.bars[self.update_index]
            bar.datetime = datetime.now()  # 更新为当前时间
            self.chart.update_bar(bar)
            self.update_index += 1
        else:
            # 循环播放
            self.update_index = 100

    def run(self):
        """运行演示应用"""
        print("\n🎯 开始功能演示...")
        print("-" * 60)

        # 测试交易功能
        self.test_trading_functions()

        # 测试Alpha功能
        self.test_alpha_features()

        # 创建Qt应用
        app = create_qapp()

        # 创建主窗口
        main_window = MainWindow(self.main_engine, self.event_engine)
        main_window.setWindowTitle("VeighNa 4.2.0 - 功能演示")
        main_window.showMaximized()
        print("✅ 主窗口已打开")

        # 显示图表窗口
        self.show_chart_window()

        # 打印提示
        print("\n" + "-" * 60)
        print("🎉 VeighNa功能演示已启动！")
        print("📝 功能说明：")
        print("   1. 主窗口：完整的交易界面")
        print("   2. 图表窗口：实时更新的K线图")
        print("   3. Alpha模块：量化研究功能")
        print("\n💡 提示：关闭所有窗口即可退出")
        print("-" * 60)

        # 运行应用
        app.exec()


def main():
    """主函数"""
    # 检查Python版本
    if sys.version_info < (3, 10):
        print("❌ 需要Python 3.10或更高版本")
        return

    # 创建并运行演示应用
    demo = DemoApp()
    demo.run()


if __name__ == "__main__":
    main()