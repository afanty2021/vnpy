# -*- coding:utf-8 -*-
"""验证：新部署的 td.py/qmt_gateway.py 周期成交查询 + vt_tradeid 去重。

直连 MiniQMT（新 session，只读查询，绝不下单），执行两次 query_trade：
  第1次：应查到当日成交并缓存到 td.traders
  第2次：应全部命中去重，0 新增（证明周期查询不会重复推送）

用法：python examples/client_server/verify_periodic_trade_query.py
"""
import sys
import time
import contextlib
import io
from pathlib import Path

import yaml

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.event import EVENT_TRADE
from vnpy_qmt import QmtGateway


# 直接读 qmt_gateway.yaml（与 run_qmt_server_full.py 同源）
cfg_path = project_root / ".vntrader_china/config/qmt_gateway.yaml"
with open(cfg_path, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

QMT_SETTING = {
    "交易账号": str(cfg["qmt"]["account_id"]),
    "mini路径": cfg["qmt"]["mini_path"],
}


def main():
    ee = EventEngine()
    me = MainEngine(ee)
    gw = me.add_gateway(QmtGateway, "QMT")

    # 收集成交事件（on_trade → EVENT_TRADE）
    received = []

    def on_trade(event):
        received.append(event.data)

    ee.register(EVENT_TRADE, on_trade)

    print(f"连接 MiniQMT: 账号 {QMT_SETTING['交易账号']}")
    print(f"             路径 {QMT_SETTING['mini路径']}")

    # 连接期间屏蔽 stdout：md 加载合约时对每个期货合约 print 警告（数千条 .SF），
    # 不屏蔽会刷屏。合约加载是同步的，connect 返回即完成。
    with contextlib.redirect_stdout(io.StringIO()):
        me.connect(QMT_SETTING, "QMT")
        for _ in range(30):
            if gw.td.inited:
                break
            time.sleep(0.5)
        time.sleep(3)  # 额外等合约加载/订阅回调沉淀

    if not gw.td.inited:
        print("\n[FAIL] QMT 未初始化成功（检查 MiniQMT 是否在线、账号/路径是否正确）")
        me.close()
        ee.stop()
        sys.exit(1)

    print("[OK] QMT 已连接\n")

    # ---- 第1次 query_trade ----
    print("【第1次 query_trade】")
    received.clear()
    gw.query_trade()
    time.sleep(3)  # 等异步回调
    first = len(received)
    print(f"  收到成交: {first} 笔")
    print(f"  td.traders 缓存: {len(gw.td.traders)} 笔")
    for t in received[:5]:
        print(f"    {t.symbol} {t.direction.name} {t.volume}@{t.price} vt_tradeid={t.vt_tradeid}")

    # ---- 第2次 query_trade（应命中去重）----
    print("\n【第2次 query_trade】（应命中去重，0 新增）")
    received.clear()
    gw.query_trade()
    time.sleep(3)
    second = len(received)
    print(f"  收到成交: {second} 笔")

    # ---- 结论 ----
    print("\n" + "=" * 55)
    if first > 0 and second == 0:
        print(f"[OK] 验证通过：第1次 {first} 笔，第2次 {second} 笔")
        print("  周期 query_trade 能查到成交，且去重生效不重复推送")
    elif first == 0:
        print("[WARN] 当日 query 未返回成交（MiniQMT 收盘后未吐当日数据）")
        print("  patches 已部署；去重逻辑在交易时段有成交时可复测")
    else:
        print(f"[WARN] 第2次收到 {second} 笔（预期 0）—— 期间可能有新成交或去重异常")
    print("=" * 55)

    me.close()
    ee.stop()


if __name__ == "__main__":
    main()
