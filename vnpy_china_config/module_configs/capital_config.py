"""
资金管理模块配置

定义仓位管理、分批交易和回撤控制相关配置。
"""

from typing import List

from pydantic import Field, field_validator

from vnpy_china_config.base import BaseConfig


class CapitalModuleConfig(BaseConfig):
    """资金管理模块配置

    统一管理仓位管理、分批交易和回撤控制配置。

    Attributes:
        # 仓位管理
        max_position_count: 最大持仓股票数量
        default_position_type: 默认持仓类型（equal_weight/risk_parity）
        risk_parity_target_vol: 风险平价目标波动率

        # 分批交易
        default_batch_type: 默认分批类型（equal/time_interval）
        default_batch_count: 默认分批次数
        batch_delay: 分批延迟（秒）

        # 回撤控制
        max_drawdown: 最大回撤比例
        drawdown_reduction_levels: 回撤 reduction 阈值列表
        drawdown_reduction_ratios: 回撤 reduction 比例列表
    """

    # 仓位管理
    max_position_count: int = 10
    default_position_type: str = "equal_weight"
    risk_parity_target_vol: float = 0.1

    # 分批交易
    default_batch_type: str = "equal"
    default_batch_count: int = 5
    batch_delay: int = 60

    # 回撤控制
    max_drawdown: float = 0.15
    drawdown_reduction_levels: List[float] = Field(default_factory=lambda: [0.5, 0.75, 1.0])
    drawdown_reduction_ratios: List[float] = Field(default_factory=lambda: [1.0, 0.7, 0.5, 0.0])

    @field_validator("max_position_count")
    @classmethod
    def validate_position_count(cls, v: int) -> int:
        """验证持仓数量"""
        if v <= 0:
            raise ValueError(f"max_position_count 必须大于 0，当前值: {v}")
        return v

    @field_validator("default_position_type")
    @classmethod
    def validate_position_type(cls, v: str) -> str:
        """验证持仓类型"""
        valid_types = ["equal_weight", "risk_parity", "custom"]
        if v not in valid_types:
            raise ValueError(f"无效的 position_type: {v}，必须是 {valid_types} 之一")
        return v

    @field_validator("risk_parity_target_vol")
    @classmethod
    def validate_target_vol(cls, v: float) -> float:
        """验证目标波动率"""
        if v <= 0 or v > 1:
            raise ValueError(f"risk_parity_target_vol 必须在 0-1 之间，当前值: {v}")
        return v

    @field_validator("default_batch_count", "batch_delay")
    @classmethod
    def validate_batch_params(cls, v: int) -> int:
        """验证分批参数"""
        if v <= 0:
            raise ValueError(f"值必须大于 0，当前值: {v}")
        return v

    @field_validator("max_drawdown")
    @classmethod
    def validate_drawdown(cls, v: float) -> float:
        """验证最大回撤"""
        if v < 0 or v > 1:
            raise ValueError(f"max_drawdown 必须在 0-1 之间，当前值: {v}")
        return v
