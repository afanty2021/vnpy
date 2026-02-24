"""
A股数据接口定义模块

定义A股交易系统所需的标准数据接口，包括：
- IDataProvider: 基础行情数据接口
- IDragonTigerProvider: 龙虎榜数据接口
- INorthboundProvider: 北向资金数据接口
- ISectorProvider: 板块数据接口

这些接口是vnpy_china_data模块的实现目标。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from datetime import date, datetime

from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval


class DragonTigerData:
    """龙虎榜数据"""

    def __init__(
        self,
        symbol: str,
        trade_date: date,
        close_price: float = 0.0,
        change_pct: float = 0.0,
        institution_net_buy: float = 0.0,
        broker_net_buy: float = 0.0,
        buy_ratio: float = 0.0,
        sell_ratio: float = 0.0,
        buy_brokers: Optional[List[str]] = None,
        sell_brokers: Optional[List[str]] = None,
    ):
        self.symbol = symbol
        self.trade_date = trade_date
        self.close_price = close_price
        self.change_pct = change_pct
        self.institution_net_buy = institution_net_buy
        self.broker_net_buy = broker_net_buy
        self.buy_ratio = buy_ratio
        self.sell_ratio = sell_ratio
        self.buy_brokers = buy_brokers or []
        self.sell_brokers = sell_brokers or []

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "close_price": self.close_price,
            "change_pct": self.change_pct,
            "institution_net_buy": self.institution_net_buy,
            "broker_net_buy": self.broker_net_buy,
            "buy_ratio": self.buy_ratio,
            "sell_ratio": self.sell_ratio,
            "buy_brokers": self.buy_brokers,
            "sell_brokers": self.sell_brokers,
        }


class NorthboundFlowData:
    """北向资金流向数据"""

    def __init__(
        self,
        trade_date: date,
        net_inflow: float = 0.0,
        buy_volume: float = 0.0,
        sell_volume: float = 0.0,
        holding_changes: Optional[Dict[str, float]] = None,
    ):
        self.trade_date = trade_date
        self.net_inflow = net_inflow
        self.buy_volume = buy_volume
        self.sell_volume = sell_volume
        self.holding_changes = holding_changes or {}

    def to_dict(self) -> Dict:
        return {
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "net_inflow": self.net_inflow,
            "buy_volume": self.buy_volume,
            "sell_volume": self.sell_volume,
            "holding_changes": self.holding_changes,
        }


class SectorData:
    """板块数据"""

    def __init__(
        self,
        sector_code: str,
        sector_name: str,
        change_pct: float = 0.0,
        volume: float = 0.0,
        turnover: float = 0.0,
        pe_ratio: float = 0.0,
    ):
        self.sector_code = sector_code
        self.sector_name = sector_name
        self.change_pct = change_pct
        self.volume = volume
        self.turnover = turnover
        self.pe_ratio = pe_ratio

    def to_dict(self) -> Dict:
        return {
            "sector_code": self.sector_code,
            "sector_name": self.sector_name,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "turnover": self.turnover,
            "pe_ratio": self.pe_ratio,
        }


class IDataProvider(ABC):
    """基础行情数据接口

    提供K线数据和Tick数据获取能力，是所有数据服务的基础接口。
    """

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
    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """获取股票基本信息

        Args:
            symbol: 股票代码

        Returns:
            股票信息字典，包含name, exchange, industry等字段
        """
        pass

    @abstractmethod
    def subscribe_quote(self, symbols: List[str]) -> bool:
        """订阅实时行情

        Args:
            symbols: 股票代码列表

        Returns:
            是否订阅成功
        """
        pass


class IDragonTigerProvider(ABC):
    """龙虎榜数据接口

    提供获取龙虎榜数据的能力，包括：
    - 每日龙虎榜数据
    - 机构席位买卖数据
    - 营业部排行数据
    """

    @abstractmethod
    def get_dragon_tiger_data(
        self,
        trade_date: date
    ) -> List[DragonTigerData]:
        """获取指定日期的龙虎榜数据

        Args:
            trade_date: 交易日期

        Returns:
            龙虎榜数据列表
        """
        pass

    @abstractmethod
    def get_institution_rank(
        self,
        trade_date: date,
        top_n: int = 10
    ) -> List[DragonTigerData]:
        """获取机构排名

        Args:
            trade_date: 交易日期
            top_n: 返回前N名

        Returns:
            按机构净买入排序的数据列表
        """
        pass


class INorthboundProvider(ABC):
    """北向资金数据接口

    提供获取北向资金（沪股通/深股通）相关数据的能力：
    - 每日北向资金流向
    - 个股持股变化
    - 北向资金持仓数据
    """

    @abstractmethod
    def get_northbound_flow(
        self,
        trade_date: date
    ) -> Optional[NorthboundFlowData]:
        """获取北向资金流向

        Args:
            trade_date: 交易日期

        Returns:
            北向资金流向数据
        """
        pass

    @abstractmethod
    def get_stock_holding_change(
        self,
        symbol: str,
        days: int = 5
    ) -> Dict[str, float]:
        """获取个股持股变化

        Args:
            symbol: 股票代码
            days: 查询天数

        Returns:
            持股变化字典，key为日期，value为变化量
        """
        pass


class ISectorProvider(ABC):
    """板块数据接口

    提供获取板块相关数据的能力：
    - 板块列表
    - 板块成分股
    - 板块指数数据
    """

    @abstractmethod
    def get_sector_list(self) -> List[SectorData]:
        """获取板块列表

        Returns:
            板块数据列表
        """
        pass

    @abstractmethod
    def get_sector_stocks(self, sector_code: str) -> List[str]:
        """获取板块成分股

        Args:
            sector_code: 板块代码

        Returns:
            成分股代码列表
        """
        pass

    @abstractmethod
    def get_sector_index(
        self,
        sector_code: str,
        start_date: str,
        end_date: str
    ) -> List[BarData]:
        """获取板块指数数据

        Args:
            sector_code: 板块代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            K线数据列表
        """
        pass
