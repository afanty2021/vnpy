# -*- coding:utf-8 -*-
"""
港股通历史数据下载测试
测试通过正确的交易所信息能否下载港股通历史数据
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.object import HistoryRequest
from vnpy.trader.constant import Exchange, Interval
from vnpy_qmt import QmtGateway

QMT_SETTING = {
    "交易账号": "40218291",
    "mini路径": "D:/国金证券QMT交易端/userdata_mini/",
}

def main():
    print("=" * 70)
    print("港股通历史数据下载测试")
    print("=" * 70)

    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    main_engine.add_gateway(QmtGateway)

    print("\n连接QMT...")
    main_engine.connect(QMT_SETTING, "QMT")

    import time
    time.sleep(3)

    gateway = main_engine.get_gateway("QMT")
    if not gateway:
        print("ERROR: QMT网关未连接")
        return

    print("OK: QMT网关已连接\n")

    # 测试时间范围（最近3个月）
    end = datetime.now()
    start = end - timedelta(days=90)

    # 港股通测试股票（使用正确的交易所）
    hk_tests = [
        # 沪港通
        ("00700", Exchange.SHHK, "腾讯控股-沪港通"),
        ("09988", Exchange.SHHK, "阿里巴巴-沪港通"),

        # 深港通
        ("00700", Exchange.SZHK, "腾讯控股-深港通"),
        ("01810", Exchange.SZHK, "小米集团-深港通"),

        # 香港本地（非港股通）
        ("00700", Exchange.SEHK, "腾讯控股-香港本地"),
        ("00388", Exchange.SEHK, "港交所-香港本地"),

        # A股对比
        ("000001", Exchange.SZSE, "平安银行-A股"),
        ("600000", Exchange.SSE, "浦发银行-A股"),
    ]

    results = []

    for symbol, exchange, name in hk_tests:
        print(f"\n{'=' * 60}")
        print(f"测试: {name} ({symbol}.{exchange.value})")
        print(f"{'=' * 60}")

        try:
            req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                start=start,
                end=end,
                interval=Interval.DAILY
            )

            bars = main_engine.query_history(req, "QMT")

            if bars:
                print(f"[OK] 成功获取 {len(bars)} 条K线数据")
                if bars:
                    latest = bars[-1]
                    print(f"  最新数据: {latest.datetime}")
                    print(f"  收盘价: {latest.close_price}")
                    print(f"  成交量: {latest.volume}")
                results.append({
                    "name": name,
                    "symbol": f"{symbol}.{exchange.value}",
                    "count": len(bars),
                    "status": "成功"
                })
            else:
                print(f"[EMPTY] 未获取到数据")
                results.append({
                    "name": name,
                    "symbol": f"{symbol}.{exchange.value}",
                    "count": 0,
                    "status": "无数据"
                })

        except Exception as e:
            print(f"[ERROR] 下载失败: {e}")
            results.append({
                "name": name,
                "symbol": f"{symbol}.{exchange.value}",
                "count": 0,
                "status": f"错误: {str(e)[:40]}"
            })

    # 打印汇总结果
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    print(f"{'名称':<20} {'代码':<20} {'数据量':<10} {'状态':<15}")
    print("-" * 70)

    success_count = 0
    for r in results:
        print(f"{r['name']:<20} {r['symbol']:<20} {r['count']:<10} {r['status']:<15}")
        if r['count'] > 0:
            success_count += 1

    print("-" * 70)
    print(f"总计: {len(results)} 个测试，{success_count} 个成功")

    # 分析结果
    print("\n" + "=" * 70)
    print("结果分析")
    print("=" * 70)

    a股_success = any("A股" in r['name'] and r['count'] > 0 for r in results)
    sh_hk_success = any("沪港通" in r['name'] and r['count'] > 0 for r in results)
    sz_hk_success = any("深港通" in r['name'] and r['count'] > 0 for r in results)
    hk_local_success = any("香港本地" in r['name'] and r['count'] > 0 for r in results)

    print(f"A股历史数据下载:      {'✅ 支持' if a股_success else '❌ 不支持'}")
    print(f"港股通(沪)历史数据下载: {'✅ 支持' if sh_hk_success else '❌ 不支持'}")
    print(f"港股通(深)历史数据下载: {'✅ 支持' if sz_hk_success else '❌ 不支持'}")
    print(f"香港本地历史数据下载:   {'✅ 支持' if hk_local_success else '❌ 不支持'}")

    input("\n按Enter键退出...")
    main_engine.close()

if __name__ == "__main__":
    main()
