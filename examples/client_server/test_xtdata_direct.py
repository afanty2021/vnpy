# -*- coding:utf-8 -*-
"""
QMT历史数据下载测试 - 详细调试版
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 直接测试 xtquant
import xtquant.xtdata as xtdata

def test_xtdata_direct():
    """直接测试 xtquant 的历史数据下载"""
    print("=" * 60)
    print("xtquant.xtdata 直接测试")
    print("=" * 60)

    # 测试股票
    symbol = "000001.SZ"
    period = '1d'
    start_time = '20240101'
    end_time = '20240201'

    print(f"\n1. 测试 download_history_data2")
    print(f"股票: {symbol}, 周期: {period}, 时间: {start_time} - {end_time}")

    try:
        result = xtdata.download_history_data2(
            stock_list=[symbol],
            period=period,
            start_time=start_time,
            end_time=end_time
        )
        print(f"   download_history_data2 返回: {result}")
    except Exception as e:
        print(f"   download_history_data2 异常: {e}")

    # 等待下载完成
    import time
    print("\n等待5秒让下载完成...")
    time.sleep(5)

    print(f"\n2. 测试 get_market_data_ex")
    try:
        data = xtdata.get_market_data_ex(
            stock_list=[symbol],
            period=period,
            start_time=start_time,
            end_time=end_time,
            dividend_type='front'
        )
        print(f"   get_market_data_ex 返回类型: {type(data)}")
        if data:
            print(f"   数据键: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
            if isinstance(data, dict) and symbol in data:
                bars = data[symbol]
                print(f"   {symbol} 数据量: {len(bars) if bars else 0}")
                if bars:
                    print(f"   最新数据: {bars[-1]}")
        else:
            print("   返回空数据")
    except Exception as e:
        print(f"   get_market_data_ex 异常: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n3. 测试 get_local_data")
    try:
        data = xtdata.get_local_data(
            field_list=['time', 'open', 'high', 'low', 'close', 'volume'],
            stock_list=[symbol],
            period=period,
            start_time=start_time,
            end_time=end_time
        )
        print(f"   get_local_data 返回类型: {type(data)}")
        if data is not None:
            print(f"   数据形状: {data.shape if hasattr(data, 'shape') else 'N/A'}")
            print(f"   数据预览:\n{data}")
        else:
            print("   返回 None")
    except Exception as e:
        print(f"   get_local_data 异常: {e}")

if __name__ == "__main__":
    test_xtdata_direct()
