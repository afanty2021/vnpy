# -*- coding:utf-8 -*-
"""
QMT历史数据下载测试 - 简化版
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
    print("QMT历史数据测试")
    print("-" * 50)

    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    main_engine.add_gateway(QmtGateway)

    print("连接QMT...")
    main_engine.connect(QMT_SETTING, "QMT")

    import time
    time.sleep(3)

    gateway = main_engine.get_gateway("QMT")
    if not gateway:
        print("ERROR: QMT网关未连接")
        return

    print("OK: QMT已连接\n")

    # 测试A股
    end = datetime.now()
    start = end - timedelta(days=30)

    tests = [
        ("000001", Exchange.SZSE, "PingAn"),
        ("600000", Exchange.SSE, "Pufa"),
        ("00700", Exchange.SSE, "Tencent-HK"),
    ]

    results = []
    for symbol, exchange, name in tests:
        req = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            start=start,
            end=end,
            interval=Interval.DAILY
        )

        try:
            bars = main_engine.query_history(req, "QMT")
            count = len(bars) if bars else 0
            status = "OK" if count > 0 else "EMPTY"
            results.append((name, symbol, count, status))
            print(f"{status}: {name} ({symbol}) - {count} bars")
        except Exception as e:
            results.append((name, symbol, 0, f"ERROR: {str(e)[:30]}"))
            print(f"ERROR: {name} ({symbol}) - {e}")

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for name, symbol, count, status in results:
        print(f"{name:15} {symbol:10} {count:5} {status}")

    input("\nPress Enter to exit...")
    main_engine.close()

if __name__ == "__main__":
    main()
