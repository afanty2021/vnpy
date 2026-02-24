# 策略参数优化系统实施方案

> 文档版本：v1.0
> 创建日期：2026-02-24
> 需求编号：REQ-010
> 优先级：P2
> 预计工时：5人天
> 实施周期：1周

---

## 1. 方案概述

### 1.1 项目背景

VeighNa框架已提供基础的参数优化功能（网格搜索、遗传算法），但缺乏更高效的优化算法和完善的过拟合检测机制。本方案通过**扩展vnpy.trader.optimize模块**，添加贝叶斯优化、粒子群优化等高级算法，以及过拟合检测和优化报告功能。

### 1.2 实施原则

**核心原则**：扩展而非替代

- ✅ 保留vnpy.trader.optimize原有功能
- ✅ 扩展新的优化算法
- ✅ 扩展A股交易成本计算
- ✅ 扩展过拟合检测功能
- ✅ 扩展优化报告功能

### 1.3 实施目标

| 目标类别 | 具体目标 | 成功标准 |
|---------|---------|---------|
| 算法扩展 | 添加贝叶斯优化、粒子群优化 | 与现有算法兼容 |
| 过拟合检测 | 样本外测试、前向验证、稳定性分析 | 检测准确率≥80% |
| 优化报告 | 参数排名、敏感性分析、可视化 | 报告完整美观 |
| A股适配 | T+1规则、涨跌停、交易成本 | 符合A股规则 |

### 1.4 交付物清单

| 序号 | 交付物 | 类型 | 说明 |
|------|--------|------|------|
| 1 | vnpy_china_optimize模块 | 代码 | 扩展优化模块 |
| 2 | 单元测试 | 代码 | pytest测试套件 |
| 3 | 使用示例 | 代码 | 示例策略和脚本 |
| 4 | API文档 | 文档 | 接口说明文档 |
| 5 | 实施报告 | 文档 | 开发过程总结 |

---

## 2. 技术架构设计

### 2.1 模块结构

```
vnpy_china_optimize/
├── __init__.py                     # 模块入口
├── base/                           # 基础层
│   ├── __init__.py
│   ├── optimizer.py                # 优化器基类
│   └── result.py                   # 优化结果数据类
├── setting/                        # 设置层
│   ├── __init__.py
│   └── china_setting.py            # A股优化设置
├── algorithms/                     # 算法层
│   ├── __init__.py
│   ├── bayesian.py                 # 贝叶斯优化
│   ├── pso.py                      # 粒子群优化
│   └── grid.py                     # 增强网格搜索
├── overfit/                        # 过拟合检测
│   ├── __init__.py
│   ├── detector.py                 # 检测器基类
│   ├── out_sample.py               # 样本外测试
│   ├── walk_forward.py             # 前向验证
│   └── stability.py                # 稳定性分析
├── report/                         # 报告层
│   ├── __init__.py
│   ├── generator.py                # 报告生成
│   ├── visualizer.py               # 可视化
│   └── exporter.py                 # 导出功能
└── utils/                          # 工具层
    ├── __init__.py
    ├── calculator.py               # 计算工具
    └── validator.py                # 参数验证
```

### 2.2 类图设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      BaseOptimizer                              │
│                      (优化器抽象基类)                            │
├─────────────────────────────────────────────────────────────────┤
│ # objective_func: Callable                                      │
│ # param_space: Dict[str, tuple]                                │
│ # results: List[OptimizationResult]                            │
├─────────────────────────────────────────────────────────────────┤
│ + optimize(n_iterations) -> OptimizationResult                 │
│ + get_best_params() -> Dict                                    │
│ + get_all_results() -> List[OptimizationResult]                │
│ # evaluate(params) -> float                                    │
└─────────────────────────────────────────────────────────────────┘
                              △
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────────────┐   ┌──────────────────┐   ┌─────────────────┐
│Bayesian       │   │PSOOptimizer     │   │GridOptimizer    │
│Optimizer      │   │(粒子群优化)     │   │(增强网格搜索)   │
├───────────────┤   ├──────────────────┤   ├─────────────────┤
│# gp: Gaussian│   │# particles: List │   │# combinations:  │
│  Process      │   │# velocities:    │   │  Iterator       │
│# bounds: List │   │   List          │   │                 │
└───────────────┘   └──────────────────┘   └─────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    OverfitDetector                              │
│                     (过拟合检测器)                               │
├─────────────────────────────────────────────────────────────────┤
│ # backtest_func: Callable                                      │
├─────────────────────────────────────────────────────────────────┤
│ + out_sample_test(...) -> Dict                                 │
│ + walk_forward_validation(...) -> Dict                         │
│ + cross_validation(...) -> Dict                                │
│ + check_stability(...) -> Dict                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                 OptimizationReportGenerator                       │
│                     (优化报告生成器)                             │
├─────────────────────────────────────────────────────────────────┤
│ + generate(results) -> str                                     │
│ + generate_ranking(results) -> DataFrame                       │
│ + generate_sensitivity(results) -> Dict                         │
│ + export_to_excel(filepath) -> None                            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 与vnpy.trader.optimize的关系

```
┌─────────────────────────────────────────────────────────────────┐
│                   vnpy.trader.optimize (原有)                    │
├─────────────────────────────────────────────────────────────────┤
│  • OptimizeSetting: 优化目标设置                                │
│  • generate_optimization_target(): 目标函数生成                 │
│  • optimize(): 遗传算法优化                                    │
│  • 穷举搜索: 完整参数空间                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓ 扩展
┌─────────────────────────────────────────────────────────────────┐
│                 vnpy_china_optimize (本模块)                     │
├─────────────────────────────────────────────────────────────────┤
│  • ChinaOptimizerSetting: A股交易成本/T+1/涨跌停               │
│  • BayesianOptimizer: 贝叶斯优化                                │
│  • PSOOptimizer: 粒子群优化                                    │
│  • OverfitDetector: 过拟合检测                                  │
│  • OptimizationReportGenerator: 优化报告                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 详细实施计划

### 3.1 第一阶段：基础框架搭建（1人天）

#### 任务1.1：创建目录结构

```bash
# 创建模块根目录
mkdir -p vnpy_china_optimize

# 创建子目录
mkdir -p vnpy_china_optimize/base
mkdir -p vnpy_china_optimize/setting
mkdir -p vnpy_china_optimize/algorithms
mkdir -p vnpy_china_optimize/overfit
mkdir -p vnpy_china_optimize/report
mkdir -p vnpy_china_optimize/utils

# 创建测试目录
mkdir -p tests/optimization

# 创建输出目录
mkdir -p optimization/results
mkdir -p optimization/reports
mkdir -p optimization/visualizations
```

#### 任务1.2：定义核心数据模型

**文件位置**：`vnpy_china_optimize/base/result.py`

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum


class OptimizationStatus(Enum):
    """优化状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OptimizationMetrics:
    """优化指标"""
    return_value: float           # 总收益率
    sharpe_ratio: float           # 夏普比率
    max_drawdown: float           # 最大回撤
    calmar_ratio: float = 0.0     # 卡玛比率
    sortino_ratio: float = 0.0    # 索提诺比率
    win_rate: float = 0.0         # 胜率
    profit_loss_ratio: float = 0.0  # 盈亏比
    total_trades: int = 0         # 总交易次数
    avg_trade_return: float = 0.0  # 平均每笔收益


@dataclass
class OptimizationResult:
    """单次优化结果"""
    # 参数
    params: Dict[str, Any]

    # 指标
    metrics: OptimizationMetrics

    # 元数据
    status: OptimizationStatus = OptimizationStatus.COMPLETED
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None

    # 样本外测试结果
    out_sample_metrics: Optional[OptimizationMetrics] = None

    @property
    def score(self) -> float:
        """综合评分"""
        # 默认使用夏普比率
        return self.metrics.sharpe_ratio

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "params": self.params,
            "return_value": self.metrics.return_value,
            "sharpe_ratio": self.metrics.sharpe_ratio,
            "max_drawdown": self.metrics.max_drawdown,
            "win_rate": self.metrics.win_rate,
            "total_trades": self.metrics.total_trades,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class OptimizationSummary:
    """优化汇总"""
    # 总体信息
    total_evaluations: int           # 总评估次数
    best_score: float                # 最优分数
    worst_score: float               # 最差分数
    avg_score: float                 # 平均分数

    # 最优参数
    best_params: Dict[str, Any]
    best_metrics: OptimizationMetrics

    # 所有结果
    all_results: List[OptimizationResult] = field(default_factory=list)

    # 收敛信息
    converged: bool = False
    convergence_iteration: int = 0

    def get_top_n(self, n: int = 10) -> List[OptimizationResult]:
        """获取前N个结果"""
        return sorted(
            self.all_results,
            key=lambda x: x.score,
            reverse=True
        )[:n]

    def get_parameter_ranking(self, param_name: str) -> Dict[Any, float]:
        """获取参数排名"""
        param_scores: Dict[Any, List[float]] = {}

        for result in self.all_results:
            param_value = result.params.get(param_name)
            if param_value not in param_scores:
                param_scores[param_value] = []
            param_scores[param_value].append(result.score)

        # 计算平均分
        return {
            k: sum(v) / len(v) for k, v in param_scores.items()
        }
```

#### 任务1.3：创建优化器基类

**文件位置**：`vnpy_china_optimize/base/optimizer.py`

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime
import numpy as np
from .result import OptimizationResult, OptimizationMetrics, OptimizationSummary, OptimizationStatus


class BaseOptimizer(ABC):
    """
    优化器基类

    所有优化算法应继承此类。
    """

    def __init__(
        self,
        objective_func: Callable[[Dict[str, Any]], float],
        param_space: Dict[str, tuple],
        maximize: bool = True
    ) -> None:
        """
        初始化优化器

        Args:
            objective_func: 目标函数，输入参数字典，返回分数
            param_space: 参数空间 {param_name: (min, max)}
            maximize: 是否最大化目标函数
        """
        self.objective_func = objective_func
        self.param_space = param_space
        self.maximize = maximize

        # 参数名称和边界
        self.param_names = list(param_space.keys())
        self.bounds = [param_space[name] for name in self.param_names]

        # 结果存储
        self.results: List[OptimizationResult] = []
        self.evaluation_count: int = 0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    @abstractmethod
    def optimize(
        self,
        n_iterations: int = 100,
        **kwargs
    ) -> OptimizationSummary:
        """
        执行优化

        Args:
            n_iterations: 迭代次数
            **kwargs: 其他算法特定参数

        Returns:
            OptimizationSummary对象
        """
        pass

    def evaluate(self, params: Dict[str, Any]) -> float:
        """
        评估参数组合

        Args:
            params: 参数字典

        Returns:
            目标函数值
        """
        self.evaluation_count += 1
        score = self.objective_func(params)

        if not self.maximize:
            score = -score

        return score

    def _create_result(
        self,
        params: Dict[str, Any],
        metrics: OptimizationMetrics
    ) -> OptimizationResult:
        """创建优化结果"""
        return OptimizationResult(
            params=params,
            metrics=metrics,
            timestamp=datetime.now()
        )

    def get_summary(self) -> OptimizationSummary:
        """获取优化汇总"""
        if not self.results:
            return OptimizationSummary(
                total_evaluations=0,
                best_score=0.0,
                worst_score=0.0,
                avg_score=0.0,
                best_params={},
                best_metrics=OptimizationMetrics(
                    return_value=0.0,
                    sharpe_ratio=0.0,
                    max_drawdown=0.0
                )
            )

        # 排序结果
        sorted_results = sorted(
            self.results,
            key=lambda x: x.score,
            reverse=True
        )

        best = sorted_results[0]

        return OptimizationSummary(
            total_evaluations=self.evaluation_count,
            best_score=best.score,
            worst_score=sorted_results[-1].score,
            avg_score=sum(r.score for r in self.results) / len(self.results),
            best_params=best.params,
            best_metrics=best.metrics,
            all_results=self.results
        )

    def _params_to_array(self, params: Dict[str, Any]) -> np.ndarray:
        """参数字典转数组"""
        return np.array([params[name] for name in self.param_names])

    def _array_to_params(self, array: np.ndarray) -> Dict[str, Any]:
        """数组转参数字典"""
        return {
            name: array[i]
            for i, name in enumerate(self.param_names)
        }

    def _validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数是否在有效范围内"""
        for name, value in params.items():
            if name not in self.param_space:
                continue
            low, high = self.param_space[name]
            if not (low <= value <= high):
                return False
        return True

    def _random_params(self) -> Dict[str, Any]:
        """生成随机参数"""
        return {
            name: np.random.uniform(low, high)
            for name, (low, high) in self.param_space.items()
        }
```

**验收标准**：
- [ ] 目录结构完整
- [ ] 数据类定义完整
- [ ] 基类接口清晰
- [ ] 通过类型检查

---

### 3.2 第二阶段：A股优化设置（0.5人天）

#### 任务2.1：A股优化设置类

**文件位置**：`vnpy_china_optimize/setting/china_setting.py`

```python
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from vnpy.trader.optimize import OptimizeSetting
from vnpy_ctastrategy.backtesting import BacktestingEngine
from vnpy_ctabacktester import BacktesterEngine


@dataclass
class ChinaTradingCost:
    """A股交易成本配置"""
    commission_rate: float = 0.0003      # 万3佣金
    min_commission: float = 5.0           # 最低5元
    stamp_duty: float = 0.001             # 印花税0.1%（仅卖出）
    transfer_fee: float = 0.00001         # 过户费0.001%
    handling_fee: float = 0.00000685      # 经手费0.000685%
    slippage: float = 0.0                 # 滑点（可配置）

    def calculate_buy_cost(self, price: float, volume: int) -> float:
        """
        计算买入成本

        Args:
            price: 买入价格
            volume: 买入数量（手）

        Returns:
            总成本
        """
        amount = price * volume * 100  # 转换为元

        # 佣金
        commission = max(amount * self.commission_rate, self.min_commission)

        # 过户费
        transfer = amount * self.transfer_fee

        # 经手费
        handling = amount * self.handling_fee

        return commission + transfer + handling

    def calculate_sell_cost(self, price: float, volume: int) -> float:
        """
        计算卖出成本

        Args:
            price: 卖出价格
            volume: 卖出数量（手）

        Returns:
            总成本
        """
        amount = price * volume * 100

        # 佣金
        commission = max(amount * self.commission_rate, self.min_commission)

        # 印花税（仅卖出）
        stamp_duty = amount * self.stamp_duty

        # 过户费
        transfer = amount * self.transfer_fee

        # 经手费
        handling = amount * self.handling_fee

        return commission + stamp_duty + transfer + handling


@dataclass
class ChinaOptimizerSetting(OptimizeSetting):
    """
    A股优化设置

    扩展vnpy.trader.optimize.OptimizeSetting，
    添加A股特有的交易规则和成本计算。
    """

    # A股交易成本
    trading_cost: ChinaTradingCost = field(
        default_factory=ChinaTradingCost
    )

    # T+1规则
    enable_t1_rule: bool = True

    # 涨跌停规则
    enable_price_limit: bool = True
    price_limit_ratio: float = 0.1  # 默认10%（主板）

    # 最小交易单位
    min_volume: int = 100  # 1手 = 100股

    # 回测引擎类型
    engine_type: str = "backtesting"  # backtesting或ctabacktester

    def generate_target_function(
        self,
        strategy_class: type,
        vt_symbol: str,
        interval: str,
        start_date: str,
        end_date: str,
        rate: float = 0.0,
        slippage: float = 0.0,
        inverse: bool = False
    ) -> Callable[[Dict[str, Any]], float]:
        """
        生成优化目标函数

        覆盖父类方法，添加A股交易成本计算。

        Args:
            strategy_class: 策略类
            vt_symbol: 交易标的
            interval: K线周期
            start_date: 回测开始日期
            end_date: 回测结束日期
            rate: 手续费率（已弃用，使用trading_cost）
            slippage: 滑点（已弃用，使用trading_cost）
            inverse: 是否反向

        Returns:
            目标函数
        """

        def target_function(params: Dict[str, Any]) -> float:
            """目标函数"""
            # 创建回测引擎
            if self.engine_type == "backtesting":
                engine = BacktestingEngine()
            else:
                engine = BacktesterEngine()

            # 设置交易成本
            engine.set_parameters(
                slippage=self.trading_cost.slippage
            )

            # 添加交易手续费
            # 注意：这里需要根据具体引擎设置手续费计算方式

            # 初始化策略
            strategy = strategy_class()
            strategy.set_parameters(params)

            # 添加策略
            engine.add_strategy(strategy)

            # 运行回测
            engine.run_backtesting()

            # 计算优化目标
            result = engine.calculate_result()

            # 默认使用夏普比率
            return result.get("sharpe_ratio", 0.0)

        return target_function

    def to_setting(self) -> OptimizeSetting:
        """转换为父类OptimizeSetting"""
        return OptimizeSetting(
            target_name=self.target_name,
            optimization_direction=self.optimization_direction
        )
```

**验收标准**：
- [ ] 继承OptimizeSetting
- [ ] A股交易成本计算正确
- [ ] T+1规则支持
- [ ] 涨跌停规则支持

---

### 3.3 第三阶段：贝叶斯优化器实现（1人天）

#### 任务3.1：贝叶斯优化器

**文件位置**：`vnpy_china_optimize/algorithms/bayesian.py`

```python
from typing import List, Dict, Any, Optional, Callable
import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, Matern
from ..base.optimizer import BaseOptimizer
from ..base.result import OptimizationSummary, OptimizationResult, OptimizationMetrics


class BayesianOptimizer(BaseOptimizer):
    """
    贝叶斯优化器

    使用高斯过程作为代理模型，
    通过期望改进（EI）采集函数进行高效优化。

    适用场景：目标函数计算成本高的黑盒优化。
    """

    def __init__(
        self,
        objective_func: Callable[[Dict[str, Any]], float],
        param_space: Dict[str, tuple],
        n_initial: int = 10,
        kernel: str = "rbf",
        alpha: float = 1e-6,
        random_state: int = None
    ) -> None:
        """
        初始化贝叶斯优化器

        Args:
            objective_func: 目标函数
            param_space: 参数空间
            n_initial: 初始随机采样次数
            kernel: 核函数类型 ("rbf", "matern")
            alpha: 高斯过程噪声参数
            random_state: 随机种子
        """
        super().__init__(objective_func, param_space)

        self.n_initial = n_initial
        self.alpha = alpha
        self.random_state = random_state

        if random_state is not None:
            np.random.seed(random_state)

        # 观测数据
        self.X_observed: List[np.ndarray] = []
        self.y_observed: List[float] = []

        # 高斯过程代理模型
        if kernel == "matern":
            gp_kernel = ConstantKernel(1.0) * Matern(
                length_scale=1.0,
                nu=2.5
            )
        else:
            gp_kernel = ConstantKernel(1.0) * RBF(length_scale=1.0)

        self.gp = GaussianProcessRegressor(
            kernel=gp_kernel,
            alpha=alpha,
            normalize_y=True,
            n_restarts_optimizer=5
        )

    def optimize(
        self,
        n_iterations: int = 100,
        verbose: bool = False,
        **kwargs
    ) -> OptimizationSummary:
        """
        执行贝叶斯优化

        Args:
            n_iterations: 总迭代次数
            verbose: 是否打印进度

        Returns:
            OptimizationSummary对象
        """
        self.start_time = datetime.now()
        self.results = []
        self.evaluation_count = 0

        # 阶段1: 随机采样初始化
        if verbose:
            print(f"初始化：随机采样 {self.n_initial} 次")

        for i in range(self.n_initial):
            x = self._random_sample()
            x_dict = self._array_to_params(x)
            y = self.evaluate(x_dict)

            self.X_observed.append(x)
            self.y_observed.append(y)

            if verbose and (i + 1) % 5 == 0:
                print(f"  已完成 {i + 1}/{self.n_initial} 次初始化采样")

        # 阶段2: 贝叶斯优化迭代
        n_bayesian_iterations = n_iterations - self.n_initial

        if verbose:
            print(f"贝叶斯优化：迭代 {n_bayesian_iterations} 次")

        for i in range(n_bayesian_iterations):
            # 找到最优采样点
            x_next = self._propose_location()

            # 评估目标函数
            x_dict = self._array_to_params(x_next)
            y = self.evaluate(x_dict)

            # 更新观测数据
            self.X_observed.append(x_next)
            self.y_observed.append(y)

            # 记录结果
            self._record_result(x_dict, y)

            if verbose and (i + 1) % 10 == 0:
                best_y = max(self.y_observed)
                print(f"  迭代 {i + 1}/{n_bayesian_iterations}, "
                      f"当前最优: {best_y:.4f}")

        self.end_time = datetime.now()

        return self.get_summary()

    def _random_sample(self) -> np.ndarray:
        """随机采样"""
        return np.array([
            np.random.uniform(low, high)
            for low, high in self.bounds
        ])

    def _propose_location(self) -> np.ndarray:
        """
        提出下一个采样位置

        通过优化采集函数找到最有希望的采样点。
        """
        # 需要至少有一个观测点
        if len(self.X_observed) == 0:
            return self._random_sample()

        # 优化采集函数
        result = minimize(
            self._acquisition_function,
            x0=self.X_observed[-1],  # 从最后一个点开始
            bounds=self.bounds,
            method='L-BFGS-B'
        )

        return result.x

    def _acquisition_function(self, X: np.ndarray) -> float:
        """
        采集函数（Expected Improvement）

        Args:
            X: 候选采样点

        Returns:
            采集函数值（负值，用于最小化）
        """
        # 确保X是2D数组
        if X.ndim == 1:
            X = X.reshape(1, -1)

        # 拟合高斯过程
        X_array = np.array(self.X_observed)
        y_array = np.array(self.y_observed)
        self.gp.fit(X_array, y_array)

        # 预测均值和标准差
        mu, sigma = self.gp.predict(X, return_std=True)

        # 当前最优值
        best_y = max(self.y_observed) if self.y_observed else 0

        # 避免除零
        sigma = max(sigma[0], 1e-6)

        # 期望改进
        z = (mu[0] - best_y) / sigma
        ei = (mu[0] - best_y) * norm.cdf(z) + sigma * norm.pdf(z)

        return -ei  # 返回负值用于最小化

    def _record_result(self, params: Dict[str, Any], score: float) -> None:
        """记录优化结果"""
        # 这里需要调用目标函数获取完整的回测指标
        # 为简化，先创建基础指标
        metrics = OptimizationMetrics(
            return_value=score,  # 使用score作为收益率
            sharpe_ratio=score,
            max_drawdown=0.0,
            win_rate=0.5
        )

        result = OptimizationResult(
            params=params,
            metrics=metrics,
            timestamp=datetime.now()
        )

        self.results.append(result)

    def get_surrogate_model(self) -> GaussianProcessRegressor:
        """获取代理模型"""
        return self.gp

    def predict(self, X: np.ndarray) -> tuple:
        """
        使用代理模型预测

        Args:
            X: 输入点

        Returns:
            (均值, 标准差)
        """
        if len(self.X_observed) == 0:
            return 0.0, 1.0

        X_array = np.array(self.X_observed)
        y_array = np.array(self.y_observed)
        self.gp.fit(X_array, y_array)

        return self.gp.predict(X.reshape(1, -1), return_std=True)
```

#### 任务3.2：贝叶斯优化器测试

```python
# tests/optimization/test_bayesian.py
import pytest
import numpy as np
from vnpy_china_optimize.algorithms.bayesian import BayesianOptimizer


def test_bayesian_optimizer():
    """测试贝叶斯优化器"""

    # 定义目标函数（简单的二次函数）
    def objective(params: dict) -> float:
        x = params["x"]
        y = params["y"]
        # 最优解在 x=2, y=-3，最大值为 20
        return -(x - 2) ** 2 - (y + 3) ** 2 + 20

    # 参数空间
    param_space = {
        "x": (-10, 10),
        "y": (-10, 10)
    }

    # 创建优化器
    optimizer = BayesianOptimizer(
        objective_func=objective,
        param_space=param_space,
        n_initial=5,
        random_state=42
    )

    # 执行优化
    summary = optimizer.optimize(n_iterations=20)

    # 验证结果
    assert summary.total_evaluations == 20
    assert len(summary.all_results) > 0

    # 最优参数应该接近 (2, -3)
    best_params = summary.best_params
    assert abs(best_params["x"] - 2) < 2  # 允许一定误差
    assert abs(best_params["y"] - (-3)) < 2
    assert summary.best_score > 15  # 应该接近最优值20


def test_bayesian_optimizer_convergence():
    """测试收敛性"""
    def objective(params: dict) -> float:
        x = params["x"]
        return -np.sin(x)  # 最大值在 x=π/2

    param_space = {"x": (0, 6)}

    optimizer = BayesianOptimizer(
        objective_func=objective,
        param_space=param_space,
        n_initial=5,
        random_state=42
    )

    summary = optimizer.optimize(n_iterations=30)

    # 最优解应该接近 π/2 ≈ 1.57
    assert abs(summary.best_params["x"] - 1.57) < 0.5
```

**验收标准**：
- [ ] 贝叶斯优化算法正确实现
- [ ] 高斯过程拟合正常
- [ ] 采集函数计算正确
- [ ] 测试用例通过

---

### 3.4 第四阶段：粒子群优化器实现（1人天）

#### 任务4.1：粒子群优化器

**文件位置**：`vnpy_china_optimize/algorithms/pso.py`

```python
from typing import List, Dict, Any, Callable
import numpy as np
from ..base.optimizer import BaseOptimizer
from ..base.result import OptimizationSummary


class PSOOptimizer(BaseOptimizer):
    """
    粒子群优化器（Particle Swarm Optimization）

    模拟鸟群觅食行为的优化算法，
    适合连续参数空间的优化问题。

    算法参数：
    - w: 惯性权重（控制历史速度的影响）
    - c1: 认知系数（个体最优的影响）
    - c2: 社会系数（全局最优的影响）
    """

    def __init__(
        self,
        objective_func: Callable[[Dict[str, Any]], float],
        param_space: Dict[str, tuple],
        population_size: int = 30,
        max_iterations: int = 100,
        w: float = 0.7,            # 惯性权重
        c1: float = 1.5,           # 认知系数
        c2: float = 1.5,           # 社会系数
        w_decay: bool = True,      # 惯性权重衰减
        random_state: int = None
    ) -> None:
        """
        初始化粒子群优化器

        Args:
            objective_func: 目标函数
            param_space: 参数空间
            population_size: 粒子数量
            max_iterations: 最大迭代次数
            w: 惯性权重
            c1: 认知系数
            c2: 社会系数
            w_decay: 是否衰减惯性权重
            random_state: 随机种子
        """
        super().__init__(objective_func, param_space)

        self.population_size = population_size
        self.max_iterations = max_iterations
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.w_decay = w_decay

        if random_state is not None:
            np.random.seed(random_state)

        # 粒子群
        self.particles: np.ndarray = None
        self.velocities: np.ndarray = None

        # 个体最优和全局最优
        self.pbest_positions: np.ndarray = None
        self.pbest_scores: np.ndarray = None
        self.gbest_position: np.ndarray = None
        self.gbest_score: float = -np.inf

    def optimize(
        self,
        n_iterations: int = None,
        verbose: bool = False,
        **kwargs
    ) -> OptimizationSummary:
        """
        执行粒子群优化

        Args:
            n_iterations: 迭代次数
            verbose: 是否打印进度

        Returns:
            OptimizationSummary对象
        """
        n_iterations = n_iterations or self.max_iterations

        self.start_time = datetime.now()
        self.results = []
        self.evaluation_count = 0

        # 初始化粒子群
        self._initialize_particles()

        if verbose:
            print(f"粒子群优化开始：粒子数={self.population_size}, "
                  f"迭代次数={n_iterations}")

        for iteration in range(n_iterations):
            # 更新惯性权重（线性衰减）
            if self.w_decay:
                w = self.w * (1 - iteration / n_iterations)
                w = max(0.4, w)  # 最小值0.4
            else:
                w = self.w

            # 更新每个粒子
            for i in range(self.population_size):
                # 更新速度
                r1, r2 = np.random.rand(2)
                cognitive = self.c1 * r1 * (self.pbest_positions[i] - self.particles[i])
                social = self.c2 * r2 * (self.gbest_position - self.particles[i])
                self.velocities[i] = w * self.velocities[i] + cognitive + social

                # 更新位置
                self.particles[i] += self.velocities[i]

                # 边界处理
                self._clip_particle(i)

                # 评估适应度
                params_dict = self._array_to_params(self.particles[i])
                score = self.evaluate(params_dict)

                # 更新个体最优
                if score > self.pbest_scores[i]:
                    self.pbest_positions[i] = self.particles[i].copy()
                    self.pbest_scores[i] = score

                    # 更新全局最优
                    if score > self.gbest_score:
                        self.gbest_position = self.particles[i].copy()
                        self.gbest_score = score

            if verbose and (iteration + 1) % 10 == 0:
                print(f"  迭代 {iteration + 1}/{n_iterations}, "
                      f"最优分数: {self.gbest_score:.4f}")

        self.end_time = datetime.now()

        return self.get_summary()

    def _initialize_particles(self) -> None:
        """初始化粒子群"""
        n_params = len(self.param_names)

        # 初始化粒子位置（随机分布）
        self.particles = np.array([
            [np.random.uniform(low, high) for low, high in self.bounds]
            for _ in range(self.population_size)
        ])

        # 初始化速度（随机小值）
        self.velocities = np.random.uniform(
            -1, 1,
            (self.population_size, n_params)
        ) * 0.1

        # 初始化个体最优
        self.pbest_positions = self.particles.copy()
        self.pbest_scores = np.full(self.population_size, -np.inf)

        # 评估初始适应度并更新最优
        for i in range(self.population_size):
            params_dict = self._array_to_params(self.particles[i])
            score = self.evaluate(params_dict)
            self.pbest_scores[i] = score

            if score > self.gbest_score:
                self.gbest_position = self.particles[i].copy()
                self.gbest_score = score

    def _clip_particle(self, i: int) -> None:
        """将粒子限制在边界内"""
        for j, (low, high) in enumerate(self.bounds):
            if self.particles[i, j] < low:
                self.particles[i, j] = low
                self.velocities[i, j] *= -0.5  # 反弹
            elif self.particles[i, j] > high:
                self.particles[i, j] = high
                self.velocities[i, j] *= -0.5  # 反弹

    def get_swarm_diversity(self) -> float:
        """获取粒子群多样性"""
        if self.particles is None:
            return 0.0

        # 计算粒子间的平均距离
        distances = []
        for i in range(self.population_size):
            for j in range(i + 1, self.population_size):
                dist = np.linalg.norm(self.particles[i] - self.particles[j])
                distances.append(dist)

        return np.mean(distances) if distances else 0.0

    def get_convergence_info(self) -> Dict[str, Any]:
        """获取收敛信息"""
        return {
            "gbest_score": self.gbest_score,
            "gbest_position": self._array_to_params(self.gbest_position),
            "swarm_diversity": self.get_swarm_diversity(),
            "pbest_std": np.std(self.pbest_scores) if len(self.pbest_scores) > 0 else 0.0
        }
```

#### 任务4.2：PSO测试

```python
# tests/optimization/test_pso.py
import pytest
import numpy as np
from vnpy_china_optimize.algorithms.pso import PSOOptimizer


def test_pso_optimizer():
    """测试粒子群优化器"""

    # Rastrigin函数（多峰优化测试函数）
    def rastrigin(params: dict) -> float:
        A = 10
        x = params["x"]
        y = params["y"]
        return -A * 2 - (x**2 - A * np.cos(2 * np.pi * x)) - (y**2 - A * np.cos(2 * np.pi * y))

    param_space = {
        "x": (-5.12, 5.12),
        "y": (-5.12, 5.12)
    }

    optimizer = PSOOptimizer(
        objective_func=rastrigin,
        param_space=param_space,
        population_size=30,
        random_state=42
    )

    summary = optimizer.optimize(n_iterations=50)

    # 验证结果
    assert summary.total_evaluations > 0
    # 最优解应该在 (0, 0) 附近
    assert abs(summary.best_params["x"]) < 1
    assert abs(summary.best_params["y"]) < 1


def test_pso_convergence():
    """测试PSO收敛性"""
    def sphere(params: dict) -> float:
        x = params["x"]
        y = params["y"]
        return -(x**2 + y**2)  # 最大值在 (0, 0)

    param_space = {"x": (-10, 10), "y": (-10, 10)}

    optimizer = PSOOptimizer(
        objective_func=sphere,
        param_space=param_space,
        population_size=20,
        random_state=42
    )

    summary = optimizer.optimize(n_iterations=100)

    # 应该收敛到 (0, 0) 附近
    assert abs(summary.best_params["x"]) < 0.5
    assert abs(summary.best_params["y"]) < 0.5
```

**验收标准**：
- [ ] PSO算法正确实现
- [ ] 惯性权重衰减正常
- [ ] 边界处理正确
- [ ] 测试用例通过

---

### 3.5 第五阶段：过拟合检测实现（1人天）

#### 任务5.1：过拟合检测器

**文件位置**：`vnpy_china_optimize/overfit/detector.py`

```python
from typing import Dict, Any, List, Callable, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass
import numpy as np
from ..base.result import OptimizationMetrics


@dataclass
class OverfitTestResult:
    """过拟合测试结果"""
    # 测试类型
    test_type: str  # "out_sample", "walk_forward", "stability"

    # 训练集指标
    train_return: float
    train_sharpe: float

    # 测试集指标
    test_return: float
    test_sharpe: float

    # 衰减比率
    return_decay: float      # 收益率衰减
    sharpe_decay: float      # 夏普比率衰减

    # 稳定性指标
    stability_score: float   # 稳定性评分

    # 判断结果
    is_overfit: bool         # 是否过拟合
    risk_level: str          # 风险等级: "low", "medium", "high"

    def to_dict(self) -> Dict:
        return {
            "test_type": self.test_type,
            "train_return": self.train_return,
            "train_sharpe": self.train_sharpe,
            "test_return": self.test_return,
            "test_sharpe": self.test_sharpe,
            "return_decay": self.return_decay,
            "sharpe_decay": self.sharpe_decay,
            "stability_score": self.stability_score,
            "is_overfit": self.is_overfit,
            "risk_level": self.risk_level
        }


class OverfitDetector:
    """
    过拟合检测器

    通过样本外测试、前向验证等方法，
    检测参数优化是否存在过拟合问题。
    """

    def __init__(
        self,
        backtest_func: Callable[[Dict[str, Any], Tuple],
        decay_threshold: float = 0.5,
        stability_threshold: float = 0.5
    ) -> None:
        """
        初始化过拟合检测器

        Args:
            backtest_func: 回测函数，输入参数和日期范围，返回回测指标
            decay_threshold: 衰减阈值（低于此值认为过拟合）
            stability_threshold: 稳定性阈值
        """
        self.backtest_func = backtest_func
        self.decay_threshold = decay_threshold
        self.stability_threshold = stability_threshold

    def out_sample_test(
        self,
        params: Dict[str, Any],
        train_start: str,
        train_end: str,
        test_start: str,
        test_end: str
    ) -> OverfitTestResult:
        """
        样本外测试

        将数据分为训练集和测试集，在训练集上优化参数，
        在测试集上验证性能。

        Args:
            params: 待测试参数
            train_start: 训练集开始日期
            train_end: 训练集结束日期
            test_start: 测试集开始日期
            test_end: 测试集结束日期

        Returns:
            OverfitTestResult对象
        """
        # 训练集回测
        train_metrics = self._run_backtest(
            params, train_start, train_end
        )

        # 测试集回测
        test_metrics = self._run_backtest(
            params, test_start, test_end
        )

        # 计算衰减比率
        return_decay = self._calculate_decay(
            train_metrics.return_value,
            test_metrics.return_value
        )
        sharpe_decay = self._calculate_decay(
            train_metrics.sharpe_ratio,
            test_metrics.sharpe_ratio
        )

        # 判断过拟合
        is_overfit = return_decay < self.decay_threshold

        # 评估风险等级
        risk_level = self._assess_risk_level(return_decay, sharpe_decay)

        return OverfitTestResult(
            test_type="out_sample",
            train_return=train_metrics.return_value,
            train_sharpe=train_metrics.sharpe_ratio,
            test_return=test_metrics.return_value,
            test_sharpe=test_metrics.sharpe_ratio,
            return_decay=return_decay,
            sharpe_decay=sharpe_decay,
            stability_score=0.0,  # 样本外测试不计算稳定性
            is_overfit=is_overfit,
            risk_level=risk_level
        )

    def walk_forward_validation(
        self,
        params: Dict[str, Any],
        start_date: str,
        end_date: str,
        train_days: int = 252,    # 训练窗口：1年
        test_days: int = 63,      # 测试窗口：3个月
        step_days: int = 21       # 步长：1个月
    ) -> OverfitTestResult:
        """
        前向验证

        滚动窗口验证，更接近实盘情况。

        Args:
            params: 待测试参数
            start_date: 开始日期
            end_date: 结束日期
            train_days: 训练窗口天数
            test_days: 测试窗口天数
            step_days: 滚动步长

        Returns:
            OverfitTestResult对象
        """
        # 转换日期为数值
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        # 执行前向验证
        test_returns = []
        test_sharpes = []
        current_date = start

        while True:
            train_start = current_date
            train_end = train_start + timedelta(days=train_days)

            test_start = train_end + timedelta(days=1)
            test_end = test_start + timedelta(days=test_days)

            # 检查是否超出范围
            if test_end > end:
                break

            # 执行测试集回测
            test_metrics = self._run_backtest(
                params,
                test_start.strftime("%Y-%m-%d"),
                test_end.strftime("%Y-%m-%d")
            )

            test_returns.append(test_metrics.return_value)
            test_sharpes.append(test_metrics.sharpe_ratio)

            # 滚动窗口
            current_date = test_start + timedelta(days=step_days)

        # 计算统计量
        if not test_returns:
            return self._empty_result("walk_forward")

        avg_return = np.mean(test_returns)
        std_return = np.std(test_returns)
        avg_sharpe = np.mean(test_sharpes)
        std_sharpe = np.std(test_sharpes)

        # 稳定性评分（变异系数的倒数）
        stability_score = 1.0 / (1.0 + std_return / (abs(avg_return) + 1e-6))

        # 使用第一次窗口作为"训练"
        train_return = test_returns[0] if test_returns else 0.0
        train_sharpe = test_sharpes[0] if test_sharpes else 0.0

        return_decay = self._calculate_decay(train_return, avg_return)
        sharpe_decay = self._calculate_decay(train_sharpe, avg_sharpe)

        # 判断过拟合（基于稳定性）
        is_overfit = stability_score < (1 - self.stability_threshold)

        return OverfitTestResult(
            test_type="walk_forward",
            train_return=train_return,
            train_sharpe=train_sharpe,
            test_return=avg_return,
            test_sharpe=avg_sharpe,
            return_decay=return_decay,
            sharpe_decay=sharpe_decay,
            stability_score=stability_score,
            is_overfit=is_overfit,
            risk_level=self._assess_risk_level(return_decay, sharpe_decay, stability_score)
        )

    def cross_validation(
        self,
        params: Dict[str, Any],
        data: List,
        n_folds: int = 5
    ) -> OverfitTestResult:
        """
        K折交叉验证

        Args:
            params: 待测试参数
            data: 数据列表
            n_folds: 折数

        Returns:
            OverfitTestResult对象
        """
        fold_size = len(data) // n_folds
        fold_returns = []
        fold_sharpes = []

        for i in range(n_folds):
            # 划分训练集和验证集
            test_start = i * fold_size
            test_end = (i + 1) * fold_size if i < n_folds - 1 else len(data)

            train_data = data[:test_start] + data[test_end:]
            test_data = data[test_start:test_end]

            # 执行回测
            # 这里需要实现数据分割的逻辑
            # test_metrics = self._run_backtest_with_data(params, test_data)

            # fold_returns.append(test_metrics.return_value)
            # fold_sharpes.append(test_metrics.sharpe_ratio)
            pass

        # 计算统计量（类似前向验证）
        # ...

        return self._empty_result("cross_validation")

    def check_stability(
        self,
        params_list: List[Dict[str, Any]],
        start_date: str,
        end_date: str,
        tolerance: float = 0.1
    ) -> Dict[str, Any]:
        """
        参数稳定性分析

        测试相似参数是否产生相似结果。

        Args:
            params_list: 参数列表
            start_date: 回测开始日期
            end_date: 回测结束日期
            tolerance: 容差

        Returns:
            稳定性分析结果
        """
        results = []

        for params in params_list:
            metrics = self._run_backtest(params, start_date, end_date)
            results.append({
                "params": params,
                "return": metrics.return_value,
                "sharpe": metrics.sharpe_ratio
            })

        if not results:
            return {"is_stable": False, "variance": 0.0}

        # 计算方差
        returns = [r["return"] for r in results]
        variance = np.var(returns)
        mean_return = np.mean(returns)

        # 变异系数
        cv = np.sqrt(variance) / (abs(mean_return) + 1e-6)

        # 判断稳定性
        is_stable = cv < tolerance

        return {
            "is_stable": is_stable,
            "variance": variance,
            "coefficient_of_variation": cv,
            "mean_return": mean_return,
            "return_range": (min(returns), max(returns))
        }

    def _run_backtest(
        self,
        params: Dict[str, Any],
        start_date: str,
        end_date: str
    ) -> OptimizationMetrics:
        """运行回测"""
        # 调用回测函数
        result = self.backtest_func(params, start_date, end_date)

        # 转换为OptimizationMetrics
        if isinstance(result, tuple):
            return result[0]  # 假设第一个是指标
        elif isinstance(result, dict):
            return OptimizationMetrics(
                return_value=result.get("return_value", 0.0),
                sharpe_ratio=result.get("sharpe_ratio", 0.0),
                max_drawdown=result.get("max_drawdown", 0.0),
                win_rate=result.get("win_rate", 0.0)
            )
        else:
            return result

    def _calculate_decay(self, train_value: float, test_value: float) -> float:
        """计算衰减比率"""
        if train_value == 0:
            return 0.0
        return test_value / train_value if train_value != 0 else 0.0

    def _assess_risk_level(
        self,
        return_decay: float,
        sharpe_decay: float,
        stability: float = 1.0
    ) -> str:
        """评估风险等级"""
        avg_decay = (return_decay + sharpe_decay) / 2

        if avg_decay < 0.3 or stability < 0.3:
            return "high"
        elif avg_decay < 0.6 or stability < 0.6:
            return "medium"
        else:
            return "low"

    def _empty_result(self, test_type: str) -> OverfitTestResult:
        """返回空结果"""
        return OverfitTestResult(
            test_type=test_type,
            train_return=0.0,
            train_sharpe=0.0,
            test_return=0.0,
            test_sharpe=0.0,
            return_decay=0.0,
            sharpe_decay=0.0,
            stability_score=0.0,
            is_overfit=False,
            risk_level="unknown"
        )
```

**验收标准**：
- [ ] 样本外测试正确
- [ ] 前向验证实现
- [ ] 稳定性分析有效
- [ ] 测试用例通过

---

### 3.6 第六阶段：优化报告实现（1人天）

#### 任务6.1：报告生成器

**文件位置**：`vnpy_china_optimize/report/generator.py`

```python
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from ..base.result import OptimizationSummary, OptimizationResult
from ..overfit.detector import OverfitTestResult


class OptimizationReportGenerator:
    """
    优化报告生成器

    生成包含参数排名、敏感性分析、可视化图表的优化报告。
    """

    def __init__(self):
        """初始化"""
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False

    def generate(
        self,
        summary: OptimizationSummary,
        overfit_result: Optional[OverfitTestResult] = None
    ) -> str:
        """
        生成文本报告

        Args:
            summary: 优化汇总
            overfit_result: 过拟合测试结果

        Returns:
            报告文本
        """
        report_lines = []

        # 标题
        report_lines.append("=" * 60)
        report_lines.append(" " * 15 + "策略参数优化报告")
        report_lines.append("=" * 60)
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")

        # 1. 优化结果统计
        report_lines.extend(self._generate_summary_section(summary))

        # 2. 最优参数
        report_lines.extend(self._generate_best_params_section(summary))

        # 3. 参数排名
        report_lines.extend(self._generate_ranking_section(summary))

        # 4. 过拟合检测
        if overfit_result:
            report_lines.extend(self._generate_overfit_section(overfit_result))

        # 5. 建议
        report_lines.extend(self._generate_suggestions(summary, overfit_result))

        return "\n".join(report_lines)

    def _generate_summary_section(self, summary: OptimizationSummary) -> List[str]:
        """生成汇总部分"""
        lines = []
        lines.append("一、优化结果统计")
        lines.append("-" * 40)
        lines.append(f"总评估次数: {summary.total_evaluations}")
        lines.append(f"最优分数: {summary.best_score:.4f}")
        lines.append(f"平均分数: {summary.avg_score:.4f}")
        lines.append(f"最差分数: {summary.worst_score:.4f}")
        lines.append("")

        # 最优指标
        m = summary.best_metrics
        lines.append("最优参数指标:")
        lines.append(f"  总收益率: {m.return_value:.2%}")
        lines.append(f"  夏普比率: {m.sharpe_ratio:.2f}")
        lines.append(f"  最大回撤: {m.max_drawdown:.2%}")
        lines.append(f"  卡玛比率: {m.calmar_ratio:.2f}")
        lines.append(f"  胜率: {m.win_rate:.2%}")
        lines.append(f"  盈亏比: {m.profit_loss_ratio:.2f}")
        lines.append("")

        return lines

    def _generate_best_params_section(self, summary: OptimizationSummary) -> List[str]:
        """生成最优参数部分"""
        lines = []
        lines.append("二、最优参数")
        lines.append("-" * 40)

        for param, value in summary.best_params.items():
            lines.append(f"{param}: {value}")

        lines.append("")
        return lines

    def _generate_ranking_section(self, summary: OptimizationSummary, top_n: int = 10) -> List[str]:
        """生成参数排名部分"""
        lines = []
        lines.append("三、参数排名 (Top 10)")
        lines.append("-" * 40)

        top_results = summary.get_top_n(top_n)

        lines.append(f"{'排名':<6} {'收益率':<10} {'夏普':<8} {'回撤':<10} {'参数'}")
        lines.append("-" * 60)

        for i, result in enumerate(top_results, 1):
            params_str = ", ".join([f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
                                      for k, v in result.params.items()])
            lines.append(
                f"{i:<6} "
                f"{result.metrics.return_value:>8.2%}  "
                f"{result.metrics.sharpe_ratio:>6.2f}  "
                f"{result.metrics.max_drawdown:>8.2%}  "
                f"{params_str[:30]}"
            )

        lines.append("")
        return lines

    def _generate_overfit_section(self, result: OverfitTestResult) -> List[str]:
        """生成过拟合检测部分"""
        lines = []
        lines.append("四、过拟合检测")
        lines.append("-" * 40)
        lines.append(f"测试类型: {result.test_type}")
        lines.append("")

        lines.append("收益率对比:")
        lines.append(f"  训练集: {result.train_return:.2%}")
        lines.append(f"  测试集: {result.test_return:.2%}")
        lines.append(f"  衰减率: {result.return_decay:.2%}")
        lines.append("")

        lines.append("夏普比率对比:")
        lines.append(f"  训练集: {result.train_sharpe:.2f}")
        lines.append(f"  测试集: {result.test_sharpe:.2f}")
        lines.append(f"  衰减率: {result.sharpe_decay:.2%}")
        lines.append("")

        if result.stability_score > 0:
            lines.append(f"稳定性评分: {result.stability_score:.2f}")
            lines.append("")

        lines.append(f"过拟合风险: {result.is_overfit}")
        lines.append(f"风险等级: {result.risk_level}")
        lines.append("")

        return lines

    def _generate_suggestions(
        self,
        summary: OptimizationSummary,
        overfit_result: Optional[OverfitTestResult]
    ) -> List[str]:
        """生成建议部分"""
        lines = []
        lines.append("五、优化建议")
        lines.append("-" * 40)

        suggestions = []

        # 基于过拟合检测的建议
        if overfit_result:
            if overfit_result.is_overfit:
                suggestions.append("• 参数存在过拟合风险，建议:")
                suggestions.append("  - 增加训练数据量")
                suggestions.append("  - 减少参数数量或使用正则化")
                suggestions.append("  - 尝试更简单的策略模型")
            else:
                suggestions.append("• 参数过拟合检测通过")

        # 基于稳定性的建议
        if overfit_result and overfit_result.stability_score > 0:
            if overfit_result.stability_score < 0.5:
                suggestions.append("• 参数稳定性较差，建议:")
                suggestions.append("  - 使用前向验证进一步测试")
                suggestions.append("  - 增加样本外测试周期")
            else:
                suggestions.append("• 参数稳定性良好")

        # 基于收敛的建议
        if summary.converged:
            suggestions.append(f"• 算法已收敛于第{summary.convergence_iteration}次迭代")
        else:
            suggestions.append("• 算法未完全收敛，建议:")
            suggestions.append("  - 增加迭代次数")
            suggestions.append("  - 尝试不同的优化算法")

        if not suggestions:
            suggestions.append("• 参数优化完成，建议进行实盘前的小资金测试")

        lines.extend(suggestions)
        lines.append("")
        lines.append("=" * 60)

        return lines

    def generate_ranking_dataframe(self, summary: OptimizationSummary) -> pd.DataFrame:
        """
        生成参数排名DataFrame

        Args:
            summary: 优化汇总

        Returns:
            排名DataFrame
        """
        results_data = []

        for result in summary.all_results:
            row = {
                "收益率": result.metrics.return_value,
                "夏普比率": result.metrics.sharpe_ratio,
                "最大回撤": result.metrics.max_drawdown,
                "卡玛比率": result.metrics.calmar_ratio,
                "胜率": result.metrics.win_rate,
                "盈亏比": result.metrics.profit_loss_ratio,
                "交易次数": result.metrics.total_trades
            }

            # 添加参数列
            for param, value in result.params.items():
                row[param] = value

            results_data.append(row)

        df = pd.DataFrame(results_data)
        df = df.sort_values("收益率", ascending=False)
        df.index = range(1, len(df) + 1)

        return df

    def analyze_sensitivity(
        self,
        summary: OptimizationSummary,
        param_name: str
    ) -> Dict[str, Any]:
        """
        参数敏感性分析

        Args:
            summary: 优化汇总
            param_name: 参数名称

        Returns:
            敏感性分析结果
        """
        if param_name not in summary.best_params:
            return {"error": f"参数 {param_name} 不存在"}

        # 按参数值分组
        param_groups: Dict[Any, List[OptimizationResult]] = {}

        for result in summary.all_results:
            param_value = result.params.get(param_name)
            if param_value not in param_groups:
                param_groups[param_value] = []
            param_groups[param_value].append(result)

        # 计算每组统计量
        sensitivity_data = {}

        for value, results in param_groups.items():
            scores = [r.score for r in results]
            returns = [r.metrics.return_value for r in results]

            sensitivity_data[value] = {
                "count": len(results),
                "avg_score": np.mean(scores),
                "std_score": np.std(scores),
                "avg_return": np.mean(returns),
                "std_return": np.std(returns),
                "min_return": np.min(returns),
                "max_return": np.max(returns)
            }

        # 计算敏感性指标（变异系数）
        all_returns = []
        for data in sensitivity_data.values():
            all_returns.extend([r.metrics.return_value for r in summary.all_results
                                if r.params.get(param_name) == list(sensitivity_data.keys())[list(data.values()).index(data)]])

        cv = np.std(all_returns) / (np.mean(all_returns) + 1e-6) if all_returns else 0

        return {
            "param_name": param_name,
            "sensitivity_coefficient": cv,
            "is_sensitive": cv > 0.5,  # 变异系数>0.5认为敏感
            "data": sensitivity_data
        }

    def export_to_excel(
        self,
        summary: OptimizationSummary,
        filepath: str,
        overfit_result: Optional[OverfitTestResult] = None
    ) -> None:
        """
        导出优化报告到Excel

        Args:
            summary: 优化汇总
            filepath: 输出文件路径
            overfit_result: 过拟合测试结果
        """
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # 1. 参数排名
            ranking_df = self.generate_ranking_dataframe(summary)
            ranking_df.to_excel(writer, sheet_name="参数排名", index=True)

            # 2. 优化汇总
            summary_data = {
                "指标": ["总评估次数", "最优分数", "平均分数", "最差分数"],
                "值": [
                    summary.total_evaluations,
                    summary.best_score,
                    summary.avg_score,
                    summary.worst_score
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name="优化汇总", index=False)

            # 3. 过拟合检测
            if overfit_result:
                overfit_data = {
                    "指标": [
                        "测试类型", "训练收益率", "测试收益率", "衰减率",
                        "训练夏普", "测试夏普", "夏普衰减",
                        "稳定性评分", "过拟合", "风险等级"
                    ],
                    "值": [
                        overfit_result.test_type,
                        f"{overfit_result.train_return:.4f}",
                        f"{overfit_result.test_return:.4f}",
                        f"{overfit_result.return_decay:.4f}",
                        f"{overfit_result.train_sharpe:.4f}",
                        f"{overfit_result.test_sharpe:.4f}",
                        f"{overfit_result.sharpe_decay:.4f}",
                        f"{overfit_result.stability_score:.4f}",
                        overfit_result.is_overfit,
                        overfit_result.risk_level
                    ]
                }
                overfit_df = pd.DataFrame(overfit_data)
                overfit_df.to_excel(writer, sheet_name="过拟合检测", index=False)

    def save_report(
        self,
        report_text: str,
        filepath: str
    ) -> None:
        """保存文本报告"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_text)
```

#### 任务6.2：可视化工具

**文件位置**：`vnpy_china_optimize/report/visualizer.py`

```python
from typing import List, Dict, Any, Optional
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import numpy as np
from ..base.result import OptimizationSummary


class OptimizationVisualizer:
    """
    优化结果可视化工具

    生成各种图表展示优化过程和结果。
    """

    def __init__(self):
        """初始化"""
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
        sns.set_style("whitegrid")

    def plot_optimization_history(
        self,
        scores: List[float],
        filepath: Optional[str] = None
    ) -> None:
        """
        绘制优化历史曲线

        Args:
            scores: 每次迭代的得分
            filepath: 保存路径
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        iterations = range(1, len(scores) + 1)
        ax.plot(iterations, scores, linewidth=2, color='#4472C4', label='得分')

        # 标记最优值
        best_idx = np.argmax(scores)
        best_score = scores[best_idx]
        ax.scatter(best_idx + 1, best_score, color='red', s=100, zorder=5, label='最优')

        ax.set_xlabel('迭代次数', fontsize=12)
        ax.set_ylabel('得分', fontsize=12)
        ax.set_title('优化历史曲线', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if filepath:
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
        else:
            plt.show()

        plt.close()

    def plot_parameter_heatmap(
        self,
        summary: OptimizationSummary,
        param1: str,
        param2: str,
        filepath: Optional[str] = None
    ) -> None:
        """
        绘制参数热力图

        Args:
            summary: 优化汇总
            param1: X轴参数
            param2: Y轴参数
            filepath: 保存路径
        """
        # 提取数据
        data = []
        x_values = set()
        y_values = set()

        for result in summary.all_results:
            p1 = result.params.get(param1)
            p2 = result.params.get(param2)
            if p1 is not None and p2 is not None:
                x_values.add(p1)
                y_values.add(p2)

        # 创建网格
        x_list = sorted(x_values)
        y_list = sorted(y_values)

        # 构建矩阵
        score_matrix = np.full((len(y_list), len(x_list)), np.nan)

        for result in summary.all_results:
            p1 = result.params.get(param1)
            p2 = result.params.get(param2)
            if p1 in x_list and p2 in y_list:
                i = y_list.index(p2)
                j = x_list.index(p1)
                score_matrix[i, j] = result.score

        # 绘制热力图
        fig, ax = plt.subplots(figsize=(12, 8))

        im = ax.imshow(score_matrix, cmap='RdYlGn', aspect='auto', origin='lower')
        ax.set_xticks(range(len(x_list)))
        ax.set_yticks(range(len(y_list)))
        ax.set_xticklabels([f"{v:.2f}" for v in x_list], rotation=45)
        ax.set_yticklabels([f"{v:.2f}" for v in y_list])

        ax.set_xlabel(param1, fontsize=12)
        ax.set_ylabel(param2, fontsize=12)
        ax.set_title(f'参数空间热力图 - {param1} vs {param2}', fontsize=14, fontweight='bold')

        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('得分', fontsize=10)

        plt.tight_layout()

        if filepath:
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
        else:
            plt.show()

        plt.close()

    def plot_parameter_distribution(
        self,
        summary: OptimizationSummary,
        param_name: str,
        filepath: Optional[str] = None
    ) -> None:
        """
        绘制参数分布图

        Args:
            summary: 优化汇总
            param_name: 参数名称
            filepath: 保存路径
        """
        param_values = [r.params.get(param_name) for r in summary.all_results]
        scores = [r.score for r in summary.all_results]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # 直方图
        ax1.hist(param_values, bins=30, color='#4472C4', alpha=0.7, edgecolor='black')
        ax1.set_xlabel(param_name, fontsize=12)
        ax1.set_ylabel('频数', fontsize=12)
        ax1.set_title(f'{param_name} 分布', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)

        # 散点图
        ax2.scatter(param_values, scores, alpha=0.6, s=50, c='#4472C4')
        ax2.set_xlabel(param_name, fontsize=12)
        ax2.set_ylabel('得分', fontsize=12)
        ax2.set_title(f'{param_name} vs 得分', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        # 添加趋势线
        z = np.polyfit(param_values, scores, 1)
        p = np.poly1d(z)
        x_trend = np.linspace(min(param_values), max(param_values), 100)
        ax2.plot(x_trend, p(x_trend), "r--", linewidth=2, label='趋势线')
        ax2.legend()

        plt.tight_layout()

        if filepath:
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
        else:
            plt.show()

        plt.close()

    def plot_multi_panel_dashboard(
        self,
        summary: OptimizationSummary,
        filepath: Optional[str] = None
    ) -> None:
        """
        绘制多面板仪表板

        Args:
            summary: 优化汇总
            filepath: 保存路径
        """
        fig = plt.figure(figsize=(16, 10))
        gs = gridspec.GridSpec(2, 3, figure=fig)

        # 1. 优化历史
        ax1 = fig.add_subplot(gs[0, 0])
        scores = [r.score for r in summary.all_results]
        ax1.plot(range(1, len(scores) + 1), scores, color='#4472C4', linewidth=2)
        ax1.set_title('优化历史', fontsize=12, fontweight='bold')
        ax1.set_xlabel('迭代')
        ax1.set_ylabel('得分')
        ax1.grid(True, alpha=0.3)

        # 2. 收益分布
        ax2 = fig.add_subplot(gs[0, 1])
        returns = [r.metrics.return_value for r in summary.all_results]
        ax2.hist(returns, bins=30, color='green', alpha=0.7, edgecolor='black')
        ax2.axvline(np.mean(returns), color='red', linestyle='--', label='均值')
        ax2.set_title('收益率分布', fontsize=12, fontweight='bold')
        ax2.set_xlabel('收益率')
        ax2.set_ylabel('频数')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # 3. 夏普分布
        ax3 = fig.add_subplot(gs[0, 2])
        sharpes = [r.metrics.sharpe_ratio for r in summary.all_results]
        ax3.hist(sharpes, bins=30, color='orange', alpha=0.7, edgecolor='black')
        ax3.axvline(np.mean(sharpes), color='red', linestyle='--', label='均值')
        ax3.set_title('夏普比率分布', fontsize=12, fontweight='bold')
        ax3.set_xlabel('夏普比率')
        ax3.set_ylabel('频数')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # 4. 收益vs回撤
        ax4 = fig.add_subplot(gs[1, 0])
        drawdowns = [r.metrics.max_drawdown for r in summary.all_results]
        ax4.scatter(returns, drawdowns, alpha=0.6, s=30, c='#4472C4')
        ax4.set_title('收益 vs 回撤', fontsize=12, fontweight='bold')
        ax4.set_xlabel('收益率')
        ax4.set_ylabel('最大回撤')
        ax4.grid(True, alpha=0.3)

        # 5. 收益Top20排名
        ax5 = fig.add_subplot(gs[1, 1:])
        top_results = sorted(summary.all_results, key=lambda x: x.score, reverse=True)[:20]
    top_scores = [r.score for r in top_results]
    bars = ax5.barh(range(len(top_scores)), top_scores, color='steelblue')
    ax5.set_yticks(range(len(top_results)))
    ax5.set_yticklabels([f"参数组合{i+1}" for i in range(len(top_results))], fontsize=8)
    ax5.set_title('Top 20 参数组合', fontsize=12, fontweight='bold')
    ax5.set_xlabel('得分')
    ax5.grid(True, alpha=0.3, axis='x')

        plt.suptitle('策略参数优化仪表板', fontsize=16, fontweight='bold')
        plt.tight_layout()

        if filepath:
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
        else:
            plt.show()

        plt.close()
```

**验收标准**：
- [ ] 报告生成正确
- [ ] Excel导出正常
- [ ] 图表生成美观
- [ ] 敏感性分析有效

---

## 4. 测试计划

### 4.1 单元测试矩阵

| 模块 | 测试文件 | 用例数 | 覆盖目标 |
|------|---------|--------|---------|
| base/result | test_result.py | 4 | 100% |
| base/optimizer | test_optimizer.py | 3 | 90% |
| setting/china_setting | test_setting.py | 3 | 85% |
| algorithms/bayesian | test_bayesian.py | 5 | 90% |
| algorithms/pso | test_pso.py | 4 | 85% |
| overfit/detector | test_detector.py | 5 | 85% |
| report/generator | test_generator.py | 4 | 80% |
| report/visualizer | test_visualizer.py | 3 | 75% |
| **合计** | | **31** | **86%** |

### 4.2 集成测试

```python
# tests/optimization/test_integration.py
import pytest
from vnpy_china_optimize.algorithms.bayesian import BayesianOptimizer
from vnpy_china_optimize.algorithms.pso import PSOOptimizer
from vnpy_china_optimize.overfit.detector import OverfitDetector
from vnpy_china_optimize.report.generator import OptimizationReportGenerator


def test_full_optimization_workflow():
    """测试完整优化流程"""

    # 1. 定义目标函数
    def objective(params: dict) -> float:
        x = params["x"]
        y = params["y"]
        return -(x - 1) ** 2 - (y - 2) ** 2 + 10

    param_space = {"x": (-5, 5), "y": (-5, 5)}

    # 2. 贝叶斯优化
    bayesian_optimizer = BayesianOptimizer(
        objective_func=objective,
        param_space=param_space,
        n_initial=5,
        random_state=42
    )

    summary = bayesian_optimizer.optimize(n_iterations=30)

    # 3. 生成报告
    generator = OptimizationReportGenerator()
    report = generator.generate(summary)

    assert "优化结果统计" in report
    assert "最优参数" in report

    # 4. 导出Excel
    generator.export_to_excel(summary, "optimization/test_report.xlsx")

    import os
    assert os.path.exists("optimization/test_report.xlsx")


def test_overfit_detection_workflow():
    """测试过拟合检测流程"""

    # 模拟回测函数
    def mock_backtest(params, start, end):
        # 返回模拟的回测指标
        from vnpy_china_optimize.base.result import OptimizationMetrics
        return OptimizationMetrics(
            return_value=0.1,
            sharpe_ratio=1.5,
            max_drawdown=0.1,
            win_rate=0.6
        )

    detector = OverfitDetector(
        backtest_func=mock_backtest,
        decay_threshold=0.5
    )

    # 样本外测试
    result = detector.out_sample_test(
        params={"x": 1.0},
        train_start="2023-01-01",
        train_end="2023-06-30",
        test_start="2023-07-01",
        test_end="2023-12-31"
    )

    assert result.test_type == "out_sample"
    assert hasattr(result, "is_overfit")
```

---

## 5. 时间安排

### 5.1 日程计划

| 日期 | 任务 | 工时 |
|------|------|------|
| Day 1 | 基础框架+A股优化设置 | 8h |
| Day 2 | 贝叶斯优化器实现 | 8h |
| Day 3 | 粒子群优化器实现 | 8h |
| Day 4 | 过拟合检测实现 | 8h |
| Day 5 | 优化报告+测试 | 8h |
| **合计** | | **40h (5人天)** |

### 5.2 里程碑

| 里程碑 | 时间 | 交付内容 |
|--------|------|---------|
| M1 | Day 1结束 | 基础框架+设置完成 |
| M2 | Day 2结束 | 贝叶斯优化完成 |
| M3 | Day 3结束 | PSO优化完成 |
| M4 | Day 4结束 | 过拟合检测完成 |
| M5 | Day 5结束 | 报告+测试完成 |

---

## 6. 风险管理

### 6.1 技术风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| sklearn依赖问题 | 中 | 中 | 提供安装说明 |
| 算法收敛问题 | 中 | 中 | 调整超参数 |
| 回测函数兼容性 | 低 | 中 | 充分测试 |

### 6.2 性能风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| 贝叶斯优化慢 | 中 | 低 | 减少初始化采样 |
| PSO粒子数过多 | 低 | 低 | 合理设置粒子数 |

---

## 7. 验收标准

### 7.1 功能验收

- [ ] 贝叶斯优化正常工作
- [ ] PSO优化正常工作
- [ ] 过拟合检测有效
- [ ] 优化报告完整
- [ ] Excel导出正常
- [ ] 图表生成美观

### 7.2 性能验收

- [ ] 100次迭代<5分钟（单参数）
- [ ] 报告生成<10秒
- [ ] Excel导出<5秒

### 7.3 质量验收

- [ ] 单元测试覆盖率≥85%
- [ ] 所有测试通过
- [ ] 代码通过类型检查
- [ ] 文档完整

---

## 8. 使用示例

### 8.1 基本使用

```python
from vnpy_china_optimize.algorithms.bayesian import BayesianOptimizer
from vnpy_china_optimize.setting import ChinaOptimizerSetting

# 1. 定义目标函数
def objective(params: dict) -> float:
    # 这里调用回测引擎
    # 返回夏普比率等指标
    return backtest_result["sharpe_ratio"]

# 2. 设置参数空间
param_space = {
    "fast_window": (5, 30),
    "slow_window": (30, 120),
    "entry_threshold": (0.5, 2.0)
}

# 3. 创建优化器
optimizer = BayesianOptimizer(
    objective_func=objective,
    param_space=param_space,
    n_initial=10
)

# 4. 执行优化
summary = optimizer.optimize(n_iterations=100)

# 5. 查看结果
print(f"最优参数: {summary.best_params}")
print(f"最优分数: {summary.best_score}")
```

### 8.2 过拟合检测

```python
from vnpy_china_optimize.overfit.detector import OverfitDetector

# 创建检测器
detector = OverfitDetector(
    backtest_func=my_backtest_func
)

# 样本外测试
result = detector.out_sample_test(
    params=best_params,
    train_start="2023-01-01",
    train_end="2023-06-30",
    test_start="2023-07-01",
    test_end="2023-12-31"
)

if result.is_overfit:
    print("警告：参数存在过拟合风险！")
else:
    print("参数过拟合检测通过")
```

---

## 9. 后续计划

### 9.1 功能扩展

- [ ] 添加差分进化算法
- [ ] 添加模拟退火算法
- [ ] 支持多目标优化
- [ ] 支持并行优化

### 9.2 优化方向

- [ ] 使用GPU加速高斯过程
- [ ] 实现增量学习
- [ ] 添加早停机制
- [ ] 支持约束优化

---

**文档版本**：v1.0
**创建日期**：2026-02-24
**维护者**：AI Assistant
**下次更新**：实施完成后更新
