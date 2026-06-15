# -*- coding: utf-8 -*-
"""
风险控制引擎

提供统一的风险检查接口，管理所有风险规则。
"""

import logging
from typing import Any, Dict, List, Optional

from vnpy_china_trading.rules import (
    RiskRule,
    RiskCheckResult,
    LimitUpDownRule,
    T1RestrictionRule,
    CapitalRule,
    PositionLimitRule,
)
from vnpy_china_trading.object import TradingSignal

logger = logging.getLogger(__name__)


class RiskEngine:
    """风险控制引擎

    负责管理和执行所有风险检查规则，提供统一的风险评估接口。

    Attributes:
        main_engine: 主引擎实例
        rules: 风险规则字典，key为规则名称
    """

    def __init__(self, main_engine: Any) -> None:
        """初始化风险引擎

        Args:
            main_engine: 主引擎实例
        """
        self.main_engine = main_engine
        self.rules: Dict[str, RiskRule] = {}

        # 初始化默认规则
        self._init_default_rules()

        logger.info("风险控制引擎初始化完成")

    def _init_default_rules(self) -> None:
        """初始化默认风控规则"""
        # 涨跌停规则
        self.add_rule(LimitUpDownRule(enabled=True))

        # T+1 规则
        self.add_rule(T1RestrictionRule(enabled=True))

        # 资金规则
        self.add_rule(CapitalRule(min_balance=10000, enabled=True))

        # 持仓限制规则
        self.add_rule(PositionLimitRule(max_positions=10, enabled=True))

        logger.info("默认风控规则初始化完成")

    def add_rule(self, rule: RiskRule) -> None:
        """添加风控规则

        Args:
            rule: RiskRule实例
        """
        if not isinstance(rule, RiskRule):
            raise TypeError(f"无效的规则类型: {type(rule)}")

        rule_name = rule.name
        if rule_name in self.rules:
            logger.warning(f"规则已存在，将被覆盖: {rule_name}")

        self.rules[rule_name] = rule
        logger.info(f"添加风控规则: {rule_name}")

    def remove_rule(self, rule_name: str) -> bool:
        """移除风控规则

        Args:
            rule_name: 规则名称

        Returns:
            bool: 移除是否成功
        """
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.info(f"移除风控规则: {rule_name}")
            return True
        logger.warning(f"规则不存在: {rule_name}")
        return False

    def get_rule(self, rule_name: str) -> Optional[RiskRule]:
        """获取风控规则

        Args:
            rule_name: 规则名称

        Returns:
            RiskRule或None
        """
        return self.rules.get(rule_name)

    def get_all_rules(self) -> List[RiskRule]:
        """获取所有风控规则

        Returns:
            List[RiskRule]: 规则列表
        """
        return list(self.rules.values())

    def enable_rule(self, rule_name: str) -> bool:
        """启用风控规则

        Args:
            rule_name: 规则名称

        Returns:
            bool: 启用是否成功
        """
        rule = self.get_rule(rule_name)
        if rule:
            rule.enabled = True
            logger.info(f"启用风控规则: {rule_name}")
            return True
        logger.warning(f"规则不存在: {rule_name}")
        return False

    def disable_rule(self, rule_name: str) -> bool:
        """禁用风控规则

        Args:
            rule_name: 规则名称

        Returns:
            bool: 禁用是否成功
        """
        rule = self.get_rule(rule_name)
        if rule:
            rule.enabled = False
            logger.info(f"禁用风控规则: {rule_name}")
            return True
        logger.warning(f"规则不存在: {rule_name}")
        return False

    def check_signal(self, signal: Any) -> RiskCheckResult:
        """检查信号是否通过所有风控

        Args:
            signal: 交易信号对象

        Returns:
            RiskCheckResult: 风控检查结果（汇总所有规则）
        """
        if not isinstance(signal, TradingSignal):
            logger.warning(f"无效的信号类型: {type(signal)}")
            return RiskCheckResult(
                passed=False,
                reasons=[f"无效的信号类型: {type(signal)}"]
            )

        all_reasons: List[str] = []
        all_warnings: List[str] = []
        limit_up = False
        limit_down = False
        t1_restriction = False
        insufficient_capital = False
        position_limit = False

        # 执行所有启用的规则
        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue

            try:
                result = rule.check(signal, self.main_engine)

                if not result.passed:
                    all_reasons.extend(result.reasons)

                all_warnings.extend(result.warnings)

                # 汇总各规则的特殊标记
                if result.limit_up:
                    limit_up = True
                if result.limit_down:
                    limit_down = True
                if result.t1_restriction:
                    t1_restriction = True
                if result.insufficient_capital:
                    insufficient_capital = True
                if result.position_limit:
                    position_limit = True

            except Exception as e:
                logger.error(f"规则执行失败: {rule_name}, 错误: {e}")
                all_reasons.append(f"规则执行失败: {rule_name}")

        # 判断是否通过
        passed = len(all_reasons) == 0

        if passed:
            logger.debug(
                f"信号风控通过: {signal.vt_symbol}, "
                f"方向: {signal.direction.value}, "
                f"规则数: {len(self.rules)}"
            )
        else:
            logger.warning(
                f"信号风控拒绝: {signal.vt_symbol}, "
                f"方向: {signal.direction.value}, "
                f"原因: {'; '.join(all_reasons)}"
            )

        return RiskCheckResult(
            passed=passed,
            reasons=all_reasons,
            warnings=all_warnings,
            limit_up=limit_up,
            limit_down=limit_down,
            t1_restriction=t1_restriction,
            insufficient_capital=insufficient_capital,
            position_limit=position_limit,
        )

    def check_rules_summary(self) -> Dict[str, Dict[str, Any]]:
        """获取所有规则的状态摘要

        Returns:
            Dict: 规则状态字典
        """
        summary: Dict[str, Dict[str, Any]] = {}
        for rule_name, rule in self.rules.items():
            summary[rule_name] = {
                "enabled": rule.enabled,
                "class": rule.__class__.__name__,
            }
        return summary


__all__ = ["RiskEngine"]
