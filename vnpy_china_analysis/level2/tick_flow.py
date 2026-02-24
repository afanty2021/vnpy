"""
逐笔成交分析模块

分析每一笔成交的详细信息，识别交易模式。
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..objects.types import TickFlowData
from ..base import RealtimeAnalyzer


class TickFlowAnalyzer(RealtimeAnalyzer):
    """
    逐笔成交分析器

    分析每一笔成交的详细信息，识别交易模式和异常交易。
    """

    def __init__(self, cache_size: int = 2000) -> None:
        super().__init__(cache_size)
        self.tick_history: Dict[str, List[TickFlowData]] = {}

    def analyze(self, symbol: str, data: Dict[str, Any]) -> TickFlowData:
        """分析逐笔成交

        Args:
            symbol: 股票代码
            data: 逐笔成交数据字典

        Returns:
            TickFlowData对象
        """
        tick = TickFlowData(
            symbol=symbol,
            datetime=data.get("datetime", datetime.now()),
            price=data.get("price", 0.0),
            volume=data.get("volume", 0),
            amount=data.get("amount", 0.0),
            direction=data.get("direction", "buy"),
            function_code=data.get("function_code", 0)
        )

        # 更新历史
        if symbol not in self.tick_history:
            self.tick_history[symbol] = []
        self.tick_history[symbol].append(tick)

        # 限制历史大小
        if len(self.tick_history[symbol]) > self.cache_size:
            self.tick_history[symbol] = self.tick_history[symbol][-self.cache_size:]

        return tick

    def get_transaction_summary(self, symbol: str, minutes: int = 5) -> Dict[str, Any]:
        """获取成交汇总

        统计最近N分钟的成交情况。

        Args:
            symbol: 股票代码
            minutes: 统计分钟数

        Returns:
            成交汇总字典
        """
        if symbol not in self.tick_history or not self.tick_history[symbol]:
            return {}

        now = datetime.now()
        cutoff_time = now - timedelta(minutes=minutes)

        recent_ticks = [
            t for t in self.tick_history[symbol]
            if t.datetime >= cutoff_time
        ]

        if not recent_ticks:
            return {}

        # 统计买入
        buy_ticks = [t for t in recent_ticks if t.direction == "buy"]
        sell_ticks = [t for t in recent_ticks if t.direction == "sell"]

        return {
            "symbol": symbol,
            "time_range": f"{minutes}min",
            "total_count": len(recent_ticks),
            "buy_count": len(buy_ticks),
            "sell_count": len(sell_ticks),
            "total_volume": sum(t.volume for t in recent_ticks),
            "buy_volume": sum(t.volume for t in buy_ticks),
            "sell_volume": sum(t.volume for t in sell_ticks),
            "total_amount": sum(t.amount for t in recent_ticks),
            "buy_amount": sum(t.amount for t in buy_ticks),
            "sell_amount": sum(t.amount for t in sell_ticks),
            "net_volume": sum(t.volume for t in buy_ticks) - sum(t.volume for t in sell_ticks),
            "avg_price": sum(t.amount for t in recent_ticks) / sum(t.volume for t in recent_ticks) if sum(t.volume for t in recent_ticks) > 0 else 0
        }

    def detect_large_trade(self, symbol: str, threshold: float = 1000000) -> List[Dict[str, Any]]:
        """检测大单交易

        检测超过阈值的大单成交。

        Args:
            symbol: 股票代码
            threshold: 大单阈值（元）

        Returns:
            大单列表
        """
        large_trades = []

        if symbol not in self.tick_history:
            return large_trades

        for tick in self.tick_history[symbol]:
            if tick.amount >= threshold:
                large_trades.append({
                    "datetime": tick.datetime,
                    "price": tick.price,
                    "volume": tick.volume,
                    "amount": tick.amount,
                    "direction": tick.direction,
                    "function_code": tick.function_code
                })

        return sorted(large_trades, key=lambda x: x["amount"], reverse=True)

    def get_trade_distribution(self, symbol: str, bins: int = 10) -> Dict[str, Any]:
        """获取成交分布

        分析成交量的分布情况。

        Args:
            symbol: 股票代码
            bins: 分箱数量

        Returns:
            成交分布字典
        """
        if symbol not in self.tick_history or not self.tick_history[symbol]:
            return {}

        volumes = [t.volume for t in self.tick_history[symbol]]

        if not volumes:
            return {}

        min_vol = min(volumes)
        max_vol = max(volumes)
        bin_size = (max_vol - min_vol) / bins if bins > 0 else 1

        distribution = [0] * bins
        for vol in volumes:
            bin_idx = min(int((vol - min_vol) / bin_size), bins - 1) if bin_size > 0 else 0
            distribution[bin_idx] += 1

        return {
            "symbol": symbol,
            "total_trades": len(volumes),
            "min_volume": min_vol,
            "max_volume": max_vol,
            "avg_volume": sum(volumes) / len(volumes),
            "distribution": distribution,
            "bins": bins
        }

    def get_transaction_speed(self, symbol: str, window_seconds: int = 60) -> Dict[str, Any]:
        """获取交易速度

        分析最近一段时间内的交易频率和速度。

        Args:
            symbol: 股票代码
            window_seconds: 统计窗口（秒）

        Returns:
            交易速度字典
        """
        if symbol not in self.tick_history or not self.tick_history[symbol]:
            return {}

        now = datetime.now()
        cutoff_time = now - timedelta(seconds=window_seconds)

        recent_ticks = [
            t for t in self.tick_history[symbol]
            if t.datetime >= cutoff_time
        ]

        if not recent_ticks:
            return {}

        # 计算时间跨度
        time_span = (recent_ticks[-1].datetime - recent_ticks[0].datetime).total_seconds()
        time_span = max(time_span, 1)  # 避免除零

        return {
            "symbol": symbol,
            "window_seconds": window_seconds,
            "trade_count": len(recent_ticks),
            "trade_speed": len(recent_ticks) / time_span * 60,  # 每分钟交易笔数
            "volume_speed": sum(t.volume for t in recent_ticks) / time_span * 60,  # 每分钟成交量
            "amount_speed": sum(t.amount for t in recent_ticks) / time_span * 60,  # 每分钟成交额
        }

    def identify_trade_pattern(self, symbol: str) -> Dict[str, Any]:
        """识别交易模式

        识别当前市场的交易模式特征。

        Args:
            symbol: 股票代码

        Returns:
            交易模式字典
        """
        if symbol not in self.tick_history or not self.tick_history[symbol]:
            return {"pattern": "unknown"}

        recent = self.get_transaction_summary(symbol, minutes=5)
        speed = self.get_transaction_speed(symbol, window_seconds=60)

        if not recent or not speed:
            return {"pattern": "unknown"}

        # 判断交易模式
        if speed.get("trade_speed", 0) > 10:
            if recent.get("net_volume", 0) > 0:
                pattern = "active_buy"
            else:
                pattern = "active_sell"
        elif speed.get("trade_speed", 0) > 3:
            pattern = "normal"
        else:
            pattern = "quiet"

        return {
            "pattern": pattern,
            "trade_speed": speed.get("trade_speed", 0),
            "net_volume": recent.get("net_volume", 0),
            "buy_ratio": recent.get("buy_count", 0) / max(recent.get("total_count", 1), 1)
        }
