"""
Tushare数据适配器

适配Tushare行情数据到分析模块。
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date


class TushareDataAdapter:
    """
    Tushare数据适配器

    将Tushare的行情数据转换为分析模块所需的格式。
    """

    def __init__(self) -> None:
        """构造函数"""
        pass

    def adapt_daily_data(self, ts_data: Dict[str, Any]) -> Dict[str, Any]:
        """适配日线数据

        Args:
            ts_data: Tushare原始数据

        Returns:
            适配后的数据字典
        """
        return {
            "symbol": ts_data.get("ts_code", ""),
            "date": ts_data.get("trade_date", date.today()),
            "open": ts_data.get("open", 0.0),
            "high": ts_data.get("high", 0.0),
            "low": ts_data.get("low", 0.0),
            "close": ts_data.get("close", 0.0),
            "pre_close": ts_data.get("pre_close", 0.0),
            "volume": ts_data.get("vol", 0),
            "amount": ts_data.get("amount", 0.0),
            "change_pct": ts_data.get("pct_chg", 0.0)
        }

    def adapt_minute_data(self, ts_data: Dict[str, Any]) -> Dict[str, Any]:
        """适配分钟线数据

        Args:
            ts_data: Tushare原始数据

        Returns:
            适配后的数据字典
        """
        return {
            "symbol": ts_data.get("ts_code", ""),
            "datetime": datetime.strptime(ts_data.get("trade_time", ""), "%Y-%m-%d %H:%M:%S"),
            "open": ts_data.get("open", 0.0),
            "high": ts_data.get("high", 0.0),
            "low": ts_data.get("low", 0.0),
            "close": ts_data.get("close", 0.0),
            "volume": ts_data.get("vol", 0),
            "amount": ts_data.get("amount", 0.0)
        }

    def adapt_money_flow_data(self, ts_data: Dict[str, Any]) -> Dict[str, Any]:
        """适配资金流向数据

        Args:
            ts_data: Tushare原始数据

        Returns:
            适配后的数据字典
        """
        return {
            "symbol": ts_data.get("ts_code", ""),
            "datetime": datetime.strptime(ts_data.get("trade_time", ""), "%Y-%m-%d %H:%M:%S"),
            "super_large_inflow": ts_data.get("net_amount_main", 0.0),
            "large_inflow": ts_data.get("net_amount_large", 0.0),
            "medium_inflow": ts_data.get("net_amount_medium", 0.0),
            "small_inflow": ts_data.get("net_amount_small", 0.0)
        }

    def adapt_limit_data(self, ts_data: Dict[str, Any]) -> Dict[str, Any]:
        """适配涨跌停数据

        Args:
            ts_data: Tushare原始数据

        Returns:
            适配后的数据字典
        """
        return {
            "symbol": ts_data.get("ts_code", ""),
            "date": datetime.strptime(ts_data.get("trade_date", ""), "%Y%m%d").date(),
            "is_limit_up": ts_data.get("limit", "") == "U",
            "is_limit_down": ts_data.get("limit", "") == "D"
        }

    def adapt_sector_data(self, ts_data: Dict[str, Any]) -> Dict[str, Any]:
        """适配板块数据

        Args:
            ts_data: Tushare原始数据

        Returns:
            适配后的数据字典
        """
        return {
            "sector_code": ts_data.get("ts_code", ""),
            "sector_name": ts_data.get("name", ""),
            "datetime": datetime.strptime(ts_data.get("trade_date", ""), "%Y%m%d"),
            "index_value": ts_data.get("close", 0.0),
            "change_pct": ts_data.get("pct_chg", 0.0),
            "volume": ts_data.get("vol", 0),
            "turnover": ts_data.get("turnover_rate", 0.0)
        }

    def adapt_auction_data(self, ts_data: Dict[str, Any]) -> Dict[str, Any]:
        """适配集合竞价数据

        Args:
            ts_data: Tushare原始数据

        Returns:
            适配后的数据字典
        """
        return {
            "symbol": ts_data.get("ts_code", ""),
            "date": datetime.strptime(ts_data.get("trade_date", ""), "%Y%m%d").date(),
            "pre_close": ts_data.get("pre_close", 0.0),
            "auction_price": ts_data.get("open", 0.0),  # 竞价成交价
            "auction_volume": ts_data.get("vol", 0),
            "auction_amount": ts_data.get("amount", 0.0)
        }

    def convert_to_analysis_format(self, ts_data: Dict[str, Any], data_type: str = "daily") -> Dict[str, Any]:
        """转换为分析模块所需格式

        Args:
            ts_data: Tushare原始数据
            data_type: 数据类型 (daily, minute, money_flow, limit, sector, auction)

        Returns:
            适配后的数据字典
        """
        if data_type == "daily":
            return self.adapt_daily_data(ts_data)
        elif data_type == "minute":
            return self.adapt_minute_data(ts_data)
        elif data_type == "money_flow":
            return self.adapt_money_flow_data(ts_data)
        elif data_type == "limit":
            return self.adapt_limit_data(ts_data)
        elif data_type == "sector":
            return self.adapt_sector_data(ts_data)
        elif data_type == "auction":
            return self.adapt_auction_data(ts_data)
        else:
            return ts_data

    def batch_convert(self, ts_data_list: List[Dict[str, Any]], data_type: str = "daily") -> List[Dict[str, Any]]:
        """批量转换数据

        Args:
            ts_data_list: Tushare原始数据列表
            data_type: 数据类型

        Returns:
            适配后的数据列表
        """
        return [self.convert_to_analysis_format(data, data_type) for data in ts_data_list]
