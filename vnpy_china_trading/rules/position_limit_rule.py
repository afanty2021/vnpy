# -*- coding: utf-8 -*-
"""
持仓限制风险规则

检查持仓数量是否超过限制。
"""

import logging
from typing import Any, List

from vnpy_china_trading.rules.base import RiskRule, RiskCheckResult
from vnpy_china_trading.object import TradingSignal, SignalDirection

logger = logging.getLogger(__name__)


class PositionLimitRule(RiskRule):
    """持仓限制风险规则

    检查当前持仓数量是否超过设定上限，防止过度分散投资。
    """

    def __init__(self, max_positions: int = 10, enabled: bool = True) -> None:
        """初始化持仓限制规则

        Args:
            max_positions: 最大持仓股票数量，默认为10只
            enabled: 规则是否启用
        """
        super().__init__("持仓限制规则", enabled)
        self._max_positions = max_positions

    @property
    def max_positions(self) -> int:
        """获取最大持仓数量"""
        return self._max_positions

    @max_positions.setter
    def max_positions(self, value: int) -> None:
        """设置最大持仓数量"""
        if value < 0:
            raise ValueError("最大持仓数量不能为负数")
        if value == 0:
            raise ValueError("最大持仓数量必须大于0")
        self._max_positions = value

    def check(self, signal: Any, main_engine: Any) -> RiskCheckResult:
        """检查信号是否满足持仓限制

        Args:
            signal: 交易信号对象
            main_engine: 主引擎实例

        Returns:
            RiskCheckResult: 风控检查结果
        """
        if not self.enabled:
            return RiskCheckResult(passed=True)

        if not isinstance(signal, TradingSignal):
            logger.warning(f"无效的信号类型: {type(signal)}")
            return RiskCheckResult(passed=False, reasons=["无效的信号类型"])

        # 只有开仓操作才需要检查持仓限制
        if signal.direction not in (SignalDirection.LONG, SignalDirection.SHORT):
            return RiskCheckResult(passed=True)

        # 获取当前持仓
        positions = self._get_all_positions(main_engine)

        # 计算当前持仓数量（只计算有实际持仓的）
        current_positions = [p for p in positions if self._has_position(p)]

        # 检查是否已达上限
        at_limit = len(current_positions) >= self._max_positions

        reasons: list[str] = []
        warnings: list[str] = []

        if at_limit:
            reasons.append(
                f"持仓数量已达上限: {len(current_positions)}/{self._max_positions}，无法开新仓"
            )
            logger.warning(
                f"持仓已达上限: 当前{len(current_positions)}只，"
                f"上限{self._max_positions}只"
            )

        # 接近上限警告
        if len(current_positions) >= self._max_positions * 0.8:
            warnings.append(
                f"持仓数量接近上限: {len(current_positions)}/{self._max_positions}"
            )

        passed = len(reasons) == 0
        return RiskCheckResult(
            passed=passed,
            reasons=reasons,
            warnings=warnings,
            position_limit=at_limit,
        )

    def _get_all_positions(self, main_engine: Any) -> List[Any]:
        """获取所有持仓

        Args:
            main_engine: 主引擎实例

        Returns:
            List[PositionData]: 持仓列表
        """
        try:
            if hasattr(main_engine, "get_all_positions"):
                positions = main_engine.get_all_positions()
                if positions:
                    return list(positions.values())
        except Exception as e:
            logger.warning(f"获取持仓列表失败: {e}")
        return []

    def _has_position(self, position: Any) -> bool:
        """检查是否有实际持仓

        Args:
            position: PositionData对象

        Returns:
            bool: 是否有实际持仓
        """
        # 检查持仓数量或持仓方向
        volume = getattr(position, "volume", 0)
        position_direction = getattr(position, "direction", None)

        # 有持仓量或者有净持仓方向
        if volume > 0:
            return True

        # 检查净持仓方向
        if position_direction:
            direction_value = str(position_direction)
            if direction_value in ("Direction.NET", "net", "净"):
                return True

        return False


__all__ = ["PositionLimitRule"]
