# -*- coding:utf-8 -*-
"""单元测试：td.on_stock_trade 的 vt_tradeid 去重逻辑。

实盘收盘后 query_stock_trades 返回空，无法实测去重；用 mock 构造相同成交
重复调用 on_stock_trade，验证周期 query_trade 不会重复推送。

用法：python examples/client_server/test_td_trade_dedup.py
"""
import sys
from pathlib import Path
from types import SimpleNamespace

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from vnpy.trader.constant import Direction, Exchange, Status, OrderType, Offset
from vnpy.trader.object import OrderData
from vnpy_qmt.td import TD
from vnpy_qmt.utils import From_VN_Trade_Type, From_VN_Exchange_map


class FakeGateway:
    """记录 on_trade 调用次数（替代真实 QmtGateway）。"""
    def __init__(self):
        self.gateway_name = "QMT"
        self.trades = []

    def on_trade(self, trade):
        self.trades.append(trade)

    def on_order(self, order):
        pass

    def get_contract(self, vt_symbol):
        return None

    def write_log(self, msg):
        pass


def build_trade(stock_code, order_remark, traded_id, price, volume, order_type, traded_time):
    """构造模拟 XtTrade（鸭子类型，SimpleNamespace 提供所需属性）。"""
    return SimpleNamespace(
        stock_code=stock_code,
        order_remark=order_remark,
        order_id="ORD1",
        traded_id=traded_id,
        traded_price=price,
        traded_time=traded_time,
        traded_volume=volume,
        order_type=order_type,
    )


def main():
    gw = FakeGateway()
    td = TD(gw)
    td.inited = True

    # 预置 order（on_stock_trade 要求 self.orders[vn_oid] 存在）
    vn_oid = "163700#1"
    td.orders[vn_oid] = OrderData(
        gateway_name="QMT", symbol="600000", exchange=Exchange.SSE,
        orderid=vn_oid, type=OrderType.LIMIT, direction=Direction.LONG,
        offset=Offset.NONE, volume=300, price=10.5, status=Status.ALLTRADED,
    )

    buy_type = From_VN_Trade_Type[Direction.LONG]      # xtconstant.STOCK_BUY
    suffix = From_VN_Exchange_map[Exchange.SSE]         # 'SH'
    code = f"600000.{suffix}"

    # 两笔不同成交（不同 traded_id）
    trade_a = build_trade(code, vn_oid, "T001", 10.48, 100, buy_type, 1718000000)
    trade_b = build_trade(code, vn_oid, "T002", 10.49, 100, buy_type, 1718000001)

    failures = []

    # 1) 首笔成交：应推送 + 缓存
    td.on_stock_trade(trade_a)
    if len(gw.trades) != 1 or len(td.traders) != 1:
        failures.append(f"[1] 首笔应推送1次/缓存1条，实际 on_trade={len(gw.trades)} traders={len(td.traders)}")
    else:
        print(f"[OK] 首笔成交已推送并缓存 (traders={len(td.traders)})")

    # 2) 重复同一成交（模拟周期 query_trade 再次返回）：应被去重
    td.on_stock_trade(trade_a)
    if len(gw.trades) != 1:
        failures.append(f"[2] 重复成交应去重，实际 on_trade={len(gw.trades)}（预期1）")
    else:
        print(f"[OK] 重复成交已去重 (on_trade 仍={len(gw.trades)})")

    # 3) 新成交（不同 traded_id）：应正常推送
    td.on_stock_trade(trade_b)
    if len(gw.trades) != 2 or len(td.traders) != 2:
        failures.append(f"[3] 新成交应推送，实际 on_trade={len(gw.trades)} traders={len(td.traders)}")
    else:
        print(f"[OK] 新成交已推送 (traders={len(td.traders)})")

    # 4) 再次重复两笔：均应被去重
    td.on_stock_trade(trade_a)
    td.on_stock_trade(trade_b)
    if len(gw.trades) != 2:
        failures.append(f"[4] 批量重复应全去重，实际 on_trade={len(gw.trades)}（预期2）")
    else:
        print(f"[OK] 批量重复全部去重 (on_trade 仍={len(gw.trades)})")

    print("\n" + "=" * 50)
    if failures:
        print("[FAIL] 去重逻辑存在问题：")
        for f in failures:
            print("  " + f)
        sys.exit(1)
    else:
        print("[PASS] 去重逻辑验证通过：周期 query_trade 不会重复推送")
    print("=" * 50)


if __name__ == "__main__":
    main()
