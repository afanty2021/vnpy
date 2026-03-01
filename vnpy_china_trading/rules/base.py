# -*- coding: utf-8 -*-
"""
风险规则基类

定义风险检查的抽象基类和结果数据类。
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Any

logger = logging.getLogger(__name__)


@dataclass
class RiskCheckResult:
    """风险检查结果数据类

    Attributes:
        passed: 是否通过风控检查
        reasons: 拒绝原因列表
        warnings: 警告信息列表
        limit_up: 是否涨停
        limit_down: 是否跌停
        t1_restriction: 是否受T+1限制
        insufficient_capital: 资金是否不足
        position_limit: 是否达到持仓上限
    """

    passed: bool
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    limit_up: bool = False
    limit_down: bool = False
    t1_restriction: bool = False
    insufficient_capital: bool = False
    position_limit: bool = False

    def __post_init__(self) -> None:
        """验证数据有效性"""
        if not isinstance(self.passed, bool):
            raise ValueError("passed必须是布尔类型")
        if not isinstance(self.reasons, list):
            raise ValueError("reasons必须是列表")
        if not isinstance(self.warnings, list):
            raise ValueError("warnings必须是列表")

    @property
    def message(self) -> str:
        """获取检查结果的消息描述"""
        if self.passed:
            if self.warnings:
                return f"通过（有警告: {'; '.join(self.warnings)}）"
            return "通过"
        return "; ".join(self.reasons) if self.reasons else "未通过"


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


__all__ = ["RiskRule", "RiskCheckResult"]
