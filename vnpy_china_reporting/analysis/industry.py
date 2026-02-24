"""
行业分析器模块

提供行业分布分析、行业轮动分析等功能。
"""

from typing import List, Dict, Optional
from collections import defaultdict
from ..core.models import PositionRecord


class IndustryAnalyzer:
    """
    行业分析器

    分析持仓的行业分布、行业轮动等。
    """

    def analyze_distribution(
        self,
        positions: List[PositionRecord]
    ) -> Dict:
        """
        分析行业分布

        Args:
            positions: 持仓列表

        Returns:
            行业分布统计
        """
        if not positions:
            return {"industries": [], "distribution": {}}

        # 按行业分组
        industry_groups: Dict[str, List[PositionRecord]] = defaultdict(list)
        for pos in positions:
            industry = getattr(pos, 'industry', None) or "未知"
            industry_groups[industry].append(pos)

        # 计算各行业统计
        total_value = sum(p.market_value for p in positions)
        total_pnl = sum(p.unrealized_pnl for p in positions)

        distribution: Dict[str, Dict] = {}
        industries = []

        for industry, pos_list in industry_groups.items():
            industries.append(industry)

            value = sum(p.market_value for p in pos_list)
            pnl = sum(p.unrealized_pnl for p in pos_list)

            distribution[industry] = {
                "value": value,
                "ratio": value / total_value if total_value > 0 else 0.0,
                "count": len(pos_list),
                "pnl": pnl,
                "pnl_ratio": pnl / total_pnl if total_pnl != 0 else 0.0,
                "avg_pnl": pnl / len(pos_list) if pos_list else 0.0
            }

        return {
            "industries": industries,
            "distribution": distribution,
            "total_industries": len(industries)
        }

    def calculate_industry_return(
        self,
        positions: List[PositionRecord]
    ) -> Dict:
        """
        计算行业收益率

        Args:
            positions: 持仓列表

        Returns:
            行业收益率
        """
        if not positions:
            return {}

        # 按行业分组
        industry_groups: Dict[str, List[PositionRecord]] = defaultdict(list)
        for pos in positions:
            industry = getattr(pos, 'industry', None) or "未知"
            industry_groups[industry].append(pos)

        industry_returns: Dict[str, float] = {}

        for industry, pos_list in industry_groups.items():
            if not pos_list:
                continue

            # 计算行业平均收益率（按市值加权）
            total_value = sum(p.market_value for p in pos_list)
            weighted_return = sum(
                p.unrealized_pnl_ratio * p.market_value / total_value
                for p in pos_list
                if total_value > 0
            )

            industry_returns[industry] = weighted_return

        return industry_returns

    def calculate_industry_correlation(
        self,
        positions: List[PositionRecord]
    ) -> Dict:
        """
        计算行业间相关性

        Args:
            positions: 持仓列表

        Returns:
            行业相关性矩阵
        """
        # 简化实现，实际需要历史收益率数据
        return {}

    def get_industry_summary(
        self,
        positions: List[PositionRecord]
    ) -> Dict:
        """
        获取行业分析摘要

        Args:
            positions: 持仓列表

        Returns:
            行业分析摘要
        """
        if not positions:
            return {
                "total_industries": 0,
                "top_industry": None,
                "worst_industry": None
            }

        distribution = self.analyze_distribution(positions)
        returns = self.calculate_industry_return(positions)

        if not returns:
            return {
                "total_industries": distribution.get("total_industries", 0),
                "top_industry": None,
                "worst_industry": None
            }

        # 找出表现最好和最差的行业
        sorted_industries = sorted(
            returns.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return {
            "total_industries": distribution.get("total_industries", 0),
            "top_industry": sorted_industries[0][0] if sorted_industries else None,
            "top_industry_return": sorted_industries[0][1] if sorted_industries else 0.0,
            "worst_industry": sorted_industries[-1][0] if sorted_industries else None,
            "worst_industry_return": sorted_industries[-1][1] if sorted_industries else 0.0
        }

    def analyze_sector_allocation(
        self,
        positions: List[PositionRecord]
    ) -> Dict:
        """
        分析板块配置

        Args:
            positions: 持仓列表

        Returns:
            板块配置分析
        """
        if not positions:
            return {"sectors": {}, "overweight": [], "underweight": []}

        # 按行业分组
        industry_groups: Dict[str, List[PositionRecord]] = defaultdict(list)
        for pos in positions:
            industry = getattr(pos, 'industry', None) or "未知"
            industry_groups[industry].append(pos)

        # 计算各板块占比
        total_value = sum(p.market_value for p in positions)
        sectors: Dict[str, Dict] = {}

        for industry, pos_list in industry_groups.items():
            value = sum(p.market_value for p in pos_list)
            sectors[industry] = {
                "value": value,
                "weight": value / total_value if total_value > 0 else 0.0,
                "count": len(pos_list)
            }

        # 假设有一个基准配置（如行业指数权重）
        # 简化：使用等权配置作为基准
        benchmark_weight = 1.0 / len(sectors) if sectors else 0.0

        overweight = [
            {"industry": k, "weight": v["weight"] - benchmark_weight}
            for k, v in sectors.items()
            if v["weight"] > benchmark_weight * 1.2  # 超过基准20%视为超配
        ]

        underweight = [
            {"industry": k, "weight": v["weight"] - benchmark_weight}
            for k, v in sectors.items()
            if v["weight"] < benchmark_weight * 0.8  # 低于基准20%视为低配
        ]

        return {
            "sectors": sectors,
            "benchmark_weight": benchmark_weight,
            "overweight": overweight,
            "underweight": underweight
        }
