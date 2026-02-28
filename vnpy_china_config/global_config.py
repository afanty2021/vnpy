"""
全局配置模块

定义系统级配置类，包括数据库、日志、RPC 和风控配置。
"""

import warnings
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .base import BaseConfig, Environment


class DatabaseConfig(BaseModel):
    """数据库配置

    统一管理 MySQL 和 Redis 数据库连接配置。

    验证规则：
        - 端口号必须在 1-65535 之间
        - 连接池大小（pool_size, max_overflow）必须大于 0 且不超过 100
        - 使用空密码或默认密码 "password" 时会发出 UserWarning

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
        pool_size: 数据库连接池大小（必须 > 0 且 <= 100）
        max_overflow: 连接池最大溢出数（必须 > 0 且 <= 100）
        enabled: 是否启用数据库功能

    Example:
        ```python
        db_config = DatabaseConfig(
            mysql_host="localhost",
            mysql_port=3306,
            mysql_user="root",
            mysql_password="strong_password",
            mysql_database="vnpy_china",
            pool_size=10,
            max_overflow=20,
            enabled=True
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
    enabled: bool = True  # 默认启用

    @field_validator("mysql_port", "redis_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """验证端口号"""
        if v <= 0 or v > 65535:
            raise ValueError(f"端口号必须在 1-65535 之间，当前值: {v}")
        return v

    @field_validator("pool_size", "max_overflow")
    @classmethod
    def validate_pool_size(cls, v: int) -> int:
        """验证连接池大小"""
        if v <= 0:
            raise ValueError(f"连接池大小必须大于0，当前值: {v}")
        if v > 100:
            raise ValueError(f"连接池大小不应超过100，当前值: {v}")
        return v

    @model_validator(mode="after")
    def validate_database_config(self) -> "DatabaseConfig":
        """数据库配置整体验证"""
        # 检查密码（生产环境警告）
        if self.mysql_password == "" or self.mysql_password == "password":
            warnings.warn(
                "MySQL使用空密码或默认密码'password'，生产环境请设置强密码！",
                UserWarning,
                stacklevel=2
            )
        return self


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


class QmtConfig(BaseModel):
    """QMT 交易接口配置

    统一管理 QMT/miniQMT 交易接口连接配置。

    Attributes:
        account_id: QMT 交易账号（必填）
        mini_path: miniQMT 路径（必填，必须是 userdata_mini 子目录）
        session_id: 会话ID（可选，用于多会话）
        password: 交易密码（可选，某些场景需要）
        enabled: 是否启用QMT（默认False，避免未配置时启动）

    Example:
        ```python
        qmt_config = QmtConfig(
            account_id="40218291",
            mini_path="D:/国金证券QMT交易端/userdata_mini/",
            enabled=True
        )
        ```
    """

    account_id: str = Field(
        default="",
        description="QMT交易账号（启用时必填）"
    )
    mini_path: str = Field(
        default="",
        description="miniQMT路径（启用时必填，必须是userdata_mini子目录）"
    )
    session_id: int = 0
    password: str = ""
    enabled: bool = False  # 默认禁用，避免未配置时启动
    use_rpc: bool = Field(
        default=False,
        description="是否使用RPC模式连接远程QMT服务"
    )

    @field_validator("account_id", "mini_path")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """去除字段首尾空格"""
        return v.strip() if v else v

    @model_validator(mode="after")
    def validate_required_qmt_fields(self) -> "QmtConfig":
        """验证QMT必填字段

        仅在enabled=True时验证必填，允许预配置但未启用的场景。
        RPC模式下mini_path可以为空。
        """
        # 如果启用QMT，则account_id必须非空
        if self.enabled:
            if not self.account_id:
                raise ValueError(
                    "account_id 在启用QMT时不能为空。"
                    "请设置有效的account_id值，或设置enabled=False。"
                )
            # RPC模式下mini_path可以为空
            if not self.use_rpc and not self.mini_path:
                raise ValueError(
                    "mini_path 在启用QMT时不能为空。"
                    "请设置有效的mini_path值，或设置use_rpc: true使用RPC模式。"
                )
        return self

    @field_validator("mini_path")
    @classmethod
    def validate_mini_path(cls, v: str) -> str:
        """验证 miniQMT 路径"""
        if not v:
            return v

        v = v.strip()

        # 检查路径是否包含 userdata_mini
        if "userdata_mini" not in v and "USERDATA_MINI" not in v.upper():
            warnings.warn(
                f"miniQMT 路径可能不正确: {v}\n"
                "正确路径应包含 userdata_mini 子目录，例如:\n"
                "  D:/国金证券QMT交易端/userdata_mini/\n"
                "  /opt/QMT/userdata_mini/",
                UserWarning,
                stacklevel=2
            )

        return v

    @model_validator(mode="after")
    def validate_qmt_config(self) -> "QmtConfig":
        """QMT配置整体验证

        验证路径有效性（如果启用且不使用RPC模式）。

        注意：必填字段验证已在 validate_required_qmt_fields 中完成。
        """
        if self.enabled and not self.use_rpc:
            # 检查路径是否存在（非RPC模式需要本地路径）
            mini_dir = Path(self.mini_path)
            if not mini_dir.exists():
                raise ValueError(
                    f"miniQMT 路径不存在: {self.mini_path}\n"
                    f"请确认路径正确或创建该目录。\n"
                    f"正确路径示例：\n"
                    f"  Windows: D:/国金证券QMT交易端/userdata_mini/\n"
                    f"  macOS/Linux: /opt/QMT/userdata_mini/\n"
                    f"或设置 use_rpc: true 使用RPC模式连接远程QMT"
                )

        return self


class GlobalConfig(BaseConfig):
    """全局配置

    系统级配置的顶层配置类，整合所有全局配置项。
    作为配置层次结构的根节点。

    提供跨模块依赖验证和功能使用前验证：

    - validate_cross_module_dependencies: 跨模块依赖验证
    - validate_for_use: 特定功能使用前验证

    Attributes:
        environment: 运行环境
        database: 数据库配置
        logging: 日志配置
        rpc: RPC 配置
        qmt: QMT 交易接口配置
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

        # 使用功能前验证配置
        global_config.validate_for_use("qmt")
        global_config.validate_for_use("database")
        ```
    """

    environment: Environment = Environment.DEVELOPMENT
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    rpc: RpcConfig = Field(default_factory=RpcConfig)
    qmt: QmtConfig = Field(default_factory=QmtConfig)
    risk: RiskGlobalConfig = Field(default_factory=RiskGlobalConfig)
    work_dir: Path = Field(default_factory=lambda: Path(".vntrader_china"))
    data_dir: Path = Field(default_factory=lambda: Path("data"))

    @model_validator(mode='after')
    def validate_cross_module_dependencies(self) -> 'GlobalConfig':
        """跨模块依赖验证

        验证：
        1. 启用RPC服务端时需要配置QMT
        2. 生产环境配置建议
        """
        # RPC依赖QMT
        # 如果启用了RPC服务端，则需要QMT配置
        rpc_server_enabled = getattr(self, 'rpc_server_enabled', False)
        if rpc_server_enabled and not self.qmt.enabled:
            raise ValueError(
                "启用RPC服务端时需要配置QMT。\n"
                f"请在global_{self.environment.value}.yaml中设置：\n"
                "  qmt:\n"
                "    enabled: true\n"
                "    account_id: \"your_account_id\"\n"
                "    mini_path: \"path/to/userdata_mini\""
            )

        # 生产环境建议
        if self.environment == Environment.PRODUCTION:
            warning_messages: List[str] = []

            if not self.database.enabled:
                warning_messages.append("生产环境建议启用数据库功能")

            if self.qmt.enabled and not self.qmt.password:
                warning_messages.append("生产环境建议设置QMT交易密码")

            if warning_messages:
                for msg in warning_messages:
                    warnings.warn(msg, UserWarning, stacklevel=2)

        return self

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

    def validate_for_use(self, feature: str) -> None:
        """验证特定功能所需的配置

        在使用特定功能前调用，确保配置正确。

        Args:
            feature: 功能名称（qmt, database, rpc_server等）

        Raises:
            ValueError: 配置不满足要求

        Example:
            ```python
            config = GlobalConfig()

            # 启动QMT前验证
            config.validate_for_use("qmt")

            # 启动数据库前验证
            config.validate_for_use("database")
            ```
        """
        if feature == "qmt":
            if not self.qmt.enabled:
                raise ValueError(
                    "QMT功能未启用，请在配置中设置 qmt.enabled=true\n"
                    f"配置文件: global_{self.environment.value}.yaml"
                )
            if not self.qmt.account_id or not self.qmt.mini_path:
                raise ValueError(
                    "QMT配置不完整，请检查account_id和mini_path字段"
                )

        elif feature == "database":
            if not self.database.enabled:
                raise ValueError("数据库功能未启用")
            if not self.database.mysql_database:
                raise ValueError("数据库名称未配置")

        elif feature == "rpc_server":
            if not self.qmt.enabled:
                raise ValueError(
                    "RPC服务端需要QMT配置\n"
                    "请在配置中设置 qmt.enabled=true 并完成QMT配置"
                )

        else:
            raise ValueError(
                f"未知的功能名称: {feature}\n"
                "支持的功能: qmt, database, rpc_server"
            )
