"""因子回测模块

提供因子有效性评估、IC/RankIC/IR计算、分层回测等功能。
"""

from .factor_backtest import (
    FactorBacktester,
    FactorIcResult,
    FactorIcStats,
    LayerBacktestResult,
    FactorBacktestReport,
    create_factor_backtester,
)

__all__ = [
    "FactorBacktester",
    "FactorIcResult",
    "FactorIcStats",
    "LayerBacktestResult",
    "FactorBacktestReport",
    "create_factor_backtester",
]
