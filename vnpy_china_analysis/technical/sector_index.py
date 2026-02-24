"""
板块指数分析模块

计算板块指数，分析板块轮动。
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from ..objects.types import SectorIndexData
from ..base import HistoricalAnalyzer


class SectorIndexAnalyzer(HistoricalAnalyzer):
    """
    板块指数分析器

    计算板块指数，分析板块轮动特征。
    """

    def __init__(self, cache_size: int = 1000) -> None:
        super().__init__(cache_size)
        self.sector_history: Dict[str, List[SectorIndexData]] = {}
        self.sector_stocks: Dict[str, List[str]] = {}  # 板块包含的股票

    def register_sector(self, sector_code: str, sector_name: str, stocks: List[str]) -> None:
        """注册板块

        设置板块的成分股。

        Args:
            sector_code: 板块代码
            sector_name: 板块名称
            stocks: 成分股列表
        """
        self.sector_stocks[sector_code] = stocks

    def calculate_index(self, sector_code: str, stock_data: Dict[str, Dict[str, Any]]) -> SectorIndexData:
        """计算板块指数

        根据成分股数据计算板块指数。

        Args:
            sector_code: 板块代码
            stock_data: 股票数据字典 {symbol: {price, change, volume, ...}}

        Returns:
            SectorIndexData对象
        """
        sector_name = sector_code  # 简化处理
        if sector_code in self.sector_stocks:
            stocks = self.sector_stocks[sector_code]
        else:
            stocks = list(stock_data.keys())

        if not stocks:
            return SectorIndexData(
                sector_code=sector_code,
                sector_name=sector_name,
                datetime=datetime.now()
            )

        # 计算加权指数
        total_change = 0.0
        total_volume = 0
        total_turnover = 0.0
        leading_stocks = []

        changes = []
        for symbol in stocks:
            if symbol not in stock_data:
                continue

            data = stock_data[symbol]
            change = data.get("change_pct", 0)
            volume = data.get("volume", 0)
            turnover = data.get("turnover", 0)

            changes.append((symbol, change))
            total_change += change
            total_volume += volume
            total_turnover += turnover

        # 获取领涨股票
        changes.sort(key=lambda x: x[1], reverse=True)
        leading_stocks = [s[0] for s in changes[:5]]

        # 计算指数
        avg_change = total_change / len(stocks) if stocks else 0

        index_data = SectorIndexData(
            sector_code=sector_code,
            sector_name=sector_name,
            datetime=datetime.now(),
            index_value=avg_change,  # 使用平均涨跌幅作为指数值
            change_pct=avg_change,
            volume=total_volume,
            turnover=total_turnover / len(stocks) if stocks else 0,
            leading_stocks=leading_stocks
        )

        # 保存历史
        if sector_code not in self.sector_history:
            self.sector_history[sector_code] = []
        self.sector_history[sector_code].append(index_data)

        # 限制历史大小
        if len(self.sector_history[sector_code]) > self.cache_size:
            self.sector_history[sector_code] = self.sector_history[sector_code][-self.cache_size:]

        return index_data

    def analyze(self, sector_code: str, data: Dict[str, Any]) -> SectorIndexData:
        """分析板块数据

        Args:
            sector_code: 板块代码
            data: 板块数据字典

        Returns:
            SectorIndexData对象
        """
        index_data = SectorIndexData(
            sector_code=sector_code,
            sector_name=data.get("sector_name", sector_code),
            datetime=data.get("datetime", datetime.now()),
            index_value=data.get("index_value", 0),
            change_pct=data.get("change_pct", 0),
            volume=data.get("volume", 0),
            turnover=data.get("turnover", 0),
            leading_stocks=data.get("leading_stocks", [])
        )

        # 保存历史
        if sector_code not in self.sector_history:
            self.sector_history[sector_code] = []
        self.sector_history[sector_code].append(index_data)

        return index_data

    def get_sector_index(self, sector_code: str) -> Optional[SectorIndexData]:
        """获取板块指数

        Args:
            sector_code: 板块代码

        Returns:
            最新的板块指数数据
        """
        if sector_code not in self.sector_history or not self.sector_history[sector_code]:
            return None
        return self.sector_history[sector_code][-1]

    def get_sector_trend(self, sector_code: str, periods: int = 5) -> Dict[str, Any]:
        """获取板块趋势

        分析板块的短期趋势。

        Args:
            sector_code: 板块代码
            periods: 统计周期

        Returns:
            趋势字典
        """
        if sector_code not in self.sector_history or not self.sector_history[sector_code]:
            return {"trend": "unknown"}

        recent = self.sector_history[sector_code][-periods:]

        if not recent:
            return {"trend": "unknown"}

        changes = [s.change_pct for s in recent]
        avg_change = sum(changes) / len(changes)

        # 判断趋势
        if avg_change > 2:
            trend = "strong_rally"
        elif avg_change > 0.5:
            trend = "rally"
        elif avg_change < -2:
            trend = "strong_decline"
        elif avg_change < -0.5:
            trend = "decline"
        else:
            trend = "consolidation"

        return {
            "sector_code": sector_code,
            "trend": trend,
            "avg_change": avg_change,
            "changes": changes
        }

    def compare_sectors(self, sector_codes: List[str]) -> List[Dict[str, Any]]:
        """对比多个板块

        Args:
            sector_codes: 板块代码列表

        Returns:
            对比结果列表
        """
        results = []

        for code in sector_codes:
            index = self.get_sector_index(code)
            trend = self.get_sector_trend(code)

            if index:
                results.append({
                    "sector_code": code,
                    "sector_name": index.sector_name,
                    "change_pct": index.change_pct,
                    "volume": index.volume,
                    "trend": trend.get("trend", "unknown"),
                    "leading_stocks": index.leading_stocks
                })

        # 按涨跌幅排序
        results.sort(key=lambda x: x["change_pct"], reverse=True)

        return results

    def find_leading_sector(self, sector_codes: List[str]) -> Optional[Dict[str, Any]]:
        """找到领涨板块

        Args:
            sector_codes: 板块代码列表

        Returns:
            领涨板块信息
        """
        comparison = self.compare_sectors(sector_codes)

        if comparison:
            return comparison[0]

        return None

    def detect_sector_rotation(self, sector_codes: List[str], window: int = 3) -> Dict[str, Any]:
        """检测板块轮动

        分析板块之间的轮动规律。

        Args:
            sector_codes: 板块代码列表
            window: 窗口大小

        Returns:
            轮动分析结果
        """
        if not sector_codes:
            return {}

        # 获取每个板块的趋势
        trends = {}
        for code in sector_codes:
            trend_data = self.get_sector_trend(code, periods=window)
            trends[code] = trend_data.get("avg_change", 0)

        # 找到最强和最弱的板块
        sorted_sectors = sorted(trends.items(), key=lambda x: x[1], reverse=True)

        if not sorted_sectors:
            return {}

        strongest = sorted_sectors[0]
        weakest = sorted_sectors[-1]

        return {
            "strongest_sector": strongest[0],
            "strongest_change": strongest[1],
            "weakest_sector": weakest[0],
            "weakest_change": weakest[1],
            "rotation_signal": "sector_rotation" if abs(strongest[1] - weakest[1]) > 3 else "sector_aligned",
            "sector_changes": trends
        }
