"""因子数据获取器

连接 vnpy_china_ml 因子模块与 vnpy_china_data 数据服务，
提供统一的数据获取接口。
"""

import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Union
from pathlib import Path

try:
    from vnpy_china_data import ChinaDataService
    CHINA_DATA_AVAILABLE = True
except ImportError:
    CHINA_DATA_AVAILABLE = False
    ChinaDataService = None

from .dragon_tiger import DragonTigerFactor
from .northbound import NorthboundFactor
from .sector_rotation import SectorRotationFactor
from .base import BaseFactor


class FactorDataLoader:
    """因子数据加载器

    负责从 vnpy_china_data 获取数据，并转换为因子可用的格式。
    """

    def __init__(self, data_service: Optional[ChinaDataService] = None):
        """初始化数据加载器

        Args:
            data_service: 数据服务实例，None时尝试创建
        """
        self.data_service = data_service

        if not CHINA_DATA_AVAILABLE:
            print("警告: vnpy_china_data 模块不可用，部分因子无法获取数据")

        if CHINA_DATA_AVAILABLE and self.data_service is None:
            self.data_service = ChinaDataService()
            self.data_service.connect()

    def load_dragon_tiger_data(
        self,
        start_date: Union[str, date],
        end_date: Union[str, date],
        symbols: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """加载龙虎榜数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            symbols: 股票代码列表（None表示全部）

        Returns:
            龙虎榜数据DataFrame
        """
        if not CHINA_DATA_AVAILABLE or not self.data_service:
            return self._create_empty_dragon_tiger_df()

        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)

        # 获取日期范围内的所有交易日数据
        records = []
        current_date = start_date

        while current_date <= end_date:
            try:
                daily_data = self.data_service.get_dragon_tiger_data(current_date)

                for item in daily_data:
                    # 过滤股票
                    if symbols and item.symbol not in symbols:
                        continue

                    records.append({
                        "symbol": item.symbol,
                        "datetime": pd.Timestamp.combine(item.trade_date, pd.Timestamp.min.time()),
                        "institution_net_buy": item.institution_net_buy,
                        "institution_buy": item.institution_buy,
                        "institution_sell": item.institution_sell,
                        "broker_net_buy": item.broker_net_buy,
                        "broker_buy": item.broker_buy,
                        "broker_sell": item.broker_sell,
                        "buy_amount": item.total_net_buy,
                        "sell_amount": 0.0,  # 龙虎榜没有单独的卖出统计
                        "close_price": item.close_price,
                        "turnover_rate": item.turnover_rate,
                        "change_pct": item.change_pct,
                        "reason": item.reason,
                        "listed": 1,  # 在龙虎榜中
                    })

            except Exception as e:
                print(f"获取龙虎榜数据失败 {current_date}: {e}")

            current_date += timedelta(days=1)

        if not records:
            return self._create_empty_dragon_tiger_df()

        df = pd.DataFrame(records)

        # 按股票和日期排序
        df = df.sort_values(["symbol", "datetime"])

        return df

    def load_northbound_data(
        self,
        start_date: Union[str, date],
        end_date: Union[str, date],
        symbols: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """加载北向资金数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            symbols: 股票代码列表（None表示全部）

        Returns:
            北向资金数据DataFrame
        """
        if not CHINA_DATA_AVAILABLE or not self.data_service:
            return self._create_empty_northbound_df()

        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)

        # 获取日期范围内的所有数据
        records = []
        current_date = start_date

        while current_date <= end_date:
            try:
                flow_data = self.data_service.get_northbound_flow(current_date)

                if flow_data:
                    # 处理持股变化数据
                    for symbol, change in flow_data.holding_changes.items():
                        if symbols and symbol not in symbols:
                            continue

                        records.append({
                            "symbol": symbol,
                            "datetime": pd.Timestamp.combine(current_date, pd.Timestamp.min.time()),
                            "net_inflow": change,  # 持股变化作为净流入近似
                            "buy_amount": max(0, change),
                            "sell_amount": max(0, -change),
                            "holding_change": change,
                            "turnover": 0.0,  # 需要补充
                        })

            except Exception as e:
                print(f"获取北向资金数据失败 {current_date}: {e}")

            current_date += timedelta(days=1)

        if not records:
            return self._create_empty_northbound_df()

        df = pd.DataFrame(records)
        df = df.sort_values(["symbol", "datetime"])

        return df

    def load_sector_data(
        self,
        start_date: Union[str, date],
        end_date: Union[str, date],
        sectors: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """加载板块数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            sectors: 板块代码列表（None表示全部）

        Returns:
            板块数据DataFrame
        """
        if not CHINA_DATA_AVAILABLE or not self.data_service:
            return self._create_empty_sector_df()

        # 获取板块列表
        sector_list = self.data_service.get_sector_list()

        if not sector_list:
            return self._create_empty_sector_df()

        # 过滤板块
        if sectors:
            sector_list = [s for s in sector_list if s.sector_code in sectors]

        # 为每个板块创建记录
        records = []
        current_date = start_date

        while current_date <= end_date:
            for sector in sector_list:
                records.append({
                    "sector": sector.sector_code,
                    "symbol": f"{sector.sector_code}.INDEX",  # 使用板块代码作为symbol
                    "datetime": pd.Timestamp.combine(current_date, pd.Timestamp.min.time()),
                    "return": 0.0,  # 需要从板块指数计算
                    "market_return": 0.0,  # 需要从市场指数计算
                    "volume": 0.0,
                    "float_share": 0.0,
                    "net_inflow": 0.0,
                })

            current_date += timedelta(days=1)

        if not records:
            return self._create_empty_sector_df()

        df = pd.DataFrame(records)
        df = df.sort_values(["sector", "datetime"])

        return df

    def _create_empty_dragon_tiger_df(self) -> pd.DataFrame:
        """创建空的龙虎榜DataFrame"""
        return pd.DataFrame(columns=[
            "symbol", "datetime", "institution_net_buy", "institution_buy",
            "institution_sell", "broker_net_buy", "broker_buy", "broker_sell",
            "buy_amount", "sell_amount", "close_price", "turnover_rate",
            "change_pct", "reason", "listed"
        ])

    def _create_empty_northbound_df(self) -> pd.DataFrame:
        """创建空的北向资金DataFrame"""
        return pd.DataFrame(columns=[
            "symbol", "datetime", "net_inflow", "buy_amount", "sell_amount",
            "holding_change", "turnover"
        ])

    def _create_empty_sector_df(self) -> pd.DataFrame:
        """创建空的板块DataFrame"""
        return pd.DataFrame(columns=[
            "sector", "symbol", "datetime", "return", "market_return",
            "volume", "float_share", "net_inflow"
        ])


class FactorCalculator:
    """因子计算器

    提供一键计算因子的便捷接口。
    """

    def __init__(self, data_loader: Optional[FactorDataLoader] = None):
        """初始化因子计算器

        Args:
            data_loader: 数据加载器
        """
        self.data_loader = data_loader or FactorDataLoader()

        # 创建因子实例
        self.dragon_tiger_factor = DragonTigerFactor()
        self.northbound_factor = NorthboundFactor()
        self.sector_rotation_factor = SectorRotationFactor()

    def calculate_dragon_tiger_factor(
        self,
        start_date: Union[str, date],
        end_date: Union[str, date],
        symbols: Optional[List[str]] = None
    ) -> Optional[pd.Series]:
        """计算龙虎榜因子

        Args:
            start_date: 开始日期
            end_date: 结束日期
            symbols: 股票代码列表

        Returns:
            因子值Series
        """
        # 加载数据
        df = self.data_loader.load_dragon_tiger_data(start_date, end_date, symbols)

        if df.empty:
            print("警告: 龙虎榜数据为空")
            return None

        # 计算因子
        return self.dragon_tiger_factor.calculate(df)

    def calculate_northbound_factor(
        self,
        start_date: Union[str, date],
        end_date: Union[str, date],
        symbols: Optional[List[str]] = None
    ) -> Optional[pd.Series]:
        """计算北向资金因子

        Args:
            start_date: 开始日期
            end_date: 结束日期
            symbols: 股票代码列表

        Returns:
            因子值Series
        """
        # 加载数据
        df = self.data_loader.load_northbound_data(start_date, end_date, symbols)

        if df.empty:
            print("警告: 北向资金数据为空")
            return None

        # 计算因子
        return self.northbound_factor.calculate(df)

    def calculate_sector_rotation_factor(
        self,
        start_date: Union[str, date],
        end_date: Union[str, date],
        sectors: Optional[List[str]] = None
    ) -> Optional[pd.Series]:
        """计算板块轮动因子

        Args:
            start_date: 开始日期
            end_date: 结束日期
            sectors: 板块代码列表

        Returns:
            因子值Series
        """
        # 加载数据
        df = self.data_loader.load_sector_data(start_date, end_date, sectors)

        if df.empty:
            print("警告: 板块数据为空")
            return None

        # 计算因子
        return self.sector_rotation_factor.calculate(df)

    def calculate_all_factors(
        self,
        start_date: Union[str, date],
        end_date: Union[str, date],
        symbols: Optional[List[str]] = None
    ) -> Dict[str, pd.Series]:
        """计算所有因子

        Args:
            start_date: 开始日期
            end_date: 结束日期
            symbols: 股票代码列表

        Returns:
            因子字典 {factor_name: factor_series}
        """
        results = {}

        # 龙虎榜因子
        dragon_tiger = self.calculate_dragon_tiger_factor(
            start_date, end_date, symbols
        )
        if dragon_tiger is not None:
            results["dragon_tiger"] = dragon_tiger

        # 北向资金因子
        northbound = self.calculate_northbound_factor(
            start_date, end_date, symbols
        )
        if northbound is not None:
            results["northbound"] = northbound

        # 板块轮动因子
        sector_rotation = self.calculate_sector_rotation_factor(
            start_date, end_date
        )
        if sector_rotation is not None:
            results["sector_rotation"] = sector_rotation

        return results


def create_factor_calculator(
    data_service: Optional[ChinaDataService] = None
) -> FactorCalculator:
    """创建因子计算器

    Args:
        data_service: 数据服务实例

    Returns:
        因子计算器实例
    """
    data_loader = FactorDataLoader(data_service)
    return FactorCalculator(data_loader)


__all__ = [
    "FactorDataLoader",
    "FactorCalculator",
    "create_factor_calculator",
]
