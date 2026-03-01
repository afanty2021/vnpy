# -*- coding: utf-8 -*-
"""
风险规则基类

定义风险检查的抽象基类。
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from vnpy_china_trading.object import RiskCheckResult

logger = logging.getLogger(__name__)


class RiskRule(ABC):
    """风险规则抽象基类

    所有风险检查规则必须继承此类并实现check方法。

    Attributes:
        name: 规则名称
        enabled: 规则是否启用
    """

    def __init__(self, name: str, enabled: bool = True) -> None:
        """初始化风险规则

        Args:
            name: 规则名称
            enabled: 规则是否启用，默认为True
        """
        self._name = name
        self._enabled = enabled
        logger.debug(f"初始化风险规则: {name}, enabled={enabled}")

    @property
    def name(self) -> str:
        """获取规则名称"""
        return self._name

    @property
    def enabled(self) -> bool:
        """获取规则是否启用"""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """设置规则是否启用"""
        self._enabled = value
        logger.debug(f"设置规则 {self._name} 启用状态: {value}")

    @abstractmethod
    def check(self, signal: Any, main_engine: Any) -> RiskCheckResult:
        """检查信号是否通过风控

        Args:
            signal: 交易信号对象
            main_engine: 主引擎实例，用于获取账户、持仓、成交等数据

        Returns:
            RiskCheckResult: 风控检查结果
        """
        pass

    def __repr__(self) -> str:
        """返回规则的字符串表示"""
        return f"{self.__class__.__name__}(name='{self._name}', enabled={self._enabled})"


__all__ = ["RiskRule"]
