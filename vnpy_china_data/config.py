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


# 模块级配置实例
data_config = DataConfig()
