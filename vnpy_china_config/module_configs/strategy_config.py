"""
策略模块配置

定义策略运行和回测相关配置。
"""

from pathlib import Path

from pydantic import Field, field_validator

from vnpy_china_config.base import BaseConfig


class StrategyModuleConfig(BaseConfig):
    """策略模块配置

    统一管理策略运行和回测相关配置。

    Attributes:
        # 策略目录
        strategy_dir: 策略文件存放目录

        # 回测配置
        backtest_start_date: 回测开始日期
        backtest_end_date: 回测结束日期
        backtest_slippage: 滑点（%）
        backtest_commission: 手续费率（%）

        # 实盘配置
        trading_enabled: 是否启用实盘交易
        max_position_count: 最大持仓股票数量
        default_position_ratio: 默认持仓比例
    """

    # 策略目录
    strategy_dir: Path = Field(default_factory=lambda: Path("strategies"))

    # 回测配置
    backtest_start_date: str = "2020-01-01"
    backtest_end_date: str = "2024-12-31"
    backtest_slippage: float = 0.001
    backtest_commission: float = 0.0003

    # 实盘配置
    trading_enabled: bool = False
    max_position_count: int = 10
    default_position_ratio: float = 0.1

    @field_validator("backtest_slippage", "backtest_commission")
    @classmethod
    def validate_rate(cls, v: float) -> float:
        """验证费率"""
        if v < 0:
            raise ValueError(f"费率不能为负数，当前值: {v}")
        return v

    @field_validator("max_position_count")
    @classmethod
    def validate_position_count(cls, v: int) -> int:
        """验证持仓数量"""
        if v <= 0:
            raise ValueError(f"max_position_count 必须大于 0，当前值: {v}")
        return v

    @field_validator("default_position_ratio")
    @classmethod
    def validate_position_ratio(cls, v: float) -> float:
        """验证持仓比例"""
        if v < 0 or v > 1:
            raise ValueError(f"default_position_ratio 必须在 0-1 之间，当前值: {v}")
        return v
