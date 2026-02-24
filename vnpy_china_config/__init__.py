"""
A股配置管理模块

提供A股交易系统的统一配置管理，包括：
- 数据库配置（MySQL、Redis）
- Tushare API配置
- QMT配置
- 缓存配置
"""

from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class DatabaseConfig:
    """数据库配置"""
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "vnpy_china"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0


@dataclass
class TushareConfig:
    """Tushare API配置"""
    token: str = ""
    rate_limit: int = 200  # 每分钟调用次数
    timeout: int = 30  # 超时时间（秒）


@dataclass
class QMTConfig:
    """QMT配置"""
    path: str = ""
    account_id: str = ""
    reconnect_interval: int = 30  # 重连间隔（秒）


@dataclass
class CacheConfig:
    """缓存配置"""
    bar_ttl: int = 3600  # K线缓存时间（秒）
    info_ttl: int = 86400  # 信息缓存时间（秒）
    dragon_tiger_ttl: int = 604800  # 龙虎榜缓存时间（秒）


@dataclass
class DataModuleConfig:
    """数据模块完整配置"""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    tushare: TushareConfig = field(default_factory=TushareConfig)
    qmt: QMTConfig = field(default_factory=QMTConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)

    # 便捷访问属性
    @property
    def tushare_token(self) -> str:
        return self.tushare.token

    @property
    def tushare_rate_limit(self) -> int:
        return self.tushare.rate_limit

    @property
    def qmt_path(self) -> str:
        return self.qmt.path

    @property
    def qmt_account_id(self) -> str:
        return self.qmt.account_id

    @property
    def cache_bar_ttl(self) -> int:
        return self.cache.bar_ttl

    @property
    def cache_info_ttl(self) -> int:
        return self.cache.info_ttl


class ConfigManager:
    """配置管理器

    负责加载和管理A股系统的所有配置。
    支持从环境变量和配置文件加载配置。
    """

    _instance: Optional["ConfigManager"] = None
    _config: Optional[DataModuleConfig] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._config = self._load_config()

    def _load_config(self) -> DataModuleConfig:
        """加载配置"""
        # 数据库配置
        database = DatabaseConfig(
            mysql_host=os.getenv("MYSQL_HOST", "localhost"),
            mysql_port=int(os.getenv("MYSQL_PORT", "3306")),
            mysql_user=os.getenv("MYSQL_USER", "root"),
            mysql_password=os.getenv("MYSQL_PASSWORD", ""),
            mysql_database=os.getenv("MYSQL_DATABASE", "vnpy_china"),
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_password=os.getenv("REDIS_PASSWORD", ""),
            redis_db=int(os.getenv("REDIS_DB", "0")),
        )

        # Tushare配置
        tushare = TushareConfig(
            token=os.getenv("TUSHARE_TOKEN", ""),
            rate_limit=int(os.getenv("TUSHARE_RATE_LIMIT", "200")),
            timeout=int(os.getenv("TUSHARE_TIMEOUT", "30")),
        )

        # QMT配置
        qmt = QMTConfig(
            path=os.getenv("QMT_PATH", ""),
            account_id=os.getenv("QMT_ACCOUNT_ID", ""),
        )

        # 缓存配置
        cache = CacheConfig(
            bar_ttl=int(os.getenv("CACHE_BAR_TTL", "3600")),
            info_ttl=int(os.getenv("CACHE_INFO_TTL", "86400")),
            dragon_tiger_ttl=int(os.getenv("CACHE_DRAGON_TIGER_TTL", "604800")),
        )

        return DataModuleConfig(
            database=database,
            tushare=tushare,
            qmt=qmt,
            cache=cache,
        )

    def get_config(self, module: str = "data") -> DataModuleConfig:
        """获取指定模块的配置

        Args:
            module: 模块名称

        Returns:
            模块配置对象
        """
        return self._config

    def update_config(self, config: DataModuleConfig) -> None:
        """更新配置

        Args:
            config: 新的配置对象
        """
        self._config = config

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例（用于测试）"""
        cls._instance = None
        cls._config = None
