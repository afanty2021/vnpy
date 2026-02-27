"""
数据服务模块配置

定义数据服务相关配置，包括 Tushare API、QMT、缓存等。
"""

import os
from pathlib import Path

from pydantic import Field, field_validator

from vnpy_china_config.base import BaseConfig


class DataModuleConfig(BaseConfig):
    """数据服务模块配置

    统一管理数据服务的所有配置项。

    Attributes:
        # Tushare配置
        tushare_token: Tushare API Token
        tushare_rate_limit: API 调用频率限制（次/分钟）
        tushare_retry_times: 重试次数
        tushare_retry_delay: 重试延迟（秒）

        # QMT配置
        qmt_path: QMT 客户端路径
        qmt_account_id: QMT 资金账号
        qmt_session_id: QMT 会话ID（可选，多会话时使用）
        qmt_password: QMT 交易密码（可选，某些场景需要）

        # QMT RPC配置（客户端连接）
        qmt_use_rpc: 是否使用RPC模式连接QMT
        qmt_rpc_req_address: QMT RPC请求地址（客户端使用）
        qmt_rpc_sub_address: QMT RPC订阅地址（客户端使用）

        # RPC服务端配置（服务端使用）
        rpc_server_rep_address: RPC服务端监听地址（REP模式）
        rpc_server_pub_address: RPC服务端监听地址（PUB模式）

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

    # QMT配置
    qmt_path: Path = Field(default_factory=lambda: Path("D:/国金证券QMT交易端/userdata_mini"))
    qmt_account_id: str = ""
    qmt_session_id: int = 0
    qmt_password: str = ""

    # QMT RPC配置（客户端连接）
    qmt_use_rpc: bool = Field(
        default=True,
        description="是否使用RPC模式连接QMT（Mac/Linux客户端推荐True）"
    )
    qmt_rpc_req_address: str = Field(
        default="tcp://127.0.0.1:2014",
        description="QMT RPC请求地址（客户端连接服务端使用）"
    )
    qmt_rpc_sub_address: str = Field(
        default="tcp://127.0.0.1:4102",
        description="QMT RPC订阅地址（客户端连接服务端使用）"
    )

    # RPC服务端配置（服务端使用）
    rpc_server_rep_address: str = Field(
        default="tcp://0.0.0.0:2014",
        description="RPC服务端监听地址（REP模式，服务端绑定）"
    )
    rpc_server_pub_address: str = Field(
        default="tcp://0.0.0.0:4102",
        description="RPC服务端监听地址（PUB模式，服务端绑定）"
    )

    # 缓存配置
    cache_bar_ttl: int = 300
    cache_tick_ttl: int = 30
    cache_info_ttl: int = 86400

    # 增量更新配置
    auto_update_enabled: bool = True
    update_interval: int = 3600
    update_start_time: str = "08:00"
    update_end_time: str = "20:00"

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
