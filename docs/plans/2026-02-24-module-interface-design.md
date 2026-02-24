# A股交易系统模块间接口设计文档

> 文档版本：v1.0
> 创建日期：2026-02-24
> 文档类型：架构设计
> 预计工时：3人天

---

## 1. 设计目标

定义A股交易系统各模块间的标准化接口，实现：

1. **清晰的数据流**：明确各模块间的数据流向
2. **统一的事件通信**：基于VeighNa事件系统扩展
3. **模块解耦**：通过接口隔离实现模块独立开发
4. **版本兼容**：接口版本化管理
5. **可测试性**：支持Mock和单元测试

---

## 2. 模块依赖关系

### 2.1 依赖图

```
┌─────────────────────────────────────────────────────────────────┐
│                    A股交易系统模块依赖图                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   vnpy_china_config (配置管理)                                  │
│         ↓                                                       │
│         ↓ 被所有模块依赖                                         │
│         ↓                                                       │
│   ┌────────────────────────────────────────────────────────┐   │
│   │            vnpy_china_data (数据服务)                   │   │
│   │              ↓                                          │   │
│   │         被以下模块依赖                                   │   │
│   │   ┌─────┬─────┬─────┬─────┬─────┬─────┐             │   │
│   │   ↓     ↓     ↓     ↓     ↓     ↓     ↓             │   │
│   │ monitor      strategy    backtest  analysis  ml      │   │
│   │   ↓           ↓           ↓         ↓        ↓       │   │
│   └────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│                        vnpy_china_capital                        │
│                              ↓                                  │
│                        vnpy_china_reporting                      │
│                              ↓                                  │
│                        vnpy_china_web (可选)                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 依赖规则

| 规则 | 说明 |
|------|------|
| **单向依赖** | 上层模块可依赖下层模块，下层不能依赖上层 |
| **接口隔离** | 模块间通过接口通信，不直接依赖实现 |
| **事件驱动** | 模块间优先使用事件通信，避免直接调用 |
| **数据唯一源** | 所有数据通过vnpy_china_data获取 |

---

## 3. 核心接口定义

### 3.1 数据服务接口 (IDataProvider)

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from datetime import datetime, date
from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval


class IDataProvider(ABC):
    """数据提供者接口"""

    @abstractmethod
    def get_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """获取K线数据"""
        pass

    @abstractmethod
    def get_tick_data(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime
    ) -> List[TickData]:
        """获取Tick数据"""
        pass

    @abstractmethod
    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """获取股票基本信息"""
        pass

    @abstractmethod
    def get_financial_data(
        self,
        symbol: str,
        report_date: str
    ) -> Optional[Dict]:
        """获取财务数据"""
        pass

    @abstractmethod
    def subscribe_quote(self, symbols: List[str]) -> bool:
        """订阅实时行情"""
        pass
```

### 3.2 龙虎榜数据接口 (IDragonTigerProvider)

```python
class DragonTigerData:
    """龙虎榜数据"""
    symbol: str
    trade_date: date
    institution_net_buy: float  # 机构净买入
    broker_net_buy: float       # 营业部净买入
    buy_ratio: float            # 买入占比
    sell_ratio: float           # 卖出占比


class IDragonTigerProvider(ABC):
    """龙虎榜数据接口"""

    @abstractmethod
    def get_dragon_tiger_data(
        self,
        trade_date: date
    ) -> List[DragonTigerData]:
        """获取指定日期的龙虎榜数据"""
        pass

    @abstractmethod
    def get_institution_rank(
        self,
        trade_date: date,
        top_n: int = 10
    ) -> List[DragonTigerData]:
        """获取机构排名"""
        pass
```

### 3.3 北向资金数据接口 (INorthboundProvider)

```python
class NorthboundFlowData:
    """北向资金流向数据"""
    trade_date: date
    net_inflow: float        # 净流入（亿元）
    buy_volume: float        # 买入量（亿元）
    sell_volume: float       # 卖出量（亿元）
    holding_change: Dict[str, float]  # 个股持股变化


class INorthboundProvider(ABC):
    """北向资金数据接口"""

    @abstractmethod
    def get_northbound_flow(
        self,
        trade_date: date
    ) -> Optional[NorthboundFlowData]:
        """获取北向资金流向"""
        pass

    @abstractmethod
    def get_stock_holding_change(
        self,
        symbol: str,
        days: int = 5
    ) -> Dict[str, float]:
        """获取个股持股变化"""
        pass
```

### 3.4 资金管理接口 (ICapitalManager)

```python
class CapitalAllocation:
    """资金分配结果"""
    symbol: str
    target_volume: int        # 目标股数
    target_value: float       # 目标金额
    weight: float             # 权重


class ICapitalManager(ABC):
    """资金管理接口"""

    @abstractmethod
    def calculate_position(
        self,
        symbols: List[str],
        total_capital: float,
        prices: Dict[str, float]
    ) -> List[CapitalAllocation]:
        """计算仓位分配"""
        pass

    @abstractmethod
    def get_order_batches(
        self,
        symbol: str,
        total_volume: int,
        batch_type: str = "equal"
    ) -> List[Dict]:
        """获取分批委托计划"""
        pass

    @abstractmethod
    def check_drawdown(self, current_equity: float) -> float:
        """检查回撤并返回调整系数"""
        pass
```

### 3.5 分析服务接口 (IAnalysisService)

```python
class Level2Analysis:
    """Level-2分析结果"""
    symbol: str
    timestamp: datetime
    main_force_ratio: float   # 主力资金占比
    large_buy_volume: float   # 大单买入量
    large_sell_volume: float  # 大单卖出量


class MoneyFlowAnalysis:
    """资金流向分析结果"""
    symbol: str
    date: date
    super_large_inflow: float
    large_inflow: float
    medium_inflow: float
    small_inflow: float
    net_inflow: float


class IAnalysisService(ABC):
    """分析服务接口"""

    @abstractmethod
    def analyze_level2(self, symbol: str) -> Optional[Level2Analysis]:
        """分析Level-2数据"""
        pass

    @abstractmethod
    def analyze_money_flow(self, symbol: str, date: date) -> Optional[MoneyFlowAnalysis]:
        """分析资金流向"""
        pass

    @abstractmethod
    def get_limit_stats(self, symbol: str) -> Dict:
        """获取涨跌停统计"""
        pass
```

---

## 4. 事件定义

### 4.1 事件常量扩展

```python
# vnpy_china_events.py

from vnpy.event import Event

# A股特有事件
EVENT_DRAGON_TIGER = "eDragonTiger"  # 龙虎榜数据
EVENT_NORTHBOUND_FLOW = "eNorthboundFlow"  # 北向资金
EVENT_MONEY_FLOW = "eMoneyFlow"  # 资金流向
EVENT_LEVEL2_DATA = "eLevel2Data"  # Level-2数据
EVENT_CAPITAL_ALLOCATION = "eCapitalAllocation"  # 资金分配
EVENT_RISK_ALERT = "eRiskAlert"  # 风险告警
EVENT_MODULE_STATUS = "eModuleStatus"  # 模块状态
```

### 4.2 事件数据结构

```python
from dataclasses import dataclass
from typing import Any, Dict
from datetime import datetime


@dataclass
class DragonTigerEvent:
    """龙虎榜事件"""
    type: str = EVENT_DRAGON_TIGER
    data: Any = None
    gateway_name: str = ""


@dataclass
class CapitalAllocationEvent:
    """资金分配事件"""
    type: str = EVENT_CAPITAL_ALLOCATION
    allocations: List[CapitalAllocation] = None
    timestamp: datetime = None


@dataclass
class RiskAlertEvent:
    """风险告警事件"""
    type: str = EVENT_RISK_ALERT
    level: str = ""  # info/warning/critical
    title: str = ""
    message: str = ""
    data: Dict[str, Any] = None
    timestamp: datetime = None
```

---

## 5. 模块集成接口

### 5.1 策略模块集成接口

```python
class IChinaStrategy(ABC):
    """A股策略基类接口"""

    @abstractmethod
    def on_init(self):
        """策略初始化"""
        pass

    @abstractmethod
    def on_bar(self, bar: BarData):
        """K线数据推送"""
        pass

    @abstractmethod
    def on_tick(self, tick: TickData):
        """Tick数据推送"""
        pass

    @abstractmethod
    def on_dragon_tiger(self, event: DragonTigerEvent):
        """龙虎榜数据推送"""
        pass

    @abstractmethod
    def on_northbound_flow(self, event: Any):
        """北向资金推送"""
        pass

    @abstractmethod
    def check_risk(self) -> tuple[bool, str]:
        """风控检查"""
        pass

    @abstractmethod
    def get_capital_allocation(self) -> List[CapitalAllocation]:
        """获取资金分配"""
        pass
```

### 5.2 回测模块集成接口

```python
class IBacktestEngine(ABC):
    """回测引擎接口"""

    @abstractmethod
    def load_data(self, data_provider: IDataProvider) -> bool:
        """加载数据"""
        pass

    @abstractmethod
    def add_strategy(self, strategy: IChinaStrategy) -> bool:
        """添加策略"""
        pass

    @abstractmethod
    def run_backtest(self) -> Dict:
        """运行回测"""
        pass

    @abstractmethod
    def get_result(self) -> Dict:
        """获取回测结果"""
        pass
```

### 5.3 监控模块集成接口

```python
class IMonitorService(ABC):
    """监控服务接口"""

    @abstractmethod
    def start(self) -> bool:
        """启动监控"""
        pass

    @abstractmethod
    def stop(self) -> bool:
        """停止监控"""
        pass

    @abstractmethod
    def register_alert_handler(self, handler: callable):
        """注册告警处理器"""
        pass

    @abstractmethod
    def get_status(self) -> Dict:
        """获取监控状态"""
        pass
```

---

## 6. 模块注册与发现

### 6.1 模块注册表

```python
class ModuleRegistry:
    """模块注册表"""

    _modules: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, module: Any, version: str = "1.0.0"):
        """注册模块"""
        cls._modules[name] = {
            "module": module,
            "version": version,
            "registered_at": datetime.now()
        }

    @classmethod
    def get(cls, name: str) -> Optional[Any]:
        """获取模块"""
        info = cls._modules.get(name)
        return info["module"] if info else None

    @classmethod
    def list_modules(cls) -> Dict[str, str]:
        """列出所有模块"""
        return {
            name: info["version"]
            for name, info in cls._modules.items()
        }
```

### 6.2 服务发现

```python
class ServiceLocator:
    """服务定位器"""

    _services: Dict[str, Any] = {}

    @classmethod
    def register_service(cls, interface: Type, implementation: Any):
        """注册服务"""
        interface_name = interface.__name__
        cls._services[interface_name] = implementation

    @classmethod
    def get_service(cls, interface: Type) -> Optional[Any]:
        """获取服务"""
        interface_name = interface.__name__
        return cls._services.get(interface_name)
```

---

## 7. 使用示例

### 7.1 策略中使用数据服务

```python
from vnpy_china_config import ConfigManager
from vnpy_china_data import ChinaDataService
from vnpy_china_interface import IDataProvider


class MyStrategy:
    def __init__(self):
        # 获取配置
        config_manager = ConfigManager()
        self.config = config_manager.get_config("strategy")

        # 获取数据服务（通过接口）
        data_service: IDataProvider = ChinaDataService()

        # 使用数据
        bars = data_service.get_bar_data(
            symbol="000001",
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
            start=datetime(2024, 1, 1),
            end=datetime.now()
        )
```

### 7.2 策略中使用资金管理

```python
from vnpy_china_capital import CapitalManager
from vnpy_china_interface import ICapitalManager


class MyStrategy:
    def calculate_position(self, symbols: List[str], capital: float):
        # 获取资金管理服务
        capital_manager: ICapitalManager = CapitalManager()

        # 获取当前价格
        prices = self.get_current_prices(symbols)

        # 计算仓位
        allocations = capital_manager.calculate_position(
            symbols=symbols,
            total_capital=capital,
            prices=prices
        )

        return allocations
```

### 7.3 模块间事件通信

```python
from vnpy_china_events import EVENT_DRAGON_TIGER, DragonTigerEvent
from vnpy.event import EventEngine


class DragonTigerDataPublisher:
    """龙虎榜数据发布者"""

    def __init__(self, event_engine: EventEngine):
        self.event_engine = event_engine

    def publish_data(self, data: List[DragonTigerData]):
        """发布龙虎榜数据"""
        event = DragonTigerEvent(data=data)
        self.event_engine.put(EVENT_DRAGON_TIGER, event)


class StrategySubscriber:
    """策略订阅者"""

    def __init__(self, event_engine: EventEngine):
        self.event_engine = event_engine
        self.event_engine.register(EVENT_DRAGON_TIGER, self.on_dragon_tiger)

    def on_dragon_tiger(self, event):
        """处理龙虎榜事件"""
        data: DragonTigerData = event.data
        # 处理逻辑...
```

---

## 8. 接口版本管理

### 8.1 版本规则

```
主版本号.次版本号.修订号

例如：1.2.3

主版本号：不兼容的API修改
次版本号：向下兼容的功能性新增
修订号：向下兼容的问题修正
```

### 8.2 版本检查

```python
def check_version(required: str, actual: str) -> bool:
    """检查版本兼容性"""
    req_parts = required.split(".")
    act_parts = actual.split(".")

    # 主版本必须匹配
    if req_parts[0] != act_parts[0]:
        return False

    # 次版本号要求
    if len(req_parts) > 1 and len(act_parts) > 1:
        if int(act_parts[1]) < int(req_parts[1]):
            return False

    return True
```

---

## 9. 测试支持

### 9.1 Mock接口实现

```python
class MockDataProvider(IDataProvider):
    """Mock数据提供者"""

    def __init__(self, test_data: Dict = None):
        self.test_data = test_data or {}

    def get_bar_data(self, symbol, exchange, interval, start, end):
        return self.test_data.get("bars", [])

    def get_tick_data(self, symbol, exchange, start, end):
        return self.test_data.get("ticks", [])

    # 其他方法...
```

### 9.2 单元测试示例

```python
import pytest
from vnpy_china_interface import IDataProvider, MockDataProvider


def test_strategy_with_mock_data():
    """使用Mock数据测试策略"""

    # 创建Mock数据提供者
    mock_data = MockDataProvider(test_data={
        "bars": [create_test_bar()],
    })

    # 注入Mock
    strategy = MyStrategy(data_provider=mock_data)

    # 测试
    strategy.on_bar(mock_data.test_data["bars"][0])
    assert strategy.position == 100
```

---

## 10. 实施计划

| 阶段 | 任务 | 预估工时 |
|------|------|---------|
| 1 | 定义核心接口 | 0.5人天 |
| 2 | 实现事件系统扩展 | 0.5人天 |
| 3 | 实现模块注册与服务发现 | 0.5人天 |
| 4 | 编写接口文档和示例 | 1人天 |
| 5 | 创建Mock实现用于测试 | 0.5人天 |
| 合计 | | **3人天** |

---

## 11. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-02-24 | 初始版本 |
