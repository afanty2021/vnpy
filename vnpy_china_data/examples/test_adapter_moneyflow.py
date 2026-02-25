"""
测试Tushare适配器资金流向数据获取
"""

import os
from datetime import date, timedelta
from vnpy_china_data.adapter import TushareDataAdapter


def test_adapter_moneyflow():
    """测试适配器资金流向数据获取"""
    # 获取Token
    token = os.getenv("TUSHARE_TOKEN", "")
    if not token:
        print("错误: TUSHARE_TOKEN 环境变量未设置")
        print("请设置环境变量: export TUSHARE_TOKEN=your_token")
        return

    print(f"Tushare Token: {token[:10]}...")

    # 创建适配器
    adapter = TushareDataAdapter(token=token)

    # 连接
    if not adapter.connect():
        print("适配器连接失败")
        return

    print("适配器已连接")

    # 测试获取资金流向数据
    today = date.today()
    test_date = today - timedelta(days=1)  # 昨天
    date_str = test_date.strftime("%Y%m%d")

    print(f"\n正在获取 000001.SZ 在 {date_str} 的资金流向数据...")

    moneyflow_list = adapter.get_moneyflow(
        ts_code="000001.SZ",
        trade_date=date_str
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
        print(f"未获取到数据")

    # 断开连接
    adapter.disconnect()
    print("\n测试完成")


if __name__ == "__main__":
    test_adapter_moneyflow()
