# 策略参数优化设计文档

> 文档版本：v1.1
> 创建日期：2026-02-24
> 更新日期：2026-02-24
> 需求编号：REQ-010
> 优先级：P2
> 预计工时：5人天（原6人天，因复用vnpy.trader.optimize减少1人天）
>
> **变更记录**:
> - v1.1: 明确扩展vnpy.trader.optimize而非重新实现
> - v1.0: 初始版本

---

## 1. 设计目标

**扩展VeighNa现有的vnpy.trader.optimize模块**，添加高级优化算法：

1. **扩展现有算法**：保留网格搜索和遗传算法，添加贝叶斯优化、粒子群优化
2. **过拟合检测**：样本外测试、参数稳定性、前向验证、交叉验证
3. **优化报告**：参数排名、收益分布、敏感性分析、最优参数

### 1.1 与vnpy.trader.optimize的关系

VeighNa的optimize模块已提供：
- `OptimizeSetting`：优化目标设置
- `generate_optimization_target()`：生成优化目标函数
- 遗传算法（DEAP库）：`optimize()`函数
- 穷举算法：完整参数空间搜索

**本模块将扩展而非替代**：

| vnpy.optimize现有功能 | 本模块扩展内容 |
|---------------------|--------------|
| 遗传算法、穷举搜索 | 添加贝叶斯优化、粒子群优化 |
| 基础优化目标函数 | 添加A股交易成本计算 |
| 基础结果输出 | 扩展过拟合检测、优化报告 |

---

## 2. 架构设计

### 2.1 整体架构（扩展模式）

```
┌─────────────────────────────────────────────────────────────────┐
│                   vnpy.trader.optimize 扩展架构                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  【vnpy.trader.optimize 原有模块】                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • OptimizeSetting: 优化设置                               │   │
│  │ • generate_optimization_target(): 目标函数生成            │   │
│  │ • 遗传算法: DEAP库实现                                   │   │
│  │ • 穷举算法: 完整参数空间搜索                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  【本模块扩展内容】                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ChinaOptimizerSetting: A股优化设置                       │   │
│  │  • china_trading_cost: A股交易成本                       │   │
│  │  • t1_rule: T+1规则                                     │   │
│  │  • price_limit: 涨跌停规则                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ BayesianOptimizer: 贝叶斯优化                           │   │
│  │  • 高斯过程代理模型                                     │   │
│  │  • EI采集函数                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ PSOOptimizer: 粒子群优化                                │   │
│  │  • 粒子群算法实现                                        │   │
│  │  • 惯性权重调整                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ OverfitDetector: 过拟合检测                             │   │
│  │  • 样本外测试                                           │   │
│  │  • 前向验证                                            │   │
│  │  • 参数稳定性分析                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块结构

```
vnpy_china_optimize/
├── __init__.py
├── base.py                    # 优化器基类
├── setting.py                 # A股优化设置
├── algorithms/
│   ├── __init__.py
│   ├── bayesian.py           # 贝叶斯优化
│   └── pso.py                # 粒子群优化
├── overfit/
│   ├── __init__.py
│   ├── out_sample.py         # 样本外测试
│   ├── stability.py          # 稳定性分析
│   └── walk_forward.py       # 前向验证
└── report/
    ├── __init__.py
    ├── generator.py          # 报告生成
    └── visualizer.py         # 可视化
```

---

## 3. 核心类设计

### 3.1 优化器基类

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Callable
from dataclasses import dataclass
import numpy as np


@dataclass
class OptimizationResult:
    """优化结果"""
    params: Dict[str, Any]
    return_value: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int


class BaseOptimizer(ABC):
    """优化器基类"""

    def __init__(
        self,
        objective_func: Callable,
        param_space: Dict[str, tuple]
    ):
        """
        初始化优化器

        Args:
            objective_func: 目标函数，最大化此函数
            param_space: 参数空间 {param_name: (min, max)}
        """
        self.objective_func = objective_func
        self.param_space = param_space
        self.results: List[OptimizationResult] = []

    @abstractmethod
    def optimize(self, n_iterations: int = 100) -> OptimizationResult:
        """执行优化"""
        pass

    def get_best_params(self) -> Dict[str, Any]:
        """获取最优参数"""
        if not self.results:
            return {}
        return max(self.results, key=lambda x: x.return_value).params
```

### 3.2 贝叶斯优化（修正版）

```python
from scipy.optimize import minimize
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel


class BayesianOptimizer(BaseOptimizer):
    """贝叶斯优化器（修正版）"""

    def __init__(self, objective_func, param_space, n_initial=5):
        super().__init__(objective_func, param_space)
        self.n_initial = n_initial
        self.X_observed = []
        self.y_observed = []

        # 初始化参数边界
        self.bounds = []
        for name, (low, high) in param_space.items():
            self.bounds.append((low, high))

        # 高斯过程代理模型
        kernel = ConstantKernel(1.0) * RBF(length_scale=1.0)
        self.gp = GaussianProcessRegressor(kernel=kernel, alpha=1e-6)

    def _surrogate(self, X):
        """代理模型（高斯过程）"""
        if len(self.X_observed) == 0:
            return 0.0
        X_array = np.array(self.X_observed).reshape(-1, len(self.bounds))
        y_array = np.array(self.y_observed)
        self.gp.fit(X_array, y_array)

        X_test = np.array(X).reshape(1, -1)
        return self.gp.predict(X_test, return_std=False)[0]

    def _acquisition(self, X):
        """采集函数（EI）- 修正版"""
        # 获取预测均值和标准差
        X_array = np.array(self.X_observed).reshape(-1, len(self.bounds))
        y_array = np.array(self.y_observed)
        self.gp.fit(X_array, y_array)

        X_test = np.array(X).reshape(1, -1)
        mu, sigma = self.gp.predict(X_test, return_std=True)

        best_y = max(self.y_observed) if self.y_observed else 0

        # 避免除零
        sigma = max(sigma[0], 1e-6)

        # 期望改进（Expected Improvement）
        z = (mu[0] - best_y) / sigma
        ei = (mu[0] - best_y) * norm.cdf(z) + sigma * norm.pdf(z)

        return -ei  # 最小化采集函数

    def optimize(self, n_iterations: int = 100) -> OptimizationResult:
        """执行贝叶斯优化"""

        # 1. 随机采样初始化
        for _ in range(self.n_initial):
            x = [np.random.uniform(b[0], b[1]) for b in self.bounds]
            y = self.objective_func(x)
            self.X_observed.append(x)
            self.y_observed.append(y)

        # 2. 迭代优化
        for _ in range(n_iterations):
            # 找到最优采样点
            result = minimize(
                self._acquisition,
                x0=self.X_observed[-1],  # 使用最后一个点作为初始值
                bounds=self.bounds,
                method='L-BFGS-B'
            )

            # 评估目标函数
            y = self.objective_func(result.x)
            self.X_observed.append(result.x.tolist())
            self.y_observed.append(y)

        # 返回最优结果
        best_idx = np.argmax(self.y_observed)
        return self._create_result(self.X_observed[best_idx], self.y_observed[best_idx])
```

### 3.3 遗传算法

```python
class GeneticOptimizer(BaseOptimizer):
    """遗传算法优化器"""

    def __init__(
        self,
        objective_func,
        param_space,
        population_size=50,
        n_generations=100,
        crossover_rate=0.8,
        mutation_rate=0.1
    ):
        super().__init__(objective_func, param_space)
        self.population_size = population_size
        self.n_generations = n_generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate

    def optimize(self, n_iterations: int = None) -> OptimizationResult:
        """执行遗传算法优化"""

        n_iterations = n_iterations or self.n_generations

        # 1. 初始化种群
        population = self._initialize_population()

        for generation in range(n_iterations):
            # 2. 评估适应度
            fitness = [self.objective_func(ind) for ind in population]

            # 3. 选择
            parents = self._selection(population, fitness)

            # 4. 交叉
            offspring = self._crossover(parents)

            # 5. 变异
            offspring = self._mutate(offspring)

            # 6. 更新种群
            population = offspring

        # 返回最优解
        best_idx = np.argmax(fitness)
        return self._create_result(population[best_idx], fitness[best_idx])

    def _initialize_population(self) -> List[np.ndarray]:
        """初始化种群"""
        population = []
        for _ in range(self.population_size):
            individual = []
            for (low, high) in self.bounds:
                individual.append(np.random.uniform(low, high))
            population.append(np.array(individual))
        return population
```

### 3.4 过拟合检测

```python
class OverfitDetector:
    """过拟合检测器"""

    def __init__(self, backtest_func: Callable):
        self.backtest_func = backtest_func

    def out_sample_test(
        self,
        params: Dict,
        train_range: tuple,
        test_range: tuple
    ) -> Dict[str, float]:
        """样本外测试"""

        # 训练集回测
        train_result = self.backtest_func(params, train_range)

        # 测试集回测
        test_result = self.backtest_func(params, test_range)

        # 计算衰减比
        return_decay = test_result.return_value / train_result.return_value \
            if train_result.return_value != 0 else 0

        sharpe_decay = test_result.sharpe_ratio / train_result.sharpe_ratio \
            if train_result.sharpe_ratio != 0 else 0

        return {
            "train_return": train_result.return_value,
            "test_return": test_result.return_value,
            "return_decay": return_decay,
            "sharpe_decay": sharpe_decay,
            "is_overfit": return_decay < 0.5  # 衰减超过50%认为过拟合
        }

    def walk_forward_validation(
        self,
        params: Dict,
        start_date: str,
        end_date: str,
        train_days: int = 252,
        test_days: int = 63
    ) -> Dict:
        """前向验证"""

        results = []
        current_date = start_date

        while current_date + train_days + test_days <= end_date:
            train_range = (current_date, current_date + train_days)
            test_range = (current_date + train_days, current_date + train_days + test_days)

            result = self.backtest_func(params, test_range)
            results.append(result)

            current_date += test_days

        # 计算稳定性
        returns = [r.return_value for r in results]
        sharpes = [r.sharpe_ratio for r in results]

        return {
            "avg_return": np.mean(returns),
            "return_std": np.std(returns),
            "return_stability": np.std(returns) / np.mean(returns) if np.mean(returns) != 0 else 0,
            "avg_sharpe": np.mean(sharpes),
            "sharpe_stability": np.std(sharpes),
            "is_stable": np.std(returns) / np.mean(returns) < 0.5 if np.mean(returns) != 0 else True
        }
```

### 3.5 优化报告

```python
class OptimizationReport:
    """优化报告生成器"""

    def generate(
        self,
        results: List[OptimizationResult],
        overfit_results: Dict = None
    ) -> str:
        """生成优化报告"""

        # 按收益排序
        sorted_results = sorted(results, key=lambda x: x.return_value, reverse=True)

        report = f"""
========================================
          策略参数优化报告
========================================

一、优化结果统计
---------------
总参数组合数: {len(results)}
最优收益: {sorted_results[0].return_value:.2%}
最优夏普: {sorted_results[0].sharpe_ratio:.2f}
最大回撤: {sorted_results[0].max_drawdown:.2%}

二、最优参数
------------
"""

        for param, value in sorted_results[0].params.items():
            report += f"{param}: {value}\n"

        if overfit_results:
            report += f"""
三、过拟合检测
-------------
样本外衰减: {overfit_results.get('return_decay', 0):.2%}
稳定性系数: {overfit_results.get('return_stability', 0):.2f}
过拟合风险: {'高' if overfit_results.get('is_overfit', False) else '低'}

========================================
"""
        return report
```

---

## 4. 实施计划

| 阶段 | 任务 | 预估工时 |
|------|------|---------|
| 1 | 创建目录结构和基类 | 0.5人天 |
| 2 | 扩展vnpy.optimize设置 | 0.5人天 |
| 3 | 实现贝叶斯优化 | 1人天 |
| 4 | 实现粒子群优化 | 1人天 |
| 5 | 实现过拟合检测 | 1人天 |
| 6 | 实现优化报告 | 1人天 |
| 合计 | | **5人天** |

> 注：由于复用vnpy.trader.optimize现有功能，工时从6人天减少到5人天

---

## 5. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.1 | 2026-02-24 | 明确扩展vnpy.trader.optimize而非重新实现；修正贝叶斯优化代码 |
| v1.0 | 2026-02-24 | 初始版本 |
