"""
资金指标计算模块

计算资金流向相关的技术指标。
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ..objects.types import MoneyFlowData
from ..base import HistoricalAnalyzer


class MoneyFlowIndicator(HistoricalAnalyzer):
    """
    资金流向技术指标

    计算资金流向相关的各种技术指标。
    """

    def __init__(self, cache_size: int = 5000) -> None:
        super().__init__(cache_size)
        self.flow_history: Dict[str, List[MoneyFlowData]] = {}

    def analyze(self, symbol: str, data: Dict[str, Any]) -> MoneyFlowData:
        """分析资金流向（实现抽象方法）

        Args:
            symbol: 股票代码
            data: 成交数据字典

        Returns:
            MoneyFlowData对象
        """
        return self.calculate(symbol, data)

    def calculate(self, symbol: str, data: Dict[str, Any]) -> MoneyFlowData:
        """计算资金流向

        Args:
            symbol: 股票代码
            data: 成交数据字典

        Returns:
            MoneyFlowData对象
        """
        from .classifier import MoneyFlowClassifier

        classifier = MoneyFlowClassifier()
        flow_data = classifier.analyze(symbol, data)

        # 保存到历史
        if symbol not in self.flow_history:
            self.flow_history[symbol] = []
        self.flow_history[symbol].append(flow_data)

        # 限制历史大小
        if len(self.flow_history[symbol]) > self.cache_size:
            self.flow_history[symbol] = self.flow_history[symbol][-self.cache_size:]

        return flow_data

    def get_net_inflow_rate(self, symbol: str, period: int = 60) -> float:
        """获取净流入率

        计算净流入占总流入的比例。

        Args:
            symbol: 股票代码
            period: 统计周期

        Returns:
            净流入率（百分比）
        """
        if symbol not in self.flow_history or not self.flow_history[symbol]:
            return 0.0

        recent = self.flow_history[symbol][-period:]

        if not recent:
            return 0.0

        total_inflow = sum(f.main_inflow for f in recent)
        total_outflow = sum(-f.retail_inflow for f in recent if f.retail_inflow < 0)

        total = abs(total_inflow) + abs(total_outflow)

        if total == 0:
            return 0.0

        return (total_inflow - total_outflow) / total * 100

    def get_main_force_strength(self, symbol: str, period: int = 60) -> float:
        """获取主力强度

        计算主力资金净流入的强度。

        Args:
            symbol: 股票代码
            period: 统计周期

        Returns:
            主力强度值
        """
        if symbol not in self.flow_history or not self.flow_history[symbol]:
            return 0.0

        recent = self.flow_history[symbol][-period:]

        if not recent:
            return 0.0

        # 计算主力净流入
        main_net = sum(f.main_inflow for f in recent)

        # 计算总成交额
        total_amount = sum(
            abs(f.super_large_inflow) + abs(f.large_inflow) +
            abs(f.medium_inflow) + abs(f.small_inflow)
            for f in recent
        )

        if total_amount == 0:
            return 0.0

        return main_net / total_amount * 100

    def get_momentum(self, symbol: str, short_period: int = 5, long_period: int = 20) -> float:
        """获取资金动量

        比较短期和长期的资金流向差异。

        Args:
            symbol: 股票代码
            short_period: 短期周期
            long_period: 长期周期

        Returns:
            动量值
        """
        if symbol not in self.flow_history or not self.flow_history[symbol]:
            return 0.0

        history = self.flow_history[symbol]

        # 短期平均
        short_data = history[-short_period:] if len(history) >= short_period else history
        short_avg = sum(f.net_inflow for f in short_data) / len(short_data)

        # 长期平均
        long_data = history[-long_period:] if len(history) >= long_period else history
        long_avg = sum(f.net_inflow for f in long_data) / len(long_data)

        return short_avg - long_avg

    def get_flow_trend(self, symbol: str, period: int = 10) -> Dict[str, Any]:
        """获取资金流向趋势

        分析资金流向的趋势方向。

        Args:
            symbol: 股票代码
            period: 统计周期

        Returns:
            趋势字典
        """
        if symbol not in self.flow_history or not self.flow_history[symbol]:
            return {"trend": "unknown"}

        recent = self.flow_history[symbol][-period:]

        if not recent:
            return {"trend": "unknown"}

        # 计算趋势
        net_flows = [f.net_inflow for f in recent]

        # 判断趋势
        increasing = sum(1 for i in range(1, len(net_flows)) if net_flows[i] > net_flows[i-1])
        decreasing = sum(1 for i in range(1, len(net_flows)) if net_flows[i] < net_flows[i-1])

        if increasing > decreasing * 2:
            trend = "strong_inflow"
        elif increasing > decreasing:
            trend = "moderate_inflow"
        elif decreasing > increasing * 2:
            trend = "strong_outflow"
        elif decreasing > increasing:
            trend = "moderate_outflow"
        else:
            trend = "neutral"

        return {
            "trend": trend,
            "net_flows": net_flows,
            "avg_net_inflow": sum(net_flows) / len(net_flows),
            "increasing_periods": increasing,
            "decreasing_periods": decreasing
        }

    def get_buying_pressure(self, symbol: str, period: int = 60) -> float:
        """获取买入压力

        计算买入力量与卖出力量的比例。

        Args:
            symbol: 股票代码
            period: 统计周期

        Returns:
            买入压力值
        """
        if symbol not in self.flow_history or not self.flow_history[symbol]:
            return 50.0  # 中性

        recent = self.flow_history[symbol][-period:]

        if not recent:
            return 50.0

        # 计算买入和卖出
        buy_amount = sum(
            f.super_large_inflow + f.large_inflow + f.medium_inflow + f.small_inflow
            for f in recent
            if f.net_inflow > 0
        )

        sell_amount = sum(
            -(f.super_large_inflow + f.large_inflow + f.medium_inflow + f.small_inflow)
            for f in recent
            if f.net_inflow < 0
        )

        total = buy_amount + sell_amount

        if total == 0:
            return 50.0

        return buy_amount / total * 100
