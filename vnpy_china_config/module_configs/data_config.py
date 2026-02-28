"""
数据服务模块配置

定义数据服务相关配置，包括 Tushare API、缓存等。
QMT 等全局配置已移至 GlobalConfig。
"""

import os
from pathlib import Path

from pydantic import Field, field_validator

from vnpy_china_config.base import BaseConfig


class DataModuleConfig(BaseConfig):
    """数据服务模块配置

    统一管理数据服务的所有配置项。
    QMT 等全局配置已移至 GlobalConfig，此处只保留数据服务特有配置。

    Attributes:
        # Tushare配置
        tushare_token: Tushare API Token
        tushare_rate_limit: API 调用频率限制（次/分钟）
        tushare_retry_times: 重试次数
        tushare_retry_delay: 重试延迟（秒）

        # 缓存配置
        cache_bar_ttl: K线缓存 TTL（秒）
        cache_tick_ttl: Tick 缓存 TTL（秒）
        cache_info_ttl: 基础信息缓存 TTL（秒）

        # 增量更新配置
        auto_update_enabled: 是否启用增量更新
        update_interval: 更新间隔（秒）
        update_start_time: 更新开始时间
        update_end_time: 更新结束时间
    """

    # Tushare配置 - 从环境变量读取
    tushare_token: str = Field(
        default=os.getenv("TUSHARE_TOKEN", ""),
        description="Tushare API Token，从环境变量TUSHARE_TOKEN读取"
    )
    tushare_rate_limit: int = 200
    tushare_retry_times: int = 3
    tushare_retry_delay: int = 1

    # 缓存配置
    cache_bar_ttl: int = 300
    cache_tick_ttl: int = 30
    cache_info_ttl: int = 86400

    # 增量更新配置
    auto_update_enabled: bool = True
    update_interval: int = 3600
    update_start_time: str = "08:00"
    update_end_time: str = "20:00"

    # QMT配置 - 从全局配置读取
    qmt_use_rpc: bool = False
    qmt_rpc_req_address: str = "tcp://127.0.0.1:2014"
    qmt_rpc_sub_address: str = "tcp://127.0.0.1:4102"
    qmt_path: str = ""
    qmt_account_id: str = ""

    @field_validator("tushare_rate_limit")
    @classmethod
    def validate_rate_limit(cls, v: int) -> int:
        """验证 API 频率限制"""
        if v <= 0:
            raise ValueError(f"tushare_rate_limit 必须大于 0，当前值: {v}")
        return v

    @field_validator("cache_bar_ttl", "cache_tick_ttl", "cache_info_ttl")
    @classmethod
    def validate_cache_ttl(cls, v: int) -> int:
        """验证缓存 TTL"""
        if v <= 0:
            raise ValueError(f"缓存 TTL 必须大于 0，当前值: {v}")
        return v
