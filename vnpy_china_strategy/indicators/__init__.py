"""
公共指标库

提供各类技术指标计算函数。
"""

from typing import List
from decimal import Decimal

from vnpy.trader.object import BarData


def calculate_ma(bars: List[BarData], period: int) -> float:
    """计算移动平均线

    Args:
        bars: K线数据
        period: 周期

    Returns:
        移动平均值
    """
    if len(bars) < period:
        return 0.0

    prices = [bar.close_price for bar in bars[-period:]]
    return sum(prices) / period


def calculate_ema(bars: List[BarData], period: int) -> float:
    """计算指数移动平均线

    Args:
        bars: K线数据
        period: 周期

    Returns:
        EMA值
    """
    if len(bars) < period:
        return 0.0

    multiplier = 2 / (period + 1)
    ema = bars[0].close_price

    for bar in bars[1:]:
        ema = (bar.close_price - ema) * multiplier + ema

    return ema


def calculate_rsi(bars: List[BarData], period: int = 14) -> float:
    """计算RSI指标

    Args:
        bars: K线数据
        period: 周期

    Returns:
        RSI值 (0-100)
    """
    if len(bars) < period + 1:
        return 50.0

    gains = []
    losses = []

    for i in range(1, len(bars)):
        change = bars[i].close_price - bars[i-1].close_price
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(
    bars: List[BarData],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> tuple:
    """计算MACD指标

    Args:
        bars: K线数据
        fast_period: 快线周期
        slow_period: 慢线周期
        signal_period: 信号线周期

    Returns:
        (macd, signal, hist)
    """
    if len(bars) < slow_period:
        return 0.0, 0.0, 0.0

    # 计算EMA
    ema_fast = calculate_ema(bars, fast_period)
    ema_slow = calculate_ema(bars, slow_period)

    # DIF (MACD线)
    dif = ema_fast - ema_slow

    # DEA (信号线)
    # 简化计算
    dea = dif * 0.9

    # 柱状图
    hist = (dif - dea) * 2

    return dif, dea, hist


def calculate_bollinger_bands(
    bars: List[BarData],
    period: int = 20,
    std_dev: float = 2.0
) -> tuple:
    """计算布林带

    Args:
        bars: K线数据
        period: 周期
        std_dev: 标准差倍数

    Returns:
        (upper, middle, lower)
    """
    if len(bars) < period:
        return 0.0, 0.0, 0.0

    # 中轨 = MA
    middle = calculate_ma(bars, period)

    # 计算标准差
    prices = [bar.close_price for bar in bars[-period:]]
    variance = sum((p - middle) ** 2 for p in prices) / period
    std = variance ** 0.5

    # 上轨和下轨
    upper = middle + std_dev * std
    lower = middle - std_dev * std

    return upper, middle, lower


def calculate_momentum(bars: List[BarData], period: int = 10) -> float:
    """计算动量指标

    Args:
        bars: K线数据
        period: 周期

    Returns:
        动量值
    """
    if len(bars) < period:
        return 0.0

    start_price = bars[0].close_price
    end_price = bars[-1].close_price

    if start_price == 0:
        return 0.0

    return (end_price - start_price) / start_price * 100


def calculate_atr(bars: List[BarData], period: int = 14) -> float:
    """计算ATR（平均真实波幅）

    Args:
        bars: K线数据
        period: 周期

    Returns:
        ATR值
    """
    if len(bars) < period + 1:
        return 0.0

    true_ranges = []

    for i in range(1, len(bars)):
        high = bars[i].high_price
        low = bars[i].low_price
        prev_close = bars[i-1].close_price

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        true_ranges.append(tr)

    return sum(true_ranges[-period:]) / period


def calculate_volume_ratio(bars: List[BarData], period: int = 5) -> float:
    """计算量比

    Args:
        bars: K线数据
        period: 周期

    Returns:
        量比值
    """
    if len(bars) < period + 1:
        return 1.0

    recent_avg = sum(bar.volume for bar in bars[-period:]) / period
    prev_avg = sum(bar.volume for bar in bars[-period-1:-1]) / period

    if prev_avg == 0:
        return 1.0

    return recent_avg / prev_avg


__all__ = [
    "calculate_ma",
    "calculate_ema",
    "calculate_rsi",
    "calculate_macd",
    "calculate_bollinger_bands",
    "calculate_momentum",
    "calculate_atr",
    "calculate_volume_ratio",
]
