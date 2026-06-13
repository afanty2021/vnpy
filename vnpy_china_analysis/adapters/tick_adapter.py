"""TickData 适配器

将 vnpy TickData（Level1）转换为模块内部 TickFlowData。
Level1 无主动方向、QMT 不填 last_volume，故需：
1. 成交量：优先 last_volume，fallback 到累计 volume 差分
2. 方向：成交价 vs 最优买卖盘推断（内外盘法）
"""

from typing import Dict

from vnpy.trader.object import TickData

from ..objects.types import TickFlowData


def tick_to_flow(
    tick: TickData,
    last_price: Dict[str, float],
    last_dir: Dict[str, str],
    last_volume: Dict[str, int]
) -> TickFlowData:
    """TickData → TickFlowData（Level1 推断）

    Args:
        tick: vnpy TickData
        last_price: 各 symbol 上一笔价格（趋势兜底用，外部维护）
        last_dir: 各 symbol 上一笔方向（持平沿用用，外部维护）
        last_volume: 各 symbol 上一笔累计成交量（差分用，外部维护）

    Returns:
        TickFlowData（volume 为本笔成交量，direction 为推断的主动方向）
    """
    symbol = tick.symbol
    price = tick.last_price

    # 1. 成交量：优先 last_volume，fallback 到累计 volume 差分
    #    QMT gateway 只填累计 volume、不填 last_volume，故差分是主路径
    prev_vol = last_volume.get(symbol, 0)
    cur_vol = int(tick.volume or 0)
    if tick.last_volume and tick.last_volume > 0:
        trade_vol = int(tick.last_volume)
    else:
        trade_vol = cur_vol - prev_vol if cur_vol > prev_vol else 0
    last_volume[symbol] = cur_vol

    # 2. 方向：成交价 vs 最优买卖盘（内外盘法）
    if tick.ask_price_1 > 0 and price >= tick.ask_price_1:
        direction = "buy"          # 吃掉卖一 → 主动买
    elif tick.bid_price_1 > 0 and price <= tick.bid_price_1:
        direction = "sell"         # 砸给买一 → 主动卖
    else:
        prev = last_price.get(symbol)         # 盘口间成交：趋势兜底
        if prev is None or price == prev:
            direction = last_dir.get(symbol, "buy")   # 持平沿用
        else:
            direction = "buy" if price > prev else "sell"

    last_price[symbol] = price
    last_dir[symbol] = direction

    return TickFlowData(
        symbol=symbol,
        datetime=tick.datetime,
        price=price,
        volume=trade_vol,
        amount=price * trade_vol,
        direction=direction,
        function_code=0
    )
