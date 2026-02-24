"""
资金流向综合分析器

整合所有资金流向分析功能。
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from .classifier import MoneyFlowClassifier
from .indicator import MoneyFlowIndicator
from ..objects.types import MoneyFlowData


class MoneyFlowAnalyzer:
    """
    资金流向综合分析器

    整合资金分类、指标计算等功能。
    """

    def __init__(self) -> None:
        """构造函数"""
        self.classifier = MoneyFlowClassifier()
        self.indicator = MoneyFlowIndicator()

    def update(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新数据并返回分析结果

        Args:
            symbol: 股票代码
            data: 成交数据字典

        Returns:
            分析结果字典
        """
        # 计算资金流向
        flow_data = self.classifier.analyze(symbol, data)
        self.classifier.update_cache(symbol, data)

        # 计算技术指标
        self.indicator.calculate(symbol, data)

        return {
            "symbol": symbol,
            "datetime": datetime.now(),
            "flow_data": flow_data,
            "structure": self.classifier.get_flow_structure(symbol)
        }

    def get_flow_summary(self, symbol: str, minutes: int = 5) -> Dict[str, Any]:
        """获取资金流向汇总

        Args:
            symbol: 股票代码
            minutes: 统计分钟数

        Returns:
            资金流向汇总
        """
        flow_data = self.classifier.calculate_period_flow(symbol, minutes)

        return {
            "symbol": symbol,
            "period": f"{minutes}min",
            "datetime": datetime.now(),
            "super_large_inflow": flow_data.super_large_inflow,
            "large_inflow": flow_data.large_inflow,
            "medium_inflow": flow_data.medium_inflow,
            "small_inflow": flow_data.small_inflow,
            "main_inflow": flow_data.main_inflow,
            "retail_inflow": flow_data.retail_inflow,
            "net_inflow": flow_data.net_inflow
        }

    def get_flow_structure(self, symbol: str) -> Dict[str, Any]:
        """获取资金结构

        Args:
            symbol: 股票代码

        Returns:
            资金结构
        """
        return self.classifier.get_flow_structure(symbol)

    def get_flow_indicators(self, symbol: str) -> Dict[str, Any]:
        """获取资金流向指标

        Args:
            symbol: 股票代码

        Returns:
            资金指标字典
        """
        return {
            "net_inflow_rate": self.indicator.get_net_inflow_rate(symbol),
            "main_force_strength": self.indicator.get_main_force_strength(symbol),
            "momentum": self.indicator.get_momentum(symbol),
            "trend": self.indicator.get_flow_trend(symbol),
            "buying_pressure": self.indicator.get_buying_pressure(symbol)
        }

    def get_comprehensive_analysis(self, symbol: str) -> Dict[str, Any]:
        """获取综合分析

        Args:
            symbol: 股票代码

        Returns:
            综合分析字典
        """
        return {
            "symbol": symbol,
            "datetime": datetime.now(),
            "summary_5min": self.get_flow_summary(symbol, minutes=5),
            "summary_60min": self.get_flow_summary(symbol, minutes=60),
            "structure": self.get_flow_structure(symbol),
            "indicators": self.get_flow_indicators(symbol)
        }

    def get_main_inflow(self, symbol: str) -> float:
        """获取主力净流入

        Args:
            symbol: 股票代码

        Returns:
            主力净流入金额
        """
        flow = self.classifier.calculate_period_flow(symbol, minutes=60)
        return flow.main_inflow

    def get_net_inflow(self, symbol: str) -> float:
        """获取总净流入

        Args:
            symbol: 股票代码

        Returns:
            总净流入金额
        """
        flow = self.classifier.calculate_period_flow(symbol, minutes=60)
        return flow.net_inflow

    def clear(self, symbol: Optional[str] = None) -> None:
        """清理缓存数据

        Args:
            symbol: 股票代码，None表示清理全部
        """
        self.classifier.clear_cache(symbol)
        self.indicator.clear_cache(symbol)
