# -*- coding:utf-8 -*-
"""
QMT历史数据下载测试脚本

测试QMT接口是否支持：
1. A股历史数据下载
2. 港股通历史数据下载
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

# QMT配置
QMT_SETTING = {
    "交易账号": "40218291",
    "mini路径": "D:/国金证券QMT交易端/userdata_mini/",
}


def test_download_history():
    """测试历史数据下载"""
    print("=" * 60)
    print("QMT历史数据下载测试")
    print("=" * 60)

    # 创建引擎
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)

    # 添加QMT网关
    main_engine.add_gateway(QmtGateway)

    # 连接QMT
    print("\n连接QMT...")
    main_engine.connect(QMT_SETTING, "QMT")
    print(f"  账号: {QMT_SETTING['交易账号']}")

    # 等待连接
    import time
    print("\n等待连接建立...")
    time.sleep(3)

    # 检查网关状态
    gateway = main_engine.get_gateway("QMT")
    if gateway:
        print(f"\n[OK] QMT网关已连接")
    else:
        print("\n[ERROR] QMT网关未连接")
        return

    # 测试股票列表
    test_symbols = [
        # A股测试
        ("000001", Exchange.SZSE, "平安银行"),
        ("600000", Exchange.SSE, "浦发银行"),
        # 港股通测试 (港股代码格式)
        ("00700", Exchange.SSE, "腾讯控股(沪港通)"),
        ("00700", Exchange.SZSE, "腾讯控股(深港通)"),
        ("09988", Exchange.SSE, "阿里巴巴(沪港通)"),
    ]

    print("\n" + "=" * 60)
    print("开始测试历史数据下载")
    print("=" * 60)

    # 设置查询时间范围（最近3个月）
    end = datetime.now()
    start = end - timedelta(days=90)

    results = []

    for symbol, exchange, name in test_symbols:
        print(f"\n{'=' * 50}")
        print(f"测试: {name} ({symbol}.{exchange.value})")
        print(f"{'=' * 50}")

        try:
            # 构造查询请求
            req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                start=start,
                end=end,
                interval=Interval.DAILY
            )

            # 调用query_history
            bars = main_engine.query_history(req, "QMT")

            if bars:
                print(f"[OK] 成功获取 {len(bars)} 条K线数据")
                if bars:
                    latest = bars[-1]
                    print(f"  最新数据: {latest.datetime}, 收盘价: {latest.close_price}")
                results.append({
                    "symbol": symbol,
                    "exchange": exchange.value,
                    "name": name,
                    "count": len(bars),
                    "status": "成功"
                })
            else:
                print(f"[WARN] 未获取到数据")
                results.append({
                    "symbol": symbol,
                    "exchange": exchange.value,
                    "name": name,
                    "count": 0,
                    "status": "无数据"
                })

        except Exception as e:
            print(f"[ERROR] 下载失败: {e}")
            results.append({
                "symbol": symbol,
                "exchange": exchange.value,
                "name": name,
                "count": 0,
                "status": f"错误: {str(e)[:30]}"
            })

    # 打印汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"{'股票代码':<12} {'交易所':<8} {'名称':<20} {'数据量':<10} {'状态':<15}")
    print("-" * 70)

    success_count = 0
    for r in results:
        print(f"{r['symbol']:<12} {r['exchange']:<8} {r['name']:<20} {r['count']:<10} {r['status']:<15}")
        if r['count'] > 0:
            success_count += 1

    print("-" * 70)
    print(f"总计: {len(results)} 只股票，{success_count} 只有数据")

    # 分析结果
    print("\n" + "=" * 60)
    print("结果分析")
    print("=" * 60)

    a股_success = any(r['count'] > 0 for r in results if r['exchange'] in ['SSE', 'SZSE'] and '港股通' not in r['name'])
    hk_success = any(r['count'] > 0 for r in results if '港股通' in r['name'])

    if a股_success:
        print("[OK] A股历史数据下载: 支持")
    else:
        print("[FAIL] A股历史数据下载: 不支持或无数据")

    if hk_success:
        print("[OK] 港股通历史数据下载: 支持")
    else:
        print("[FAIL] 港股通历史数据下载: 不支持或无数据")

    # 关闭
    print("\n按Enter键退出...")
    input()
    main_engine.close()


if __name__ == "__main__":
    try:
        test_download_history()
    except KeyboardInterrupt:
        print("\n测试已中断")
    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()
