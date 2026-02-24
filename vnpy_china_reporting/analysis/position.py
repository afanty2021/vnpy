"""
持仓分析器模块

提供持仓分布、行业分布、盈亏分布、集中度等分析功能。
"""

from typing import List, Dict
from collections import defaultdict
from ..core.models import PositionRecord, PositionAnalysis


class PositionAnalyzer:
    """
    持仓分析器

    分析持仓分布、行业分布、盈亏分布等。
    """

    def analyze(
        self,
        positions: List[PositionRecord]
    ) -> PositionAnalysis:
        """
        综合持仓分析

        Args:
            positions: 持仓列表

        Returns:
            PositionAnalysis对象
        """
        # 分布分析
        distribution = self.analyze_distribution(positions)

        # 行业分析
        industry_dist = self.analyze_industry(positions)

        # 盈亏分析
        pnl_analysis = self.analyze_pnl(positions)

        # 集中度分析
        concentration = self.analyze_concentration(positions)

        # 获取前十大持仓
        top_holdings = self.get_top_positions(positions, 10)

        return PositionAnalysis(
            total_positions=distribution["total_positions"],
            total_market_value=distribution["total_market_value"],
            top_holdings=top_holdings,
            concentration=concentration["ratio"],
            industry_distribution=industry_dist
        )

    def analyze_distribution(
        self,
        positions: List[PositionRecord]
    ) -> Dict:
        """
        分析持仓市值分布

        Args:
            positions: 持仓列表

        Returns:
            分布统计字典
        """
        if not positions:
            return {
                "total_positions": 0,
                "total_market_value": 0.0,
                "large_position_ratio": 0.0,
                "medium_position_ratio": 0.0,
                "small_position_ratio": 0.0
            }

        total_value = sum(p.market_value for p in positions)

        # 分类：大市值(>10万)、中市值(3-10万)、小市值(<3万)
        large = sum(p.market_value for p in positions if p.market_value > 100000)
        medium = sum(p.market_value for p in positions
                    if 30000 <= p.market_value <= 100000)
        small = sum(p.market_value for p in positions if p.market_value < 30000)

        return {
            "total_positions": len(positions),
            "total_market_value": total_value,
            "large_position_ratio": large / total_value if total_value > 0 else 0.0,
            "medium_position_ratio": medium / total_value if total_value > 0 else 0.0,
            "small_position_ratio": small / total_value if total_value > 0 else 0.0
        }

    def analyze_industry(
        self,
        positions: List[PositionRecord]
    ) -> Dict[str, Dict]:
        """
        分析行业分布

        Args:
            positions: 持仓列表

        Returns:
            {行业: {value, ratio, count, avg_pnl}}
        """
        if not positions:
            return {}

        # 按行业分组
        industry_groups: Dict[str, List[PositionRecord]] = defaultdict(list)
        for pos in positions:
            # 使用属性获取行业，如果没有则使用"未知"
            industry = getattr(pos, 'industry', None) or "未知"
            industry_groups[industry].append(pos)

        # 计算各行业统计
        total_value = sum(p.market_value for p in positions)
        industry_data: Dict[str, Dict] = {}

        for industry, pos_list in industry_groups.items():
            value = sum(p.market_value for p in pos_list)
            pnls = [p.unrealized_pnl for p in pos_list]
            pnl_ratios = [p.unrealized_pnl_ratio for p in pos_list]

            industry_data[industry] = {
                "value": value,
                "ratio": value / total_value if total_value > 0 else 0.0,
                "count": len(pos_list),
                "avg_pnl": sum(pnls) / len(pnls) if pnls else 0.0,
                "pnl_ratio": sum(pnl_ratios) / len(pnl_ratios) if pnl_ratios else 0.0
            }

        return industry_data

    def analyze_pnl(
        self,
        positions: List[PositionRecord]
    ) -> Dict:
        """
        分析盈亏分布

        Args:
            positions: 持仓列表

        Returns:
            盈亏统计字典
        """
        if not positions:
            return {
                "profitable_count": 0,
                "loss_count": 0,
                "total_pnl": 0.0,
                "best_pnl": 0.0,
                "worst_pnl": 0.0
            }

        profitable = [p for p in positions if p.unrealized_pnl > 0]
        loss = [p for p in positions if p.unrealized_pnl < 0]

        pnls = [p.unrealized_pnl for p in positions]

        return {
            "profitable_count": len(profitable),
            "loss_count": len(loss),
            "total_pnl": sum(pnls),
            "avg_pnl": sum(pnls) / len(pnls) if pnls else 0.0,
            "best_pnl": max(pnls) if pnls else 0.0,
            "worst_pnl": min(pnls) if pnls else 0.0
        }

    def analyze_concentration(
        self,
        positions: List[PositionRecord]
    ) -> Dict:
        """
        分析持仓集中度

        Args:
            positions: 持仓列表

        Returns:
            {ratio: 前十大持仓占比, hhi: 赫芬达尔指数}
        """
        if not positions:
            return {"ratio": 0.0, "hhi": 0.0}

        # 按市值排序
        sorted_positions = sorted(
            positions,
            key=lambda p: p.market_value,
            reverse=True
        )

        total_value = sum(p.market_value for p in positions)

        # 前十大持仓占比
        top10_value = sum(
            p.market_value for p in sorted_positions[:10]
        )
        concentration_ratio = top10_value / total_value if total_value > 0 else 0.0

        # 赫芬达尔指数（HHI）
        # HHI = sum(权重^2)，范围[1/n, 1]，越接近1越集中
        weights = [p.market_value / total_value for p in positions if total_value > 0]
        hhi = sum(w ** 2 for w in weights)

        return {
            "ratio": concentration_ratio,
            "hhi": hhi
        }

    def get_top_positions(
        self,
        positions: List[PositionRecord],
        top_n: int = 10
    ) -> List[Dict]:
        """
        获取前N大持仓

        Args:
            positions: 持仓列表
            top_n: 前N名

        Returns:
            前N持仓列表
        """
        sorted_positions = sorted(
            positions,
            key=lambda p: p.market_value,
            reverse=True
        )

        total_value = sum(p.market_value for p in positions)

        result = []
        for p in sorted_positions[:top_n]:
            weight = p.market_value / total_value if total_value > 0 else 0.0
            result.append({
                "代码": p.symbol,
                "名称": p.name,
                "市值": f"{p.market_value:.2f}",
                "占比": f"{weight:.2%}",
                "盈亏": f"{p.unrealized_pnl:.2f}",
                "盈亏比例": f"{p.unrealized_pnl_ratio:.2%}"
            })

        return result
