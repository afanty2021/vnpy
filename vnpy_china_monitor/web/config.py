"""
Web监控配置管理

支持从YAML文件和环境变量加载配置
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


class LogLevel(str, Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class RpcConfig:
    """RPC配置"""
    rep_address: str = "tcp://127.0.0.1:2014"
    pub_address: str = "tcp://127.0.0.1:4102"
    auto_reconnect: bool = True
    reconnect_interval: int = 5
    request_timeout: int = 30
    max_retries: int = 3


@dataclass
class WebConfig:
    """Web服务配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False
    log_level: LogLevel = LogLevel.INFO


@dataclass
class AuthConfig:
    """认证配置"""
    enabled: bool = True
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7


@dataclass
class CorsConfig:
    """CORS配置"""
    enabled: bool = True
    allow_origins: list[str] = field(default_factory=lambda: ["*"])
    allow_credentials: bool = True
    allow_methods: list[str] = field(default_factory=lambda: ["*"])
    allow_headers: list[str] = field(default_factory=lambda: ["*"])


@dataclass
class WebSocketConfig:
    """WebSocket配置"""
    heartbeat_interval: int = 30
    max_connections: int = 100
    message_queue_size: int = 1000


@dataclass
class SecurityConfig:
    """安全配置"""
    enable_https: bool = False
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds


@dataclass
class WebMonitorConfig:
    """Web监控总配置"""

    rpc: RpcConfig = field(default_factory=RpcConfig)
    web: WebConfig = field(default_factory=WebConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    cors: CorsConfig = field(default_factory=CorsConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)

    @classmethod
    def from_env(cls) -> "WebMonitorConfig":
        """从环境变量加载配置"""
        config = cls()

        # RPC配置
        if rpc_rep := os.getenv("WEB_RPC_REP_ADDRESS"):
            config.rpc.rep_address = rpc_rep
        if rpc_pub := os.getenv("WEB_RPC_PUB_ADDRESS"):
            config.rpc.pub_address = rpc_pub

        # Web配置
        if web_host := os.getenv("WEB_HOST"):
            config.web.host = web_host
        if web_port := os.getenv("WEB_PORT"):
            config.web.port = int(web_port)

        # 认证配置
        if secret_key := os.getenv("WEB_AUTH_SECRET_KEY"):
            config.auth.secret_key = secret_key
        if token_expire := os.getenv("WEB_ACCESS_TOKEN_EXPIRE"):
            config.auth.access_token_expire_minutes = int(token_expire)

        # CORS配置
        if allow_origins := os.getenv("WEB_CORS_ORIGINS"):
            config.cors.allow_origins = allow_origins.split(",")

        return config

    @classmethod
    def from_file(cls, config_file: Path) -> "WebMonitorConfig":
        """从YAML文件加载配置"""
        try:
            import yaml
        except ImportError:
            raise ImportError("pyyaml is required to load config from file")

        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict) -> "WebMonitorConfig":
        """从字典创建配置"""
        config = cls()

        if rpc_data := data.get("rpc"):
            config.rpc = RpcConfig(**rpc_data)

        if web_data := data.get("web"):
            config.web = WebConfig(**web_data)

        if auth_data := data.get("auth"):
            config.auth = AuthConfig(**auth_data)

        if cors_data := data.get("cors"):
            config.cors = CorsConfig(**cors_data)

        if ws_data := data.get("websocket"):
            config.websocket = WebSocketConfig(**ws_data)

        if security_data := data.get("security"):
            config.security = SecurityConfig(**security_data)

        return config

    def validate(self) -> None:
        """验证配置"""
        if self.auth.enabled and not self.auth.secret_key:
            raise ValueError("auth.secret_key is required when auth is enabled")

        if self.security.enable_https:
            if not self.security.ssl_certfile or not self.security.ssl_keyfile:
                raise ValueError("ssl_certfile and ssl_keyfile are required when HTTPS is enabled")

        if self.rpc.request_timeout <= 0:
            raise ValueError("rpc.request_timeout must be positive")

        if self.web.port < 1 or self.web.port > 65535:
            raise ValueError("web.port must be between 1 and 65535")


# 全局配置实例
_config: Optional[WebMonitorConfig] = None


def get_config() -> WebMonitorConfig:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = WebMonitorConfig.from_env()
    return _config


def set_config(config: WebMonitorConfig) -> None:
    """设置全局配置"""
    global _config
    _config = config
