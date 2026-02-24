"""
辅助工具函数

提供常用的辅助函数。
"""

from typing import Optional
from datetime import datetime, time


def format_money(amount: float, currency: str = "CNY") -> str:
    """格式化金额显示

    Args:
        amount: 金额
        currency: 货币类型

    Returns:
        格式化后的字符串
    """
    if currency == "CNY":
        if amount >= 100000000:
            return f"{amount / 100000000:.2f}亿"
        elif amount >= 10000:
            return f"{amount / 10000:.2f}万"
        else:
            return f"{amount:.2f}"
    return f"{amount:.2f}"


def format_volume(volume: int) -> str:
    """格式化成交量显示

    Args:
        volume: 成交量

    Returns:
        格式化后的字符串
    """
    if volume >= 100000000:
        return f"{volume / 100000000:.2f}亿"
    elif volume >= 10000:
        return f"{volume / 10000:.2f}万"
    else:
        return f"{volume}"


def calculate_change_pct(current: float, previous: float) -> float:
    """计算涨跌幅

    Args:
        current: 当前价格
        previous: 前期价格

    Returns:
        涨跌幅百分比
    """
    if previous == 0:
        return 0.0
    return (current - previous) / previous * 100


def get_trading_status(dt: Optional[datetime] = None) -> str:
    """获取交易状态

    判断当前是否在交易时间。

    Args:
        dt: 日期时间，None表示当前时间

    Returns:
        交易状态 (trading, auction, closed, pre_market)
    """
    if dt is None:
        dt = datetime.now()

    current_time = dt.time()

    # 集合竞价时间
    auction_start = time(9, 15)
    auction_end = time(9, 25)

    # 早盘交易时间
    morning_start = time(9, 30)
    morning_end = time(11, 30)

    # 午盘交易时间
    afternoon_start = time(13, 0)
    afternoon_end = time(15, 0)

    if auction_start <= current_time <= auction_end:
        return "auction"
    elif morning_start <= current_time <= morning_end:
        return "trading"
    elif afternoon_start <= current_time <= afternoon_end:
        return "trading"
    elif current_time < auction_start:
        return "pre_market"
    else:
        return "closed"


def normalize_symbol(symbol: str, market: str = "SH") -> str:
    """标准化股票代码

    统一股票代码格式。

    Args:
        symbol: 股票代码
        market: 市场 (SH, SZ)

    Returns:
        标准化后的代码
    """
    # 去除空格
    symbol = symbol.strip()

    # 如果已经包含市场后缀，直接返回
    if symbol.endswith(".SH") or symbol.endswith(".SZ"):
        return symbol

    # 添加市场后缀
    return f"{symbol}.{market}"


def is_trading_day(dt: Optional[datetime] = None) -> bool:
    """判断是否为交易日

    Args:
        dt: 日期时间，None表示当前时间

    Returns:
        是否为交易日
    """
    if dt is None:
        dt = datetime.now()

    # 简单判断：周末不是交易日
    if dt.weekday() >= 5:
        return False

    return True


def calculate_turnover_rate(volume: int, total_shares: int) -> float:
    """计算换手率

    Args:
        volume: 成交量
        total_shares: 总股本

    Returns:
        换手率百分比
    """
    if total_shares == 0:
        return 0.0

    return volume / total_shares * 100
