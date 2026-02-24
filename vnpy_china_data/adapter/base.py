"""
数据适配器基类

定义所有数据适配器的抽象基类。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval


class BaseDataAdapter(ABC):
    """数据适配器基类

    所有数据适配器都应继承此类，实现标准数据接口。
    """

    def __init__(self):
        self._connected = False

    @property
    def connected(self) -> bool:
        """检查连接状态"""
        return self._connected

    @abstractmethod
    def connect(self) -> bool:
        """连接数据源

        Returns:
            是否连接成功
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """断开连接"""
        pass

    # ========== 行情数据接口 ==========

    @abstractmethod
    def get_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """获取K线数据

        Args:
            symbol: 股票代码
            exchange: 交易所
            interval: K线周期
            start: 开始时间
            end: 结束时间

        Returns:
            K线数据列表
        """
        pass

    @abstractmethod
    def get_tick_data(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime
    ) -> List[TickData]:
        """获取Tick数据

        Args:
            symbol: 股票代码
            exchange: 交易所
            start: 开始时间
            end: 结束时间

        Returns:
            Tick数据列表
        """
        pass

    @abstractmethod
    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取股票基本信息

        Args:
            symbol: 股票代码

        Returns:
            股票信息字典
        """
        pass

    # ========== 订阅接口 ==========

    @abstractmethod
    def subscribe(self, symbols: List[str]) -> bool:
        """订阅实时行情

        Args:
            symbols: 股票代码列表

        Returns:
            是否订阅成功
        """
        pass

    @abstractmethod
    def unsubscribe(self, symbols: List[str]) -> bool:
        """取消订阅

        Args:
            symbols: 股票代码列表

        Returns:
            是否取消成功
        """
        pass

    # ========== 工具方法 ==========

    def symbol_to_ts_code(self, symbol: str, exchange: Exchange) -> str:
        """转换symbol为tushare格式

        Args:
            symbol: 股票代码
            exchange: 交易所

        Returns:
            tushare格式代码
        """
        suffix_map = {
            Exchange.SSE: "SH",
            Exchange.SZSE: "SZ",
            Exchange.BSE: "BJ"
        }
        suffix = suffix_map.get(exchange, "SZ")
        return f"{symbol}.{suffix}"

    def ts_code_to_symbol(self, ts_code: str) -> tuple:
        """从tushare格式转换为symbol

        Args:
            ts_code: tushare格式代码

        Returns:
            (symbol, exchange)元组
        """
        if '.' not in ts_code:
            return ts_code, Exchange.SZSE

        symbol, suffix = ts_code.split('.')

        exchange_map = {
            "SH": Exchange.SSE,
            "SZ": Exchange.SZSE,
            "BJ": Exchange.BSE
        }
        exchange = exchange_map.get(suffix, Exchange.SZSE)

        return symbol, exchange
