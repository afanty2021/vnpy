"""
涨跌停统计分析模块

统计股票的涨跌停情况，计算连板天数等。
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date

from ..objects.types import LimitStats, LimitType
from ..base import HistoricalAnalyzer


class LimitStatsAnalyzer(HistoricalAnalyzer):
    """
    涨跌停统计分析器

    统计股票的涨跌停情况，计算连板天数。
    """

    def __init__(self, cache_size: int = 1000) -> None:
        super().__init__(cache_size)
        self.limit_history: Dict[str, List[LimitStats]] = {}
        self.last_limit_type: Dict[str, LimitType] = {}

    def analyze(self, symbol: str, data: Dict[str, Any]) -> LimitStats:
        """分析涨跌停

        Args:
            symbol: 股票代码
            data: 包含价格、涨跌停信息的字典

        Returns:
            LimitStats对象
        """
        current_date = data.get("date", date.today())
        is_limit_up = data.get("is_limit_up", False)
        is_limit_down = data.get("is_limit_down", False)

        # 获取上一次的涨跌停状态
        last_type = self.last_limit_type.get(symbol, LimitType.NORMAL)

        # 计算连续天数
        if is_limit_up:
            if last_type == LimitType.LIMIT_UP:
                # 继续涨停
                last_days = self._get_last_limit_days(symbol, LimitType.LIMIT_UP)
                limit_up_days = last_days + 1
            else:
                # 首次涨停
                limit_up_days = 1
            limit_down_days = 0
            current_type = LimitType.LIMIT_UP
        elif is_limit_down:
            if last_type == LimitType.LIMIT_DOWN:
                # 继续跌停
                last_days = self._get_last_limit_days(symbol, LimitType.LIMIT_DOWN)
                limit_down_days = last_days + 1
            else:
                # 首次跌停
                limit_down_days = 1
            limit_up_days = 0
            current_type = LimitType.LIMIT_DOWN
        else:
            # 未涨跌停
            limit_up_days = 0
            limit_down_days = 0
            current_type = LimitType.NORMAL

        # 更新最后涨跌停类型
        self.last_limit_type[symbol] = current_type

        # 获取历史涨停次数
        limit_up_count = self._get_total_limit_count(symbol, LimitType.LIMIT_UP)
        limit_down_count = self._get_total_limit_count(symbol, LimitType.LIMIT_DOWN)

        if is_limit_up:
            limit_up_count += 1
        if is_limit_down:
            limit_down_count += 1

        # 创建统计对象
        stats = LimitStats(
            symbol=symbol,
            date=current_date,
            limit_up_days=limit_up_days,
            limit_down_days=limit_down_days,
            is_limit_up=is_limit_up,
            is_limit_down=is_limit_down,
            limit_up_count=limit_up_count,
            limit_down_count=limit_down_count
        )

        # 保存到历史
        if symbol not in self.limit_history:
            self.limit_history[symbol] = []
        self.limit_history[symbol].append(stats)

        # 限制历史大小
        if len(self.limit_history[symbol]) > self.cache_size:
            self.limit_history[symbol] = self.limit_history[symbol][-self.cache_size:]

        return stats

    def get_limit_stats(self, symbol: str) -> Optional[LimitStats]:
        """获取涨跌停统计

        Args:
            symbol: 股票代码

        Returns:
            最新的涨跌停统计
        """
        if symbol not in self.limit_history or not self.limit_history[symbol]:
            return None
        return self.limit_history[symbol][-1]

    def get_continuous_limit_up(self, symbol: str) -> int:
        """获取连续涨停天数

        Args:
            symbol: 股票代码

        Returns:
            连续涨停天数
        """
        stats = self.get_limit_stats(symbol)
        if stats:
            return stats.limit_up_days
        return 0

    def get_continuous_limit_down(self, symbol: str) -> int:
        """获取连续跌停天数

        Args:
            symbol: 股票代码

        Returns:
            连续跌停天数
        """
        stats = self.get_limit_stats(symbol)
        if stats:
            return stats.limit_down_days
        return 0

    def is_in_limit_up(self, symbol: str) -> bool:
        """是否在涨停中

        Args:
            symbol: 股票代码

        Returns:
            是否涨停
        """
        stats = self.get_limit_stats(symbol)
        if stats:
            return stats.is_limit_up
        return False

    def is_in_limit_down(self, symbol: str) -> bool:
        """是否在跌停中

        Args:
            symbol: 股票代码

        Returns:
            是否跌停
        """
        stats = self.get_limit_stats(symbol)
        if stats:
            return stats.is_limit_down
        return False

    def get_limit_formation(self, symbol: str, days: int = 5) -> Dict[str, Any]:
        """获取涨停形态

        分析最近的涨停形态特征。

        Args:
            symbol: 股票代码
            days: 分析天数

        Returns:
            涨停形态字典
        """
        if symbol not in self.limit_history or not self.limit_history[symbol]:
            return {}

        recent = self.limit_history[symbol][-days:]

        # 统计涨停次数
        limit_up_count = sum(1 for s in recent if s.is_limit_up)
        limit_down_count = sum(1 for s in recent if s.is_limit_down)

        # 计算最大连板
        max_consecutive = 0
        current_consecutive = 0

        for s in recent:
            if s.is_limit_up:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return {
            "symbol": symbol,
            "limit_up_count": limit_up_count,
            "limit_down_count": limit_down_count,
            "max_consecutive": max_consecutive,
            "current_consecutive": recent[-1].limit_up_days if recent else 0,
            "formation": self._classify_formation(limit_up_count, max_consecutive)
        }

    def get_market_limit_summary(self) -> Dict[str, Any]:
        """获取市场涨跌停汇总

        统计所有跟踪股票的涨跌停情况。

        Returns:
            市场汇总字典
        """
        total_stocks = len(self.limit_history)
        limit_up_stocks = 0
        limit_down_stocks = 0

        for symbol in self.limit_history:
            stats = self.get_limit_stats(symbol)
            if stats:
                if stats.is_limit_up:
                    limit_up_stocks += 1
                elif stats.is_limit_down:
                    limit_down_stocks += 1

        return {
            "total_stocks": total_stocks,
            "limit_up_stocks": limit_up_stocks,
            "limit_down_stocks": limit_down_stocks,
            "limit_up_ratio": limit_up_stocks / total_stocks * 100 if total_stocks > 0 else 0,
            "limit_down_ratio": limit_down_stocks / total_stocks * 100 if total_stocks > 0 else 0
        }

    def _get_last_limit_days(self, symbol: str, limit_type: LimitType) -> int:
        """获取上一次的连续天数"""
        if symbol not in self.limit_history or not self.limit_history[symbol]:
            return 0

        # 向前查找
        for stats in reversed(self.limit_history[symbol][:-1]):
            if limit_type == LimitType.LIMIT_UP:
                return stats.limit_up_days
            elif limit_type == LimitType.LIMIT_DOWN:
                return stats.limit_down_days

        return 0

    def _get_total_limit_count(self, symbol: str, limit_type: LimitType) -> int:
        """获取历史涨跌停总次数"""
        if symbol not in self.limit_history:
            return 0

        if limit_type == LimitType.LIMIT_UP:
            return sum(s.limit_up_count for s in self.limit_history[symbol])
        elif limit_type == LimitType.LIMIT_DOWN:
            return sum(s.limit_down_count for s in self.limit_history[symbol])

        return 0

    def _classify_formation(self, limit_count: int, max_consecutive: int) -> str:
        """分类涨停形态"""
        if max_consecutive >= 5:
            return "龙头"
        elif max_consecutive >= 3:
            return "强势"
        elif max_consecutive >= 2:
            return "接力"
        elif limit_count >= 3:
            return "反复"
        else:
            return "首板"
