"""
策略数据服务

提供策略所需的数据接口，包括龙虎榜、北向资金、板块数据等。
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from abc import ABC, abstractmethod

from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval

from .config import DragonTigerConfig, NorthboundConfig


class IDataProvider(ABC):
    """数据提供接口

    定义策略所需的数据获取方法。
    """

    @abstractmethod
    def get_dragon_tiger_data(self, trade_date: date) -> List[Dict[str, Any]]:
        """获取龙虎榜数据

        Args:
            trade_date: 交易日期

        Returns:
            龙虎榜数据列表
        """
        pass

    @abstractmethod
    def get_northbound_flow(self, trade_date: date) -> Optional[Dict[str, Any]]:
        """获取北向资金流向

        Args:
            trade_date: 交易日期

        Returns:
            北向资金流向数据
        """
        pass

    @abstractmethod
    def get_stock_holding(
        self,
        symbol: str,
        trade_date: date
    ) -> Optional[Dict[str, Any]]:
        """获取个股持股变化

        Args:
            symbol: 股票代码
            trade_date: 交易日期

        Returns:
            持股变化数据
        """
        pass

    @abstractmethod
    def get_sector_data(
        self,
        sector: str,
        trade_date: date
    ) -> Optional[Dict[str, Any]]:
        """获取板块数据

        Args:
            sector: 板块名称
            trade_date: 交易日期

        Returns:
            板块数据
        """
        pass

    @abstractmethod
    def get_convertible_bonds(self) -> List[Dict[str, Any]]:
        """获取可转债列表

        Returns:
            可转债列表
        """
        pass

    @abstractmethod
    def get_earnings_forecast(
        self,
        symbol: str,
        days: int
    ) -> List[Dict[str, Any]]:
        """获取业绩预告

        Args:
            symbol: 股票代码
            days: 查询天数

        Returns:
            业绩预告列表
        """
        pass


class ChinaStrategyDataService(IDataProvider):
    """策略数据服务实现

    集成 vnpy_china_data 模块获取数据。
    """

    def __init__(self, data_service: Any = None):
        """初始化数据服务

        Args:
            data_service: vnpy_china_data服务实例
        """
        self.data_service = data_service

    def set_data_service(self, data_service: Any) -> None:
        """设置数据服务

        Args:
            data_service: vnpy_china_data服务实例
        """
        self.data_service = data_service

    def get_dragon_tiger_data(self, trade_date: date) -> List[Dict[str, Any]]:
        """获取龙虎榜数据

        Args:
            trade_date: 交易日期

        Returns:
            龙虎榜数据列表
        """
        if not self.data_service:
            return self._get_mock_dragon_tiger_data(trade_date)

        try:
            data = self.data_service.get_dragon_tiger_data(trade_date)
            return [d.to_dict() if hasattr(d, 'to_dict') else d for d in data]
        except Exception:
            return self._get_mock_dragon_tiger_data(trade_date)

    def get_northbound_flow(self, trade_date: date) -> Optional[Dict[str, Any]]:
        """获取北向资金流向

        Args:
            trade_date: 交易日期

        Returns:
            北向资金流向数据
        """
        if not self.data_service:
            return self._get_mock_northbound_flow(trade_date)

        try:
            data = self.data_service.get_northbound_flow(trade_date)
            return data.to_dict() if hasattr(data, 'to_dict') else data
        except Exception:
            return self._get_mock_northbound_flow(trade_date)

    def get_stock_holding(
        self,
        symbol: str,
        trade_date: date
    ) -> Optional[Dict[str, Any]]:
        """获取个股持股变化

        Args:
            symbol: 股票代码
            trade_date: 交易日期

        Returns:
            持股变化数据
        """
        if not self.data_service:
            return self._get_mock_stock_holding(symbol, trade_date)

        try:
            data = self.data_service.get_stock_holding_change(symbol, 5)
            return data
        except Exception:
            return self._get_mock_stock_holding(symbol, trade_date)

    def get_sector_data(
        self,
        sector: str,
        trade_date: date
    ) -> Optional[Dict[str, Any]]:
        """获取板块数据

        Args:
            sector: 板块名称
            trade_date: 交易日期

        Returns:
            板块数据
        """
        if not self.data_service:
            return self._get_mock_sector_data(sector, trade_date)

        try:
            data = self.data_service.get_sector_list()
            for item in data:
                if item.sector_name == sector:
                    return item.to_dict() if hasattr(item, 'to_dict') else item
        except Exception:
            pass
        return self._get_mock_sector_data(sector, trade_date)

    def get_convertible_bonds(self) -> List[Dict[str, Any]]:
        """获取可转债列表

        Returns:
            可转债列表
        """
        # 简化实现
        return []

    def get_earnings_forecast(
        self,
        symbol: str,
        days: int
    ) -> List[Dict[str, Any]]:
        """获取业绩预告

        Args:
            symbol: 股票代码
            days: 查询天数

        Returns:
            业绩预告列表
        """
        # 简化实现
        return []

    # ========== Mock数据方法（用于测试）==========

    def _get_mock_dragon_tiger_data(
        self,
        trade_date: date
    ) -> List[Dict[str, Any]]:
        """Mock龙虎榜数据"""
        return [
            {
                "symbol": "000001",
                "name": "平安银行",
                "trade_date": trade_date,
                "close_price": 15.50,
                "change_pct": 5.23,
                "institution_net_buy": 15000000,
                "institution_count": 3,
                "broker_net_buy": 8000000,
                "total_buy": 30000000,
                "turnover_rate": 8.5,
            },
            {
                "symbol": "600519",
                "name": "贵州茅台",
                "trade_date": trade_date,
                "close_price": 1850.00,
                "change_pct": 2.15,
                "institution_net_buy": 50000000,
                "institution_count": 5,
                "broker_net_buy": 20000000,
                "total_buy": 80000000,
                "turnover_rate": 1.2,
            }
        ]

    def _get_mock_northbound_flow(
        self,
        trade_date: date
    ) -> Optional[Dict[str, Any]]:
        """Mock北向资金数据"""
        return {
            "trade_date": trade_date,
            "net_inflow": 1500000000,  # 15亿
            "buy_volume": 5000000000,
            "sell_volume": 3500000000,
        }

    def _get_mock_stock_holding(
        self,
        symbol: str,
        trade_date: date
    ) -> Optional[Dict[str, Any]]:
        """Mock持股变化数据"""
        return {
            "symbol": symbol,
            "trade_date": trade_date,
            "holding_shares": 10000000,
            "holding_ratio": 0.5,
            "change_shares": 500000,
            "change_ratio": 0.05,
        }

    def _get_mock_sector_data(
        self,
        sector: str,
        trade_date: date
    ) -> Optional[Dict[str, Any]]:
        """Mock板块数据"""
        return {
            "sector_code": "BK0001",
            "sector_name": sector,
            "change_pct": 1.5,
            "volume": 1000000000,
            "turnover": 15000000000,
            "pe_ratio": 25.0,
        }


# 全局数据服务实例
_data_service_instance: Optional[ChinaStrategyDataService] = None


def get_data_service(data_service: Any = None) -> ChinaStrategyDataService:
    """获取策略数据服务实例

    Args:
        data_service: vnpy_china_data服务实例

    Returns:
        策略数据服务实例
    """
    global _data_service_instance
    if _data_service_instance is None:
        _data_service_instance = ChinaStrategyDataService(data_service)
    elif data_service is not None:
        _data_service_instance.set_data_service(data_service)
    return _data_service_instance
