# -*- coding: utf-8 -*-
"""
验证 vnpy_qmt td.on_stock_asset 的 extra 赋值不再崩溃（资金空白的根因）。

根因：
    BaseData.extra 默认值是 None（vnpy/trader/object.py:26），
    td.py 在 on_stock_asset 中直接执行 account.extra["cash"] = ...，
    在 None 上做 item 赋值抛 TypeError，
    导致 self.gateway.on_account() 永远执行不到 ->
    服务端 accounts 字典为空 -> 客户端资金数据空白。
    持仓路径 on_stock_position 不涉及 extra，故正常显示。
"""
import sys
from pathlib import Path

# 确保用项目源码的 vnpy
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from vnpy_qmt.td import TD


class FakeAsset:
    """模拟 xtquant.xttype.XtAsset 的资产快照"""
    account_id = "12345678"
    frozen_cash = 1000.0
    total_asset = 100000.0
    cash = 90000.0          # 可用现金
    market_value = 9000.0


class FakeGateway:
    """记录 on_account 调用，替代真实 BaseGateway"""
    def __init__(self):
        self.gateway_name = "QMT"
        self.accounts = []

    def on_account(self, account):
        self.accounts.append(account)


def test_on_stock_asset_does_not_crash():
    gw = FakeGateway()
    td = TD(gw)

    # 修复前：下一行抛 TypeError: 'NoneType' object does not support item assignment
    td.on_stock_asset(FakeAsset())

    # 修复后：on_account 被调用一次
    assert len(gw.accounts) == 1, f"on_account 应被调用一次，实际 {len(gw.accounts)}"

    acc = gw.accounts[0]
    assert acc.accountid == "12345678", f"accountid 错误: {acc.accountid}"
    assert acc.balance == 100000.0, f"balance 错误: {acc.balance}"
    assert acc.frozen == 1000.0, f"frozen 错误: {acc.frozen}"

    # extra 被正确填充
    assert acc.extra is not None, "extra 不应为 None"
    assert acc.extra["cash"] == 90000.0, f"cash 错误: {acc.extra.get('cash')}"
    assert acc.extra["market_value"] == 9000.0, f"market_value 错误: {acc.extra.get('market_value')}"

    print("[PASS] on_stock_asset 正常，on_account 被调用，extra 填充正确")


if __name__ == "__main__":
    test_on_stock_asset_does_not_crash()
