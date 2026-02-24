"""
A股风险管理模块

包含四大风控规则：
- PositionControlRule: 仓位控制规则
- StopProfitLossRule: 止损止盈规则
- CapitalRiskRule: 资金风控规则
- TradingLimitRule: 交易限制规则
"""

from vnpy_china_rules.risk.manager import AStockRiskManager

__all__ = [
    "AStockRiskManager",
    "PositionControlRule",
    "StopProfitLossRule",
    "CapitalRiskRule",
    "TradingLimitRule",
]
