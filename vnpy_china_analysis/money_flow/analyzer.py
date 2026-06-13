"""
资金流向综合分析器

整合所有资金流向分析功能。
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from vnpy.trader.object import TickData

from .classifier import MoneyFlowClassifier
from .indicator import MoneyFlowIndicator
from ..objects.types import MoneyFlowData, TickFlowData, MoneyFlowLevel
from ..adapters.tick_adapter import tick_to_flow


class MoneyFlowAnalyzer:
    """
    资金流向综合分析器

    整合资金分类、指标计算等功能。
    """

    def __init__(self, thresholds: Optional[Dict[MoneyFlowLevel, float]] = None) -> None:
        """构造函数

        Args:
            thresholds: 自定义资金分类阈值
        """
        self.classifier = MoneyFlowClassifier(thresholds)
        self.indicator = MoneyFlowIndicator()
        self.flow_history: Dict[str, List[MoneyFlowData]] = {}      # 聚合快照（供 get_flow_summary）
        self.tick_history: Dict[str, List[TickFlowData]] = {}       # 原始 tick 缓冲（供 update/on_tick 聚合）
        self.max_tick_cache = 1000                                   # 单标的 tick 缓冲上限
        # Level1 方向推断 / 成交量差分所需状态（供 tick_adapter 复用）
        self._last_price: Dict[str, float] = {}
        self._last_dir: Dict[str, str] = {}
        self._last_volume: Dict[str, int] = {}

    def analyze(
        self,
        symbol: str,
        tick_flows: List[TickFlowData],
        window_minutes: int = 5
    ) -> MoneyFlowData:
        """分析资金流向

        Args:
            symbol: 股票代码
            tick_flows: 逐笔成交列表
            window_minutes: 时间窗口（分钟）

        Returns:
            MoneyFlowData对象
        """
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=window_minutes)

        # 筛选时间窗口内的成交
        window_flows = [
            t for t in tick_flows
            if t.datetime >= cutoff_time
        ]

        # 初始化各层级资金流向
        flows = {
            MoneyFlowLevel.SUPER_LARGE: 0.0,
            MoneyFlowLevel.LARGE: 0.0,
            MoneyFlowLevel.MEDIUM: 0.0,
            MoneyFlowLevel.SMALL: 0.0,
        }

        # 统计各层级资金
        for flow in window_flows:
            level = self.classifier.classify(flow.price, flow.volume)
            amount = flow.price * flow.volume * 100

            if flow.direction == "buy":
                flows[level] += amount
            else:
                flows[level] -= amount

        # 汇总
        main_inflow = flows[MoneyFlowLevel.SUPER_LARGE] + flows[MoneyFlowLevel.LARGE]
        retail_inflow = flows[MoneyFlowLevel.MEDIUM] + flows[MoneyFlowLevel.SMALL]
        net_inflow = sum(flows.values())

        money_flow = MoneyFlowData(
            symbol=symbol,
            datetime=now,
            super_large_inflow=flows[MoneyFlowLevel.SUPER_LARGE],
            large_inflow=flows[MoneyFlowLevel.LARGE],
            medium_inflow=flows[MoneyFlowLevel.MEDIUM],
            small_inflow=flows[MoneyFlowLevel.SMALL],
            main_inflow=main_inflow,
            retail_inflow=retail_inflow,
            net_inflow=net_inflow
        )

        # 保存到历史
        if symbol not in self.flow_history:
            self.flow_history[symbol] = []
        self.flow_history[symbol].append(money_flow)

        return money_flow

    def update(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新数据并返回分析结果（向后兼容）

        Args:
            symbol: 股票代码
            data: 成交数据字典

        Returns:
            分析结果字典
        """
        # 将字典数据转换为TickFlowData
        tick_flow = TickFlowData(
            symbol=symbol,
            datetime=data.get("datetime", datetime.now()),
            price=data.get("price", 0.0),
            volume=data.get("volume", 0),
            amount=data.get("amount", 0.0),
            direction=data.get("direction", "buy"),
            function_code=data.get("function_code", 1)
        )

        # 写入 tick 缓冲并限长
        buf = self.tick_history.setdefault(symbol, [])
        buf.append(tick_flow)
        if len(buf) > self.max_tick_cache:
            del buf[:-self.max_tick_cache]

        # 用窗口内全部 tick 聚合（analyze 内部按 window_minutes 过滤 datetime）
        result = self.analyze(symbol, buf)

        return {
            "symbol": symbol,
            "datetime": datetime.now(),
            "flow_data": result,
            "structure": self.get_flow_structure(symbol)
        }

    def on_tick(self, tick: TickData) -> None:
        """实时 Tick 驱动资金流分析（Level1）

        Level1 无主动方向、QMT 不填 last_volume，由 tick_adapter 推断方向并差分成交量。
        跳过无新增成交量的 tick，避免 0 成交污染聚合。

        Args:
            tick: vnpy TickData
        """
        flow = tick_to_flow(tick, self._last_price, self._last_dir, self._last_volume)

        # 跳过无新增成交量（差分为 0 或回退）
        if flow.volume <= 0:
            return

        buf = self.tick_history.setdefault(tick.symbol, [])
        buf.append(flow)
        if len(buf) > self.max_tick_cache:
            del buf[:-self.max_tick_cache]

        self.analyze(tick.symbol, buf)

    def get_flow_summary(self, symbol: str, minutes: int = 5) -> Dict[str, Any]:
        """获取资金流向汇总

        Args:
            symbol: 股票代码
            minutes: 统计分钟数

        Returns:
            资金流向汇总
        """
        if symbol not in self.flow_history or not self.flow_history[symbol]:
            return {
                "symbol": symbol,
                "period": f"{minutes}min",
                "datetime": datetime.now(),
                "super_large_inflow": 0,
                "large_inflow": 0,
                "medium_inflow": 0,
                "small_inflow": 0,
                "main_inflow": 0,
                "retail_inflow": 0,
                "net_inflow": 0
            }

        # 获取最近的数据
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_flows = [
            f for f in self.flow_history[symbol]
            if f.datetime >= cutoff_time
        ]

        if not recent_flows:
            recent_flows = self.flow_history[symbol][-1:]

        # 汇总
        flow_data = MoneyFlowData(
            symbol=symbol,
            datetime=datetime.now(),
            super_large_inflow=sum(f.super_large_inflow for f in recent_flows),
            large_inflow=sum(f.large_inflow for f in recent_flows),
            medium_inflow=sum(f.medium_inflow for f in recent_flows),
            small_inflow=sum(f.small_inflow for f in recent_flows)
        )

        flow_data.main_inflow = flow_data.super_large_inflow + flow_data.large_inflow
        flow_data.retail_inflow = flow_data.medium_inflow + flow_data.small_inflow
        flow_data.net_inflow = flow_data.main_inflow + flow_data.retail_inflow

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
        summary = self.get_flow_summary(symbol, minutes=60)
        return summary["main_inflow"]

    def get_net_inflow(self, symbol: str) -> float:
        """获取总净流入

        Args:
            symbol: 股票代码

        Returns:
            总净流入金额
        """
        summary = self.get_flow_summary(symbol, minutes=60)
        return summary["net_inflow"]

    def clear(self, symbol: Optional[str] = None) -> None:
        """清理缓存数据

        Args:
            symbol: 股票代码，None表示清理全部
        """
        if symbol:
            self.flow_history.pop(symbol, None)
            self.tick_history.pop(symbol, None)
            self._last_price.pop(symbol, None)
            self._last_dir.pop(symbol, None)
            self._last_volume.pop(symbol, None)
        else:
            self.flow_history.clear()
            self.tick_history.clear()
            self._last_price.clear()
            self._last_dir.clear()
            self._last_volume.clear()

        self.classifier.clear_cache(symbol)
        self.indicator.clear_cache(symbol)
