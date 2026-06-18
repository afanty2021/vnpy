# -*- coding:utf-8 -*-
"""诊断：客户端视角下，服务端缓存里到底有没有委托/成交。

用法（收盘后客户端看不到数据时运行）：
    conda run -n quant-3.11 python examples/client_server/diag_rpc_snapshot.py

原理：复用 RpcGateway.connect 的 query_all 路径，直接打印服务端
main_engine.orders / trades 缓存的数量。若返回 0，则根因确认在服务端
（xtquant 收盘后未返回当日数据），而非客户端显示逻辑。
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_rpcservice.rpc_gateway import RpcGateway

from vnpy_china_config import ConfigManager


def load_rpc_config() -> dict:
    ConfigManager.reset_instance()
    config_dir = project_root / ".vntrader_china/config"
    cm = ConfigManager()
    cm.set_config_path(config_dir)
    config = cm.load_config(force_reload=True)
    return {
        "主动请求地址": config.rpc.rep_address,
        "推送订阅地址": config.rpc.pub_address,
    }


def main():
    setting = load_rpc_config()
    print(f"连接服务端: {setting['主动请求地址']}")

    ee = EventEngine()
    me = MainEngine(ee)
    me.add_gateway(RpcGateway, "RPC")
    me.connect(setting, "RPC")

    # 等 query_all 完成（RpcGateway.connect 内同步调用）
    import time
    time.sleep(1)

    contracts = me.get_all_contracts()
    orders = me.get_all_orders()
    trades = me.get_all_trades()
    positions = me.get_all_positions()
    accounts = me.get_all_accounts()

    print("\n" + "=" * 50)
    print("服务端缓存快照（客户端视角）:")
    print("=" * 50)
    print(f"  合约 contracts : {len(contracts)}")
    print(f"  账户 accounts  : {len(accounts)}")
    print(f"  持仓 positions : {len(positions)}")
    print(f"  委托 orders    : {len(orders)}")
    print(f"  成交 trades    : {len(trades)}")
    print("=" * 50)

    if orders:
        print("\n委托样例(前3条):")
        for o in orders[:3]:
            print(f"  {o.symbol} {o.direction} {o.volume}@{o.price} {o.status}")
    if trades:
        print("\n成交样例(前3条):")
        for t in trades[:3]:
            print(f"  {t.symbol} {t.direction} {t.volume}@{t.price}")

    me.close()
    ee.stop()

    if not orders and not trades:
        print("\n⚠ 委托/成交均为 0 —— 根因在服务端：xtquant 在当前时段未返回当日委托/成交。")
        print("  请确认: 服务端是否收盘后重启过? MiniQMT 是否仍在线?")
    else:
        print("\n✓ 服务端缓存有数据 —— 若界面仍不显示，则查客户端显示逻辑。")


if __name__ == "__main__":
    main()
