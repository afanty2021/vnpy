"""
vnpy_china_data配置项

定义模块内部使用的配置常量。
"""

from dataclasses import dataclass


@dataclass
class DataConfig:
    """数据服务配置"""
    # 缓存配置
    DEFAULT_CACHE_TTL: int = 3600  # 默认缓存时间（秒）
    BAR_CACHE_TTL: int = 3600  # K线缓存时间
    TICK_CACHE_TTL: int = 60  # Tick缓存时间
    INFO_CACHE_TTL: int = 86400  # 信息缓存时间（1天）

    # 数据库配置
    BATCH_SIZE: int = 1000  # 批量写入大小

    # API配置
    MAX_RETRY: int = 3  # 最大重试次数
    RETRY_DELAY: float = 1.0  # 重试延迟（秒）

    # QMT配置
    QMT_RECONNECT_INTERVAL: int = 30  # QMT重连间隔（秒）
    QMT_TICK_BUFFER_SIZE: int = 1000  # Tick缓冲区大小

    # 港股通名单更新配置
    HK_CONNECT_UPDATE_DAYS: int = 7  # 港股通名单更新周期（天）
    HK_CONNECT_AUTO_UPDATE: bool = True  # 是否自动检查更新
    HK_CONNECT_UPDATE_ON_START: bool = False  # 启动时是否自动更新


# 模块级配置实例
data_config = DataConfig()
