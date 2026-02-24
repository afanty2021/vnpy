# 资金管理系统实施方案

> 文档版本：v1.0
> 创建日期：2026-02-24
> 需求编号：REQ-007
> 优先级：P1
> 预计工时：5人天
> 实施周期：1周

---

## 1. 方案概述

### 1.1 项目背景

资金管理是量化交易系统的核心模块之一，直接影响策略的风险收益特征。本方案旨在为VeighNa A股交易系统构建完善的资金管理能力，支持多种仓位分配策略、分批交易执行和资金曲线管理。

### 1.2 实施目标

| 目标类别 | 具体目标 | 成功标准 |
|---------|---------|---------|
| 功能完整性 | 实现仓位管理、分批交易、资金曲线管理三大功能 | 所有功能点100%实现 |
| 代码质量 | 遵循VeighNa架构规范 | 通过MyPy类型检查 |
| 测试覆盖 | 核心算法有完整测试 | 测试覆盖率≥80% |
| 文档完整 | 代码文档和用户文档齐全 | 文档覆盖率100% |

### 1.3 交付物清单

| 序号 | 交付物 | 类型 | 说明 |
|------|--------|------|------|
| 1 | vnpy_china_capital模块 | 代码 | 核心资金管理模块 |
| 2 | 单元测试 | 代码 | pytest测试套件 |
| 3 | 使用示例 | 代码 | 示例代码和脚本 |
| 4 | API文档 | 文档 | 接口说明文档 |
| 5 | 实施报告 | 文档 | 开发过程总结 |

---

## 2. 技术架构设计

### 2.1 模块结构

```
vnpy_china_capital/
├── __init__.py                 # 模块入口
├── position/                   # 仓位管理子模块
│   ├── __init__.py
│   ├── base.py                # 仓位管理器基类
│   ├── equal_weight.py        # 等权重仓位管理器
│   ├── value_weight.py        # 市值加权仓位管理器
│   ├── risk_parity.py         # 风险平价仓位管理器
│   └── dynamic.py             # 动态仓位管理器
├── order/                      # 分批交易子模块
│   ├── __init__.py
│   ├── base.py                # 订单执行器基类
│   ├── split.py               # 分批委托执行器
│   ├── pyramid.py             # 金字塔委托执行器
│   └── twap.py                # 时间加权平均执行器
├── equity/                     # 资金曲线子模块
│   ├── __init__.py
│   ├── curve.py               # 资金曲线管理器
│   ├── drawdown.py            # 回撤控制器
│   └── compound.py            # 复利增长计算器
├── objects/                    # 数据对象定义
│   ├── __init__.py
│   └── types.py               # 类型定义
└── utils/                      # 工具函数
    ├── __init__.py
    └── helpers.py             # 辅助函数
```

### 2.2 类图设计

```
┌─────────────────────────────────────────────────────────────────┐
│                        PositionSizer                            │
│                    (仓位管理器抽象基类)                          │
├─────────────────────────────────────────────────────────────────┤
│ + calculate_positions(symbols, capital, **kwargs) -> Dict       │
│ + validate_position(symbol, volume, price) -> bool              │
│ + get_position_summary() -> Dict                               │
└─────────────────────────────────────────────────────────────────┘
                              △
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────────────┐   ┌──────────────────┐   ┌─────────────────┐
│EqualWeight    │   │RiskParity        │   │DynamicPosition  │
│(等权重)       │   │(风险平价)        │   │(动态仓位)       │
├───────────────┤   ├──────────────────┤   ├─────────────────┤
│-max_position  │   │-risk_target      │   │-market_detector │
└───────────────┘   └──────────────────┘   └─────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      OrderExecutor                              │
│                   (订单执行器抽象基类)                           │
├─────────────────────────────────────────────────────────────────┤
│ + create_batches(total_volume, **kwargs) -> List[OrderBatch]    │
│ + execute_batch(batch, gateway) -> OrderData                   │
│ + get_execution_status() -> str                                │
└─────────────────────────────────────────────────────────────────┘
                              △
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────────────┐   ┌──────────────────┐   ┌─────────────────┐
│SplitOrder     │   │PyramidOrder      │   │TWAPOrder        │
│(分批委托)     │   │(金字塔委托)      │   │(时间加权)       │
├───────────────┤   ├──────────────────┤   ├─────────────────┤
│-n_batches     │   │-n_levels         │   │-time_window     │
└───────────────┘   └──────────────────┘   └─────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    EquityCurveManager                           │
│                      (资金曲线管理器)                            │
├─────────────────────────────────────────────────────────────────┤
│ -equity_curve: List[EquityPoint]                               │
│ -initial_capital: float                                         │
│ -peak_equity: float                                             │
├─────────────────────────────────────────────────────────────────┤
│ + update(equity: float) -> None                                │
│ + get_max_drawdown() -> float                                  │
│ + get_current_drawdown() -> float                              │
│ + get_equity_curve() -> List[EquityPoint]                      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 依赖关系

```
vnpy_china_capital
    ├── vnpy.trader (核心数据结构)
    │   ├── object (数据对象)
    │   └── enum (枚举类型)
    ├── vnpy.ctastrategy (策略集成)
    │   └── CtaTemplate (策略基类)
    └── 第三方库
        ├── numpy (数值计算)
        ├── pandas (数据处理)
        └── dataclasses (数据类)
```

---

## 3. 详细实施计划

### 3.1 第一阶段：基础框架搭建（0.5人天）

#### 任务1.1：创建目录结构

**操作步骤**：
```bash
# 创建模块根目录
mkdir -p vnpy_china_capital

# 创建子目录
mkdir -p vnpy_china_capital/position
mkdir -p vnpy_china_capital/order
mkdir -p vnpy_china_capital/equity
mkdir -p vnpy_china_capital/objects
mkdir -p vnpy_china_capital/utils

# 创建测试目录
mkdir -p tests/capital
```

**验收标准**：
- [ ] 所有目录创建完成
- [ ] 每个目录包含`__init__.py`文件
- [ ] 目录结构符合设计规范

#### 任务1.2：定义核心数据类型

**文件位置**：`vnpy_china_capital/objects/types.py`

**实现内容**：
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class PositionType(Enum):
    """仓位类型"""
    EQUAL_WEIGHT = "equal_weight"      # 等权重
    VALUE_WEIGHT = "value_weight"      # 市值加权
    RISK_PARITY = "risk_parity"        # 风险平价
    DYNAMIC = "dynamic"                # 动态仓位


class OrderBatchType(Enum):
    """订单批次类型"""
    EQUAL = "equal"                    # 等量分批
    PYRAMID_BUY = "pyramid_buy"        # 金字塔买入
    PYRAMID_SELL = "pyramid_sell"      # 金字塔卖出
    TWAP = "twap"                      # 时间加权
    VWAP = "vwap"                      # 成交量加权


@dataclass
class OrderBatch:
    """委托批次"""
    price: float                       # 委托价格（0=市价）
    volume: int                        # 委托数量
    delay: int                         # 延迟秒数
    batch_type: OrderBatchType         # 批次类型


@dataclass
class PositionAllocation:
    """仓位分配结果"""
    symbol: str                        # 股票代码
    target_volume: int                 # 目标股数
    target_value: float                # 目标金额
    weight: float                      # 权重比例
    reason: str                        # 分配原因


@dataclass
class EquityPoint:
    """资金曲线点"""
    datetime: datetime                 # 时间点
    equity: float                      # 资金值
    drawdown: float = 0.0              # 回撤比例
    daily_return: float = 0.0          # 日收益率
    cumulative_return: float = 0.0     # 累计收益率


@dataclass
class RiskMetrics:
    """风险指标"""
    max_drawdown: float                # 最大回撤
    current_drawdown: float            # 当前回撤
    sharpe_ratio: float                # 夏普比率
    sortino_ratio: float               # 索提诺比率
    calmar_ratio: float                # 卡玛比率
    volatility: float                  # 波动率
```

**验收标准**：
- [ ] 所有数据类型定义完成
- [ ] 通过MyPy类型检查
- [ ] 数据类型有完整的文档字符串

#### 任务1.3：创建基类接口

**文件位置**：`vnpy_china_capital/position/base.py`

**实现内容**：
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from vnpy.trader.object import TickData
from ..objects.types import PositionAllocation


class PositionSizer(ABC):
    """
    仓位管理器抽象基类

    负责根据策略信号和资金情况，计算各股票的目标仓位。
    所有具体的仓位管理算法都应继承此类。
    """

    def __init__(self) -> None:
        """构造函数"""
        self.allocations: Dict[str, PositionAllocation] = {}

    @abstractmethod
    def calculate_positions(
        self,
        symbols: List[str],
        total_capital: float,
        prices: Dict[str, float],
        **kwargs
    ) -> Dict[str, int]:
        """
        计算各股票的目标仓位

        Args:
            symbols: 股票代码列表
            total_capital: 总资金
            prices: 各股票当前价格 {symbol: price}
            **kwargs: 其他参数

        Returns:
            {symbol: 股数} 的字典

        Raises:
            ValueError: 参数无效时
        """
        pass

    def validate_position(
        self,
        symbol: str,
        volume: int,
        price: float
    ) -> bool:
        """
        验证仓位是否合法

        Args:
            symbol: 股票代码
            volume: 股数
            price: 价格

        Returns:
            是否合法
        """
        # A股交易单位检查
        if volume % 100 != 0:
            return False
        if volume <= 0:
            return False
        if price <= 0:
            return False
        return True

    def get_allocation_summary(self) -> Dict:
        """获取仓位分配摘要"""
        return {
            "total_positions": len(self.allocations),
            "allocations": self.allocations
        }
```

**验收标准**：
- [ ] 基类接口定义完成
- [ ] 抽象方法签名明确
- [ ] 包含基础验证方法
- [ ] 文档字符串完整

---

### 3.2 第二阶段：仓位管理实现（1.5人天）

#### 任务2.1：等权重仓位管理器

**文件位置**：`vnpy_china_capital/position/equal_weight.py`

**实现内容**：
```python
from typing import Dict, List
from .base import PositionSizer
from ..objects.types import PositionAllocation


class EqualWeightPosition(PositionSizer):
    """
    等权重仓位管理器

    将资金平均分配到所有目标股票，适用于多因子选股、
    指数增强等需要均匀分散风险的策略。
    """

    def __init__(self, max_position: int = 10) -> None:
        """
        构造函数

        Args:
            max_position: 最大持仓数量
        """
        super().__init__()
        self.max_position = max_position

    def calculate_positions(
        self,
        symbols: List[str],
        total_capital: float,
        prices: Dict[str, float],
        **kwargs
    ) -> Dict[str, int]:
        """
        等权重分配仓位

        Args:
            symbols: 目标股票列表
            total_capital: 总资金
            prices: 各股票价格

        Returns:
            {symbol: 股数}
        """
        if not symbols:
            return {}

        n = min(len(symbols), self.max_position)
        if n == 0:
            return {}

        # 平均分配资金
        capital_per_stock = total_capital / n

        positions = {}
        self.allocations = {}

        for symbol in symbols[:n]:
            price = prices.get(symbol, 0)
            if price <= 0:
                continue

            # 计算股数（取整到100股）
            volume = int(capital_per_stock / price / 100) * 100

            if volume > 0 and self.validate_position(symbol, volume, price):
                positions[symbol] = volume
                self.allocations[symbol] = PositionAllocation(
                    symbol=symbol,
                    target_volume=volume,
                    target_value=volume * price,
                    weight=1.0 / n,
                    reason="等权重分配"
                )

        return positions
```

**测试用例**：
```python
import pytest
from vnpy_china_capital.position.equal_weight import EqualWeightPosition


def test_equal_weight_basic():
    """测试基本等权重分配"""
    sizer = EqualWeightPosition(max_position=5)

    symbols = ["000001", "000002", "000003", "000004", "000005"]
    prices = {s: 10.0 for s in symbols}
    capital = 100000.0

    positions = sizer.calculate_positions(symbols, capital, prices)

    # 验证结果
    assert len(positions) == 5
    for symbol, volume in positions.items():
        # 每只股票分配20000元，10元价格 = 2000股
        assert volume == 2000


def test_equal_weight_max_position():
    """测试最大持仓数量限制"""
    sizer = EqualWeightPosition(max_position=3)

    symbols = ["000001", "000002", "000003", "000004", "000005"]
    prices = {s: 10.0 for s in symbols}
    capital = 100000.0

    positions = sizer.calculate_positions(symbols, capital, prices)

    # 最多持仓3只
    assert len(positions) == 3


def test_equal_weight_rounding():
    """测试取整规则"""
    sizer = EqualWeightPosition(max_position=1)

    symbols = ["000001"]
    prices = {"000001": 10.5}
    capital = 10000.0

    positions = sizer.calculate_positions(symbols, capital, prices)

    # 10000 / 10.5 = 952.38 -> 900股（取整到100）
    assert positions["000001"] % 100 == 0
    assert positions["000001"] > 0
```

**验收标准**：
- [ ] 功能实现完整
- [ ] 测试用例通过
- [ ] 边界条件处理正确
- [ ] 文档完整

#### 任务2.2：风险平价仓位管理器

**文件位置**：`vnpy_china_capital/position/risk_parity.py`

**核心算法**：
```python
import numpy as np
from typing import Dict, List
from .base import PositionSizer
from ..objects.types import PositionAllocation


class RiskParityPosition(PositionSizer):
    """
    风险平价仓位管理器

    根据各股票的波动率分配资金，使得各股票对组合的
    风险贡献相等。适用于多资产配置场景。
    """

    def __init__(self, risk_target: float = 0.1) -> None:
        """
        构造函数

        Args:
            risk_target: 目标组合波动率
        """
        super().__init__()
        self.risk_target = risk_target

    def calculate_positions(
        self,
        symbols: List[str],
        total_capital: float,
        prices: Dict[str, float],
        volatilities: Dict[str, float] = None,
        **kwargs
    ) -> Dict[str, int]:
        """
        风险平价分配

        Args:
            symbols: 目标股票列表
            total_capital: 总资金
            prices: 各股票价格
            volatilities: 各股票波动率 {symbol: volatility}

        Returns:
            {symbol: 股数}
        """
        if not symbols:
            return {}

        # 默认波动率（年化20%）
        if volatilities is None:
            volatilities = {s: 0.2 for s in symbols}

        # 获取波动率数组
        vols = np.array([volatilities.get(s, 0.2) for s in symbols])

        # 风险平价权重 = 1/波动率
        inverse_vols = 1.0 / vols
        weights = inverse_vols / inverse_vols.sum()

        # 计算仓位
        positions = {}
        self.allocations = {}

        for symbol, weight in zip(symbols, weights):
            price = prices.get(symbol, 0)
            if price <= 0:
                continue

            position_value = total_capital * weight
            volume = int(position_value / price / 100) * 100

            if volume > 0 and self.validate_position(symbol, volume, price):
                positions[symbol] = volume
                self.allocations[symbol] = PositionAllocation(
                    symbol=symbol,
                    target_volume=volume,
                    target_value=volume * price,
                    weight=weight,
                    reason=f"风险平价分配(波动率:{volatilities[symbol]:.2%})"
                )

        return positions
```

**验收标准**：
- [ ] 风险平价算法正确
- [ ] 波动率处理合理
- [ ] 测试覆盖完整

#### 任务2.3：动态仓位管理器

**文件位置**：`vnpy_china_capital/position/dynamic.py`

**实现要点**：
```python
class DynamicPosition(PositionSizer):
    """
    动态仓位管理器

    根据市场状况（如波动率、趋势强度）动态调整仓位大小。
    市场环境好时高仓位，环境差时低仓位。
    """

    def __init__(
        self,
        base_position: float = 0.8,
        min_position: float = 0.3,
        max_position: float = 1.0
    ) -> None:
        """
        Args:
            base_position: 基础仓位比例
            min_position: 最小仓位比例
            max_position: 最大仓位比例
        """
        super().__init__()
        self.base_position = base_position
        self.min_position = min_position
        self.max_position = max_position

    def calculate_dynamic_ratio(self, market_volatility: float) -> float:
        """
        根据市场波动率计算动态仓位比例

        Args:
            market_volatility: 市场波动率

        Returns:
            仓位比例
        """
        # 波动率越低，仓位越高
        ratio = self.base_position / (1 + market_volatility * 10)
        return max(self.min_position, min(self.max_position, ratio))
```

---

### 3.3 第三阶段：分批交易实现（1.5人天）

#### 任务3.1：分批委托执行器

**文件位置**：`vnpy_china_capital/order/split.py`

**核心实现**：
```python
from typing import List, Optional
from datetime import datetime, timedelta
from ..objects.types import OrderBatch, OrderBatchType


class SplitOrderExecutor:
    """
    分批委托执行器

    将大单拆分成多个小单分批执行，降低市场冲击成本。
    """

    def __init__(
        self,
        total_volume: int,
        n_batches: int = 5,
        interval_seconds: int = 60
    ) -> None:
        """
        Args:
            total_volume: 总委托数量
            n_batches: 分批数量
            interval_seconds: 每批间隔秒数
        """
        self.total_volume = total_volume
        self.n_batches = n_batches
        self.interval_seconds = interval_seconds
        self.batches: List[OrderBatch] = []
        self.current_batch = 0

    def create_equal_batches(self) -> List[OrderBatch]:
        """
        创建等量分批

        Returns:
            批次列表
        """
        volume_per_batch = self.total_volume // self.n_batches
        batches = []

        for i in range(self.n_batches):
            # 最后一批调整数量
            if i == self.n_batches - 1:
                volume = self.total_volume - volume_per_batch * (self.n_batches - 1)
            else:
                volume = volume_per_batch

            batch = OrderBatch(
                price=0,  # 市价单
                volume=volume,
                delay=i * self.interval_seconds,
                batch_type=OrderBatchType.EQUAL
            )
            batches.append(batch)

        self.batches = batches
        return batches

    def get_next_batch(self) -> Optional[OrderBatch]:
        """获取下一批委托"""
        if self.current_batch >= len(self.batches):
            return None

        batch = self.batches[self.current_batch]
        self.current_batch += 1
        return batch

    def is_complete(self) -> bool:
        """是否所有批次都已完成"""
        return self.current_batch >= len(self.batches)
```

**测试用例**：
```python
def test_split_order_equal():
    """测试等量分批"""
    executor = SplitOrderExecutor(total_volume=1000, n_batches=5)
    batches = executor.create_equal_batches()

    assert len(batches) == 5
    assert sum(b.volume for b in batches) == 1000

    # 验证时间间隔
    for i, batch in enumerate(batches):
        assert batch.delay == i * 60


def test_split_order_execution():
    """测试分批执行流程"""
    executor = SplitOrderExecutor(total_volume=1000, n_batches=5)
    executor.create_equal_batches()

    # 模拟执行
    executed = 0
    while not executor.is_complete():
        batch = executor.get_next_batch()
        if batch:
            executed += batch.volume

    assert executed == 1000
```

#### 任务3.2：金字塔委托执行器

**文件位置**：`vnpy_china_capital/order/pyramid.py`

**实现要点**：
```python
class PyramidOrderExecutor:
    """
    金字塔委托执行器

    买入时：越买越多（左侧金字塔）
    卖出时：越卖越多

    适用于趋势跟踪策略，随着趋势确认逐步加仓。
    """

    def __init__(
        self,
        total_volume: int,
        n_levels: int = 3,
        interval_seconds: int = 120
    ) -> None:
        """
        Args:
            total_volume: 总委托数量
            n_levels: 金字塔层数
            interval_seconds: 每层间隔秒数
        """
        self.total_volume = total_volume
        self.n_levels = n_levels
        self.interval_seconds = interval_seconds

    def create_pyramid_batches(
        self,
        direction: str = "buy",
        ratios: List[float] = None
    ) -> List[OrderBatch]:
        """
        创建金字塔批次

        Args:
            direction: "buy" 或 "sell"
            ratios: 自定义比例列表

        Returns:
            批次列表
        """
        if ratios is None:
            # 默认金字塔比例
            if direction == "buy":
                ratios = [0.2, 0.3, 0.5]  # 买入：越买越多
            else:
                ratios = [0.5, 0.3, 0.2]  # 卖出：越卖越多

        # 调整层数
        if len(ratios) != self.n_levels:
            ratios = ratios[:self.n_levels]

        # 计算每批数量
        volumes = [int(self.total_volume * r) for r in ratios]

        # 调整最后一批确保总数正确
        volumes[-1] = self.total_volume - sum(volumes[:-1])

        # 创建批次
        batch_type = (OrderBatchType.PYRAMID_BUY if direction == "buy"
                     else OrderBatchType.PYRAMID_SELL)

        batches = [
            OrderBatch(
                price=0,
                volume=v,
                delay=i * self.interval_seconds,
                batch_type=batch_type
            )
            for i, v in enumerate(volumes)
        ]

        return batches
```

#### 任务3.3：TWAP执行器

**文件位置**：`vnpy_china_capital/order/twap.py`

**实现要点**：
```python
class TWAPOrderExecutor:
    """
    时间加权平均价格执行器

    在指定时间窗口内均匀执行委托，以获得时间加权平均价格。
    适用于大单拆分场景。
    """

    def __init__(
        self,
        total_volume: int,
        time_window_seconds: int = 300,
        n_slices: int = 10
    ) -> None:
        """
        Args:
            total_volume: 总委托数量
            time_window_seconds: 时间窗口（秒）
            n_slices: 切片数量
        """
        self.total_volume = total_volume
        self.time_window_seconds = time_window_seconds
        self.n_slices = n_slices

    def create_twap_batches(self) -> List[OrderBatch]:
        """创建TWAP批次"""
        interval = self.time_window_seconds // self.n_slices
        volume_per_slice = self.total_volume // self.n_slices

        batches = []
        for i in range(self.n_slices):
            volume = volume_per_slice if i < self.n_slices - 1 else (
                self.total_volume - volume_per_slice * (self.n_slices - 1)
            )

            batch = OrderBatch(
                price=0,
                volume=volume,
                delay=i * interval,
                batch_type=OrderBatchType.TWAP
            )
            batches.append(batch)

        return batches
```

---

### 3.4 第四阶段：资金曲线管理（1.5人天）

#### 任务4.1：资金曲线管理器

**文件位置**：`vnpy_china_capital/equity/curve.py`

**核心实现**：
```python
from typing import List, Optional
from datetime import datetime
from ..objects.types import EquityPoint


class EquityCurveManager:
    """
    资金曲线管理器

    记录和管理策略的资金曲线，计算各种风险收益指标。
    """

    def __init__(self, initial_capital: float = 0.0) -> None:
        """
        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.equity_curve: List[EquityPoint] = []
        self.peak_equity: float = initial_capital
        self.current_equity: float = initial_capital

    def update(
        self,
        equity: float,
        dt: Optional[datetime] = None
    ) -> EquityPoint:
        """
        更新资金曲线

        Args:
            equity: 当前资金值
            dt: 时间点（默认为当前时间）

        Returns:
            创建的资金曲线点
        """
        if dt is None:
            dt = datetime.now()

        # 更新最高资金
        if equity > self.peak_equity:
            self.peak_equity = equity

        # 计算回撤
        drawdown = 0.0
        if self.peak_equity > 0:
            drawdown = (self.peak_equity - equity) / self.peak_equity

        # 计算收益率
        daily_return = 0.0
        if self.equity_curve:
            daily_return = (equity - self.current_equity) / self.current_equity

        cumulative_return = 0.0
        if self.initial_capital > 0:
            cumulative_return = (equity - self.initial_capital) / self.initial_capital

        # 创建资金曲线点
        point = EquityPoint(
            datetime=dt,
            equity=equity,
            drawdown=drawdown,
            daily_return=daily_return,
            cumulative_return=cumulative_return
        )

        self.equity_curve.append(point)
        self.current_equity = equity

        return point

    def get_max_drawdown(self) -> float:
        """获取最大回撤"""
        if not self.equity_curve:
            return 0.0
        return max((p.drawdown for p in self.equity_curve), default=0.0)

    def get_current_drawdown(self) -> float:
        """获取当前回撤"""
        if self.peak_equity > 0:
            return (self.peak_equity - self.current_equity) / self.peak_equity
        return 0.0

    def get_returns(self) -> List[float]:
        """获取收益率序列"""
        return [p.daily_return for p in self.equity_curve]

    def calculate_sharpe_ratio(
        self,
        risk_free_rate: float = 0.03,
        periods_per_year: int = 252
    ) -> float:
        """
        计算夏普比率

        Args:
            risk_free_rate: 无风险利率（年化）
            periods_per_year: 年化周期数

        Returns:
            夏普比率
        """
        if len(self.equity_curve) < 2:
            return 0.0

        returns = self.get_returns()
        if not returns:
            return 0.0

        avg_return = sum(returns) / len(returns)
        std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5

        if std_return == 0:
            return 0.0

        # 年化
        annual_return = avg_return * periods_per_year
        annual_std = std_return * (periods_per_year ** 0.5)
        daily_rf = risk_free_rate / periods_per_year

        sharpe = (annual_return - risk_free_rate) / annual_std
        return sharpe
```

**验收标准**：
- [ ] 资金曲线更新正确
- [ ] 回撤计算准确
- [ ] 夏普比率计算正确
- [ ] 测试覆盖完整

#### 任务4.2：回撤控制器

**文件位置**：`vnpy_china_capital/equity/drawdown.py`

**实现要点**：
```python
class DrawdownController:
    """
    回撤控制器

    根据当前回撤水平动态调整仓位，控制下行风险。
    """

    def __init__(
        self,
        max_drawdown: float = 0.15,
        warning_level: float = 0.10
    ) -> None:
        """
        Args:
            max_drawdown: 最大允许回撤
            warning_level: 预警回撤水平
        """
        self.max_drawdown = max_drawdown
        self.warning_level = warning_level

    def get_position_multiplier(self, current_drawdown: float) -> float:
        """
        根据当前回撤计算仓位调整系数

        Args:
            current_drawdown: 当前回撤比例

        Returns:
            仓位调整系数（0-1）
        """
        if current_drawdown < self.warning_level:
            # 正常状态，满仓
            return 1.0
        elif current_drawdown < self.max_drawdown * 0.75:
            # 预警状态，7成仓
            return 0.7
        elif current_drawdown < self.max_drawdown:
            # 风险状态，5成仓
            return 0.5
        else:
            # 超过最大回撤，清仓
            return 0.0

    def should_stop_trading(self, current_drawdown: float) -> bool:
        """判断是否应该停止交易"""
        return current_drawdown >= self.max_drawdown
```

#### 任务4.3：复利增长计算器

**文件位置**：`vnpy_china_capital/equity/compound.py`

**实现要点**：
```python
class CompoundGrowthCalculator:
    """
    复利增长计算器

    使用凯利公式等方法计算最优仓位，
    实现资金的复利增长。
    """

    def __init__(self, target_return: float = 0.20) -> None:
        """
        Args:
            target_return: 年化目标收益率
        """
        self.target_return = target_return

    def calculate_kelly_fraction(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        使用凯利公式计算最优仓位比例

        f* = (bp - q) / b

        其中：
        f* = 最优仓位比例
        b = 盈亏比 = avg_win / avg_loss
        p = 胜率 = win_rate
        q = 1 - p

        Args:
            win_rate: 胜率
            avg_win: 平均盈利
            avg_loss: 平均亏损

        Returns:
            最优仓位比例（使用半凯利）
        """
        if win_rate <= 0 or win_rate >= 1:
            return 0.0

        if avg_loss == 0:
            return 0.0

        b = abs(avg_win / avg_loss)
        p = win_rate
        q = 1 - p

        # 凯利公式
        f_star = (b * p - q) / b

        # 限制在0-1之间，并使用半凯利（更保守）
        f_star = max(0, min(1, f_star * 0.5))

        return f_star

    def calculate_position_size(
        self,
        current_capital: float,
        kelly_fraction: float,
        max_position: float = 0.25
    ) -> float:
        """
        计算目标仓位金额

        Args:
            current_capital: 当前资金
            kelly_fraction: 凯利比例
            max_position: 最大仓位限制

        Returns:
            目标仓位金额
        """
        position_size = current_capital * kelly_fraction
        max_size = current_capital * max_position

        return min(position_size, max_size)

    def project_growth(
        self,
        initial_capital: float,
        annual_return: float,
        years: int = 10
    ) -> float:
        """
        计算复利增长后的资金

        Args:
            initial_capital: 初始资金
            annual_return: 年化收益率
            years: 年数

        Returns:
            增长后的资金
        """
        return initial_capital * ((1 + annual_return) ** years)
```

---

## 4. 测试计划

### 4.1 单元测试

| 模块 | 测试文件 | 测试用例数 |
|------|---------|-----------|
| position/equal_weight | test_equal_weight.py | 5 |
| position/risk_parity | test_risk_parity.py | 6 |
| position/dynamic | test_dynamic.py | 4 |
| order/split | test_split.py | 5 |
| order/pyramid | test_pyramid.py | 5 |
| order/twap | test_twap.py | 4 |
| equity/curve | test_curve.py | 8 |
| equity/drawdown | test_drawdown.py | 4 |
| equity/compound | test_compound.py | 6 |
| **合计** | | **47** |

### 4.2 集成测试

```python
# tests/capital/test_integration.py
import pytest
from vnpy_china_capital.position import EqualWeightPosition
from vnpy_china_capital.order import SplitOrderExecutor
from vnpy_china_capital.equity import EquityCurveManager


def test_full_workflow():
    """测试完整工作流程"""
    # 1. 创建仓位管理器
    sizer = EqualWeightPosition(max_position=5)
    symbols = ["000001", "000002", "000003"]
    prices = {s: 10.0 for s in symbols}
    capital = 100000.0

    # 2. 计算仓位
    positions = sizer.calculate_positions(symbols, capital, prices)
    assert len(positions) > 0

    # 3. 创建分批执行器
    total_volume = positions["000001"]
    executor = SplitOrderExecutor(total_volume, n_batches=3)
    batches = executor.create_equal_batches()
    assert len(batches) == 3

    # 4. 创建资金曲线管理器
    equity_mgr = EquityCurveManager(initial_capital=capital)
    equity_mgr.update(capital + 1000)
    assert equity_mgr.current_equity == capital + 1000
```

### 4.3 性能测试

```python
def test_position_sizer_performance():
    """测试仓位计算性能"""
    import time

    sizer = EqualWeightPosition(max_position=50)
    symbols = [f"{i:06d}.SZ" for i in range(1, 1001)]
    prices = {s: 10.0 for s in symbols}
    capital = 1000000.0

    start = time.time()
    positions = sizer.calculate_positions(symbols, capital, prices)
    elapsed = time.time() - start

    assert elapsed < 0.1  # 应在100ms内完成
    assert len(positions) == 50
```

---

## 5. 文档计划

### 5.1 代码文档

- 每个类和方法添加完整的docstring
- 复杂算法添加注释说明
- 使用类型注解

### 5.2 用户文档

创建 `docs/capital_management.md`：

```markdown
# 资金管理模块使用指南

## 1. 快速开始

### 1.1 等权重仓位配置

```python
from vnpy_china_capital.position import EqualWeightPosition

# 创建仓位管理器
sizer = EqualWeightPosition(max_position=10)

# 计算仓位
symbols = ["000001", "000002", "000003"]
prices = {"000001": 10.0, "000002": 20.0, "000003": 15.0}
positions = sizer.calculate_positions(symbols, 100000, prices)
```

### 1.2 分批委托

```python
from vnpy_china_capital.order import SplitOrderExecutor

# 创建执行器
executor = SplitOrderExecutor(total_volume=10000, n_batches=5)
batches = executor.create_equal_batches()

# 依次执行
for batch in batches:
    # 发送委托
    pass
```

### 1.3 资金曲线管理

```python
from vnpy_china_capital.equity import EquityCurveManager

# 创建管理器
manager = EquityCurveManager(initial_capital=100000)

# 更新资金
manager.update(102000)
manager.update(101500)

# 获取指标
max_dd = manager.get_max_drawdown()
sharpe = manager.calculate_sharpe_ratio()
```

## 2. API参考

[详细API文档...]
```

---

## 6. 风险管理

### 6.1 技术风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| 数值计算精度问题 | 中 | 中 | 使用Decimal处理金额 |
| 取整误差 | 中 | 低 | 完善取整逻辑 |
| 性能问题 | 低 | 低 | 算法优化 |

### 6.2 业务风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| 仓位计算错误 | 低 | 高 | 充分测试验证 |
| 风控参数设置不当 | 中 | 中 | 提供默认参数 |

---

## 7. 时间安排

### 7.1 日程计划

| 日期 | 任务 | 工时 |
|------|------|------|
| Day 1上午 | 基础框架搭建 | 4h |
| Day 1下午 | 等权重仓位管理器 | 4h |
| Day 2上午 | 风险平价+动态仓位 | 4h |
| Day 2下午 | 分批交易执行器 | 4h |
| Day 3上午 | 资金曲线管理器 | 4h |
| Day 3下午 | 回撤控制+复利增长 | 4h |
| Day 4上午 | 单元测试编写 | 4h |
| Day 4下午 | 集成测试+文档 | 4h |
| Day 5 | 代码审查+优化 | 8h |

### 7.2 里程碑

| 里程碑 | 时间 | 交付内容 |
|--------|------|---------|
| M1 | Day 1结束 | 基础框架+等权重仓位 |
| M2 | Day 2结束 | 所有仓位管理器+分批交易 |
| M3 | Day 3结束 | 资金曲线管理完成 |
| M4 | Day 4结束 | 测试+文档完成 |
| M5 | Day 5结束 | 代码审查通过 |

---

## 8. 验收标准

### 8.1 功能验收

- [ ] 所有仓位管理器功能正常
- [ ] 分批交易执行正确
- [ ] 资金曲线计算准确
- [ ] 回撤控制有效
- [ ] 凯利公式计算正确

### 8.2 质量验收

- [ ] 单元测试覆盖率≥80%
- [ ] 所有测试用例通过
- [ ] 代码通过MyPy类型检查
- [ ] 代码通过Ruff检查
- [ ] 文档完整

### 8.3 性能验收

- [ ] 仓位计算<100ms（1000只股票）
- [ ] 资金曲线更新<10ms
- [ ] 内存占用<100MB

---

## 9. 后续计划

### 9.1 功能扩展

- [ ] 支持更多仓位管理策略（如市值加权）
- [ ] 支持VWAP执行算法
- [ ] 支持资金归因分析
- [ ] 集成到策略框架

### 9.2 优化方向

- [ ] 性能优化（使用Numba加速）
- [ ] 支持多进程计算
- [ ] 添加可视化图表

---

**文档版本**：v1.0
**创建日期**：2026-02-24
**维护者**：AI Assistant
**下次更新**：实施完成后更新
