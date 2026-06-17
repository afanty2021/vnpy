# -*- coding: utf-8 -*-
"""
验证 vnpy_qmt md.on_tick 填充 A 股增强字段到 tick.extra。

根因（行情表格成交额/量比/涨幅/分时均价空白）：
    TickMonitor headers 含 turnover/volume_ratio/change_pct/avg_price，
    但这些不是 TickData 原生属性，渲染走 _get_attr(__getattribute__) 取不到返回 ""。
    md.on_tick 既没计算也没写入 extra，导致客户端空白。

修复：md.on_tick 内计算4字段写入 tick.extra（RPC pickle 自动传输到客户端）。

实盘口径：
    成交额 turnover     = amount（xtdata tick 原生字段）
    涨幅 change_pct     = (last - pre_close) / pre_close * 100
    分时均价 avg_price  = amount / volume
    量比 volume_ratio   = (volume/已交易分钟) / (5日日均量/240)
"""
import sys
import datetime
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from vnpy.trader.constant import Exchange, Product
from vnpy.trader.object import TickData
from vnpy_qmt.md import MD


class FakeGateway:
    def __init__(self):
        self.gateway_name = "QMT"
        self.exchanges = (Exchange.SZSE,)
        self.TRADE_TYPE = (Product.EQUITY,)
        self.contracts = {}
        self.ticks = []

    def get_contract(self, vt_symbol):
        return self.contracts.get(vt_symbol)

    def on_tick(self, tick):
        self.ticks.append(tick)


def make_tick_dict(last_price=11.0, volume=10000, amount=11000000.0, last_close=10.0,
                   ts_ms=None):
    """构造 xtdata tick 推送字典。

    xtdata volume 单位为"手"(×100股)，amount 为元：10000手=100万股，
    11000000元 → 每股均价 11.0（与 last_price 一致）。
    ts_ms 默认本地 2024-06-03 10:30:00（已交易60分钟），动态生成以适配机器时区。
    """
    if ts_ms is None:
        ts_ms = int(datetime.datetime(2024, 6, 3, 10, 30).timestamp() * 1000)
    return {
        'lastPrice': last_price,
        'volume': volume,
        'amount': amount,
        'open': 10.5,
        'high': 11.2,
        'low': 10.3,
        'lastClose': last_close,
        'time': ts_ms,
        'askPrice': [11.0] * 5,
        'askVol': [100] * 5,
        'bidPrice': [10.99] * 5,
        'bidVol': [100] * 5,
    }


def test_trading_minutes():
    """交易分钟数计算（剔除午休）"""
    t = lambda h, m: datetime.datetime(2024, 6, 3, h, m).time()
    assert MD._trading_minutes(datetime.datetime(2024, 6, 3, 9, 30)) == 0
    assert MD._trading_minutes(datetime.datetime(2024, 6, 3, 10, 30)) == 60
    assert MD._trading_minutes(datetime.datetime(2024, 6, 3, 11, 30)) == 120
    assert MD._trading_minutes(datetime.datetime(2024, 6, 3, 12, 0)) == 120
    assert MD._trading_minutes(datetime.datetime(2024, 6, 3, 13, 0)) == 120
    assert MD._trading_minutes(datetime.datetime(2024, 6, 3, 14, 0)) == 180
    assert MD._trading_minutes(datetime.datetime(2024, 6, 3, 15, 0)) == 240
    print("[PASS] _trading_minutes 计算正确")


def test_tick_extra_fields():
    gw = FakeGateway()
    md = MD(gw)
    # mock 5日日均量 = 240000 股/日 → 日均每分钟 = 1000
    with patch.object(MD, '_get_avg_daily_vol', return_value=240000.0):
        md.on_tick({'000001.SZ': [make_tick_dict()]})

    assert len(gw.ticks) == 1
    tick = gw.ticks[0]

    # 成交额（TickData 原生字段，直接赋值，单位元）
    assert tick.turnover == 11000000.0, f"turnover: {tick.turnover}"
    assert tick.extra is not None, "extra 不应为 None"
    # 涨幅 (11-10)/10*100 = 10%
    assert abs(tick.extra['change_pct'] - 10.0) < 0.001, f"change_pct: {tick.extra.get('change_pct')}"
    # 分时均价 11000000元/(10000手×100股) = 11.0（xtdata volume 单位为手）
    assert abs(tick.extra['avg_price'] - 11.0) < 0.001, f"avg_price: {tick.extra.get('avg_price')}"
    # 量比 (10000/60)/(240000/240) = 166.67/1000 = 0.1667（今日量与日均量单位一致，抵消）
    assert abs(tick.extra['volume_ratio'] - 0.1667) < 0.01, f"volume_ratio: {tick.extra.get('volume_ratio')}"

    print("[PASS] tick 4字段填充正确:",
          f"成交额={tick.turnover}, 涨幅={tick.extra['change_pct']:.2f}%,",
          f"分时均价={tick.extra['avg_price']}, 量比={tick.extra['volume_ratio']:.4f}")


def test_change_pct_zero_pre_close():
    """pre_close=0 时涨幅不崩溃，返回0"""
    gw = FakeGateway()
    md = MD(gw)
    with patch.object(MD, '_get_avg_daily_vol', return_value=240000.0):
        md.on_tick({'000001.SZ': [make_tick_dict(last_close=0, volume=0, amount=0)]})
    tick = gw.ticks[0]
    assert tick.extra['change_pct'] == 0.0
    assert tick.extra['avg_price'] == 0.0  # volume=0 不除零
    print("[PASS] pre_close=0/volume=0 边界处理正确（不除零）")


def test_get_attr_fallback_extra():
    """BaseMonitor._get_attr 应在原生属性缺失时 fallback 到 data.extra。

    TickMonitor 的 turnover/volume_ratio/change_pct/avg_price 不是 TickData 原生属性，
    通过 extra 传输；_get_attr 必须能从 extra 取到，否则渲染空白。
    """
    from vnpy.trader.ui.widget import BaseMonitor
    from vnpy.trader.constant import Exchange

    tick = TickData(
        gateway_name="QMT", symbol="000001", exchange=Exchange.SZSE,
        datetime=datetime.datetime(2024, 6, 3, 10, 30), last_price=11.0,
    )
    # turnover 是原生字段（直接赋值）；change_pct/volume_ratio/avg_price 非原生，走 extra
    tick.turnover = 100000.0
    tick.extra = {"change_pct": 5.0, "volume_ratio": 1.2}

    class FakeSelf:
        pass

    # 原生属性优先（turnover/last_price）
    assert BaseMonitor._get_attr(FakeSelf(), tick, "last_price", "") == 11.0
    assert BaseMonitor._get_attr(FakeSelf(), tick, "turnover", "") == 100000.0
    # 非原生属性 fallback 到 extra
    assert BaseMonitor._get_attr(FakeSelf(), tick, "change_pct", "") == 5.0
    assert BaseMonitor._get_attr(FakeSelf(), tick, "volume_ratio", "") == 1.2
    # 都没有返回 default
    assert BaseMonitor._get_attr(FakeSelf(), tick, "not_exist", "N/A") == "N/A"
    print("[PASS] _get_attr 原生属性优先 + extra fallback 正确")


def test_avg_daily_vol_cache_within_same_day():
    """同一交易日内，_get_avg_daily_vol 首次取数后缓存，第二次不重复查 xtdata。"""
    import pandas as pd
    gw = FakeGateway()
    md = MD(gw)
    df = pd.DataFrame({"time": [1, 2, 3, 4, 5], "volume": [240000] * 5})

    def fake_get_local_data(**kwargs):
        return {c: df for c in kwargs.get("stock_list", [])}

    with patch("xtquant.xtdata.get_local_data", side_effect=fake_get_local_data) as m:
        dt = datetime.datetime(2024, 6, 3, 10, 0)
        v1 = md._get_avg_daily_vol("000001", Exchange.SZSE, "000001.SZSE", dt)
        v2 = md._get_avg_daily_vol("000001", Exchange.SZSE, "000001.SZSE", dt)
    assert v1 == 240000.0 and v2 == 240000.0
    assert m.call_count == 1, f"同一交易日应只取数一次，实际 {m.call_count} 次"
    print("[PASS] 同交易日缓存复用，xtdata 仅查询 1 次")


def test_avg_daily_vol_cache_invalidates_next_day():
    """跨交易日缓存失效：clear 后重新取数（5日均量次日纳入新交易日数据）。"""
    import pandas as pd
    gw = FakeGateway()
    md = MD(gw)
    df = pd.DataFrame({"time": [1], "volume": [240000]})

    def fake_get_local_data(**kwargs):
        return {c: df for c in kwargs.get("stock_list", [])}

    with patch("xtquant.xtdata.get_local_data", side_effect=fake_get_local_data) as m:
        dt1 = datetime.datetime(2024, 6, 3, 10, 0)
        v1 = md._get_avg_daily_vol("000001", Exchange.SZSE, "000001.SZSE", dt1)
        dt2 = datetime.datetime(2024, 6, 4, 10, 0)
        v2 = md._get_avg_daily_vol("000001", Exchange.SZSE, "000001.SZSE", dt2)
    assert v1 == 240000.0 and v2 == 240000.0
    assert m.call_count == 2, f"跨交易日应重新取数，实际 {m.call_count} 次"
    assert md._avg_daily_vol_date == dt2.date(), "缓存日期应更新为次日"
    print("[PASS] 跨交易日缓存失效，重新取数")


if __name__ == "__main__":
    test_trading_minutes()
    test_tick_extra_fields()
    test_change_pct_zero_pre_close()
    test_get_attr_fallback_extra()
    test_avg_daily_vol_cache_within_same_day()
    test_avg_daily_vol_cache_invalidates_next_day()
    print("\n全部通过")
