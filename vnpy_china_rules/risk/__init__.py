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

# 风控规则继承 vnpy_riskmanager.template.RuleTemplate，属于可选运行时依赖。
# 缺失时降级：管理器与告警接口仍可用，规则类置空，避免阻断整个 risk 包导入
# （与 vnpy_china_monitor.risk_connector 的 try/except 容错设计一致）。
try:
    from vnpy_china_rules.risk.rules import (
        PositionControlRule,
        StopProfitLossRule,
        CapitalRiskRule,
        TradingLimitRule,
    )
except ImportError:
    PositionControlRule = None
    StopProfitLossRule = None
    CapitalRiskRule = None
    TradingLimitRule = None

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
