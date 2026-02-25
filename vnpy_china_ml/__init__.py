"""vnpy_china_ml - A股机器学习模块"""

# GUI应用
from .app import ChinaMlApp
from .gui_engine import ChinaMlGuiEngine

# 模型管理
from .model.manager import ModelManager, ModelMetadata
from .model.china_model import ChinaAlphaModel

# 数据集
from .dataset import (
    ChinaDataLoader,
    Alpha158Calculator,
    ChinaAlphaDataset,
    create_alpha_dataset,
)

# 监控
from .monitoring import (
    ModelPerformanceMonitor,
    PerformanceMetric,
    PerformanceThreshold,
    ModelPerformanceSnapshot,
)

# 在线学习
from .online_learning import (
    OnlineLearner,
    OnlineLearningManager,
    OnlineLearningConfig,
    TrainingSample,
)

# 因子
from .factors import (
    BaseFactor,
    DragonTigerFactor,
    NorthboundFactor,
    SectorRotationFactor,
    FactorDataLoader,
    FactorCalculator,
    create_factor_calculator,
    # 因子组合
    FactorCombiner,
    FactorTimer,
    FactorCombinationConfig,
    FactorTimingConfig,
    FactorWeight,
    WeightMethod,
    OrthogonalMethod,
    create_factor_combiner,
)

# 数据管理
from .data import (
    DataPreloader,
    DataUpdateScheduler,
    PreloadConfig,
    UpdateConfig,
    create_data_manager,
    EVENT_DATA_PRELOAD_START,
    EVENT_DATA_PRELOAD_COMPLETE,
    EVENT_DATA_UPDATE_START,
    EVENT_DATA_UPDATE_COMPLETE,
)

# 回测
from .backtesting import (
    FactorBacktester,
    FactorIcResult,
    FactorIcStats,
    LayerBacktestResult,
    FactorBacktestReport,
    create_factor_backtester,
)

__version__ = "1.4.0"

__all__ = [
    # GUI应用
    "ChinaMlApp",
    "ChinaMlGuiEngine",
    # 模型管理
    "ModelManager",
    "ModelMetadata",
    "ChinaAlphaModel",
    # 数据集
    "ChinaDataLoader",
    "Alpha158Calculator",
    "ChinaAlphaDataset",
    "create_alpha_dataset",
    # 监控
    "ModelPerformanceMonitor",
    "PerformanceMetric",
    "PerformanceThreshold",
    "ModelPerformanceSnapshot",
    # 在线学习
    "OnlineLearner",
    "OnlineLearningManager",
    "OnlineLearningConfig",
    "TrainingSample",
    # 因子
    "BaseFactor",
    "DragonTigerFactor",
    "NorthboundFactor",
    "SectorRotationFactor",
    "FactorDataLoader",
    "FactorCalculator",
    "create_factor_calculator",
    # 因子组合
    "FactorCombiner",
    "FactorTimer",
    "FactorCombinationConfig",
    "FactorTimingConfig",
    "FactorWeight",
    "WeightMethod",
    "OrthogonalMethod",
    "create_factor_combiner",
    # 数据管理
    "DataPreloader",
    "DataUpdateScheduler",
    "PreloadConfig",
    "UpdateConfig",
    "create_data_manager",
    "EVENT_DATA_PRELOAD_START",
    "EVENT_DATA_PRELOAD_COMPLETE",
    "EVENT_DATA_UPDATE_START",
    "EVENT_DATA_UPDATE_COMPLETE",
    # 回测
    "FactorBacktester",
    "FactorIcResult",
    "FactorIcStats",
    "LayerBacktestResult",
    "FactorBacktestReport",
    "create_factor_backtester",
]
