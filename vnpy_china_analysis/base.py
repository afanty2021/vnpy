"""
分析器基类模块

定义所有行情分析器的基类和通用接口。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime


class BaseAnalyzer(ABC):
    """
    分析器基类

    所有行情分析器应继承此类，实现统一的接口。
    提供缓存管理、数据更新等通用功能。
    """

    def __init__(self, cache_size: int = 1000) -> None:
        """构造函数

        Args:
            cache_size: 缓存最大容量
        """
        self.data_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.cache_size = cache_size
        self.last_update: Dict[str, datetime] = {}

    @abstractmethod
    def analyze(self, symbol: str, data: Dict[str, Any]) -> Any:
        """
        分析行情数据

        Args:
            symbol: 股票代码
            data: 原始行情数据

        Returns:
            分析结果对象
        """
        pass

    def update_cache(self, symbol: str, data: Dict[str, Any]) -> None:
        """
        更新缓存数据

        Args:
            symbol: 股票代码
            data: 行情数据
        """
        if symbol not in self.data_cache:
            self.data_cache[symbol] = []

        self.data_cache[symbol].append(data)

        # 限制缓存大小
        if len(self.data_cache[symbol]) > self.cache_size:
            self.data_cache[symbol] = self.data_cache[symbol][-self.cache_size:]

        # 更新最后更新时间
        self.last_update[symbol] = datetime.now()

    def get_cached_data(
        self,
        symbol: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """获取缓存数据

        Args:
            symbol: 股票代码
            limit: 返回最近N条数据，None表示全部

        Returns:
            缓存的数据列表
        """
        data = self.data_cache.get(symbol, [])
        if limit is not None:
            return data[-limit:]
        return data

    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """清理缓存

        Args:
            symbol: 指定股票代码，None表示清理全部
        """
        if symbol:
            self.data_cache.pop(symbol, None)
            self.last_update.pop(symbol, None)
        else:
            self.data_cache.clear()
            self.last_update.clear()

    def get_last_update(self, symbol: str) -> Optional[datetime]:
        """获取最后更新时间

        Args:
            symbol: 股票代码

        Returns:
            最后更新时间
        """
        return self.last_update.get(symbol)

    def has_data(self, symbol: str) -> bool:
        """检查是否有缓存数据

        Args:
            symbol: 股票代码

        Returns:
            是否有数据
        """
        return symbol in self.data_cache and len(self.data_cache[symbol]) > 0


class RealtimeAnalyzer(BaseAnalyzer):
    """
    实时分析器基类

    适用于需要实时处理推送数据的分析器。
    """

    def __init__(self, cache_size: int = 1000) -> None:
        super().__init__(cache_size)
        self.current_data: Dict[str, Dict[str, Any]] = {}

    def update(self, symbol: str, data: Dict[str, Any]) -> Any:
        """
        更新实时数据

        Args:
            symbol: 股票代码
            data: 实时行情数据

        Returns:
            分析结果
        """
        # 保存当前数据
        self.current_data[symbol] = data

        # 更新缓存
        self.update_cache(symbol, data)

        # 执行分析
        return self.analyze(symbol, data)

    def get_current(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取当前数据

        Args:
            symbol: 股票代码

        Returns:
            当前数据
        """
        return self.current_data.get(symbol)


class HistoricalAnalyzer(BaseAnalyzer):
    """
    历史分析器基类

    适用于需要批量处理历史数据的分析器。
    """

    def analyze_batch(self, symbol: str, data_list: List[Dict[str, Any]]) -> List[Any]:
        """
        批量分析历史数据

        Args:
            symbol: 股票代码
            data_list: 历史数据列表

        Returns:
            分析结果列表
        """
        results = []
        for data in data_list:
            result = self.analyze(symbol, data)
            self.update_cache(symbol, data)
            results.append(result)
        return results

    def get_statistics(self, symbol: str) -> Dict[str, Any]:
        """
        获取统计信息

        Args:
            symbol: 股票代码

        Returns:
            统计信息字典
        """
        data = self.get_cached_data(symbol)
        if not data:
            return {}

        return {
            "symbol": symbol,
            "data_count": len(data),
            "first_time": data[0].get("datetime"),
            "last_time": data[-1].get("datetime"),
        }
