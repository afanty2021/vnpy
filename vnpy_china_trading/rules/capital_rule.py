# -*- coding: utf-8 -*-
"""
资金风险规则

检查账户资金是否充足。
"""

import logging
from typing import Any, List, Optional

from vnpy_china_trading.rules.base import RiskRule, RiskCheckResult
from vnpy_china_trading.object import TradingSignal, SignalDirection

logger = logging.getLogger(__name__)


class CapitalRule(RiskRule):
    """资金风险规则

    检查账户资金是否充足，确保有足够的资金执行交易。
    """

    def __init__(self, min_balance: float = 10000, enabled: bool = True) -> None:
        """初始化资金规则

        Args:
            min_balance: 最小保留资金，默认为10000元
            enabled: 规则是否启用
        """
        super().__init__("资金规则", enabled)
        self._min_balance = min_balance

    @property
    def min_balance(self) -> float:
        """获取最小保留资金"""
        return self._min_balance

    @min_balance.setter
    def min_balance(self, value: float) -> None:
        """设置最小保留资金"""
        if value < 0:
            raise ValueError("最小保留资金不能为负数")
        self._min_balance = value

    def check(self, signal: Any, main_engine: Any) -> RiskCheckResult:
        """检查信号是否满足资金要求

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

        # 获取账户信息
        account = self._get_account(main_engine)
        if not account:
            logger.warning("未获取到账户信息，跳过资金检查")
            return RiskCheckResult(passed=False, reasons=["未获取到账户信息"])

        available = getattr(account, "available", 0)

        reasons: list[str] = []
        warnings: list[str] = []

        # 检查可用资金是否充足
        if available < self._min_balance:
            reasons.append(
                f"可用资金不足: {available:.2f}元 < 最低要求{self._min_balance:.2f}元"
            )
            logger.warning(f"资金不足: 可用{available:.2f}元，需要{self._min_balance:.2f}元")

        # 资金不足警告
        if available < self._min_balance * 2:
            warnings.append(
                f"可用资金较低: {available:.2f}元"
            )

        passed = len(reasons) == 0
        return RiskCheckResult(
            passed=passed,
            reasons=reasons,
            warnings=warnings,
            insufficient_capital=available < self._min_balance,
        )

    def _get_account(self, main_engine: Any, gateway_name: Optional[str] = None) -> Optional[Any]:
        """获取账户信息

        Args:
            main_engine: 主引擎实例
            gateway_name: 网关名称，如果为None则获取第一个账户

        Returns:
            AccountData对象或None
        """
        try:
            if hasattr(main_engine, "get_account"):
                if gateway_name:
                    return main_engine.get_account(gateway_name)
                else:
                    # 获取第一个账户
                    accounts = self._get_all_accounts(main_engine)
                    if accounts:
                        return accounts[0]
        except Exception as e:
            logger.warning(f"获取账户信息失败: {e}")
        return None

    def _get_all_accounts(self, main_engine: Any) -> List[Any]:
        """获取所有账户

        Args:
            main_engine: 主引擎实例

        Returns:
            List[AccountData]: 账户列表
        """
        try:
            if hasattr(main_engine, "get_all_accounts"):
                accounts = main_engine.get_all_accounts()
                if accounts:
                    return list(accounts.values())
        except Exception as e:
            logger.warning(f"获取账户列表失败: {e}")
        return []


__all__ = ["CapitalRule"]
