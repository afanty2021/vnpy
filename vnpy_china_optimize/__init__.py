"""
VeighNa策略参数优化扩展模块

本模块扩展了vnpy.trader.optimize，提供：
- 高级优化算法（贝叶斯优化、粒子群优化）
- 过拟合检测（样本外测试、前向验证、稳定性分析）
- 优化报告（参数排名、敏感性分析、可视化）
- A股交易成本适配
"""

from .base.result import (
    OptimizationStatus,
    OptimizationMetrics,
    OptimizationResult,
    OptimizationSummary,
)

from .base.optimizer import BaseOptimizer

from .setting import (
    ChinaTradingCost,
    ChinaOptimizerSetting,
    calculate_china_trading_cost,
)

from .algorithms import (
    BayesianOptimizer,
    PSOOptimizer,
)

from .overfit import (
    OverfitDetector,
    OverfitTestResult,
)

from .report import (
    OptimizationReportGenerator,
)

from .utils import (
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_calmar_ratio,
    calculate_sortino_ratio,
)

__version__ = "1.0.0"

__all__ = [
    # 版本
    "__version__",
    # 基础类
    "BaseOptimizer",
    "OptimizationStatus",
    "OptimizationMetrics",
    "OptimizationResult",
    "OptimizationSummary",
    # A股设置
    "ChinaTradingCost",
    "ChinaOptimizerSetting",
    "calculate_china_trading_cost",
    # 优化算法
    "BayesianOptimizer",
    "PSOOptimizer",
    # 过拟合检测
    "OverfitDetector",
    "OverfitTestResult",
    # 报告生成
    "OptimizationReportGenerator",
    # 工具函数
    "calculate_sharpe_ratio",
    "calculate_max_drawdown",
    "calculate_calmar_ratio",
    "calculate_sortino_ratio",
]
