"""
测试Tushare资金流向数据获取
"""

from datetime import date
from vnpy_china_data import get_data_service
from vnpy.trader.constant import Exchange


def test_moneyflow():
    """测试资金流向数据获取"""
    # 获取数据服务
    service = get_data_service()

    # 连接
    if not service.connected:
        print("正在连接数据服务...")
        if not service.connect():
            print("数据服务连接失败，请检查配置")
            return

    print("数据服务已连接")

    # 测试获取单个股票的资金流向数据
    symbol = "000001"
    exchange = Exchange.SZSE
    trade_date = date(2026, 2, 20)  # 使用最近的交易日

    print(f"\n正在获取 {symbol} 的资金流向数据...")

    moneyflow_list = service.get_moneyflow(
        symbol=symbol,
        exchange=exchange,
        trade_date=trade_date
    )

    if moneyflow_list:
        print(f"成功获取 {len(moneyflow_list)} 条数据")
        for mf in moneyflow_list:
            print(f"\n股票: {mf.name} ({mf.symbol})")
            print(f"交易日期: {mf.trade_date}")
            print(f"收盘价: {mf.close_price:.2f}")
            print(f"涨跌幅: {mf.change_pct:.2f}%")
            print(f"\n超大单:")
            print(f"  买入: {mf.super_large_buy} 手, {mf.super_large_buy_amount/10000:.2f} 万元")
            print(f"  卖出: {mf.super_large_sell} 手, {mf.super_large_sell_amount/10000:.2f} 万元")
            print(f"  净流入: {mf.super_large_net} 手, {mf.super_large_net_amount/10000:.2f} 万元")
            print(f"\n大单:")
            print(f"  买入: {mf.large_buy} 手, {mf.large_buy_amount/10000:.2f} 万元")
            print(f"  卖出: {mf.large_sell} 手, {mf.large_sell_amount/10000:.2f} 万元")
            print(f"  净流入: {mf.large_net} 手, {mf.large_net_amount/10000:.2f} 万元")
            print(f"\n主力净流入: {mf.main_net_amount/10000:.2f} 万元")
            print(f"总净流入: {mf.total_net_amount/10000:.2f} 万元")
    else:
        print(f"未获取到 {symbol} 的资金流向数据")
        print("可能原因:")
        print("1. 该日期不是交易日")
        print("2. Tushare API 没有该股票的数据")
        print("3. TUSHARE_TOKEN 环境变量未设置或无效")

    # 断开连接
    service.disconnect()
    print("\n测试完成")


if __name__ == "__main__":
    test_moneyflow()
