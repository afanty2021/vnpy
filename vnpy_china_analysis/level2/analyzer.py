"""
Level-2综合分析器

整合所有Level-2行情分析功能。
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from .order_queue import OrderQueueAnalyzer
from .tick_flow import TickFlowAnalyzer
from .main_force import MainForceAnalyzer


class Level2Analyzer:
    """
    Level-2行情综合分析器

    整合委托队列、逐笔成交、主力动向等分析功能。
    """

    def __init__(self) -> None:
        """构造函数"""
        self.order_queue = OrderQueueAnalyzer()
        self.tick_flow = TickFlowAnalyzer()
        self.main_force = MainForceAnalyzer()

    def update(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新数据并返回分析结果

        Args:
            symbol: 股票代码
            data: Level-2数据字典

        Returns:
            综合分析结果字典
        """
        results = {
            "symbol": symbol,
            "datetime": datetime.now()
        }

        # 更新委托队列数据
        if "order_queue" in data:
            order_queue_data = self.order_queue.analyze(symbol, data["order_queue"])
            results["order_queue"] = order_queue_data

            # 添加支撑阻力位分析
            results["support_level"] = self.order_queue.get_support_level(symbol)
            results["resistance_level"] = self.order_queue.get_resistance_level(symbol)
            results["price_depth"] = self.order_queue.get_price_depth(symbol)

        # 更新逐笔成交数据
        if "tick" in data:
            tick_data = self.tick_flow.analyze(symbol, data["tick"])
            results["tick_flow"] = tick_data

            # 添加成交分析
            results["transaction_summary"] = self.tick_flow.get_transaction_summary(symbol)
            results["trade_pattern"] = self.tick_flow.identify_trade_pattern(symbol)

        # 更新主力动向
        if "tick" in data:
            main_force_data = self.main_force.analyze(symbol, data)
            results["main_force"] = main_force_data

            # 添加主力趋势
            results["main_force_trend"] = self.main_force.get_main_force_trend(symbol)
            results["main_force_action"] = self.main_force.detect_main_force_action(symbol)

        return results

    def get_order_queue_analysis(self, symbol: str) -> Dict[str, Any]:
        """获取委托队列分析

        Args:
            symbol: 股票代码

        Returns:
            分析结果字典
        """
        return {
            "support_level": self.order_queue.get_support_level(symbol),
            "resistance_level": self.order_queue.get_resistance_level(symbol),
            "price_depth": self.order_queue.get_price_depth(symbol),
            "large_orders": self.order_queue.detect_large_order(symbol)
        }

    def get_tick_flow_analysis(self, symbol: str) -> Dict[str, Any]:
        """获取逐笔成交分析

        Args:
            symbol: 股票代码

        Returns:
            分析结果字典
        """
        return {
            "summary_5min": self.tick_flow.get_transaction_summary(symbol, minutes=5),
            "summary_1min": self.tick_flow.get_transaction_summary(symbol, minutes=1),
            "large_trades": self.tick_flow.detect_large_trade(symbol),
            "trade_distribution": self.tick_flow.get_trade_distribution(symbol),
            "trade_speed": self.tick_flow.get_transaction_speed(symbol),
            "trade_pattern": self.tick_flow.identify_trade_pattern(symbol)
        }

    def get_main_force_analysis(self, symbol: str) -> Dict[str, Any]:
        """获取主力动向分析

        Args:
            symbol: 股票代码

        Returns:
            分析结果字典
        """
        return {
            "current": self.main_force.calculate_main_force(symbol),
            "trend": self.main_force.get_main_force_trend(symbol),
            "action": self.main_force.detect_main_force_action(symbol)
        }

    def get_comprehensive_analysis(self, symbol: str) -> Dict[str, Any]:
        """获取综合分析

        返回完整的Level-2分析结果。

        Args:
            symbol: 股票代码

        Returns:
            综合分析字典
        """
        return {
            "symbol": symbol,
            "datetime": datetime.now(),
            "order_queue": self.get_order_queue_analysis(symbol),
            "tick_flow": self.get_tick_flow_analysis(symbol),
            "main_force": self.get_main_force_analysis(symbol)
        }

    def clear(self, symbol: Optional[str] = None) -> None:
        """清理缓存数据

        Args:
            symbol: 股票代码，None表示清理全部
        """
        self.order_queue.clear_cache(symbol)
        self.tick_flow.clear_cache(symbol)
        self.main_force.clear_cache(symbol)
