# -*- coding:utf-8 -*-
"""
诊断脚本：检查 XtAsset 对象的所有字段

在 Windows 服务端运行此脚本，查看账户数据的实际字段名。
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from xtquant.xttype import XtAsset
from xtquant.xttrader import XtQuantTrader, StockAccount


def diagnose_asset_fields():
    """诊断 XtAsset 字段"""
    print("=" * 60)
    print("诊断 XtAsset 对象字段")
    print("=" * 60)

    # 配置
    account_id = "40218291"  # 请修改为你的账号
    mini_path = r"D:/国金证券QMT交易端/userdata_mini/"  # 请修改为你的路径

    # 创建交易对象
    session_id = 123456
    account = StockAccount(account_id)
    trader = XtQuantTrader(path=mini_path, session=session_id)

    # 注册回调
    class AssetCallback:
        def on_stock_asset(self, asset: XtAsset):
            print("\n" + "=" * 60)
            print("XtAsset 对象所有属性:")
            print("=" * 60)

            # 方法1: 使用 dir() 查看所有属性
            attrs = [attr for attr in dir(asset) if not attr.startswith('_')]
            print(f"\n通过 dir() 找到的属性 ({len(attrs)} 个):")
            for attr in sorted(attrs):
                try:
                    value = getattr(asset, attr)
                    if not callable(value):
                        print(f"  {attr}: {value}")
                except Exception as e:
                    print(f"  {attr}: (无法获取: {e})")

            # 方法2: 使用 __dict__ 查看实例变量
            if hasattr(asset, '__dict__'):
                print(f"\n通过 __dict__ 找到的属性:")
                for key, value in asset.__dict__.items():
                    print(f"  {key}: {value}")

            # 方法3: 检查常见字段名
            print(f"\n检查常见的资金字段:")
            common_fields = [
                'cash', 'available_cash', 'buying_power', 'total_asset',
                'frozen_cash', 'market_value', 'account_id', 'balance'
            ]
            for field in common_fields:
                if hasattr(asset, field):
                    value = getattr(asset, field)
                    print(f"  ✓ {field}: {value}")
                else:
                    print(f"  ✗ {field}: (不存在)")

            print("\n" + "=" * 60)

            # 停止交易对象
            trader.stop()
            sys.exit(0)

    callback = AssetCallback()
    trader.register_callback(callback)

    # 连接并查询
    print(f"\n连接 QMT...")
    print(f"  账号: {account_id}")
    print(f"  路径: {mini_path}")

    trader.start()
    cnn_msg = trader.connect()
    if cnn_msg != 0:
        print(f"连接失败: {cnn_msg}")
        return False

    print("连接成功，订阅账户...")
    sub_msg = trader.subscribe(account=account)
    if sub_msg != 0:
        print(f"订阅失败: {sub_msg}")
        return False

    print("查询账户资产...")
    trader.query_stock_asset_async(account=account, callback=callback)

    # 等待回调
    import time
    print("等待数据返回（最多30秒）...")
    for i in range(30):
        time.sleep(1)
        print(f".", end="", flush=True)

    print("\n未收到数据，请检查 QMT 是否正常运行")


if __name__ == "__main__":
    diagnose_asset_fields()
