"""A股机器学习数据管理模块

提供数据预加载和定时更新功能。
"""

from .data_manager import (
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

__all__ = [
    "DataPreloader",
    "DataUpdateScheduler",
    "PreloadConfig",
    "UpdateConfig",
    "create_data_manager",
    "EVENT_DATA_PRELOAD_START",
    "EVENT_DATA_PRELOAD_COMPLETE",
    "EVENT_DATA_UPDATE_START",
    "EVENT_DATA_UPDATE_COMPLETE",
]
