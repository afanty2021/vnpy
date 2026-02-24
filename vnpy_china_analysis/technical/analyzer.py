"""
技术指标综合分析器

整合所有技术指标分析功能。
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from .limit_stats import LimitStatsAnalyzer
from .sector_index import SectorIndexAnalyzer


class TechnicalAnalyzer:
    """
    技术指标综合分析器

    整合涨跌停统计、板块指数等技术指标分析功能。
    """

    def __init__(self) -> None:
        """构造函数"""
        self.limit_stats = LimitStatsAnalyzer()
        self.sector_index = SectorIndexAnalyzer()

    def update_limit(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新涨跌停数据

        Args:
            symbol: 股票代码
            data: 包含价格、涨跌停信息的字典

        Returns:
            分析结果
        """
        stats = self.limit_stats.analyze(symbol, data)

        return {
            "symbol": symbol,
            "datetime": datetime.now(),
            "is_limit_up": stats.is_limit_up,
            "is_limit_down": stats.is_limit_down,
            "continuous_limit_up": stats.limit_up_days,
            "continuous_limit_down": stats.limit_down_days,
            "limit_formation": self.limit_stats.get_limit_formation(symbol)
        }

    def get_limit_analysis(self, symbol: str) -> Dict[str, Any]:
        """获取涨跌停分析

        Args:
            symbol: 股票代码

        Returns:
            涨跌停分析结果
        """
        stats = self.limit_stats.get_limit_stats(symbol)

        if not stats:
            return {}

        return {
            "symbol": symbol,
            "is_limit_up": stats.is_limit_up,
            "is_limit_down": stats.is_limit_down,
            "continuous_limit_up": stats.limit_up_days,
            "continuous_limit_down": stats.limit_down_days,
            "total_limit_up": stats.limit_up_count,
            "total_limit_down": stats.limit_down_count,
            "formation": self.limit_stats.get_limit_formation(symbol)
        }

    def update_sector(self, sector_code: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新板块数据

        Args:
            sector_code: 板块代码
            data: 板块数据字典

        Returns:
            分析结果
        """
        index_data = self.sector_index.analyze(sector_code, data)

        return {
            "sector_code": sector_code,
            "datetime": datetime.now(),
            "index_value": index_data.index_value,
            "change_pct": index_data.change_pct,
            "leading_stocks": index_data.leading_stocks
        }

    def get_sector_analysis(self, sector_code: str) -> Dict[str, Any]:
        """获取板块分析

        Args:
            sector_code: 板块代码

        Returns:
            板块分析结果
        """
        index = self.sector_index.get_sector_index(sector_code)
        trend = self.sector_index.get_sector_trend(sector_code)

        if not index:
            return {}

        return {
            "sector_code": sector_code,
            "sector_name": index.sector_name,
            "change_pct": index.change_pct,
            "volume": index.volume,
            "turnover": index.turnover,
            "leading_stocks": index.leading_stocks,
            "trend": trend
        }

    def get_market_overview(self, sector_codes: List[str]) -> Dict[str, Any]:
        """获取市场概览

        Args:
            sector_codes: 板块代码列表

        Returns:
            市场概览字典
        """
        # 涨跌停统计
        limit_summary = self.limit_stats.get_market_limit_summary()

        # 板块对比
        sector_comparison = self.sector_index.compare_sectors(sector_codes)

        # 领涨板块
        leading = self.sector_index.find_leading_sector(sector_codes)

        # 板块轮动
        rotation = self.sector_index.detect_sector_rotation(sector_codes)

        return {
            "datetime": datetime.now(),
            "limit_summary": limit_summary,
            "sector_comparison": sector_comparison,
            "leading_sector": leading,
            "sector_rotation": rotation
        }

    def get_comprehensive_analysis(self, symbol: str, sector_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取综合分析

        Args:
            symbol: 股票代码
            sector_codes: 相关板块代码列表

        Returns:
            综合分析字典
        """
        result = {
            "symbol": symbol,
            "datetime": datetime.now(),
            "limit_analysis": self.get_limit_analysis(symbol)
        }

        if sector_codes:
            result["sector_analysis"] = {
                code: self.get_sector_analysis(code)
                for code in sector_codes
            }

        return result

    def clear(self, symbol: Optional[str] = None) -> None:
        """清理缓存数据

        Args:
            symbol: 股票代码，None表示清理全部
        """
        self.limit_stats.clear_cache(symbol)
        if symbol is None:
            self.sector_index.clear_cache(None)
