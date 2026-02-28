# vnpy_china_config - A股配置管理模块

> 更新时间：2026-02-28
> 版本：1.1.0

## 模块概述

vnpy_china_config是VeighNa量化交易框架的A股配置管理模块，基于 Pydantic v2 提供类型安全的配置验证和管理。

## 核心功能

### 配置验证系统

- **Pydantic v2 集成**：使用最新的 Pydantic v2 进行配置验证
- **类型安全**：完整的类型注解和运行时验证
- **字段验证器**：使用 `field_validator` 和 `model_validator` 进行复杂验证
- **环境变量支持**：自动从环境变量读取敏感配置

### 配置层级

```
vnpy_china_config/
├── __init__.py                 # 模块初始化，导出主要类
├── base.py                     # BaseConfig 基类
├── global_config.py            # GlobalConfig 全局配置
└── module_configs/             # 子模块配置
    ├── __init__.py
    ├── data_config.py          # DataModuleConfig 数据模块配置
    └── (其他模块配置...)
```

## 快速开始

### 基本使用

```python
from vnpy_china_config import ConfigManager, GlobalConfig

# 加载配置
config_manager = ConfigManager()
global_config = config_manager.load_global_config()

# 访问配置
print(f"MySQL Host: {global_config.mysql.host}")
print(f"QMT Account: {global_config.qmt.account_id}")
```

### 环境特定配置

```python
# 加载开发环境配置
config_manager = ConfigManager(environment="development")
global_config = config_manager.load_global_config()

# 加载生产环境配置
config_manager = ConfigManager(environment="production")
global_config = config_manager.load_global_config()
```

### 配置文件位置

配置文件位于 `.vntrader_china/config/` 目录：

```
.vntrader_china/config/
├── global_development.yaml    # 开发环境全局配置
├── global_production.yaml     # 生产环境全局配置
├── data_development.yaml      # 开发环境数据模块配置
└── data_production.yaml       # 生产环境数据模块配置
```

## 配置结构

### GlobalConfig

全局配置包含以下子配置：

```python
class GlobalConfig(BaseConfig):
    mysql: DatabaseConfig      # MySQL 数据库配置
    qmt: QmtConfig             # QMT 交易终端配置
    rpc: RpcConfig             # RPC 通信配置
    logging: LoggingConfig     # 日志配置
```

### DatabaseConfig

数据库连接配置：

```python
class DatabaseConfig(BaseConfig):
    host: str = "localhost"
    port: int = 3306
    user: str = "vnpy"
    password: str = ""
    database: str = "vnpy_china"
    charset: str = "utf8mb4"
    pool_size: int = 5         # 连接池大小
    max_overflow: int = 10     # 最大溢出连接数
```

### QmtConfig

QMT 交易终端配置：

```python
class QmtConfig(BaseConfig):
    enabled: bool = False      # 是否启用 QMT
    use_rpc: bool = False      # 是否使用 RPC 模式连接远程服务器
    account_id: str = ""       # QMT 账号 ID
    mini_path: str = ""        # MiniQMT 路径
    session_id: int = 0        # 会话 ID
    password: str = ""         # QMT 密码
```

**RPC 模式说明**：
- 当 `use_rpc=True` 时，连接到远程 QMT RPC 服务器（无需本地 QMT 安装）
- 当 `use_rpc=False` 时，需要本地安装 QMT 并配置 `mini_path`

### RpcConfig

RPC 通信配置：

```python
class RpcConfig(BaseConfig):
    rep_address: str = ""      # REP 服务器地址
    pub_address: str = ""      # PUB 服务器地址
    request_timeout: int = 5000  # 请求超时（毫秒）
```

### LoggingConfig

日志配置：

```python
class LoggingConfig(BaseConfig):
    level: str = "INFO"
    log_file: str = ""
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### DataModuleConfig

数据模块配置（仅包含数据服务特有配置）：

```python
class DataModuleConfig(BaseConfig):
    # Tushare配置
    tushare_token: str = ""
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
```

**注意**：QMT 配置已移至 `GlobalConfig.QmtConfig` 统一管理。

## 配置验证

### 字段验证器

```python
@field_validator("port")
@classmethod
def validate_port(cls, v: int) -> int:
    """验证端口号"""
    if not 0 < v <= 65535:
        raise ValueError(f"端口号必须在 1-65535 之间，当前值: {v}")
    return v
```

### 模型验证器

```python
@model_validator(mode="after")
def validate_qmt_config(self) -> "QmtConfig":
    """验证 QMT 配置"""
    if self.enabled and not self.use_rpc:
        if not self.mini_path:
            raise ValueError("本地模式需要配置 mini_path")
        if not Path(self.mini_path).exists():
            raise ValueError(f"MiniQMT 路径不存在: {self.mini_path}")
    return self
```

## 环境变量

支持通过环境变量覆盖配置：

```bash
# MySQL 配置
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=vnpy
export MYSQL_PASSWORD=your_password

# QMT 配置
export QMT_ACCOUNT_ID=your_account_id
export QMT_MINI_PATH=/path/to/qmt/userdata_mini

# Tushare 配置
export TUSHARE_TOKEN=your_token
```

## 依赖项

- pydantic >= 2.0
- pyyaml
- pathlib

## 相关模块

- [vnpy_china_data](../vnpy_china_data/) - A股数据服务
- [vnpy_china_interface](../vnpy_china_interface/) - 接口定义

## 变更记录

### 2026-02-28 - v1.1.0
- 🔧 **配置重构**：
  - 将 QMT 配置从 DataModuleConfig 迁移到 GlobalConfig.QmtConfig
  - 添加 `use_rpc` 字段支持远程 QMT RPC 服务器连接
  - 更新 QmtConfig 验证器，在 RPC 模式下跳过路径检查

- ✅ **测试完善**：
  - 修复测试隔离问题（清理模块缓存）
  - 修复跨模块依赖测试（添加密码和路径 mock）

### 2026-02-26
- 🎨 **UI 定制**：A 股 UI 定制和 Tick 数据增强

### 2026-02-24
- ✨ **初始版本**：实现 vnpy_china_config 统一配置管理模块


