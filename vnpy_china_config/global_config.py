"""
全局配置模块

定义系统级配置类，包括数据库、日志、RPC 和风控配置。
"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .base import BaseConfig, Environment


class DatabaseConfig(BaseModel):
    """数据库配置

    统一管理 MySQL 和 Redis 数据库连接配置。

    Attributes:
        mysql_host: MySQL 主机地址
        mysql_port: MySQL 端口
        mysql_user: MySQL 用户名
        mysql_password: MySQL 密码
        mysql_database: MySQL 数据库名
        redis_host: Redis 主机地址
        redis_port: Redis 端口
        redis_db: Redis 数据库编号
        redis_password: Redis 密码
        pool_size: 数据库连接池大小
        max_overflow: 连接池最大溢出数

    Example:
        ```python
        db_config = DatabaseConfig(
            mysql_host="localhost",
            mysql_port=3306,
            mysql_user="root",
            mysql_password="password",
            mysql_database="vnpy_china"
        )
        ```
    """

    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "vnpy"
    mysql_password: str = ""
    mysql_database: str = "vnpy_china"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    pool_size: int = 5
    max_overflow: int = 10

    @field_validator("mysql_port", "redis_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """验证端口号"""
        if v <= 0 or v > 65535:
            raise ValueError(f"端口号必须在 1-65535 之间，当前值: {v}")
        return v


class LoggingConfig(BaseModel):
    """日志配置

    统一管理系统日志输出配置。

    Attributes:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: 日志格式
        file_enabled: 是否启用文件日志
        file_path: 日志文件路径
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的日志文件数量
        console_enabled: 是否启用控制台日志

    Example:
        ```python
        log_config = LoggingConfig(
            level="INFO",
            file_enabled=True,
            file_path=Path("logs/vnpy_china.log")
        )
        ```
    """

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_path: Path = Field(default_factory=lambda: Path("logs/vnpy_china.log"))
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_enabled: bool = True

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"无效的日志级别: {v}，必须是 {valid_levels} 之一")
        return v.upper()

    @field_validator("max_bytes")
    @classmethod
    def validate_max_bytes(cls, v: int) -> int:
        """验证日志文件大小"""
        if v <= 0:
            raise ValueError(f"max_bytes 必须大于 0，当前值: {v}")
        return v

    @field_validator("backup_count")
    @classmethod
    def validate_backup_count(cls, v: int) -> int:
        """验证日志文件保留数量"""
        if v < 0:
            raise ValueError(f"backup_count 不能为负数，当前值: {v}")
        return v


class RpcConfig(BaseModel):
    """RPC 配置

    统一管理 RPC 通信配置。

    Attributes:
        rep_address: REP 模式地址（请求-响应）
        pub_address: PUB 模式地址（发布-订阅）
        timeout: 超时时间（毫秒）

    Example:
        ```python
        rpc_config = RpcConfig(
            rep_address="tcp://127.0.0.1:2014",
            pub_address="tcp://127.0.0.1:4102",
            timeout=5000
        )
        ```
    """

    rep_address: str = "tcp://127.0.0.1:2014"
    pub_address: str = "tcp://127.0.0.1:4102"
    timeout: int = 5000

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """验证超时时间"""
        if v <= 0:
            raise ValueError(f"timeout 必须大于 0，当前值: {v}")
        return v


class RiskGlobalConfig(BaseModel):
    """风控全局参数配置

    统一管理系统级风控参数。

    Attributes:
        max_position_ratio: 最大持仓比例
        max_single_position_ratio: 单只股票最大持仓比例
        max_daily_loss_ratio: 单日最大亏损比例
        max_consecutive_losses: 最大连续亏损次数

    Example:
        ```python
        risk_config = RiskGlobalConfig(
            max_position_ratio=0.8,
            max_single_position_ratio=0.2,
            max_daily_loss_ratio=0.05,
            max_consecutive_losses=5
        )
        ```
    """

    max_position_ratio: float = 0.8
    max_single_position_ratio: float = 0.2
    max_daily_loss_ratio: float = 0.05
    max_consecutive_losses: int = 5

    @field_validator("max_position_ratio", "max_single_position_ratio", "max_daily_loss_ratio")
    @classmethod
    def validate_ratio(cls, v: float) -> float:
        """验证比例值"""
        if v < 0 or v > 1:
            raise ValueError(f"比例值必须在 0-1 之间，当前值: {v}")
        return v

    @field_validator("max_consecutive_losses")
    @classmethod
    def validate_consecutive_losses(cls, v: int) -> int:
        """验证连续亏损次数"""
        if v < 0:
            raise ValueError(f"max_consecutive_losses 不能为负数，当前值: {v}")
        return v


class GlobalConfig(BaseConfig):
    """全局配置

    系统级配置的顶层配置类，整合所有全局配置项。
    作为配置层次结构的根节点。

    Attributes:
        environment: 运行环境
        database: 数据库配置
        logging: 日志配置
        rpc: RPC 配置
        risk: 风控全局参数
        work_dir: 工作目录
        data_dir: 数据目录

    Example:
        ```python
        global_config = GlobalConfig(
            environment=Environment.PRODUCTION,
            database=DatabaseConfig(mysql_host="prod-db.example.com"),
            logging=LoggingConfig(level="WARNING")
        )
        ```
    """

    environment: Environment = Environment.DEVELOPMENT
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    rpc: RpcConfig = Field(default_factory=RpcConfig)
    risk: RiskGlobalConfig = Field(default_factory=RiskGlobalConfig)
    work_dir: Path = Field(default_factory=lambda: Path(".vntrader_china"))
    data_dir: Path = Field(default_factory=lambda: Path("data"))

    def get_mysql_dsn(self) -> str:
        """获取 MySQL DSN 连接字符串

        Returns:
            MySQL DSN 字符串
        """
        return (
            f"mysql+pymysql://{self.database.mysql_user}:{self.database.mysql_password}"
            f"@{self.database.mysql_host}:{self.database.mysql_port}/{self.database.mysql_database}"
        )

    def get_redis_url(self) -> str:
        """获取 Redis 连接 URL

        Returns:
            Redis 连接 URL
        """
        if self.database.redis_password:
            return f"redis://:{self.database.redis_password}@{self.database.redis_host}:{self.database.redis_port}/{self.database.redis_db}"
        return f"redis://{self.database.redis_host}:{self.database.redis_port}/{self.database.redis_db}"
