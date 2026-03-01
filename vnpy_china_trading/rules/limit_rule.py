# -*- coding: utf-8 -*-
"""
涨跌停风险规则

检查股票是否处于涨停或跌停状态，禁止反向交易。
"""

import logging
from typing import Any, Optional

from vnpy_china_trading.rules.base import RiskRule, RiskCheckResult
from vnpy_china_trading.object import TradingSignal, SignalDirection

logger = logging.getLogger(__name__)


class LimitUpDownRule(RiskRule):
    """涨跌停风险规则

    检查股票是否处于涨停或跌停状态：
    - 涨停时禁止做多（买入）
    - 跌停时禁止做空（卖出）
    """

    def __init__(self, enabled: bool = True) -> None:
        """初始化涨跌停规则

        Args:
            enabled: 规则是否启用
        """
        super().__init__("涨跌停规则", enabled)

    def check(self, signal: Any, main_engine: Any) -> RiskCheckResult:
        """检查信号是否受涨跌停限制

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

        vt_symbol = signal.vt_symbol
        direction = signal.direction

        # 获取行情数据
        tick = self._get_tick(main_engine, vt_symbol)
        if not tick:
            logger.debug(f"未获取到行情数据，跳过涨跌停检查: {vt_symbol}")
            return RiskCheckResult(passed=True, warnings=["未获取到行情数据"])

        # 检查是否涨停
        is_limit_up = self._is_limit_up(tick)
        # 检查是否跌停
        is_limit_down = self._is_limit_down(tick)

        reasons: list[str] = []
        warnings: list[str] = []

        if is_limit_up:
            if direction == SignalDirection.LONG:
                reasons.append(f"股票 {vt_symbol} 已涨停，禁止买入")
            logger.info(f"检测到涨停: {vt_symbol}, 当前价={tick.last_price}, 涨停价={tick.limit_up}")

        if is_limit_down:
            if direction == SignalDirection.SHORT:
                reasons.append(f"股票 {vt_symbol} 已跌停，禁止卖出")
            logger.info(f"检测到跌停: {vt_symbol}, 当前价={tick.last_price}, 跌停价={tick.limit_down}")

        passed = len(reasons) == 0
        return RiskCheckResult(
            passed=passed,
            reasons=reasons,
            warnings=warnings,
            limit_up=is_limit_up,
            limit_down=is_limit_down,
        )

    def _get_tick(self, main_engine: Any, vt_symbol: str) -> Optional[Any]:
        """获取行情数据

        Args:
            main_engine: 主引擎实例
            vt_symbol: 合约代码

        Returns:
            TickData对象或None
        """
        try:
            # 尝试从主引擎获取tick数据
            if hasattr(main_engine, "get_tick"):
                return main_engine.get_tick(vt_symbol)
        except Exception as e:
            logger.warning(f"获取行情数据失败: {e}")
        return None

    def _is_limit_up(self, tick: Any) -> bool:
        """判断是否涨停

        Args:
            tick: TickData对象

        Returns:
            bool: 是否涨停
        """
        # 涨停价大于0且当前价大于等于涨停价
        if tick.limit_up > 0 and tick.last_price >= tick.limit_up:
            return True
        return False

    def _is_limit_down(self, tick: Any) -> bool:
        """判断是否跌停

        Args:
            tick: TickData对象

        Returns:
            bool: 是否跌停
        """
        # 跌停价大于0且当前价小于等于跌停价
        if tick.limit_down > 0 and tick.last_price <= tick.limit_down:
            return True
        return False


__all__ = ["LimitUpDownRule"]
