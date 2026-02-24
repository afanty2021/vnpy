"""
委托队列分析模块

分析十档买卖盘的委托队列变化，识别支撑阻力位。
"""

from typing import List, Dict, Optional, Any
from datetime import datetime

from ..objects.types import OrderQueueData
from ..base import RealtimeAnalyzer


class OrderQueueAnalyzer(RealtimeAnalyzer):
    """
    委托队列分析器

    分析十档买卖盘的委托队列变化，识别支撑阻力位。
    """

    def __init__(self, cache_size: int = 500) -> None:
        super().__init__(cache_size)
        self.queue_history: Dict[str, List[OrderQueueData]] = {}

    def analyze(self, symbol: str, data: Dict[str, Any]) -> OrderQueueData:
        """分析委托队列

        Args:
            symbol: 股票代码
            data: 包含十档行情的字典

        Returns:
            OrderQueueData对象
        """
        order_queue = OrderQueueData(
            symbol=symbol,
            datetime=datetime.now(),
            ask_prices=data.get("ask_prices", []),
            ask_volumes=data.get("ask_volumes", []),
            ask_queue=data.get("ask_queue", []),
            bid_prices=data.get("bid_prices", []),
            bid_volumes=data.get("bid_volumes", []),
            bid_queue=data.get("bid_queue", [])
        )

        # 更新历史
        if symbol not in self.queue_history:
            self.queue_history[symbol] = []
        self.queue_history[symbol].append(order_queue)

        # 限制历史大小
        if len(self.queue_history[symbol]) > self.cache_size:
            self.queue_history[symbol] = self.queue_history[symbol][-self.cache_size:]

        return order_queue

    def get_support_level(self, symbol: str) -> Dict[str, Any]:
        """识别支撑位

        通过分析买盘委托量，识别强支撑价位。

        Returns:
            支撑位信息字典
        """
        if symbol not in self.queue_history or not self.queue_history[symbol]:
            return {}

        latest = self.queue_history[symbol][-1]

        # 计算各档位的委托强度
        max_strength = 0.0
        support_price = 0.0
        support_volume = 0

        for i, (price, volume) in enumerate(zip(latest.bid_prices, latest.bid_volumes)):
            if volume <= 0:
                continue

            # 计算强度（价格越接近现价，权重越高）
            strength = volume * (1 - i * 0.1)

            if strength > max_strength:
                max_strength = strength
                support_price = price
                support_volume = volume

        return {
            "price": support_price,
            "volume": support_volume,
            "strength": max_strength,
            "level": self._calculate_level(max_strength)
        }

    def get_resistance_level(self, symbol: str) -> Dict[str, Any]:
        """识别阻力位

        通过分析卖盘委托量，识别强阻力价位。

        Returns:
            阻力位信息字典
        """
        if symbol not in self.queue_history or not self.queue_history[symbol]:
            return {}

        latest = self.queue_history[symbol][-1]

        max_strength = 0.0
        resistance_price = 0.0
        resistance_volume = 0

        for i, (price, volume) in enumerate(zip(latest.ask_prices, latest.ask_volumes)):
            if volume <= 0:
                continue

            # 计算强度（价格越接近现价，权重越高）
            strength = volume * (1 - i * 0.1)

            if strength > max_strength:
                max_strength = strength
                resistance_price = price
                resistance_volume = volume

        return {
            "price": resistance_price,
            "volume": resistance_volume,
            "strength": max_strength,
            "level": self._calculate_level(max_strength)
        }

    def get_price_depth(self, symbol: str) -> Dict[str, Any]:
        """计算价格深度

        分析买卖盘的深度情况。

        Returns:
            深度信息字典
        """
        if symbol not in self.queue_history or not self.queue_history[symbol]:
            return {}

        latest = self.queue_history[symbol][-1]

        # 计算买卖盘总量
        bid_total = sum(latest.bid_volumes)
        ask_total = sum(latest.ask_volumes)

        # 计算加权平均价格
        bid_wap = sum(p * v for p, v in zip(latest.bid_prices, latest.bid_volumes)) / bid_total if bid_total > 0 else 0
        ask_wap = sum(p * v for p, v in zip(latest.ask_prices, latest.ask_volumes)) / ask_total if ask_total > 0 else 0

        return {
            "bid_total": bid_total,
            "ask_total": ask_total,
            "depth_ratio": bid_total / ask_total if ask_total > 0 else 0,
            "bid_wap": bid_wap,
            "ask_wap": ask_wap,
            "spread": ask_wap - bid_wap,
            "spread_pct": (ask_wap - bid_wap) / bid_wap * 100 if bid_wap > 0 else 0
        }

    def detect_large_order(self, symbol: str, threshold: float = 500000) -> List[Dict[str, Any]]:
        """检测大单委托

        检测超过阈值的大单委托。

        Args:
            symbol: 股票代码
            threshold: 大单阈值（元）

        Returns:
            大单列表
        """
        large_orders = []

        if symbol not in self.queue_history:
            return large_orders

        latest = self.queue_history[symbol][-1]

        # 检查卖盘大单
        for i, (price, volume) in enumerate(zip(latest.ask_prices, latest.ask_volumes)):
            amount = price * volume
            if amount >= threshold:
                large_orders.append({
                    "side": "ask",
                    "level": i + 1,
                    "price": price,
                    "volume": volume,
                    "amount": amount
                })

        # 检查买盘大单
        for i, (price, volume) in enumerate(zip(latest.bid_prices, latest.bid_volumes)):
            amount = price * volume
            if amount >= threshold:
                large_orders.append({
                    "side": "bid",
                    "level": i + 1,
                    "price": price,
                    "volume": volume,
                    "amount": amount
                })

        return sorted(large_orders, key=lambda x: x["amount"], reverse=True)

    def _calculate_level(self, strength: float) -> str:
        """计算支撑/阻力强度等级

        Args:
            strength: 强度值

        Returns:
            强度等级
        """
        if strength > 1000000:
            return "strong"
        elif strength > 500000:
            return "medium"
        elif strength > 100000:
            return "weak"
        return "minimal"
