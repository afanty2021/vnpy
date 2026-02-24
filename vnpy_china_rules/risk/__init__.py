"""
A股风险管理模块

包含四大风控规则：
- PositionControlRule: 仓位控制规则
- StopProfitLossRule: 止损止盈规则
- CapitalRiskRule: 资金风控规则
- TradingLimitRule: 交易限制规则

以及集成接口：
- IRiskAlertProvider: 风控告警提供者接口
- RiskAlertEvent: 风控告警事件
"""

from vnpy_china_rules.risk.manager import (
    AStockRiskManager,
    create_risk_manager,
    IRiskAlertProvider,
    RiskAlertEvent,
)
from vnpy_china_rules.risk.rules import (
    PositionControlRule,
    StopProfitLossRule,
    CapitalRiskRule,
    TradingLimitRule,
)

__all__ = [
    "AStockRiskManager",
    "create_risk_manager",
    "IRiskAlertProvider",
    "RiskAlertEvent",
    "PositionControlRule",
    "StopProfitLossRule",
    "CapitalRiskRule",
    "TradingLimitRule",
]
