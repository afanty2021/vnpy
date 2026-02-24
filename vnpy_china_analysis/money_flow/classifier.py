"""
资金分类器模块

根据成交金额对资金进行分类统计。
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from ..objects.types import MoneyFlowLevel, MoneyFlowData
from ..base import RealtimeAnalyzer


class MoneyFlowClassifier(RealtimeAnalyzer):
    """
    资金流向分类器

    根据成交金额对资金进行分类统计：
    - 超大单：> 100万
    - 大单：20-100万
    - 中单：5-20万
    - 小单：< 5万
    """

    # 默认阈值（元）
    DEFAULT_THRESHOLDS = {
        MoneyFlowLevel.SUPER_LARGE: 1_000_000,   # 100万
        MoneyFlowLevel.LARGE: 200_000,           # 20万
        MoneyFlowLevel.MEDIUM: 50_000,           # 5万
    }

    # 资金分级阈值（元）- 向后兼容
    SUPER_LARGE_THRESHOLD = 1000000
    LARGE_THRESHOLD = 200000
    MEDIUM_THRESHOLD = 50000

    def __init__(self, thresholds: Optional[Dict[MoneyFlowLevel, float]] = None, cache_size: int = 2000) -> None:
        """
        Args:
            thresholds: 自定义阈值
            cache_size: 缓存大小
        """
        super().__init__(cache_size)
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS

    def classify(self, price: float, volume: int) -> MoneyFlowLevel:
        """分类订单

        根据成交价格和数量返回资金等级。

        Args:
            price: 成交价格
            volume: 成交数量（手）

        Returns:
            资金级别
        """
        # 转换为元：价格 * 数量 * 100 (每手100股)
        amount = price * volume * 100

        if amount >= self.thresholds[MoneyFlowLevel.SUPER_LARGE]:
            return MoneyFlowLevel.SUPER_LARGE
        elif amount >= self.thresholds[MoneyFlowLevel.LARGE]:
            return MoneyFlowLevel.LARGE
        elif amount >= self.thresholds[MoneyFlowLevel.MEDIUM]:
            return MoneyFlowLevel.MEDIUM
        else:
            return MoneyFlowLevel.SMALL

    def classify_by_amount(self, amount: float) -> MoneyFlowLevel:
        """根据金额分类（向后兼容方法）

        Args:
            amount: 成交金额（元）

        Returns:
            资金等级枚举
        """
        if amount >= self.thresholds[MoneyFlowLevel.SUPER_LARGE]:
            return MoneyFlowLevel.SUPER_LARGE
        elif amount >= self.thresholds[MoneyFlowLevel.LARGE]:
            return MoneyFlowLevel.LARGE
        elif amount >= self.thresholds[MoneyFlowLevel.MEDIUM]:
            return MoneyFlowLevel.MEDIUM
        else:
            return MoneyFlowLevel.SMALL

    def classify_batch(self, trades: List[Dict[str, Any]]) -> Dict[MoneyFlowLevel, List[Dict[str, Any]]]:
        """批量分类

        Args:
            trades: 交易列表，每个交易包含price和volume

        Returns:
            {级别: 交易列表}
        """
        result = {
            MoneyFlowLevel.SUPER_LARGE: [],
            MoneyFlowLevel.LARGE: [],
            MoneyFlowLevel.MEDIUM: [],
            MoneyFlowLevel.SMALL: [],
        }

        for trade in trades:
            level = self.classify(trade["price"], trade["volume"])
            result[level].append(trade)

        return result

    def analyze(self, symbol: str, data: Dict[str, Any]) -> MoneyFlowData:
        """分析资金流向

        Args:
            symbol: 股票代码
            data: 成交数据字典

        Returns:
            MoneyFlowData对象
        """
        price = data.get("price", 0.0)
        volume = data.get("volume", 0)
        direction = data.get("direction", "buy")

        # 根据价格和数量分类
        level = self.classify(price, volume)
        amount = price * volume * 100  # 转换为元

        # 根据方向计算流入/流出
        multiplier = 1 if direction == "buy" else -1

        # 构建资金流向数据
        flow_data = MoneyFlowData(
            symbol=symbol,
            datetime=data.get("datetime", datetime.now())
        )

        if level == MoneyFlowLevel.SUPER_LARGE:
            flow_data.super_large_inflow = amount * multiplier
        elif level == MoneyFlowLevel.LARGE:
            flow_data.large_inflow = amount * multiplier
        elif level == MoneyFlowLevel.MEDIUM:
            flow_data.medium_inflow = amount * multiplier
        else:
            flow_data.small_inflow = amount * multiplier

        # 计算汇总指标
        flow_data.main_inflow = flow_data.super_large_inflow + flow_data.large_inflow
        flow_data.retail_inflow = flow_data.medium_inflow + flow_data.small_inflow
        flow_data.net_inflow = flow_data.main_inflow + flow_data.retail_inflow

        return flow_data

    def calculate_period_flow(self, symbol: str, minutes: int = 5) -> MoneyFlowData:
        """计算周期内的资金流向

        Args:
            symbol: 股票代码
            minutes: 统计周期（分钟）

        Returns:
            汇总的资金流向数据
        """
        cached_data = self.get_cached_data(symbol)

        if not cached_data:
            return MoneyFlowData(symbol=symbol, datetime=datetime.now())

        # 汇总各分类资金
        super_large = 0.0
        large = 0.0
        medium = 0.0
        small = 0.0

        for data in cached_data:
            flow = self.analyze(symbol, data)
            super_large += flow.super_large_inflow
            large += flow.large_inflow
            medium += flow.medium_inflow
            small += flow.small_inflow

        result = MoneyFlowData(
            symbol=symbol,
            datetime=datetime.now(),
            super_large_inflow=super_large,
            large_inflow=large,
            medium_inflow=medium,
            small_inflow=small,
            main_inflow=super_large + large,
            retail_inflow=medium + small,
            net_inflow=super_large + large + medium + small
        )

        return result

    def get_flow_structure(self, symbol: str) -> Dict[str, Any]:
        """获取资金结构

        分析各等级资金的占比情况。

        Args:
            symbol: 股票代码

        Returns:
            资金结构字典
        """
        flow = self.calculate_period_flow(symbol)

        total = abs(flow.super_large_inflow) + abs(flow.large_inflow) + \
                abs(flow.medium_inflow) + abs(flow.small_inflow)

        if total == 0:
            return {
                "symbol": symbol,
                "structure": {},
                "total": 0
            }

        return {
            "symbol": symbol,
            "total": total,
            "structure": {
                "super_large_pct": abs(flow.super_large_inflow) / total * 100,
                "large_pct": abs(flow.large_inflow) / total * 100,
                "medium_pct": abs(flow.medium_inflow) / total * 100,
                "small_pct": abs(flow.small_inflow) / total * 100
            },
            "main_ratio": (abs(flow.super_large_inflow) + abs(flow.large_inflow)) / total * 100,
            "retail_ratio": (abs(flow.medium_inflow) + abs(flow.small_inflow)) / total * 100
        }

    def get_threshold(self, level: MoneyFlowLevel) -> float:
        """获取指定级别的阈值

        Args:
            level: 资金级别

        Returns:
            阈值（元）
        """
        return self.thresholds.get(level, 0.0)
