# 资金管理系统设计文档

> 文档版本：v1.1
> 创建日期：2026-02-24
> 更新日期：2026-02-24
> 需求编号：REQ-007
> 优先级：P1
> 预计工时：5人天
>
> **变更记录**: 修正REQ编号（原REQ-008）

---

## 1. 设计目标

构建A股资金管理模块：

1. **仓位管理**：等权重、市值加权、风险平价、动态仓位
2. **分批交易**：分批建仓、分批平仓、金字塔加仓
3. **资金曲线管理**：资金曲线、回撤控制、复利增长

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                       资金管理系统架构                            │
├─────────────────────────────────────────────────────────────────┤
│  【仓位管理】                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │EqualWeight   │  │ValueWeight   │  │RiskParity   │        │
│  │(等权重)      │  │(市值加权)    │  │(风险平价)   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│  【分批交易】                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ SplitOrder   │  │PyramidOrder │  │TWAPOrder    │        │
│  │(分批委托)    │  │(金字塔委托)  │  │(时间加权)   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│  【资金曲线】                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │EquityCurve   │  │DrawdownCtrl │  │Compound     │        │
│  │(资金曲线)    │  │(回撤控制)   │  │(复利增长)   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块结构

```
vnpy_china_capital/
├── __init__.py
├── position/
│   ├── __init__.py
│   ├── base.py            # 仓位管理基类
│   ├── equal_weight.py   # 等权重
│   ├── value_weight.py   # 市值加权
│   ├── risk_parity.py    # 风险平价
│   └── dynamic.py         # 动态仓位
├── order/
│   ├── __init__.py
│   ├── split.py          # 分批委托
│   ├── pyramid.py        # 金字塔委托
│   └── twap.py           # 时间加权
└── equity/
    ├── __init__.py
    ├── curve.py           # 资金曲线
    ├── drawdown.py        # 回撤控制
    └── compound.py        # 复利增长
```

---

## 3. 核心类设计

### 3.1 仓位管理器基类

```python
from abc import ABC, abstractmethod
from typing import Dict, List


class PositionSizer(ABC):
    """仓位管理器基类"""

    @abstractmethod
    def calculate_positions(
        self,
        symbols: List[str],
        total_capital: float,
        **kwargs
    ) -> Dict[str, int]:
        """
        计算各股票仓位

        返回: {symbol: 股数}
        """
        pass


class EqualWeightPosition(PositionSizer):
    """等权重仓位管理器"""

    def __init__(self, max_position: int = 10):
        self.max_position = max_position

    def calculate_positions(
        self,
        symbols: List[str],
        total_capital: float,
        **kwargs
    ) -> Dict[str, int]:
        """等权重分配"""
        n = min(len(symbols), self.max_position)
        if n == 0:
            return {}

        # 平均分配
        capital_per_stock = total_capital / n

        positions = {}
        for symbol in symbols[:n]:
            # 假设价格为10元，计算股数
            # 实际需要获取当前价格
            price = kwargs.get('prices', {}).get(symbol, 10.0)
            positions[symbol] = int(capital_per_stock / price / 100) * 100  # 取整到100股

        return positions
```

### 3.2 风险平价仓位

```python
import numpy as np


class RiskParityPosition(PositionSizer):
    """风险平价仓位管理器"""

    def __init__(self, risk_target: float = 0.1):
        self.risk_target = risk_target  # 目标波动率

    def calculate_positions(
        self,
        symbols: List[str],
        total_capital: float,
        volatilities: Dict[str, float] = None,
        **kwargs
    ) -> Dict[str, int]:
        """风险平价分配"""

        if not symbols or not volatilities:
            return {}

        # 获取各股票波动率
        vols = np.array([volatilities.get(s, 0.02) for s in symbols])

        # 风险平价权重 = 1/波动率
        inverse_vols = 1.0 / vols
        weights = inverse_vols / inverse_vols.sum()

        # 根据权重计算仓位
        positions = {}
        prices = kwargs.get('prices', {})

        for symbol, weight in zip(symbols, weights):
            position_value = total_capital * weight
            price = prices.get(symbol, 10.0)
            positions[symbol] = int(position_value / price / 100) * 100

        return positions
```

### 3.3 分批委托

```python
from dataclasses import dataclass
from typing import List
from datetime import datetime, timedelta


@dataclass
class OrderBatch:
    """委托批次"""
    price: float
    volume: int
    delay: int  # 延迟秒数


class SplitOrderExecutor:
    """分批委托执行器"""

    def __init__(self, total_volume: int, n_batches: int = 5):
        self.total_volume = total_volume
        self.n_batches = n_batches

    def create_batches(
        self,
        order_type: str = "equal"
    ) -> List[OrderBatch]:
        """创建委托批次"""

        if order_type == "equal":
            # 等量分批
            volume_per_batch = self.total_volume // self.n_batches
            batches = [
                OrderBatch(price=0, volume=volume_per_batch, delay=i * 60)
                for i in range(self.n_batches)
            ]
            # 调整最后一批
            batches[-1].volume = self.total_volume - volume_per_batch * (self.n_batches - 1)

        elif order_type == "twap":
            # 时间加权：假设价格线性变化
            volumes = [self.total_volume // self.n_batches] * self.n_batches
            batches = [
                OrderBatch(price=0, volume=v, delay=i * 60)
                for i, v in enumerate(volumes)
            ]

        elif order_type == "vwap":
            # 成交量加权
            # 需要历史成交量分布
            weights = self._get_vwap_weights()
            volumes = [int(self.total_volume * w) for w in weights]
            batches = [
                OrderBatch(price=0, volume=v, delay=i * 60)
                for i, v in enumerate(volumes)
            ]

        return batches


class PyramidOrderExecutor:
    """金字塔委托执行器"""

    def __init__(self, total_volume: int, n_levels: int = 3):
        self.total_volume = total_volume
        self.n_levels = n_levels

    def create_batches(self, direction: str = "buy") -> List[OrderBatch]:
        """创建金字塔批次"""

        if direction == "buy":
            # 买入：越买越多（左侧金字塔）
            # 例如：3层，分别是20%，30%，50%
            ratios = [0.2, 0.3, 0.5]
        else:
            # 卖出：越卖越多
            ratios = [0.5, 0.3, 0.2]

        volumes = [int(self.total_volume * r) for r in ratios]

        batches = [
            OrderBatch(price=0, volume=v, delay=i * 120)
            for i, v in enumerate(volumes)
        ]

        return batches
```

### 3.4 资金曲线管理

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class EquityPoint:
    """资金曲线点"""
    datetime: datetime
    equity: float
    drawdown: float = 0.0


class EquityCurveManager:
    """资金曲线管理器"""

    def __init__(self):
        self.equity_curve: List[EquityPoint] = []
        self.initial_capital = 0.0
        self.peak_equity = 0.0

    def update(self, equity: float):
        """更新资金曲线"""
        # 计算回撤
        if equity > self.peak_equity:
            self.peak_equity = equity

        drawdown = (self.peak_equity - equity) / self.peak_equity if self.peak_equity > 0 else 0

        self.equity_curve.append(EquityPoint(
            datetime=datetime.now(),
            equity=equity,
            drawdown=drawdown
        ))

    def get_max_drawdown(self) -> float:
        """获取最大回撤"""
        return max((p.drawdown for p in self.equity_curve), default=0.0)


class DrawdownController:
    """回撤控制器"""

    def __init__(self, max_drawdown: float = 0.15):
        self.max_drawdown = max_drawdown

    def should_reduce_position(self, current_drawdown: float) -> float:
        """
        根据回撤计算仓位调整比例

        返回: 仓位调整系数 (0-1)
        """
        if current_drawdown < self.max_drawdown * 0.5:
            return 1.0  # 满仓
        elif current_drawdown < self.max_drawdown * 0.75:
            return 0.7  # 7成仓
        elif current_drawdown < self.max_drawdown:
            return 0.5  # 5成仓
        else:
            return 0.0  # 清仓


class CompoundGrowth:
    """复利增长计算器"""

    def __init__(self, target_return: float = 0.20):
        self.target_return = target_return  # 年化目标收益

    def calculate_position_size(
        self,
        current_capital: float,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        凯利公式计算仓位

        f* = (bp - q) / b

        f*: 仓位比例
        b: 盈亏比
        p: 胜率
        q: 1-p
        """

        if win_rate <= 0 or win_rate >= 1:
            return 0.0

        # 计算盈亏比
        b = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        if b == 0:
            return 0.0

        p = win_rate
        q = 1 - p

        # 凯利公式
        f_star = (b * p - q) / b

        # 限制在0-1之间，并使用半凯利
        f_star = max(0, min(1, f_star * 0.5))

        return f_star

    def calculate_annual_target(
        self,
        initial_capital: float,
        years: int = 10
    ) -> float:
        """计算年度目标"""
        return initial_capital * ((1 + self.target_return) ** years)
```

---

## 4. 实施计划

| 阶段 | 任务 | 预估工时 |
|------|------|---------|
| 1 | 创建目录结构 | 0.5人天 |
| 2 | 实现仓位管理器 | 1.5人天 |
| 3 | 实现分批交易 | 1.5人天 |
| 4 | 实现资金曲线管理 | 1.5人天 |
| 合计 | | **5人天** |

---

## 5. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-02-24 | 初始版本 |
