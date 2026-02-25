"""
行情分析模块配置

定义 Level-2 数据、资金流向分类和板块配置。
"""

from pydantic import field_validator

from vnpy_china_config.base import BaseConfig


class AnalysisModuleConfig(BaseConfig):
    """行情分析模块配置

    统一管理行情分析相关配置。

    Attributes:
        # Level-2数据
        level2_enabled: 是否启用 Level-2 数据
        level2_data_source: Level-2 数据源（qmt/tushare）

        # 资金流向分类阈值（万元）
        super_large_threshold: 超大单阈值
        large_threshold: 大单阈值
        medium_threshold: 中单阈值

        # 板块配置
        sector_count: 板块数量
        sector_update_interval: 板块更新间隔（秒）
    """

    # Level-2数据
    level2_enabled: bool = False
    level2_data_source: str = "qmt"

    # 资金流向分类阈值（万元）
    super_large_threshold: float = 100.0
    large_threshold: float = 20.0
    medium_threshold: float = 5.0

    # 板块配置
    sector_count: int = 30
    sector_update_interval: int = 3600

    @field_validator("level2_data_source")
    @classmethod
    def validate_data_source(cls, v: str) -> str:
        """验证数据源"""
        valid_sources = ["qmt", "tushare", "custom"]
        if v not in valid_sources:
            raise ValueError(f"无效的 level2_data_source: {v}，必须是 {valid_sources} 之一")
        return v

    @field_validator("super_large_threshold", "large_threshold", "medium_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        """验证阈值"""
        if v < 0:
            raise ValueError(f"阈值不能为负数，当前值: {v}")
        return v

    @field_validator("sector_count")
    @classmethod
    def validate_sector_count(cls, v: int) -> int:
        """验证板块数量"""
        if v <= 0:
            raise ValueError(f"sector_count 必须大于 0，当前值: {v}")
        return v

    @field_validator("sector_update_interval")
    @classmethod
    def validate_update_interval(cls, v: int) -> int:
        """验证更新间隔"""
        if v <= 0:
            raise ValueError(f"sector_update_interval 必须大于 0，当前值: {v}")
        return v
