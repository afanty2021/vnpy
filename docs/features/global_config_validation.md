# GlobalConfig 配置验证功能使用指南

## 概述

`GlobalConfig` 现在提供了两种验证机制：

1. **自动跨模块依赖验证**（`validate_cross_module_dependencies`）
2. **功能使用前验证**（`validate_for_use`）

## 新增功能

### 1. DatabaseConfig 新增 `enabled` 字段

```python
class DatabaseConfig(BaseModel):
    # ... 其他字段 ...
    enabled: bool = True  # 默认启用
```

### 2. GlobalConfig 新增 `validate_cross_module_dependencies` 验证器

自动验证跨模块依赖关系：

- **RPC 服务端依赖 QMT**：如果启用 RPC 服务端，必须配置 QMT
- **生产环境建议**：
  - 建议启用数据库功能
  - 如果启用 QMT，建议设置交易密码

### 3. GlobalConfig 新增 `validate_for_use` 方法

在使用特定功能前手动验证配置：

```python
def validate_for_use(self, feature: str) -> None:
    """验证特定功能所需的配置

    Args:
        feature: 功能名称（qmt, database, rpc_server等）

    Raises:
        ValueError: 配置不满足要求
    """
```

支持的功能：
- `"qmt"` - QMT 交易接口
- `"database"` - 数据库
- `"rpc_server"` - RPC 服务端

## 使用示例

### 示例 1: 启动 QMT 前验证

```python
from vnpy_china_config import ConfigManager

manager = ConfigManager()
config = manager.load_global_config()

# 启动 QMT 前验证配置
try:
    config.validate_for_use("qmt")
    print("QMT 配置验证通过，可以启动")
except ValueError as e:
    print(f"QMT 配置错误: {e}")
    # 处理配置错误
```

### 示例 2: 使用数据库前验证

```python
from vnpy_china_config import ConfigManager

manager = ConfigManager()
config = manager.load_global_config()

# 使用数据库前验证
try:
    config.validate_for_use("database")
    dsn = config.get_mysql_dsn()
    print(f"数据库连接字符串: {dsn}")
except ValueError as e:
    print(f"数据库配置错误: {e}")
```

### 示例 3: 启动 RPC 服务端前验证

```python
from vnpy_china_config import ConfigManager

manager = ConfigManager()
config = manager.load_global_config()

# 启动 RPC 服务端前验证
try:
    config.validate_for_use("rpc_server")
    print("RPC 服务端配置验证通过")
except ValueError as e:
    print(f"RPC 服务端配置错误: {e}")
```

### 示例 4: 生产环境警告

```python
from vnpy_china_config.global_config import GlobalConfig, DatabaseConfig, QmtConfig
from vnpy_china_config.base import Environment

import warnings

# 捕获所有警告
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")

    config = GlobalConfig(
        environment=Environment.PRODUCTION,
        database=DatabaseConfig(enabled=False),  # 生产环境未启用数据库
        qmt=QmtConfig(enabled=True, password="")  # 未设置密码
    )

    # 查看警告
    for warning in w:
        print(f"警告: {warning.message}")
        # 输出:
        # 警告: 生产环境建议启用数据库功能
        # 警告: 生产环境建议设置QMT交易密码
```

## 验证规则

### QMT 验证规则

调用 `validate_for_use("qmt")` 时：

1. 检查 `qmt.enabled` 是否为 `True`
2. 检查 `qmt.account_id` 是否非空
3. 检查 `qmt.mini_path` 是否非空

错误示例：
```python
# QMT 未启用
config.validate_for_use("qmt")
# ValueError: QMT功能未启用，请在配置中设置 qmt.enabled=true
#           配置文件: global_development.yaml

# QMT 配置不完整
config.qmt.enabled = True
config.validate_for_use("qmt")
# ValueError: QMT配置不完整，请检查account_id和mini_path字段
```

### 数据库验证规则

调用 `validate_for_use("database")` 时：

1. 检查 `database.enabled` 是否为 `True`
2. 检查 `database.mysql_database` 是否非空

错误示例：
```python
# 数据库未启用
config.validate_for_use("database")
# ValueError: 数据库功能未启用

# 数据库名称为空
config.database.enabled = True
config.database.mysql_database = ""
config.validate_for_use("database")
# ValueError: 数据库名称未配置
```

### RPC 服务端验证规则

调用 `validate_for_use("rpc_server")` 时：

1. 检查 `qmt.enabled` 是否为 `True`（RPC 服务端依赖 QMT）

错误示例：
```python
# QMT 未启用
config.validate_for_use("rpc_server")
# ValueError: RPC服务端需要QMT配置
#           请在配置中设置 qmt.enabled=true 并完成QMT配置
```

## 错误提示

所有错误提示都包含：

1. 问题描述
2. 修复建议
3. 相关配置文件名（基于当前环境）

示例：
```
QMT功能未启用，请在配置中设置 qmt.enabled=true
配置文件: global_production.yaml
```

## 配置文件示例

### global_development.yaml

```yaml
environment: development

database:
  enabled: true  # 启用数据库
  mysql_host: localhost
  mysql_port: 3306
  mysql_user: vnpy
  mysql_password: ""
  mysql_database: vnpy_china
  # ... 其他配置

qmt:
  enabled: false  # 开发环境可以禁用
  account_id: ""
  mini_path: ""
```

### global_production.yaml

```yaml
environment: production

database:
  enabled: true  # 生产环境建议启用
  mysql_host: prod-db.example.com
  mysql_port: 3306
  mysql_user: vnpy
  mysql_password: "strong_password_here"  # 生产环境使用强密码
  mysql_database: vnpy_china
  # ... 其他配置

qmt:
  enabled: true  # 启用 QMT
  account_id: "your_account_id"
  mini_path: "D:/国金证券QMT交易端/userdata_mini/"
  password: "your_password"  # 生产环境建议设置密码
```

## 最佳实践

1. **启动功能前验证**：在使用任何功能前，先调用 `validate_for_use()`
2. **处理验证错误**：捕获 `ValueError` 并提供用户友好的错误提示
3. **生产环境配置**：确保生产环境启用数据库并设置强密码
4. **配置文件管理**：为不同环境维护独立的配置文件

## 相关文件

- 实现文件：`vnpy_china_config/global_config.py`
- 测试文件：`tests/test_global_config_validation_simple.py`
- 演示文件：`tests/demo_global_config_validation.py`
