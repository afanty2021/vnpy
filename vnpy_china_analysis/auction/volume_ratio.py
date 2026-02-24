"""
量比计算模块

计算集合竞价量比指标。
"""

from typing import Dict, Any, Optional
from datetime import datetime, date

from ..base import HistoricalAnalyzer


class VolumeRatioCalculator(HistoricalAnalyzer):
    """
    量比计算器

    计算集合竞价的量比指标。
    """

    def __init__(self, cache_size: int = 500) -> None:
        super().__init__(cache_size)
        self.avg_volume: Dict[str, float] = {}  # 股票的平均成交量

    def calculate(self, symbol: str, auction_volume: int, avg_volume: Optional[float] = None) -> float:
        """计算量比

        Args:
            symbol: 股票代码
            auction_volume: 集合竞价成交量
            avg_volume: 平均成交量，None表示使用历史计算

        Returns:
            量比值
        """
        # 使用提供的平均值或计算历史平均值
        if avg_volume is None:
            avg_volume = self._calculate_avg_volume(symbol)

        if avg_volume is None or avg_volume == 0:
            return 0.0

        return auction_volume / avg_volume

    def update_avg_volume(self, symbol: str, volume: int) -> None:
        """更新平均成交量

        Args:
            symbol: 股票代码
            volume: 当日成交量
        """
        # 简单移动平均
        if symbol not in self.avg_volume:
            self.avg_volume[symbol] = volume
        else:
            # 5日简单移动平均
            self.avg_volume[symbol] = self.avg_volume[symbol] * 0.8 + volume * 0.2

    def _calculate_avg_volume(self, symbol: str) -> Optional[float]:
        """计算历史平均成交量

        Args:
            symbol: 股票代码

        Returns:
            平均成交量
        """
        cached = self.get_cached_data(symbol)

        if not cached:
            return self.avg_volume.get(symbol)

        volumes = [d.get("volume", 0) for d in cached]

        if not volumes:
            return self.avg_volume.get(symbol)

        return sum(volumes) / len(volumes)

    def analyze_volume_ratio(self, volume_ratio: float) -> Dict[str, Any]:
        """分析量比含义

        Args:
            volume_ratio: 量比值

        Returns:
            分析结果字典
        """
        if volume_ratio >= 5:
            interpretation = "大幅放量"
            signal = "strong"
        elif volume_ratio >= 2:
            interpretation = "明显放量"
            signal = "moderate"
        elif volume_ratio >= 0.5:
            interpretation = "正常"
            signal = "normal"
        elif volume_ratio >= 0.2:
            interpretation = "明显缩量"
            signal = "weak"
        else:
            interpretation = "大幅缩量"
            signal = "very_weak"

        return {
            "volume_ratio": volume_ratio,
            "interpretation": interpretation,
            "signal": signal
        }
