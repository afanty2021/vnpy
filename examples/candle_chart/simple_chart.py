#!/usr/bin/env python3
"""
简化的K线图表示例
不需要从数据库加载历史数据
"""

from datetime import datetime, timedelta
from vnpy.trader.ui import create_qapp, QtCore
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy.chart import ChartWidget, VolumeItem, CandleItem


def generate_sample_data():
    """生成示例K线数据"""
    bars = []
    base_price = 4000.0
    base_volume = 1000

    # 生成100根K线
    for i in range(100):
        dt = datetime.now() - timedelta(minutes=100-i)

        # 简单随机价格生成
        change = (i % 10 - 5) * 2
        open_price = base_price + change
        high_price = open_price + abs(change) + 5
        low_price = open_price - abs(change) - 5
        close_price = open_price + (i % 5 - 2) * 3

        bar = BarData(
            symbol="DEMO",
            exchange=Exchange.SSE,
            datetime=dt,
            interval=Interval.MINUTE,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=base_volume + i * 10,
            turnover=close_price * (base_volume + i * 10),
            gateway_name="DEMO"
        )
        bars.append(bar)
        base_price = close_price

    return bars


def main():
    """主函数"""
    print("创建K线图表示例（使用模拟数据）...")

    # 创建Qt应用
    app = create_qapp()

    # 生成示例数据
    bars = generate_sample_data()
    print(f"生成了 {len(bars)} 根K线数据")

    # 创建图表控件
    chart = ChartWidget()
    chart.setWindowTitle("VeighNa K线图表示例 - 模拟数据")

    # 添加K线和成交量子图
    chart.add_plot("candle", hide_x_axis=True)
    chart.add_plot("volume", maximum_height=200)

    # 添加K线和成交量图项
    chart.add_item(CandleItem, "candle", "candle")
    chart.add_item(VolumeItem, "volume", "volume")

    # 添加十字光标
    chart.add_cursor()

    # 加载历史数据
    chart.update_history(bars)

    # 创建定时器模拟实时数据更新
    new_data = bars.copy()

    def update_bar():
        """模拟实时数据更新"""
        if new_data:
            # 循环使用已有数据
            bar = new_data.pop(0)
            # 更新时间戳为当前时间
            bar.datetime = datetime.now()
            chart.update_bar(bar)
            # 将数据加回末尾实现循环
            new_data.append(bar)

    # 设置定时器（每1秒更新一次）
    timer = QtCore.QTimer()
    timer.timeout.connect(update_bar)
    timer.start(1000)

    # 显示窗口
    chart.show()
    print("图表窗口已打开")
    print("提示：关闭窗口即可退出程序")

    # 运行应用
    app.exec()


if __name__ == "__main__":
    main()