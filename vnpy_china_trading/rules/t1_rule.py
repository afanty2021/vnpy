# -*- coding: utf-8 -*-
"""
T+1 风险规则

检查当日是否已买入过该股票，A股市场实行T+1交易制度。
"""

import logging
from datetime import datetime, time
from typing import Any, List, Optional

from vnpy_china_trading.rules.base import RiskRule, RiskCheckResult
from vnpy_china_trading.object import TradingSignal, SignalDirection

logger = logging.getLogger(__name__)


class T1RestrictionRule(RiskRule):
    """T+1 风险规则

    A股市场实行T+1交易制度，即当天买入的股票必须等到下一个交易日才能卖出。
    本规则检查当日是否已经买入过该股票，如果买入过则禁止再次买入。
    """

    def __init__(self, enabled: bool = True) -> None:
        """初始化T+1规则

        Args:
            enabled: 规则是否启用
        """
        super().__init__("T+1规则", enabled)

    def check(self, signal: Any, main_engine: Any) -> RiskCheckResult:
        """检查信号是否受T+1限制

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

        # 只有买入操作才需要检查T+1
        if signal.direction != SignalDirection.LONG:
            return RiskCheckResult(passed=True)

        vt_symbol = signal.vt_symbol
        symbol = signal.symbol
        exchange = signal.exchange

        # 检查当日是否已有买入成交
        has_bought_today = self._has_bought_today(main_engine, vt_symbol, symbol, exchange)

        reasons: list[str] = []
        warnings: list[str] = []

        if has_bought_today:
            reasons.append(f"股票 {vt_symbol} 当日已买入，受T+1限制无法重复买入")
            logger.info(f"检测到T+1限制: {vt_symbol} 当日已有买入")

        passed = len(reasons) == 0
        return RiskCheckResult(
            passed=passed,
            reasons=reasons,
            warnings=warnings,
            t1_restriction=has_bought_today,
        )

    def _has_bought_today(
        self,
        main_engine: Any,
        vt_symbol: str,
        symbol: str,
        exchange: str,
    ) -> bool:
        """检查当日是否已有买入成交

        Args:
            main_engine: 主引擎实例
            vt_symbol: 合约代码
            symbol: 股票代码
            exchange: 交易所

        Returns:
            bool: 当日是否有买入成交
        """
        try:
            # 获取所有成交记录
            trades = self._get_all_trades(main_engine)
            if not trades:
                return False

            today = datetime.now().date()

            for trade in trades:
                # 检查是否是同一个股票
                trade_vt_symbol = getattr(trade, "vt_symbol", None)
                trade_symbol = getattr(trade, "symbol", None)

                # 匹配股票代码
                is_same_stock = False
                if trade_vt_symbol == vt_symbol:
                    is_same_stock = True
                elif trade_symbol == symbol:
                    is_same_stock = True

                if not is_same_stock:
                    continue

                # 检查是否是买入方向
                trade_direction = getattr(trade, "direction", None)
                if not trade_direction:
                    continue

                # 检查交易方向（买入）
                # VeighNa中Direction.LONG表示买入，Direction.SHORT表示卖出
                direction_value = str(trade_direction)
                if direction_value not in ("Direction.LONG", "long", "多"):
                    continue

                # 检查是否是当日成交
                trade_datetime = getattr(trade, "datetime", None)
                if trade_datetime:
                    # 支持datetime或date类型
                    trade_date = (
                        trade_datetime.date() if isinstance(trade_datetime, datetime)
                        else trade_datetime
                    )
                    if trade_date == today:
                        logger.debug(
                            f"找到当日买入成交: {vt_symbol}, 时间: {trade_datetime}"
                        )
                        return True

            return False

        except Exception as e:
            logger.warning(f"检查T+1限制时出错: {e}")
            # 出错时返回False，避免阻断正常交易
            return False

    def _get_all_trades(self, main_engine: Any) -> List[Any]:
        """获取所有成交记录

        Args:
            main_engine: 主引擎实例

        Returns:
            List[TradeData]: 成交记录列表
        """
        try:
            if hasattr(main_engine, "get_all_trades"):
                return main_engine.get_all_trades()
        except Exception as e:
            logger.warning(f"获取成交记录失败: {e}")
        return []


__all__ = ["T1RestrictionRule"]
