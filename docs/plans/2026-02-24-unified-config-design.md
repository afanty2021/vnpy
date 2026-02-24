# A股交易系统统一配置管理设计文档

> 文档版本：v1.0
> 创建日期：2026-02-24
> 文档类型：架构设计
> 预计工时：2人天

---

## 1. 设计目标

构建A股交易系统的统一配置管理中心，实现：

1. **集中式配置**：所有模块配置统一管理
2. **分层配置**：支持全局、模块、策略三层配置
3. **动态加载**：支持配置热更新
4. **类型安全**：使用Pydantic进行配置验证
5. **环境隔离**：支持开发、测试、生产环境

---

## 2. 架构设计

### 2.1 配置层次结构

```
┌─────────────────────────────────────────────────────────────────┐
│                    配置管理层次结构                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  【全局配置层】 (GlobalConfig)                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • 数据库连接配置 (MySQL/Redis)                          │   │
│  │ • 日志配置 (级别、格式、输出)                           │   │
│  │ • RPC通信配置 (地址、端口、超时)                        │   │
│  │ • 风控全局参数 (最大持仓、单日止损)                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  【模块配置层】 (ModuleConfig)                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ DataConfig   │  │ MonitorConfig│  │ StrategyConfig│        │
│  │ (数据服务)   │  │ (监控告警)   │  │ (策略参数)   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ CapitalConfig│  │ AnalysisConfig│ │ MLConfig     │        │
│  │ (资金管理)   │  │ (行情分析)   │  │ (机器学习)   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│                              ↓                                  │
│  【策略配置层】 (StrategyParams)                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • 具体策略的运行参数                                      │   │
│  │ • 支持JSON/YAML格式                                       │   │
│  │ • 支持参数分组和继承                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块结构

```
vnpy_china_config/
├── __init__.py
├── base.py                    # 配置基类
├── global_config.py           # 全局配置
├── module_configs/
│   ├── __init__.py
│   ├── data_config.py         # 数据服务配置
│   ├── monitor_config.py      # 监控告警配置
│   ├── strategy_config.py     # 策略配置
│   ├── capital_config.py      # 资金管理配置
│   ├── analysis_config.py     # 行情分析配置
│   └── ml_config.py           # 机器学习配置
├── loader.py                  # 配置加载器
├── validator.py               # 配置验证器
└── utils.py                   # 配置工具函数
```

---

## 3. 核心类设计

### 3.1 配置基类

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
        # 允许字段别名
        allow_population_by_field_name = True
        # 验证赋值
        validate_assignment = True
        # 使用枚举值而不是名称
        use_enum_values = True
        # JSON编码额外配置
        json_encoders = {
            Path: str,
        }

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
        from .utils import NumpyEncoder

        suffix = config_path.suffix.lower()

        config_path.parent.mkdir(parents=True, exist_ok=True)

        if suffix == ".json":
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(
                    self.dict(),
                    f,
                    ensure_ascii=False,
                    indent=2,
                    cls=NumpyEncoder
                )
        elif suffix in [".yaml", ".yml"]:
            import yaml
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self.dict(),
                    f,
                    allow_unicode=True,
                    default_flow_style=False
                )
```

### 3.2 全局配置

```python
class DatabaseConfig(BaseModel):
    """数据库配置"""
    # MySQL配置
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "vnpy"
    mysql_password: str = ""
    mysql_database: str = "vnpy_china"

    # Redis配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # 连接池配置
    pool_size: int = 5
    max_overflow: int = 10


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 文件日志
    file_enabled: bool = True
    file_path: Path = Field(default_factory=lambda: Path("logs/vnpy_china.log"))
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

    # 控制台日志
    console_enabled: bool = True

    # 日志级别映射
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
    timeout: int = 5000  # 毫秒


class RiskGlobalConfig(BaseModel):
    """风控全局参数"""
    max_position_ratio: float = 0.8  # 最大总仓位
    max_single_position_ratio: float = 0.2  # 单只股票最大仓位
    max_daily_loss_ratio: float = 0.05  # 单日最大亏损
    max_consecutive_losses: int = 5  # 最大连续亏损次数


class GlobalConfig(BaseConfig):
    """全局配置"""

    # 环境配置
    environment: Environment = Environment.DEVELOPMENT

    # 数据库配置
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)

    # 日志配置
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # RPC配置
    rpc: RpcConfig = Field(default_factory=RpcConfig)

    # 风控全局参数
    risk: RiskGlobalConfig = Field(default_factory=RiskGlobalConfig)

    # 工作目录
    work_dir: Path = Field(default_factory=lambda: Path(".vntrader_china"))

    # 数据目录
    data_dir: Path = Field(default_factory=lambda: Path("data"))
```

### 3.3 模块配置

```python
class DataModuleConfig(BaseConfig):
    """数据服务模块配置"""

    # Tushare配置
    tushare_token: str = ""
    tushare_rate_limit: int = 200  # 每分钟调用次数
    tushare_retry_times: int = 3
    tushare_retry_delay: int = 1  # 秒

    # QMT配置
    qmt_path: Path = Field(default_factory=lambda: Path("D:/国金证券QMT交易端/userdata_mini"))
    qmt_account_id: str = ""

    # 缓存配置
    cache_bar_ttl: int = 300  # K线缓存5分钟
    cache_tick_ttl: int = 30  # Tick缓存30秒
    cache_info_ttl: int = 86400  # 信息缓存24小时

    # 增量更新配置
    auto_update_enabled: bool = True
    update_interval: int = 3600  # 秒
    update_start_time: str = "08:00"
    update_end_time: str = "20:00"


class MonitorModuleConfig(BaseConfig):
    """监控告警模块配置"""

    # 系统监控
    enable_system_monitor: bool = True
    system_check_interval: int = 60  # 秒
    cpu_threshold: float = 80.0  # 百分比
    memory_threshold: float = 80.0
    disk_threshold: float = 90.0

    # 交易监控
    enable_trade_monitor: bool = True
    trade_check_interval: int = 10

    # 告警配置
    enable_alert: bool = True
    alert_cooldown: int = 300  # 告警冷却时间

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

    # 短信配置
    sms_enabled: bool = False
    sms_api_key: str = ""


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


class CapitalModuleConfig(BaseConfig):
    """资金管理模块配置"""

    # 仓位管理
    max_position_count: int = 10
    default_position_type: str = "equal_weight"  # equal_weight/value_weight/risk_parity
    risk_parity_target_vol: float = 0.1

    # 分批交易
    default_batch_type: str = "equal"  # equal/twap/vwap
    default_batch_count: int = 5
    batch_delay: int = 60  # 秒

    # 回撤控制
    max_drawdown: float = 0.15
    drawdown_reduction_levels: list[float] = Field(default_factory=lambda: [0.5, 0.75, 1.0])
    drawdown_reduction_ratios: list[float] = Field(default_factory=lambda: [1.0, 0.7, 0.5, 0.0])


class AnalysisModuleConfig(BaseConfig):
    """行情分析模块配置"""

    # Level-2数据
    level2_enabled: bool = False
    level2_data_source: str = "qmt"  # qmt/custom

    # 资金流向分类阈值（万元）
    super_large_threshold: float = 100
    large_threshold: float = 20
    medium_threshold: float = 5

    # 板块配置
    sector_count: int = 30
    sector_update_interval: int = 3600


class MLModuleConfig(BaseConfig):
    """机器学习模块配置"""

    # 特征配置
    feature_types: list[str] = Field(default_factory=lambda: ["technical", "fundamental", "market"])

    # 模型配置
    default_model_type: str = "lightgbm"  # lightgbm/xgboost/random_forest
    train_test_split: float = 0.8

    # 训练配置
    retrain_interval: int = 7  # 天
    min_train_samples: int = 1000

    # IC/IR分析
    ic_threshold: float = 0.05
    ir_threshold: float = 0.5
```

### 3.4 配置管理器

```python
from typing import Type, TypeVar, Dict
import threading


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

    def load_global_config(self) -> GlobalConfig:
        """加载全局配置"""
        config_file = self._config_path / f"global_{self._environment.value}.yaml"

        if config_file.exists():
            config = GlobalConfig.from_file(config_file)
        else:
            # 使用默认配置
            config = GlobalConfig()
            # 保存默认配置
            config.to_file(config_file)

        self._configs["global"] = config
        return config

    def load_module_config(
        self,
        module_name: str,
        config_class: Type[T],
        filename: Optional[str] = None
    ) -> T:
        """加载模块配置"""
        if filename is None:
            filename = f"{module_name}_{self._environment.value}.yaml"

        config_file = self._config_path / filename

        if config_file.exists():
            config = config_class.from_file(config_file)
        else:
            # 使用默认配置
            config = config_class()
            # 保存默认配置
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

        # 重新加载
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

        # 更新字段
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                raise ValueError(f"Invalid config field: {key}")
```

---

## 4. 配置文件示例

### 4.1 全局配置文件 (global_development.yaml)

```yaml
environment: development

database:
  mysql_host: localhost
  mysql_port: 3306
  mysql_user: vnpy
  mysql_password: ""
  mysql_database: vnpy_china_dev
  redis_host: localhost
  redis_port: 6379
  redis_db: 0

logging:
  level: DEBUG
  file_enabled: true
  file_path: logs/vnpy_china_dev.log
  console_enabled: true

rpc:
  rep_address: tcp://127.0.0.1:2014
  pub_address: tcp://127.0.0.1:4102

risk:
  max_position_ratio: 0.8
  max_single_position_ratio: 0.2
  max_daily_loss_ratio: 0.05
```

### 4.2 生产环境配置 (global_production.yaml)

```yaml
environment: production

database:
  mysql_host: your-production-host
  mysql_port: 3306
  mysql_user: vnpy_prod
  mysql_password: ${MYSQL_PASSWORD}  # 从环境变量读取
  mysql_database: vnpy_china_prod

logging:
  level: INFO
  file_enabled: true
  file_path: /var/log/vnpy_china/app.log
  console_enabled: false

risk:
  max_position_ratio: 0.7  # 生产环境更保守
  max_single_position_ratio: 0.15
  max_daily_loss_ratio: 0.03
```

### 4.3 数据服务模块配置 (data_module_production.yaml)

```yaml
tushare_token: ${TUSHARE_TOKEN}
tushare_rate_limit: 200
tushare_retry_times: 3

qmt_path: D:/国金证券QMT交易端/userdata_mini
qmt_account_id: ""

cache_bar_ttl: 300
cache_tick_ttl: 30
cache_info_ttl: 86400

auto_update_enabled: true
update_interval: 3600
```

---

## 5. 配置使用示例

### 5.1 初始化配置

```python
from vnpy_china_config import ConfigManager, GlobalConfig, DataModuleConfig

# 初始化配置管理器
config_manager = ConfigManager()
config_manager.set_environment(Environment.PRODUCTION)
config_manager.set_config_path(Path(".vntrader_china/config"))

# 加载全局配置
global_config = config_manager.load_global_config()

# 加载模块配置
data_config = config_manager.load_module_config(
    "data",
    DataModuleConfig
)

# 访问配置
print(f"MySQL Host: {global_config.database.mysql_host}")
print(f"Tushare Token: {data_config.tushare_token}")
```

### 5.2 在模块中使用配置

```python
# vnpy_china_data/service.py

from vnpy_china_config import ConfigManager, DataModuleConfig

class ChinaDataService:
    def __init__(self):
        # 获取配置
        config_manager = ConfigManager()
        self.config: DataModuleConfig = config_manager.get_config("data")

        # 使用配置初始化组件
        self.cache = DataQueryCache(
            host=self.config.database.redis_host,
            port=self.config.database.redis_port
        )
        self.tushare_adapter = TushareDataAdapter(
            token=self.config.tushare_token,
            rate_limit=self.config.tushare_rate_limit
        )
```

### 5.3 动态更新配置

```python
# 更新配置
config_manager = ConfigManager()
data_config = config_manager.get_config("data")

# 修改配置
data_config.cache_bar_ttl = 600  # 改为10分钟

# 保存到文件
config_manager.save_config("data")

# 热更新（如果支持）
config_manager.reload_config("data")
```

---

## 6. 实施计划

| 阶段 | 任务 | 预估工时 |
|------|------|---------|
| 1 | 创建配置基类和全局配置 | 0.5人天 |
| 2 | 实现各模块配置类 | 0.5人天 |
| 3 | 实现配置管理器 | 0.5人天 |
| 4 | 编写配置文件模板 | 0.5人天 |
| 合计 | | **2人天** |

---

## 7. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-02-24 | 初始版本 |
