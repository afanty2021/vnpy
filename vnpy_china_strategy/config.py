"""
策略配置管理

提供各类策略的默认配置参数。
"""

from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class DragonTigerConfig:
    """龙虎榜策略配置"""

    # 机构席位策略
    institution_threshold: float = 1000.0  # 机构买入阈值(万)
    min_institution_count: int = 3  # 最少机构数
    institution_buy_ratio: float = 0.6  # 机构买入占比阈值

    # 游资策略
    broker_threshold: float = 500.0  # 游资买入阈值(万)
    broker_ratio: float = 0.6  # 游资买入占比

    # 跟随策略
    appear_count: int = 2  # 上榜次数
    follow_days: int = 5  # 跟随天数
    pullback_ratio: float = 0.05  # 回调买入比例

    # 通用参数
    holding_days: int = 5  # 持有天数
    position_ratio: float = 0.1  # 仓位比例
    stop_loss_pct: float = -5.0  # 止损比例
    stop_profit_pct: float = 10.0  # 止盈比例


@dataclass
class NorthboundConfig:
    """北向资金策略配置"""

    # 资金流向策略
    net_inflow_threshold: float = 10.0  # 净流入阈值(亿)
    market_filter: str = "沪深300"  # 市场筛选

    # 持股变化策略
    change_threshold: float = 0.05  # 变化阈值 5%
    consecutive_days: int = 3  # 连续天数
    min_shares: int = 1000000  # 最少持股数

    # 板块偏好策略
    sector_top_n: int = 5  # 板块前N只
    sector_change_threshold: float = 0.03  # 板块涨幅阈值

    # 通用参数
    position_ratio: float = 0.15  # 仓位比例
    holding_days: int = 10  # 持有天数


@dataclass
class SectorRotationConfig:
    """板块轮动策略配置"""

    # 板块强度策略
    rotation_period: int = 20  # 轮动周期(交易日)
    top_n: int = 3  # 选取板块数
    momentum_days: int = 60  # 动量计算天数
    min_strength: float = 1.0  # 最小强度阈值

    # 轮动信号策略
    rebalance_threshold: float = 0.2  # 轮动阈值
    momentum_lookback: int = 20  # 动量回看天数

    # 通用参数
    position_ratio: float = 0.2  # 仓位比例
    max_sector_count: int = 5  # 最大板块数


@dataclass
class EventDrivenConfig:
    """事件驱动策略配置"""

    # 业绩预告策略
    event_types: list = field(default_factory=lambda: ["预增", "扭亏", "续盈"])
    min_yoy_change: float = 0.2  # 最少同比变化 20%
    holding_days: int = 5  # 持有天数

    # 并购重组策略
    mna_min_impact: float = 0.1  # 最小影响金额(亿)

    # 政策事件策略
    keywords: list = field(default_factory=lambda: [
        "新能源", "半导体", "医药", "房地产", "5G", "人工智能"
    ])
    impact_threshold: float = 0.5  # 影响阈值
    sector_exposure: float = 0.15  # 板块暴露度

    # 通用参数
    position_ratio: float = 0.1  # 仓位比例
    stop_loss_pct: float = -7.0  # 止损比例
    stop_profit_pct: float = 15.0  # 止盈比例


@dataclass
class ConvertibleConfig:
    """可转债策略配置"""

    # 转股套利策略
    premium_threshold: float = -5.0  # 溢价率阈值 (负数%)
    min_conversion_value: float = 100.0  # 最小转股价值
    trend_days: int = 20  # 趋势判断天数
    min_volume: float = 10000000  # 最小成交额

    # 定价模型
    risk_free_rate: float = 0.03  # 无风险利率
    volatility: float = 0.2  # 波动率

    # 通用参数
    position_ratio: float = 0.2  # 仓位比例
    holding_days: int = 20  # 持有天数
    stop_loss_pct: float = -5.0  # 止损比例
    stop_profit_pct: float = 8.0  # 止盈比例


class StrategyConfig:
    """策略配置管理类"""

    # 龙虎榜策略配置
    DRAGON_TIGER = DragonTigerConfig()

    # 北向资金策略配置
    NORTHBOUND = NorthboundConfig()

    # 板块轮动策略配置
    SECTOR_ROTATION = SectorRotationConfig()

    # 事件驱动策略配置
    EVENT_DRIVEN = EventDrivenConfig()

    # 可转债策略配置
    CONVERTIBLE = ConvertibleConfig()

    @classmethod
    def get_config(cls, strategy_type: str) -> Any:
        """获取策略配置

        Args:
            strategy_type: 策略类型

        Returns:
            策略配置对象
        """
        config_map = {
            "dragon_tiger": cls.DRAGON_TIGER,
            "northbound": cls.NORTHBOUND,
            "sector_rotation": cls.SECTOR_ROTATION,
            "event_driven": cls.EVENT_DRIVEN,
            "convertible": cls.CONVERTIBLE,
        }
        return config_map.get(strategy_type.lower())

    @classmethod
    def update_config(cls, strategy_type: str, **kwargs) -> None:
        """更新策略配置

        Args:
            strategy_type: 策略类型
            **kwargs: 配置参数
        """
        config = cls.get_config(strategy_type)
        if config:
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)


# 默认配置实例
strategy_config = StrategyConfig()
