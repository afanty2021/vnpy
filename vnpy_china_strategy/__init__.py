"""
vnpy_china_strategy - A股特色策略库

提供5大类A股特有策略：
- 龙虎榜策略（机构席位追踪、游资追踪、跟随交易）
- 北向资金策略（资金流向、持股变化、板块偏好）
- 板块轮动策略（板块强度、资金流向、轮动信号）
- 事件驱动策略（业绩预告、并购重组、政策事件）
- 可转债套利策略（转股套利、定价模型）
"""

__version__ = "1.0.0"

# 导入主要类和函数
from .template import ChinaStrategyTemplate, ChinaStrategyBase
from .base import RiskControlMixin, PositionManager, SignalChecker
from .data_service import (
    IDataProvider,
    ChinaStrategyDataService,
    get_data_service,
)

# 策略导入
from .dragon_tiger.institution import InstitutionTrackerStrategy
from .dragon_tiger.broker import BrokerMoneyStrategy
from .dragon_tiger.follow import FollowStrategy

from .northbound.flow import NorthboundFlowStrategy
from .northbound.holding import HoldingChangeStrategy
from .northbound.sector import SectorPreferenceStrategy

from .sector_rotation.strength import SectorStrengthStrategy
from .sector_rotation.signal import RotationSignalStrategy

from .event_driven.earnings import EarningsForecastStrategy
from .event_driven.policy import PolicyEventStrategy

from .convertible.arbitrage import ConvertibleArbitrageStrategy

# GUI应用导入
from .app import ChinaStrategyApp
from .engine import ChinaStrategyEngine
from .gui_engine import ChinaStrategyGuiEngine

__all__ = [
    # 版本
    "__version__",
    # 基础类
    "ChinaStrategyTemplate",
    "ChinaStrategyBase",
    "RiskControlMixin",
    "PositionManager",
    "SignalChecker",
    # 数据服务
    "IDataProvider",
    "ChinaStrategyDataService",
    "get_data_service",
    # 龙虎榜策略
    "InstitutionTrackerStrategy",
    "BrokerMoneyStrategy",
    "FollowStrategy",
    # 北向资金策略
    "NorthboundFlowStrategy",
    "HoldingChangeStrategy",
    "SectorPreferenceStrategy",
    # 板块轮动策略
    "SectorStrengthStrategy",
    "RotationSignalStrategy",
    # 事件驱动策略
    "EarningsForecastStrategy",
    "PolicyEventStrategy",
    # 可转债策略
    "ConvertibleArbitrageStrategy",
    # GUI应用
    "ChinaStrategyApp",
    "ChinaStrategyEngine",
    "ChinaStrategyGuiEngine",
]
