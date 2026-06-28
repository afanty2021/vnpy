# -*- coding: utf-8 -*-
"""
直接测试 xtquant API

账号/路径从环境变量读取，避免把真实资金账号写入仓库：
    export QMT_ACCOUNT_ID=xxxxx
    export QMT_MINI_PATH='D:/xxx/userdata_mini/'
"""

import os
import sys
from pathlib import Path

# 添加补丁路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "patches"))

# 配置（从环境变量读取，缺失则提示并退出，杜绝硬编码账号）
account_id = os.getenv("QMT_ACCOUNT_ID", "")
mini_path = os.getenv("QMT_MINI_PATH", "")
if not account_id or not mini_path:
    print("请先设置环境变量 QMT_ACCOUNT_ID 与 QMT_MINI_PATH")
    sys.exit(1)

from xtquant.xttrader import XtQuantTrader
from xtquant.xttype import StockAccount
import time

print("=" * 60)
print("直接测试 xtquant API")
print("=" * 60)

session_id = 999999
account = StockAccount(account_id)
trader = XtQuantTrader(path=mini_path, session=session_id)

print("\n启动交易线程...")
trader.start()

print("连接 QMT...")
cnn_msg = trader.connect()
print(f"连接结果: {cnn_msg}")

print("订阅账户...")
sub_msg = trader.subscribe(account=account)
print(f"订阅结果: {sub_msg}")

# 尝试同步查询
print("\n尝试同步查询账户资产...")
try:
    # 尝试同步方法
    asset = trader.query_stock_asset(account)
    print(f"同步查询结果: {asset}")
    if asset:
        print(f"  账户ID: {asset.account_id}")
        print(f"  总资产: {asset.total_asset}")
        print(f"  可用现金: {asset.cash}")
        print(f"  冻结资金: {asset.frozen_cash}")
except Exception as e:
    print(f"同步查询失败: {e}")

# 等待一下看看异步回调是否触发
print("\n等待 5 秒...")
time.sleep(5)

print("\n测试完成")
trader.stop()
