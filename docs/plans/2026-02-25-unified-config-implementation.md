# 统一配置管理系统实施方案

> 文档版本：v1.0
> 创建日期：2026-02-25
> 需求编号：REQ-012（统一配置管理）
> 优先级：P2
> 预计工时：2人天
> 实施周期：0.5天

---

## 1. 方案概述

### 1.1 项目背景

A股交易系统包含多个模块（数据服务、监控告警、资金管理、机器学习等），各模块配置分散管理，缺乏统一标准。本方案旨在构建统一的配置管理中心，实现配置集中管理、分层设计、动态加载和类型安全验证。

### 1.2 实施目标

| 目标类别 | 具体目标 | 成功标准 |
|---------|---------|---------|
| 集中管理 | 所有模块配置统一管理 | 配置集中存储和访问 |
| 分层配置 | 支持全局/模块/策略三层 | 层级清晰、继承完整 |
| 动态加载 | 支持配置热更新 | 无需重启即可生效 |
| 类型安全 | Pydantic验证 | 类型错误提前发现 |
| 环境隔离 | 支持开发/测试/生产 | 配置自动切换 |

### 1.3 交付物清单

| 序号 | 交付物 | 类型 | 说明 |
|------|--------|------|------|
| 1 | vnpy_china_config模块 | 代码 | 配置管理核心模块 |
| 2 | 单元测试 | 代码 | pytest测试套件 |
| 3 | 配置文件模板 | 文件 | YAML配置模板 |
| 4 | 使用示例 | 代码 | 示例代码 |

---

## 2. 技术架构设计

### 2.1 模块结构

```
vnpy_china_config/
├── __init__.py                     # 模块入口
├── base.py                        # 配置基类
├── global_config.py               # 全局配置
├── module_configs/                 # 模块配置
│   ├── __init__.py
│   ├── data_config.py            # 数据服务配置
│   ├── monitor_config.py         # 监控告警配置
│   ├── strategy_config.py        # 策略配置
│   ├── capital_config.py         # 资金管理配置
│   ├── analysis_config.py        # 行情分析配置
│   └── ml_config.py              # 机器学习配置
├── loader.py                     # 配置加载器
├── validator.py                  # 配置验证器
└── utils.py                     # 工具函数
```

### 2.2 配置层次结构

```
┌─────────────────────────────────────────────────────────┐
│  【全局配置层】 (GlobalConfig)                          │
│  • 数据库连接配置 (MySQL/Redis)                         │
│  • 日志配置 (级别、格式、输出)                          │
│  • RPC通信配置 (地址、端口、超时)                       │
│  • 风控全局参数 (最大持仓、单日止损)                     │
└───────────────────────┬─────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  【模块配置层】 (ModuleConfig)                         │
│  • DataConfig (数据服务)                               │
│  • MonitorConfig (监控告警)                           │
│  • StrategyConfig (策略参数)                           │
│  • CapitalConfig (资金管理)                            │
│  • AnalysisConfig (行情分析)                           │
│  • MLConfig (机器学习)                                 │
└───────────────────────┬─────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  【策略配置层】 (StrategyParams)                       │
│  • 具体策略运行参数                                     │
│  • JSON/YAML格式                                      │
│  • 参数分组和继承                                      │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 详细实施计划

### 3.1 第一阶段：配置基类和环境枚举（0.25人天）

#### 任务1.1：创建目录结构

```bash
# 创建模块根目录
mkdir -p vnpy_china_config

# 创建子目录
mkdir -p vnpy_china_config/module_configs

# 创建测试目录
mkdir -p tests/config
```

**验收标准**：
- [ ] 所有目录创建完成
- [ ] 每个目录包含 `__init__.py` 文件

#### 任务1.2：实现配置基类和枚举

**文件位置**: `vnpy_china_config/base.py`

```python
from typing import Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field, validator
from enum import Enum


class Environment(str, Enum):
    """运行环境"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class BaseConfig(BaseModel):
    """配置基类"""

    class Config:
        allow_population_by_field_name = True
        validate_assignment = True
        use_enum_values = True

    @classmethod
    def from_file(cls, config_path: Path) -> "BaseConfig":
        """从文件加载配置"""
        import json
        import yaml

        suffix = config_path.suffix.lower()
        if suffix == ".json":
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif suffix in [".yaml", ".yml"]:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported config format: {suffix}")
        return cls(**data)

    def to_file(self, config_path: Path):
        """保存配置到文件"""
        import json
        suffix = config_path.suffix.lower()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if suffix == ".json":
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.dict(), f, ensure_ascii=False, indent=2)
        elif suffix in [".yaml", ".yml"]:
            import yaml
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(self.dict(), f, allow_unicode=True, default_flow_style=False)
```

**验收标准**：
- [ ] Environment 枚举定义正确
- [ ] BaseConfig 基类实现完成
- [ ] from_file/to_file 方法正确实现
- [ ] 文档字符串完整

---

### 3.2 第二阶段：全局配置（0.25人天）

#### 任务2.1：实现全局配置类

**文件位置**: `vnpy_china_config/global_config.py`

```python
from pydantic import Field
from pathlib import Path
from .base import BaseConfig, Environment


class DatabaseConfig(BaseModel):
    """数据库配置"""
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


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_path: Path = Field(default_factory=lambda: Path("logs/vnpy_china.log"))
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5
    console_enabled: bool = True

    @validator("level")
    def validate_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}")
        return v.upper()


class RpcConfig(BaseModel):
    """RPC配置"""
    rep_address: str = "tcp://127.0.0.1:2014"
    pub_address: str = "tcp://127.0.0.1:4102"
    timeout: int = 5000


class RiskGlobalConfig(BaseModel):
    """风控全局参数"""
    max_position_ratio: float = 0.8
    max_single_position_ratio: float = 0.2
    max_daily_loss_ratio: float = 0.05
    max_consecutive_losses: int = 5


class GlobalConfig(BaseConfig):
    """全局配置"""
    environment: Environment = Environment.DEVELOPMENT
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    rpc: RpcConfig = Field(default_factory=RpcConfig)
    risk: RiskGlobalConfig = Field(default_factory=RiskGlobalConfig)
    work_dir: Path = Field(default_factory=lambda: Path(".vntrader_china"))
    data_dir: Path = Field(default_factory=lambda: Path("data"))
```

**验收标准**：
- [ ] DatabaseConfig 正确实现
- [ ] LoggingConfig 正确实现（含验证器）
- [ ] RpcConfig 正确实现
- [ ] RiskGlobalConfig 正确实现
- [ ] GlobalConfig 正确组合所有配置

---

### 3.3 第三阶段：模块配置（0.5人天）

#### 任务3.1：数据服务配置

**文件位置**: `vnpy_china_config/module_configs/data_config.py`

```python
from pydantic import Field
from pathlib import Path
from ...base import BaseConfig


class DataModuleConfig(BaseConfig):
    """数据服务模块配置"""
    # Tushare配置
    tushare_token: str = ""
    tushare_rate_limit: int = 200
    tushare_retry_times: int = 3
    tushare_retry_delay: int = 1

    # QMT配置
    qmt_path: Path = Field(default_factory=lambda: Path("D:/国金证券QMT交易端/userdata_mini"))
    qmt_account_id: str = ""

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

#### 任务3.2：监控告警配置

**文件位置**: `vnpy_china_config/module_configs/monitor_config.py`

```python
from pydantic import Field
from ...base import BaseConfig


class MonitorModuleConfig(BaseConfig):
    """监控告警模块配置"""
    # 系统监控
    enable_system_monitor: bool = True
    system_check_interval: int = 60
    cpu_threshold: float = 80.0
    memory_threshold: float = 80.0
    disk_threshold: float = 90.0

    # 交易监控
    enable_trade_monitor: bool = True
    trade_check_interval: int = 10

    # 告警配置
    enable_alert: bool = True
    alert_cooldown: int = 300

    # 邮件配置
    email_enabled: bool = False
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 465
    email_username: str = ""
    email_password: str = ""
    email_to: list[str] = Field(default_factory=list)

    # 微信配置
    wechat_enabled: bool = False
    wechat_webhook: str = ""
```

#### 任务3.3：策略配置

**文件位置**: `vnpy_china_config/module_configs/strategy_config.py`

```python
from pydantic import Field
from pathlib import Path
from ...base import BaseConfig


class StrategyModuleConfig(BaseConfig):
    """策略模块配置"""
    # 策略目录
    strategy_dir: Path = Field(default_factory=lambda: Path("strategies"))

    # 回测配置
    backtest_start_date: str = "2020-01-01"
    backtest_end_date: str = "2024-12-31"
    backtest_slippage: float = 0.001
    backtest_commission: float = 0.0003

    # 实盘配置
    trading_enabled: bool = False
    max_position_count: int = 10
    default_position_ratio: float = 0.1
```

#### 任务3.4：资金管理配置

**文件位置**: `vnpy_china_config/module_configs/capital_config.py`

```python
from pydantic import Field
from ...base import BaseConfig


class CapitalModuleConfig(BaseConfig):
    """资金管理模块配置"""
    # 仓位管理
    max_position_count: int = 10
    default_position_type: str = "equal_weight"
    risk_parity_target_vol: float = 0.1

    # 分批交易
    default_batch_type: str = "equal"
    default_batch_count: int = 5
    batch_delay: int = 60

    # 回撤控制
    max_drawdown: float = 0.15
    drawdown_reduction_levels: list[float] = Field(default_factory=lambda: [0.5, 0.75, 1.0])
    drawdown_reduction_ratios: list[float] = Field(default_factory=lambda: [1.0, 0.7, 0.5, 0.0])
```

#### 任务3.5：行情分析配置

**文件位置**: `vnpy_china_config/module_configs/analysis_config.py`

```python
from ...base import BaseConfig


class AnalysisModuleConfig(BaseConfig):
    """行情分析模块配置"""
    # Level-2数据
    level2_enabled: bool = False
    level2_data_source: str = "qmt"

    # 资金流向分类阈值（万元）
    super_large_threshold: float = 100
    large_threshold: float = 20
    medium_threshold: float = 5

    # 板块配置
    sector_count: int = 30
    sector_update_interval: int = 3600
```

#### 任务3.6：机器学习配置

**文件位置**: `vnpy_china_config/module_configs/ml_config.py`

```python
from pydantic import Field
from ...base import BaseConfig


class MLModuleConfig(BaseConfig):
    """机器学习模块配置"""
    # 特征配置
    feature_types: list[str] = Field(default_factory=lambda: ["technical", "fundamental", "market"])

    # 模型配置
    default_model_type: str = "lightgbm"
    train_test_split: float = 0.8

    # 训练配置
    retrain_interval: int = 7
    min_train_samples: int = 1000

    # IC/IR分析
    ic_threshold: float = 0.05
    ir_threshold: float = 0.5
```

**验收标准**：
- [ ] 所有6个模块配置类正确实现
- [ ] 字段类型和默认值正确
- [ ] 文档字符串完整

---

### 3.4 第四阶段：配置管理器（0.5人天）

#### 任务4.1：实现配置管理器

**文件位置**: `vnpy_china_config/loader.py`

```python
from typing import Type, TypeVar, Dict, Optional
import threading
from pathlib import Path
from .base import BaseConfig, Environment


T = TypeVar("T", bound=BaseConfig)


class ConfigManager:
    """配置管理器（单例模式）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._configs: Dict[str, BaseConfig] = {}
            self._config_path: Path = Path(".vntrader_china/config")
            self._environment: Environment = Environment.DEVELOPMENT
            self._initialized = True

    def set_environment(self, env: Environment):
        """设置运行环境"""
        self._environment = env

    def set_config_path(self, path: Path):
        """设置配置文件路径"""
        self._config_path = path

    def load_global_config(self) -> BaseConfig:
        """加载全局配置"""
        config_file = self._config_path / f"global_{self._environment.value}.yaml"
        from .global_config import GlobalConfig
        if config_file.exists():
            config = GlobalConfig.from_file(config_file)
        else:
            config = GlobalConfig()
            config.to_file(config_file)
        self._configs["global"] = config
        return config

    def load_module_config(self, module_name: str, config_class: Type[T], filename: Optional[str] = None) -> T:
        """加载模块配置"""
        if filename is None:
            filename = f"{module_name}_{self._environment.value}.yaml"
        config_file = self._config_path / filename
        if config_file.exists():
            config = config_class.from_file(config_file)
        else:
            config = config_class()
            config.to_file(config_file)
        self._configs[module_name] = config
        return config

    def get_config(self, name: str) -> Optional[BaseConfig]:
        """获取已加载的配置"""
        return self._configs.get(name)

    def reload_config(self, name: str) -> BaseConfig:
        """重新加载配置"""
        config = self._configs.get(name)
        if config is None:
            raise ValueError(f"Config not found: {name}")
        if name == "global":
            return self.load_global_config()
        else:
            return self.load_module_config(name, type(config))

    def save_config(self, name: str):
        """保存配置到文件"""
        config = self._configs.get(name)
        if config is None:
            raise ValueError(f"Config not found: {name}")
        filename = f"{name}_{self._environment.value}.yaml"
        config_file = self._config_path / filename
        config.to_file(config_file)

    def update_config(self, name: str, **kwargs):
        """更新配置"""
        config = self._configs.get(name)
        if config is None:
            raise ValueError(f"Config not found: {name}")
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                raise ValueError(f"Invalid config field: {key}")
```

#### 任务4.2：实现配置验证器

**文件位置**: `vnpy_china_config/validator.py`

```python
from typing import List, Dict, Any
from .base import BaseConfig


class ConfigValidator:
    """配置验证器"""

    @staticmethod
    def validate_required_fields(config: BaseConfig, required_fields: List[str]) -> Dict[str, Any]:
        """验证必需字段"""
        errors = []
        for field in required_fields:
            value = getattr(config, field, None)
            if value is None or value == "":
                errors.append(f"Required field '{field}' is missing")
        return {"valid": len(errors) == 0, "errors": errors}

    @staticmethod
    def validate_range(config: BaseConfig, field: str, min_val: float, max_val: float) -> Dict[str, Any]:
        """验证数值范围"""
        value = getattr(config, field, None)
        if value is None:
            return {"valid": True}
        if value < min_val or value > max_val:
            return {
                "valid": False,
                "errors": [f"Field '{field}' value {value} is out of range [{min_val}, {max_val}]"]
            }
        return {"valid": True}

    @staticmethod
    def validate_enum(config: BaseConfig, field: str, valid_values: List[str]) -> Dict[str, Any]:
        """验证枚举值"""
        value = getattr(config, field, None)
        if value is None:
            return {"valid": True}
        if value not in valid_values:
            return {
                "valid": False,
                "errors": [f"Field '{field}' value '{value}' is not in valid values: {valid_values}"]
            }
        return {"valid": True}
```

**验收标准**：
- [ ] ConfigManager 单例模式正确实现
- [ ] 配置加载/保存/更新方法正确实现
- [ ] ConfigValidator 验证方法正确实现
- [ ] 线程安全保证

---

### 3.5 第五阶段：工具函数和模块导出（0.25人天）

#### 任务5.1：工具函数

**文件位置**: `vnpy_china_config/utils.py`

```python
import json
import numpy as np
from pathlib import Path
from datetime import datetime


class NumpyEncoder(json.JSONEncoder):
    """NumPy类型JSON编码器"""

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Path):
            return str(obj)
        return super().default(obj)


def merge_configs(base_config: dict, override_config: dict) -> dict:
    """合并配置（override优先）"""
    result = base_config.copy()
    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def resolve_env_variables(config: dict) -> dict:
    """解析环境变量引用 ${VAR_NAME}"""
    import os
    result = {}
    for key, value in config.items():
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            result[key] = os.environ.get(env_var, "")
        elif isinstance(value, dict):
            result[key] = resolve_env_variables(value)
        else:
            result[key] = value
    return result
```

#### 任务5.2：模块导出

**文件位置**: `vnpy_china_config/__init__.py`

```python
from .base import BaseConfig, Environment
from .global_config import GlobalConfig, DatabaseConfig, LoggingConfig, RpcConfig, RiskGlobalConfig
from .loader import ConfigManager
from .validator import ConfigValidator
from .module_configs.data_config import DataModuleConfig
from .module_configs.monitor_config import MonitorModuleConfig
from .module_configs.strategy_config import StrategyModuleConfig
from .module_configs.capital_config import CapitalModuleConfig
from .module_configs.analysis_config import AnalysisModuleConfig
from .module_configs.ml_config import MLModuleConfig

__all__ = [
    "BaseConfig",
    "Environment",
    "GlobalConfig",
    "DatabaseConfig",
    "LoggingConfig",
    "RpcConfig",
    "RiskGlobalConfig",
    "ConfigManager",
    "ConfigValidator",
    "DataModuleConfig",
    "MonitorModuleConfig",
    "StrategyModuleConfig",
    "CapitalModuleConfig",
    "AnalysisModuleConfig",
    "MLModuleConfig",
]
```

**验收标准**：
- [ ] 工具函数正确实现
- [ ] 模块导出完整
- [ ] 文档字符串完整

---

## 4. 测试计划

### 4.1 单元测试

| 模块 | 测试文件 | 测试用例数 |
|------|---------|-----------|
| base | test_base.py | 8 |
| global_config | test_global_config.py | 10 |
| module_configs | test_module_configs.py | 15 |
| loader | test_loader.py | 12 |
| validator | test_validator.py | 8 |
| utils | test_utils.py | 7 |
| **合计** | | **60** |

### 4.2 测试用例示例

```python
# test_base.py
def test_base_config_from_json():
    """测试从JSON文件加载配置"""
    config = GlobalConfig.from_file(Path("test_config.json"))
    assert config.environment == Environment.DEVELOPMENT

def test_base_config_to_yaml():
    """测试保存为YAML文件"""
    config = GlobalConfig()
    config.to_file(Path("output.yaml"))
    assert Path("output.yaml").exists()
```

---

## 5. 文档计划

### 5.1 代码文档

- 每个类添加完整的docstring
- 复杂方法添加行内注释
- 使用类型注解

### 5.2 使用文档

创建配置使用示例：

```python
# 使用示例
from vnpy_china_config import ConfigManager, GlobalConfig, Environment
from pathlib import Path

# 初始化
config_manager = ConfigManager()
config_manager.set_environment(Environment.PRODUCTION)
config_manager.set_config_path(Path(".vntrader_china/config"))

# 加载配置
global_config = config_manager.load_global_config()
print(f"MySQL Host: {global_config.database.mysql_host}")
```

---

## 6. 风险管理

### 6.1 技术风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| Pydantic版本兼容性 | 低 | 中 | 使用稳定版本v2.x |
| 配置文件格式解析错误 | 中 | 高 | 添加异常处理和默认值回退 |
| 线程安全问题 | 低 | 高 | 使用锁保护共享资源 |

### 6.2 业务风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| 配置字段遗漏 | 中 | 中 | 完善测试覆盖 |
| 默认值不合理 | 低 | 低 | 提供配置模板 |

---

## 7. 时间安排

| 日期 | 任务 | 工时 |
|------|------|------|
| Day 1上午 | 配置基类和全局配置 | 0.5人天 |
| Day 1下午 | 模块配置类 | 0.5人天 |
| Day 2上午 | 配置管理器和验证器 | 0.5人天 |
| Day 2下午 | 测试和文档 | 0.5人天 |

### 里程碑

| 里程碑 | 时间 | 交付内容 |
|--------|------|---------|
| M1 | Day 1结束 | 基类+全局配置+模块配置 |
| M2 | Day 2结束 | 完整模块+测试+文档 |

---

## 8. 验收标准

### 8.1 功能验收

- [ ] 配置基类正确实现，支持JSON/YAML格式
- [ ] 全局配置正确实现（数据库、日志、RPC、风控）
- [ ] 6个模块配置正确实现
- [ ] ConfigManager 单例模式正确实现
- [ ] 配置加载/保存/更新/热更新功能正常
- [ ] 配置验证器正确实现

### 8.2 质量验收

- [ ] 单元测试覆盖率≥80%
- [ ] 所有测试用例通过
- [ ] 代码通过MyPy类型检查
- [ ] 文档完整

### 8.3 性能验收

- [ ] 配置加载<100ms
- [ ] 内存占用<10MB

---

## 9. 后续计划

### 9.1 功能扩展

- [ ] 配置热更新Web界面
- [ ] 配置版本管理
- [ ] 配置对比工具

### 9.2 优化方向

- [ ] 配置缓存优化
- [ ] 分布式配置支持

---

**文档版本**：v1.0
**创建日期**：2026-02-25
**维护者**：AI Assistant
