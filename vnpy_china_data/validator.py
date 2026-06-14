"""
数据验证器模块

提供数据验证功能，确保数据的完整性和正确性。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date

from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval


class DataValidator:
    """数据验证器

    验证数据的完整性和正确性，包括：
    - K线数据验证
    - Tick数据验证
    - 股票代码验证
    """

    @staticmethod
    def validate_bar_data(bar: BarData) -> bool:
        """验证K线数据的有效性

        Args:
            bar: K线数据

        Returns:
            是否有效
        """
        # 检查基本字段
        if not bar.symbol:
            return False

        if bar.open_price <= 0 or bar.high_price <= 0 or \
           bar.low_price <= 0 or bar.close_price <= 0:
            return False

        # 检查价格关系
        if bar.high_price < bar.low_price:
            return False

        if bar.high_price < bar.open_price or \
           bar.high_price < bar.close_price:
            return False

        if bar.low_price > bar.open_price or \
           bar.low_price > bar.close_price:
            return False

        # 检查成交量
        if bar.volume < 0:
            return False

        return True

    @staticmethod
    def validate_bar_list(bars: List[BarData]) -> List[BarData]:
        """验证并过滤K线数据列表

        Args:
            bars: K线数据列表

        Returns:
            有效的K线数据列表
        """
        valid_bars = []
        for bar in bars:
            if DataValidator.validate_bar_data(bar):
                valid_bars.append(bar)
        return valid_bars

    @staticmethod
    def validate_tick_data(tick: TickData) -> bool:
        """验证Tick数据的有效性

        Args:
            tick: Tick数据

        Returns:
            是否有效
        """
        if not tick.symbol:
            return False

        # 检查买卖盘价格
        if tick.bid_price_1 <= 0 or tick.ask_price_1 <= 0:
            return False

        # 检查价差合理性
        spread = tick.ask_price_1 - tick.bid_price_1
        if spread < 0:
            return False

        # 检查价格合理性（防止异常值）
        mid_price = (tick.bid_price_1 + tick.ask_price_1) / 2
        if mid_price <= 0:
            return False

        return True

    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """验证股票代码格式

        Args:
            symbol: 股票代码

        Returns:
            是否有效
        """
        if not symbol:
            return False

        # A股股票代码为6位数字
        if not symbol.isdigit():
            return False

        if len(symbol) != 6:
            return False

        return True

    @staticmethod
    def validate_exchange(exchange: Exchange) -> bool:
        """验证交易所

        Args:
            exchange: 交易所

        Returns:
            是否有效
        """
        return exchange in [
            Exchange.SSE,   # 上交所
            Exchange.SZSE,  # 深交所
            Exchange.BSE,   # 北交所
            Exchange.SHHK,  # 沪港通
            Exchange.SZHK,  # 深港通
            Exchange.SEHK,  # 香港联交所
        ]

    @staticmethod
    def validate_interval(interval: Interval) -> bool:
        """验证K线周期

        Args:
            interval: K线周期

        Returns:
            是否有效
        """
        return interval in [
            Interval.MINUTE,
            Interval.HOUR,
            Interval.DAILY,
            Interval.WEEKLY,
        ]

    @staticmethod
    def validate_date_range(
        start: datetime,
        end: datetime
    ) -> bool:
        """验证日期范围

        Args:
            start: 开始时间
            end: 结束时间

        Returns:
            是否有效
        """
        if start >= end:
            return False

        # 禁止查询超过5年的数据
        from datetime import timedelta
        if end - start > timedelta(days=365 * 5):
            return False

        return True


class DataNormalizer:
    """数据标准化器

    标准化数据格式，确保数据一致性。
    """

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        """标准化股票代码

        Args:
            symbol: 股票代码

        Returns:
            标准化后的股票代码
        """
        # 移除空格
        symbol = symbol.strip()
        # 转为大写
        symbol = symbol.upper()
        # 移除后缀（如.SH, .SZ）
        if '.' in symbol:
            symbol = symbol.split('.')[0]
        return symbol

    @staticmethod
    def normalize_exchange(exchange: str) -> Optional[Exchange]:
        """标准化交易所

        Args:
            exchange: 交易所字符串

        Returns:
            Exchange枚举
        """
        exchange = exchange.upper()

        if exchange in ["SSE", "SH", "SHANGHAI", "上交所"]:
            return Exchange.SSE
        elif exchange in ["SZSE", "SZ", "SHENZHEN", "深交所"]:
            return Exchange.SZSE
        elif exchange in ["BSE", "BJ", "BEIJING", "北交所"]:
            return Exchange.BSE

        return None

    @staticmethod
    def format_date(dt: datetime) -> str:
        """格式化日期为字符串

        Args:
            dt: 日期时间

        Returns:
            YYYYMMDD格式字符串
        """
        return dt.strftime("%Y%m%d")

    @staticmethod
    def format_datetime(dt: datetime) -> str:
        """格式化日期时间为字符串

        Args:
            dt: 日期时间

        Returns:
            YYYYMMDDHHMMSS格式字符串
        """
        return dt.strftime("%Y%m%d%H%M%S")
