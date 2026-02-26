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

        Raises:
            RuntimeError: 当数据服务不可用或数据加载失败时
        """
        if not self.data_service:
            raise RuntimeError(
                f"数据服务未初始化\n"
                f"请确保已配置 vnpy_china_data 服务"
            )

        try:
            data = self.data_service.get_dragon_tiger_data(trade_date)
            if not data:
                raise RuntimeError(
                    f"本地数据库中没有 {trade_date} 的龙虎榜数据\n"
                    f"请使用「A股数据」模块下载龙虎榜数据"
                )
            return [d.to_dict() if hasattr(d, 'to_dict') else d for d in data]
        except Exception as e:
            raise RuntimeError(
                f"获取龙虎榜数据失败: {e}\n"
                f"请使用「A股数据」模块下载数据"
            ) from e

    def get_northbound_flow(self, trade_date: date) -> Optional[Dict[str, Any]]:
        """获取北向资金流向

        Args:
            trade_date: 交易日期

        Returns:
            北向资金流向数据

        Raises:
            RuntimeError: 当数据服务不可用或数据加载失败时
        """
        if not self.data_service:
            raise RuntimeError(
                f"数据服务未初始化\n"
                f"请确保已配置 vnpy_china_data 服务"
            )

        try:
            data = self.data_service.get_northbound_flow(trade_date)
            if not data:
                raise RuntimeError(
                    f"本地数据库中没有 {trade_date} 的北向资金数据\n"
                    f"请使用「A股数据」模块下载北向资金数据"
                )
            return data.to_dict() if hasattr(data, 'to_dict') else data
        except Exception as e:
            raise RuntimeError(
                f"获取北向资金数据失败: {e}\n"
                f"请使用「A股数据」模块下载数据"
            ) from e

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

        Raises:
            RuntimeError: 当数据服务不可用或数据加载失败时
        """
        if not self.data_service:
            raise RuntimeError(
                f"数据服务未初始化\n"
                f"请确保已配置 vnpy_china_data 服务"
            )

        try:
            data = self.data_service.get_stock_holding_change(symbol, 5)
            if not data:
                raise RuntimeError(
                    f"本地数据库中没有 {symbol} 在 {trade_date} 的持股变化数据\n"
                    f"请使用「A股数据」模块下载持股数据"
                )
            return data
        except Exception as e:
            raise RuntimeError(
                f"获取持股变化数据失败: {e}\n"
                f"请使用「A股数据」模块下载数据"
            ) from e

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
            raise RuntimeError(
                f"数据服务未初始化\n"
                f"请确保已配置 vnpy_china_data 服务"
            )

        try:
            # 获取板块列表
            sector_list = self.data_service.get_sector_list()
            for item in sector_list:
                # 支持按名称或代码匹配
                if item.sector_name == sector or item.sector_code == sector:
                    # 获取板块当日行情
                    sector_index = self.data_service.get_sector_index(item.sector_code, trade_date)
                    result = item.to_dict() if hasattr(item, 'to_dict') else item
                    if sector_index:
                        result.update(sector_index)
                    return result
            raise RuntimeError(f"未找到板块: {sector}")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"获取板块数据失败: {e}\n"
                f"请使用「A股数据」模块下载板块数据"
            ) from e

    def get_convertible_bonds(self) -> List[Dict[str, Any]]:
        """获取可转债列表

        Returns:
            可转债列表
        """
        if not self.data_service:
            raise RuntimeError(
                f"数据服务未初始化\n"
                f"请确保已配置 vnpy_china_data 服务"
            )

        try:
            # 从tushare获取可转债数据
            # 使用get_stock_list过滤可转债（沪深转债代码以110/113/123/127开头）
            from datetime import datetime, timedelta

            # 获取近期上市的转债
            stocks = self.data_service.get_stock_list()
            convertible_bonds = []

            for stock in stocks:
                symbol = stock.get("ts_code", "")
                # 筛选可转债（沪深转债代码特征）
                if symbol and any(symbol.startswith(prefix) for prefix in ["110", "113", "123", "127", "128", "129"]):
                    convertible_bonds.append(stock)

            return convertible_bonds
        except Exception as e:
            raise RuntimeError(
                f"获取可转债列表失败: {e}\n"
                f"请使用「A股数据」模块下载数据"
            ) from e

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
        if not self.data_service:
            raise RuntimeError(
                f"数据服务未初始化\n"
                f"请确保已配置 vnpy_china_data 服务"
            )

        try:
            # 获取财务数据
            from datetime import datetime, timedelta
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)

            financial_data = self.data_service.get_financial_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )

            if financial_data:
                return [f.to_dict() if hasattr(f, 'to_dict') else f for f in financial_data]

            return []
        except Exception as e:
            raise RuntimeError(
                f"获取业绩预告失败: {e}\n"
                f"请使用「A股数据」模块下载财务数据"
            ) from e

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
