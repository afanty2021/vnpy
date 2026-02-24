# 机器学习策略系统实施方案

> 文档版本：v1.0
> 创建日期：2026-02-24
> 需求编号：REQ-011
> 优先级：P2
> 预计工时：8人天
> 实施周期：2周

---

## 1. 方案概述

### 1.1 项目背景

VeighNa框架已提供完善的vnpy.alpha模块用于AI量化研究。本方案通过**扩展vnpy.alpha模块**，添加A股市场特有的因子、模型适配和评估指标，构建适用于A股市场的机器学习策略系统。

### 1.2 实施原则

**核心原则**：扩展而非替代

- ✅ 保留vnpy.alpha原有功能（AlphaDataset、AlphaModel、BacktestingEngine）
- ✅ 扩展A股特色因子（龙虎榜、北向资金、板块轮动）
- ✅ 适配A股交易规则（T+1、涨跌停）
- ✅ 扩展评估指标（IC/IR、A股特有指标）
- ✅ 支持在线学习（增量训练、模型更新）

### 1.3 与vnpy.alpha的关系

```
vnpy.alpha (原有)                    vnpy_china_ml (扩展)
├── AlphaDataset                     ├── ChinaAlphaDataset (扩展数据集)
│   ├── Alpha 158因子集               │   ├── add_dragon_tiger_factors()
│   ├── 表达式引擎                    │   ├── add_northbound_factors()
│   └── 时序/截面函数                  │   └── add_sector_rotation_factors()
├── AlphaModel                        ├── ChinaAlphaModel (扩展模型)
│   ├── Lasso/LightGBM/MLP            │   ├── train_with_china_rules()
│   └── 模型训练                       │   ├── predict_with_t1()
└── BacktestingEngine                 └── incremental_train()
                                        ├── ChinaFactor (龙虎榜因子)
                                        ├── NorthboundFactor (北向资金因子)
                                        └── SectorRotationFactor (板块轮动因子)
                                        ├── ChinaMetrics (IC/IR分析)
                                        └── MLStrategy (A股ML策略)
```

### 1.4 实施目标

| 目标类别 | 具体目标 | 成功标准 |
|---------|---------|---------|
| 因子扩展 | 龙虎榜、北向资金、板块轮动因子 | 至少15个新因子 |
| 模型适配 | T+1规则、涨跌停适配 | 预测准确率提升 |
| 在线学习 | 增量训练、模型更新 | 支持实时更新 |
| 评估指标 | IC/IR、A股特有指标 | IC>0.05，IR>1 |

### 1.5 交付物清单

| 序号 | 交付物 | 类型 | 说明 |
|------|--------|------|------|
| 1 | vnpy_china_ml模块 | 代码 | ML策略扩展模块 |
| 2 | A股因子库 | 代码 | 龙虎榜、北向资金、板块因子 |
| 3 | 模型适配器 | 代码 | A股规则适配层 |
| 4 | 评估工具 | 代码 | IC/IR分析工具 |
| 5 | 策略模板 | 代码 | ML策略基类 |
| 6 | 单元测试 | 代码 | pytest测试套件 |
| 7 | 使用示例 | 代码 | 示例策略和脚本 |
| 8 | API文档 | 文档 | 接口说明文档 |

---

## 2. 技术架构设计

### 2.1 模块结构

```
vnpy_china_ml/
├── __init__.py                         # 模块入口
├── dataset/                             # 数据集扩展
│   ├── __init__.py
│   ├── china_dataset.py               # 扩展AlphaDataset
│   └── feature_engine.py              # 特征工程工具
├── factors/                             # A股因子库
│   ├── __init__.py
│   ├── base.py                        # 因子基类
│   ├── dragon_tiger.py                # 龙虎榜因子
│   ├── northbound.py                  # 北向资金因子
│   ├── sector_rotation.py             # 板块轮动因子
│   └── limit_stats.py                 # 涨跌停统计因子
├── model/                               # 模型扩展
│   ├── __init__.py
│   ├── china_model.py                 # 扩展AlphaModel
│   ├── adapters.py                    # A股规则适配器
│   └── online.py                       # 在线学习支持
├── evaluation/                          # 评估工具
│   ├── __init__.py
│   ├── ic_ir.py                       # IC/IR分析
│   ├── metrics.py                     # A股评估指标
│   └── validator.py                    # 模型验证器
├── strategy/                            # 策略模板
│   ├── __init__.py
│   ├── china_ml_strategy.py           # A股ML策略基类
│   └── signal_generator.py             # 信号生成器
└── utils/                               # 工具函数
    ├── __init__.py
    ├── calculator.py                  # 计算工具
    └── transformer.py                  # 数据转换
```

### 2.2 类图设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    ChinaAlphaDataset                            │
│                  (扩展AlphaDataset)                             │
├─────────────────────────────────────────────────────────────────┤
│ + add_dragon_tiger_factors(lookback)                        │
│ + add_northbound_factors(lookback)                           │
│ + add_sector_rotation_factors(lookback)                       │
│ + add_technical_indicators()                                  │
│ # dragon_tiger_provider: IDataProvider                       │
│ # northbound_provider: IDataProvider                          │
└─────────────────────────────────────────────────────────────────┘
                              △ 继承
┌─────────────────────────────────────────────────────────────────┐
│                      AlphaDataset                                │
│                   (vnpy.alpha原有)                             │
├─────────────────────────────────────────────────────────────────┤
│ + add_feature(factor)                                         │
│ + get_features(start_date, end_date)                          │
│ + get_labels(start_date, end_date)                            │
│ + load_data(symbol)                                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    ChinaAlphaModel                              │
│                  (扩展AlphaModel)                               │
├─────────────────────────────────────────────────────────────────┤
│ + train_with_china_rules(dataset, ...)                        │
│ + predict_with_t1(features)                                   │
│ + incremental_train(X_new, y_new, ...)                        │
│ # t1_adapter: T1RuleAdapter                                   │
│ # limit_adapter: PriceLimitAdapter                           │
└─────────────────────────────────────────────────────────────────┘
                              △ 继承
┌─────────────────────────────────────────────────────────────────┐
│                      AlphaModel                                  │
│                   (vnpy.alpha原有)                             │
├─────────────────────────────────────────────────────────────────┤
│ + fit(X, y, sample_weight)                                    │
│ + predict(X)                                                   │
│ + get_feature_importance()                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    ChinaMLStrategy                               │
│                    (A股ML策略)                                   │
├─────────────────────────────────────────────────────────────────┤
│ # model: ChinaAlphaModel                                     │
│ # feature_engine: FeatureEngine                              │
│ + on_bar(bar)                                                  │
│ + prepare_features(bar) -> np.ndarray                        │
│ + predict_signal(features) -> float                            │
│ + should_retrain() -> bool                                    │
│ + retrain_model()                                             │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 数据流设计

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  数据源层     │ ──>  │  特征工程层   │ ──>  │  模型层      │
├──────────────┤      ├──────────────┤      ├──────────────┤
│ • Tushare   │      │ • A股因子    │      │ • LightGBM   │
│ • 龙虎榜数据 │      │ • 技术指标    │      │ • XGBoost    │
│ • 北向资金   │      │ • 因子组合    │      │ • LSTM       │
│ • 板块数据   │      │ • 特征选择    │      │ │
└──────────────┘      └──────────────┘      └──────────────┘
                                                     │
                                                     v
                                              ┌──────────────┐
                                              │  策略执行层  │
                                              ├──────────────┤
                                              │ • 信号生成   │
                                              │ • 仓位管理   │
                                              │ • T+1规则    │
                                              │ • 风控检查   │
                                              └──────────────┘
```

---

## 3. 详细实施计划

### 3.1 第一阶段：基础框架搭建（1人天）

#### 任务1.1：创建目录结构

```bash
# 创建模块根目录
mkdir -p vnpy_china_ml

# 创建子目录
mkdir -p vnpy_china_ml/dataset
mkdir -p vnpy_china_ml/factors
mkdir -p vnpy_china_ml/model
mkdir -p vnpy_china_ml/evaluation
mkdir -p vnpy_china_ml/strategy
mkdir -p vnpy_china_ml/utils

# 创建测试目录
mkdir -p tests/ml_strategy

# 创建输出目录
mkdir -p ml_models
mkdir -ml backtest_results
mkdir -ml predictions
```

#### 任务1.2：定义核心数据模型

**文件位置**：`vnpy_china_ml/utils/types.py`

```python
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Union
from enum import Enum
import numpy as np


class FactorType(Enum):
    """因子类型"""
    TECHNICAL = "technical"        # 技术指标因子
    FUNDAMENTAL = "fundamental"    # 基本面因子
    DRAGON_TIGER = "dragon_tiger"  # 龙虎榜因子
    NORTHBOUND = "northbound"      # 北向资金因子
    SECTOR_ROTATION = "sector_rotation"  # 板块轮动因子
    LIMIT_STATS = "limit_stats"    # 涨跌停统计因子


class ModelType(Enum):
    """模型类型"""
    LIGHTGBM = "lightgbm"
    XGBOOST = "xgboost"
    RANDOM_FOREST = "random_forest"
    LASSO = "lasso"
    RIDGE = "ridge"
    LSTM = "lstm"
    TRANSFORMER = "transformer"
    SVM = "svm"


class PredictionSignal(Enum):
    """预测信号"""
    STRONG_BUY = "strong_buy"      # 强买入
    BUY = "buy"                   # 买入
    WEAK_BUY = "weak_buy"         # 弱买入
    NEUTRAL = "neutral"           # 中性
    WEAK_SELL = "weak_sell"       # 弱卖出
    SELL = "sell"                 # 卖出
    STRONG_SELL = "strong_sell"   # 强卖出


@dataclass
class FactorValue:
    """因子值"""
    name: str                          # 因子名称
    symbol: str                       # 股票代码
    datetime: datetime               # 时间点
    value: float                      # 因子值
    type: FactorType                 # 因子类型


@dataclass
class ModelPrediction:
    """模型预测结果"""
    symbol: str                       # 股票代码
    datetime: datetime               # 预测时间
    model_type: ModelType             # 模型类型
    prediction: float                # 预测值（收益率）
    probability: float               # 概率（分类模型）
    signal: PredictionSignal         # 交易信号
    confidence: float                 # 置信度


@dataclass
class ICMetric:
    """IC/IR指标"""
    ic_mean: float                     # IC均值
    ic_std: float                      # IC标准差
    ic_ir: float                      # IC信息比率
    rank_ic_mean: float               # Rank IC均值
    positive_ic_ratio: float          # 正IC占比
    ic_series: List[float] = field(default_factory=list)  # IC序列


@dataclass
class ModelPerformance:
    """模型性能指标"""
    # 回测指标
    total_return: float                # 总收益率
    annual_return: float              # 年化收益率
    sharpe_ratio: float                # 夏普比率
    max_drawdown: float                # 最大回撤
    calmar_ratio: float                # 卡玛比率

    # 预测指标
    accuracy: float                    # 准确率（分类）
    precision: float                   # 精确率
    recall: float                      # 召回率
    f1_score: float                    # F1分数
    mse: float                        # 均方误差（回归）
    mae: float                        # 平均绝对误差
    r2_score: float                   # R平方

    # IC/IR指标
    ic_metric: Optional[ICMetric] = None

    # 稳定性指标
    stability_score: float = 0.0      # 稳定性评分
    overfit_risk: str = "low"          # 过拟合风险


@dataclass
class TrainingConfig:
    """训练配置"""
    # 数据配置
    start_date: str                   # 训练开始日期
    end_date: str                     # 训练结束日期
    rebalance_freq: str = "d"         # 再平衡频率

    # 模型配置
    model_type: ModelType = ModelType.LIGHTGBM
    model_params: Dict[str, Any] = field(default_factory=dict)

    # 特征配置
    features: List[str] = field(default_factory=list)
    feature_selection: bool = False
    max_features: int = 50

    # 训练配置
    train_ratio: float = 0.7           # 训练集比例
    rolling_window: int = 252          # 滚动窗口大小
    cv_folds: int = 5                  # 交叉验证折数

    # A股规则适配
    consider_t1: bool = True           # 考虑T+1规则
    consider_limit: bool = True        # 考虑涨跌停

    # 在线学习
    enable_online: bool = False        # 启用在线学习
    retrain_interval: int = 30         # 重训练间隔（天）
    forget_ratio: float = 0.1          # 遗忘比率
```

#### 任务1.3：创建因子基类

**文件位置**：`vnpy_china_ml/factors/base.py`

```python
from abc import ABC, abstractmethod
from typing import Union
import polars as pl
from vnpy.alpha.dataset import BaseFactor


class ChinaFactor(ABC):
    """
    A股因子基类

    所有A股特色因子应继承此类。
    """

    def __init__(self, lookback: int = 5):
        """
        初始化因子

        Args:
            lookback: 回溯窗口
        """
        self.lookback = lookback
        self.name: str = ""

    @abstractmethod
    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """
        计算因子值

        Args:
            df: 包含OHLCV数据的DataFrame

        Returns:
            因子值Series
        """
        pass

    def __call__(self, df: pl.DataFrame) -> pl.Series:
        """使因子可调用"""
        return self.calculate(df)


class DragonTigerFactor(ChinaFactor):
    """龙虎榜因子基类"""
    pass


class NorthboundFactor(ChinaFactor):
    """北向资金因子基类"""
    pass


class SectorRotationFactor(ChinaFactor):
    """板块轮动因子基类"""
    pass
```

**验收标准**：
- [ ] 目录结构完整
- [ ] 数据类定义完整
- [ ] 因子基类清晰
- [ ] 通过类型检查

---

### 3.2 第二阶段：A股因子实现（2人天）

#### 任务2.1：龙虎榜因子

**文件位置**：`vnpy_china_ml/factors/dragon_tiger.py`

```python
from typing import Dict, Any, List
import polars as pl
from .base import DragonTigerFactor
from vnpy.alpha.dataset import BaseFactor


class InstitutionNetBuyFactor(DragonTigerFactor):
    """
    机构净买入因子

    计算龙虎榜中机构席位的净买入量，
    反映机构资金的进出情况。
    """

    def __init__(self, lookback: int = 5):
        super().__init__(lookback)
        self.name = "institution_net_buy"

    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """
        计算机构净买入因子

        Args:
            df: 包含龙虎榜数据的DataFrame
                需要列: dragon_tiger_institution_buy, dragon_tiger_institution_sell

        Returns:
            因子值Series
        """
        # 确保必要列存在
        if "dragon_tiger_institution_buy" not in df.columns:
            return pl.Series([0.0] * len(df))

        buy = df.get("dragon_tiger_institution_buy", pl.Series([0.0] * len(df)))
        sell = df.get("dragon_tiger_institution_sell", pl.Series([0.0] * len(df)))

        net_buy = buy - sell

        # 滚动求和
        return net_buy.rolling(self.lookback).sum().fill_null(0)


class BrokerNetBuyFactor(DragonTigerFactor):
    """
    营业部净买入因子

    计算龙虎榜中营业部席位的净买入量，
    反映游资的动向。
    """

    def __init__(self, lookback: int = 5):
        super().__init__(lookback)
        self.name = "broker_net_buy"

    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """
        计算营业部净买入因子

        Args:
            df: 包含龙虎榜数据的DataFrame
                需要列: dragon_tiger_broker_buy, dragon_tiger_broker_sell

        Returns:
            因子值Series
        """
        buy = df.get("dragon_tiger_broker_buy", pl.Series([0.0] * len(df)))
        sell = df.get("dragon_tiger_broker_sell", pl.Series([0.0] * len(df)))

        net_buy = buy - sell

        return net_buy.rolling(self.lookback).sum().fill_null(0)


class BuyRatioFactor(DragonTigerFactor):
    """
    买入比例因子

    计算龙虎榜买入金额占总成交金额的比例，
    反映市场的买入意愿强度。
    """

    def __init__(self, lookback: int = 5):
        super().__init__(lookback)
        self.name = "buy_ratio"

    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """
        计算买入比例因子

        Args:
            df: 包含龙虎榜数据和成交数据的DataFrame
                需要列: dragon_tiger_total_buy, total_amount

        Returns:
            因子值Series
        """
        total_buy = df.get("dragon_tiger_total_buy", pl.Series([0.0] * len(df)))
        total_amount = df.get("total_amount", pl.Series([1.0] * len(df)))

        # 避免除零
        ratio = pl.when(
            total_amount > 0,
            total_buy / total_amount,
            0.0
        )

        return ratio.rolling(self.lookback).mean().fill_null(0)


class InstitutionRankFactor(DragonTigerFactor):
    """
    机构席位排名因子

    统计机构席位在龙虎榜中的出现频次，
    反映机构对该股票的关注度。
    """

    def __init__(self, lookback: int = 20):
        super().__init__(lookback)
        self.name = "institution_rank"

    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """
        计算机构席位排名因子

        Args:
            df: 包含龙虎榜数据的DataFrame
                需要列: dragon_tiger_institution_rank

        Returns:
            因子值Series
        """
        rank = df.get("dragon_tiger_institution_rank", pl.Series([999] * len(df)))

        # 排名转换为分数（排名越靠前分数越高）
        max_rank = rank.max()
        if max_rank > 0:
            score = (max_rank - rank) / max_rank
        else:
            score = pl.Series([0.0] * len(df))

        # 近期加权平均（越近权重越大）
        weights = list(range(1, self.lookback + 1))
        weighted_score = score.rolling(self.lookback).sum(
            weights[::-1]  # 反转权重，使最近期的权重最大
            min_periods=1
        ) / sum(weights)

        return weighted_score.fill_null(0)
```

#### 任务2.2：北向资金因子

**文件位置**：`vnpy_china_ml/factors/northbound.py`

```python
from typing import Dict, Any
import polars as pl
from .base import NorthboundFactor


class NorthboundNetInflowFactor(NorthboundFactor):
    """
    北向资金净流入因子

    计算北向资金的净流入金额，
    反映外资对A股的配置意愿。
    """

    def __init__(self, lookback: int = 5):
        super().__init__(lookback)
        self.name = "northbound_net_inflow"

    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """
        计算北向资金净流入因子

        Args:
            df: 包含北向资金数据的DataFrame
                需要列: northbound_net_inflow

        Returns:
            因子值Series
        """
        inflow = df.get("northbound_net_inflow", pl.Series([0.0] * len(df)))

        # 滚动求和并标准化
        rolling_sum = inflow.rolling(self.lookback).sum().fill_null(0)

        # 计算z-score进行标准化
        mean = rolling_sum.mean()
        std = rolling_sum.std()

        z_score = pl.when(
            std > 0,
            (rolling_sum - mean) / std,
            0.0
        )

        return z_score


class HoldingChangeFactor(NorthboundFactor):
    """
    持仓变化因子

    计算北向资金持仓股票的变化，
    反映外资对个股的配置调整。
    """

    def __init__(self, lookback: int = 5):
        super().__init__(lookback)
        self.name = "holding_change"

    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """
        计算持仓变化因子

        Args:
            df: 包含北向资金持仓数据的DataFrame
                需要列: northbound_holding

        Returns:
            因子值Series
        """
        holding = df.get("northbound_holding", pl.Series([0.0] * len(df)))

        # 计算持仓变化
        change = holding.diff().fill_null(0)

        # 滚动标准化的变化
        rolling_change = change.rolling(self.lookback).sum().fill_null(0)

        return rolling_change


class SectorPreferenceFactor(NorthboundFactor):
    """
    板块偏好因子

    计算北向资金对各板块的配置偏好，
    识别外资青睐的板块。
    """

    def __init__(self, lookback: int = 20):
        super().__init__(lookback)
        self.name = "sector_preference"

    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """
        计算板块偏好因子

        Args:
            df: 包含板块数据的DataFrame
                需要列: sector, northbound_flow

        Returns:
            因子值Series
        """
        sector = df.get("sector", pl.Series(["未知"] * len(df)))
        flow = df.get("northbound_flow", pl.Series([0.0] * len(df)))

        # 计算各板块的总流入
        sector_flow = flow.group_by([sector, "datetime"]).sum().sort_by("datetime")

        # 这里简化处理，实际需要更复杂的逻辑
        # 返回当前股票所属板块的相对偏好度
        return flow.rolling(self.lookback).sum().fill_null(0)


class NorthboundHoldingRatioFactor(NorthboundFactor):
    """
    北向持仓占比因子

    计算北向资金持仓占流通盘的比例，
    反映外资对该股票的掌控程度。
    """

    def __init__(self, lookback: int = 5):
        super().__init__(lookback)
        self.name = "northbound_holding_ratio"

    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """
        计算北向持仓占比因子

        Args:
            df: 包含持仓和流通盘数据的DataFrame
                需要列: northbound_holding, circulation

        Returns:
            因子值Series
        """
        holding = df.get("northbound_holding", pl.Series([0.0] * len(df)))
        circulation = df.get("circulation", pl.Series([1.0] * len(df)))

        # 避免除零
        ratio = pl.when(
            circulation > 0,
            holding / circulation * 100,  # 转换为百分比
            0.0
        )

        return ratio.rolling(self.lookback).mean().fill_null(0)
```

#### 任务2.3：板块轮动因子

**文件位置**：`vnpy_china_ml/factors/sector_rotation.py`

```python
from typing import Dict, List
import polars as pl
import numpy as np
from .base import SectorRotationFactor


class SectorRelativeStrengthFactor(SectorRotationFactor):
    """
    板块相对强度因子

    计算板块相对大盘的强度，
    识别强势板块。
    """

    def __init__(self, lookback: int = 20):
        super().__init__(lookback)
        self.name = "sector_relative_strength"

    def calculate(self, df: pl.DataFrame, index_df: pl.DataFrame = None) -> pl.Series:
        """
        计算板块相对强度因子

        Args:
            df: 板块指数数据
            index_df: 大盘指数数据（可选）

        Returns:
            因子值Series
        """
        # 获取板块收益率
        sector_return = df.get("close", pl.Series([0.0] * len(df)))
        sector_return = sector_return.pct_change().fill_null(0)

        # 如果有大盘数据，计算相对强度
        if index_df is not None and len(index_df) == len(df):
            index_return = index_df.get("close", pl.Series([0.0] * len(df)))
            index_return = index_return.pct_change().fill_null(0)

            # 相对强度 = 板块收益 - 大盘收益
            relative_strength = sector_return - index_return
        else:
            relative_strength = sector_return

        # 滚动累计相对强度
        cumulative_strength = relative_strength.rolling(self.lookback).sum().fill_null(0)

        return cumulative_strength


class SectorMomentumFactor(SectorRotationFactor):
    """
    板块动量因子

    计算板块的价格动量，
    识别加速上涨的板块。
    """

    def __init__(self, lookback: int = 20):
        super().__init__(lookback)
        self.name = "sector_momentum"

    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """
        计算板块动量因子

        Args:
            df: 板块指数数据
                需要列: close

        Returns:
            因子值Series
        """
        close = df.get("close", pl.Series([0.0] * len(df)))

        # 计算不同周期的收益率
        return_1d = close.pct_change(1).fill_null(0)
        return_5d = close.pct_change(5).fill_null(0)
        return_20d = close.pct_change(20).fill_null(0)

        # 动量 = 近期收益 - 远期收益
        momentum = return_1d * 0.5 + return_5d * 0.3 + return_20d * 0.2

        # 滚动平滑
        smoothed_momentum = momentum.rolling(5).mean().fill_null(0)

        return smoothed_momentum


class SectorFlowFactor(SectorRotationFactor):
    """
    板块资金流向因子

    计算板块的资金流向情况，
    识别资金流入的板块。
    """

    def __init__(self, lookback: int = 5):
        super().__init__(lookback)
        self.name = "sector_flow"

    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """
        计算板块资金流向因子

        Args:
            df: 包含板块成交数据的DataFrame
                需要列: volume, turnover, avg_price

        Returns:
            因子值Series
        """
        volume = df.get("volume", pl.Series([0.0] * len(df)))
        turnover = df.get("turnover", pl.Series([0.0] * len(df)))
        avg_price = df.get("avg_price", pl.Series([0.0] * len(df)))

        # 计算成交金额
        amount = volume * avg_price

        # 计算换手率变化
        turnover_change = turnover.pct_change().fill_null(0)

        # 资金流向 = 成交量变化 * 换手率变化
        flow = amount * (1 + turnover_change)

        # 滚动求和
        rolling_flow = flow.rolling(self.lookback).sum().fill_null(0)

        # 标准化
        mean = rolling_flow.mean()
        std = rolling_flow.std()

        z_score = pl.when(
            std > 0,
            (rolling_flow - mean) / std,
            0.0
        )

        return z_score


class SectorDispersionFactor(SectorRotationFactor):
    """
    板块离散度因子

    计算板块内股票收益的离散程度，
    离散度高可能预示板块轮动。
    """

    def __init__(self, lookback: int = 5):
        super().__init__(lookback)
        self.name = "sector_dispersion"

    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """
        计算板块离散度因子

        Args:
            df: 包含板块成分股数据的DataFrame
                需要列: stock_returns_list

        Returns:
            因子值Series
        """
        # 这里假设df有一个列包含了成分股收益率列表
        # 实际实现可能需要更复杂的数据结构

        # 简化处理：使用成交量的离散度作为代理
        volume = df.get("volume", pl.Series([0.0] * len(df)))

        # 计算成交量的标准差（离散度）
        rolling_std = volume.rolling(self.lookback).std().fill_null(0)
        rolling_mean = volume.rolling(self.lookback).mean().fill_null(0)

        # 离散系数 = 标准差 / 均值
        dispersion = pl.when(
            rolling_mean > 0,
            rolling_std / rolling_mean,
            0.0
        )

        return dispersion.fill_null(0)
```

#### 任务2.4：涨跌停统计因子

**文件位置**：`vnpy_china_ml/factors/limit_stats.py`

```python
from typing import Dict, Any
import polars as pl
from vnpy.alpha.dataset import BaseFactor


class LimitUpCountFactor(BaseFactor):
    """
    涨停次数因子

    统计近期涨停次数，
    捕捉股票的强势特征。
    """

    def __init__(self, lookback: int = 20):
        super().__init__()
        self.lookback = lookback

    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """
        计算涨停次数因子

        Args:
            df: 包含涨跌停数据的DataFrame
                需要列: is_limit_up (bool)

        Returns:
            因子值Series
        """
        is_limit_up = df.get("is_limit_up", pl.Series([False] * len(df)))

        # 将布尔值转换为整数并求和
        limit_up_count = is_limit_up.cast(pl.Int32).rolling(self.lookback).sum().fill_null(0)

        return limit_up_cast


class LimitUpStreakFactor(BaseFactor):
    """
    连续涨停因子

    统计连续涨停天数，
    捕捉极强的上涨动能。
    """

    def __init__(self, lookback: int = 5):
        super().__init__()
        self.lookback = lookback

    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """
        计算连续涨停因子

        Args:
            df: 包含涨跌停数据的DataFrame
                需要列: is_limit_up (bool), consecutive_limit_up (int)

        Returns:
            因子值Series
        """
        consecutive = df.get("consecutive_limit_up", pl.Series([0] * len(df)))

        # 近期最大连续涨停天数
        max_consecutive = consecutive.rolling(self.lookback).max().fill_null(0)

        return max_consecutive


class LimitUpFrequencyFactor(BaseFactor):
    """
    涨停频率因子

    计算涨停发生的频率，
    识别频繁涨停的活跃股票。
    """

    def __init__(self, lookback: int = 60):
        super().__init__()
        self.lookback = lookback

    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """
        计算涨停频率因子

        Args:
            df: 包含涨跌停数据的DataFrame
                需要列: is_limit_up (bool)

        Returns:
            因子值Series
        """
        is_limit_up = df.get("is_limit_up", pl.Series([False] * len(df)))

        # 涨停频率 = 涨停天数 / 总天数
        frequency = is_limit_up.cast(pl.Int32).rolling(self.lookback).sum() / self.lookback

        return frequency.fill_null(0)


class PriceLimitDistanceFactor(BaseFactor):
    """
    涨跌停距离因子

    计算当前价格距离涨跌停价的距离，
    识别接近涨停的股票。
    """

    def __init__(self):
        super().__init__()
        self.name = "price_limit_distance"

    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """
        计算涨跌停距离因子

        Args:
            df: 包含价格和涨跌停数据的DataFrame
                需要列: close, limit_up_price, limit_down_price

        Returns:
            因子Series
        """
        close = df.get("close", pl.Series([0.0] * len(df)))
        limit_up = df.get("limit_up_price", pl.Series([0.0] * len(df)))
        limit_down = df.get("limit_down_price", pl.Series([0.0] * len(df)))

        # 计算到涨停价和跌停价的距离
        distance_to_up = (limit_up - close) / close * 100
        distance_to_down = (close - limit_down) / close * 100

        # 综合距离（优先考虑到涨停的距离）
        distance = pl.when(
            distance_to_up >= 0,
            distance_to_up,  # 上涨空间
            -distance_to_down  # 下跌空间（负值）
        )

        return distance.fill_null(0)
```

**验收标准**：
- [ ] 龙虎榜因子实现完整
- [ ] 北向资金因子实现完整
- [ ] 板块轮动因子实现完整
- [ ] 涨跌停因子实现完整
- [ ] 测试用例通过

---

### 3.3 第三阶段：模型适配器实现（1.5人天）

#### 任务3.1：A股规则适配器

**文件位置**：`vnpy_china_ml/model/adapters.py`

```python
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


class T1RuleAdapter:
    """
    T+1规则适配器

    处理A股T+1交易规则对模型训练和预测的影响。
    """

    def __init__(self):
        """初始化适配器"""
        self.t1_history: Dict[str, List[datetime]] = {}

    def adjust_label(
        self,
        labels: np.ndarray,
        dates: List[datetime],
        shift: int = 1
    ) -> np.ndarray:
        """
        调整标签以适应T+1规则

        T+1规则下，当日买入的股票次日才能卖出。
        因此预测信号需要向后移一天。

        Args:
            labels: 原始标签（收益率）
            dates: 对应的日期列表
            shift: 向后移动的天数

        Returns:
            调整后的标签
        """
        # 将标签向后移动
        adjusted_labels = np.roll(labels, shift)

        # 最后shift个标签设为0（无法交易）
        adjusted_labels[-shift:] = 0

        return adjusted_labels

    def filter_buyable_trades(
        self,
        signals: np.ndarray,
        buy_dates: List[datetime],
        symbol: str
    ) -> np.ndarray:
        """
        过滤出可执行的买入信号

        Args:
            signals: 买入信号
            buy_dates: 买入日期
            symbol: 股票代码

        Returns:
            过滤后的信号
        """
        filtered_signals = signals.copy()

        # 记录买入日期
        if symbol not in self.t1_history:
            self.t1_history[symbol] = []

        for i, (signal, date) in enumerate(zip(signals, buy_dates)):
            if signal > 0.5:  # 买入信号
                # 检查是否已经在T+1期间
                if not self._is_in_t1_period(symbol, date):
                    filtered_signals[i] = signal
                    self.t1_history[symbol].append(date)
            else:
                # 非买入信号，清空T+1历史
                if len(self.t1_history.get(symbol, [])) > 0:
                    last_buy_date = self.t1_history[symbol][-1]
                    if self._is_t1_expired(symbol, last_buy_date, date):
                        self.t1_history[symbol] = []

        return filtered_signals

    def _is_in_t1_period(self, symbol: str, date: datetime) -> bool:
        """检查是否在T+1期间"""
        if symbol not in self.t1_history or not self.t1_history[symbol]:
            return False

        last_buy = self.t1_history[symbol][-1]
        days_diff = (date - last_buy).days

        return 0 < days_diff <= 1  # T+1，当天或次日

    def _is_t1_expired(self, symbol: str, last_buy: datetime, current: datetime) -> bool:
        """检查T+1是否已过期"""
        days_diff = (current - last_buy).days
        return days_diff > 1


class PriceLimitAdapter:
    """
    涨跌停规则适配器

    处理涨跌停对模型训练和交易的影响。
    """

    def __init__(self):
        """初始化适配器"""
        self.limit_info: Dict[str, Dict[str, float]] = {}

    def adjust_sample_weight(
        self,
        features: np.ndarray,
        dates: List[datetime],
        limit_info: Dict[str, Any]
    ) -> np.ndarray:
        """
        调整样本权重

        涨跌停日的样本权重降低，
        因为这些日子无法交易或流动性差。

        Args:
            features: 特征数据
            dates: 对应日期
            limit_info: 涨跌停信息 {date: {"is_limit_up": bool, "is_limit_down": bool}}

        Returns:
            样本权重
        """
        weights = np.ones(len(dates))

        for i, date in enumerate(dates):
            date_str = date.strftime("%Y-%m-%d")
            info = limit_info.get(date_str, {})

            # 涨停日权重降低
            if info.get("is_limit_up", False) or info.get("is_limit_down", False):
                weights[i] = 0.5  # 权重减半

            # 接近涨跌停时权重也降低
            distance_to_limit = info.get("distance_to_limit", 1.0)
            if distance_to_limit < 0.01:  # 距离<1%
                weights[i] *= distance_to_limit * 100

        return weights

    def filter_limit_signals(
        self,
        signals: np.ndarray,
        prices: np.ndarray,
        limit_ups: np.ndarray,
        limit_downs: np.ndarray
    ) -> np.ndarray:
        """
        过滤涨跌停信号

        Args:
            signals: 原始信号
            prices: 当前价格
            limit_ups: 涨停价
            limit_downs: 跌停价

        Returns:
            过滤后的信号
        """
        filtered_signals = signals.copy()

        for i, (signal, price, limit_up, limit_down) in enumerate(
            zip(signals, prices, limit_ups, limit_downs)
        ):
            # 如果接近涨停价，降低买入信号强度
            if signal > 0 and abs(price - limit_up) / limit_up < 0.01:
                filtered_signals[i] = signal * 0.5

            # 如果接近跌停价，降低卖出信号强度
            elif signal < 0 and abs(price - limit_down) / limit_down < 0.01:
                filtered_signals[i] = signal * 0.5

            # 涨停无法买入，跌停无法卖出
            if abs(price - limit_up) < 0.001:  # 已涨停
                filtered_signals[i] = min(0, filtered_signals[i])
            if abs(price - limit_down) < 0.001:  # 已跌停
                filtered_signals[i] = max(0, filtered_signals[i])

        return filtered_signals


class ChinaModelAdapter:
    """
    A股模型综合适配器

    整合T+1规则和涨跌停规则的适配。
    """

    def __init__(self):
        """初始化适配器"""
        self.t1_adapter = T1RuleAdapter()
        self.limit_adapter = PriceLimitAdapter()

    def prepare_training_data(
        self,
        features: pd.DataFrame,
        labels: np.ndarray,
        metadata: Dict[str, Any]
    ) -> tuple:
        """
        准备训练数据

        Args:
            features: 特征DataFrame
            labels: 标签数组
            metadata: 元数据（包含日期、涨跌停信息等）

        Returns:
            (调整后的特征, 调整后的标签, 样本权重)
        """
        # 1. T+1规则调整标签
        dates = metadata.get("dates", [])
        if dates and len(dates) == len(labels):
            adjusted_labels = self.t1_adapter.adjust_label(labels, dates)
        else:
            adjusted_labels = labels.copy()

        # 2. 调整样本权重
        limit_info = metadata.get("limit_info", {})
        sample_weights = self.limit_adapter.adjust_sample_weight(
            features.values, dates, limit_info
        )

        # 3. 特征标准化处理（如果有涨跌停相关特征）
        # 这里可以根据需要添加

        return features, adjusted_labels, sample_weights

    def adjust_prediction(
        self,
        predictions: np.ndarray,
        current_data: Dict[str, Any]
    ) -> np.ndarray:
        """
        调整预测信号

        根据T+1规则和涨跌停规则调整预测信号。

        Args:
            predictions: 原始预测
            current_data: 当前市场数据

        Returns:
            调整后的预测信号
        """
        adjusted = predictions.copy()

        # 1. T+1规则适配
        if current_data.get("can_buy_today", True):
            # 如果今天可以买入（持仓为空或T+1已过），使用预测信号
            pass
        else:
            # 今天不能买入，信号置0
            adjusted = np.where(adjusted > 0, 0, adjusted)

        # 2. 涨跌停适配
        price = current_data.get("price", 0)
        limit_up = current_data.get("limit_up", float('inf'))
        limit_down = current_data.get("limit_down", 0)

        adjusted = self.limit_adapter.filter_limit_signals(
            adjusted, np.array([price]), np.array([limit_up]), np.array([limit_down])
        )

        return adjusted
```

**验收标准**：
- [ ] T+1规则适配正确
- [ ] 涨跌停适配正确
- [ ] 综合适配器工作正常
- [ ] 测试用例通过

---

### 3.4 第四阶段：在线学习支持（1人天）

#### 任务4.1：在线学习管理器

**文件位置**：`vnpy_china_ml/model/online.py`

```python
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pickle
from datetime import datetime, timedelta
from pathlib import Path


class OnlineLearningManager:
    """
    在线学习管理器

    支持增量训练、模型更新、版本管理。
    """

    def __init__(
        self,
        model_dir: str = "ml_models",
        retrain_interval: int = 30,
        forget_ratio: float = 0.1,
        min_samples: int = 252
    ):
        """
        初始化在线学习管理器

        Args:
            model_dir: 模型保存目录
            retrain_interval: 重训练间隔（天）
            forget_ratio: 遗忘比率（旧数据权重）
            min_samples: 最小样本数
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.retrain_interval = retrain_interval
        self.forget_ratio = forget_ratio
        self.min_samples = min_samples

        # 训练历史
        self.last_train_date: Optional[datetime] = None
        self.total_samples: int = 0

        # 增量数据缓存
        self.new_data_features: List[np.ndarray] = []
        self.new_data_labels: List[np.ndarray] = []

    def should_retrain(self, current_date: datetime) -> bool:
        """
        判断是否应该重训练

        Args:
            current_date: 当前日期

        Returns:
            是否应该重训练
        """
        # 首次训练
        if self.last_train_date is None:
            return True

        # 检查重训练间隔
        days_since_last_train = (current_date - self.last_train_date).days

        if days_since_last_train >= self.retrain_interval:
            return True

        # 检查新数据积累量
        new_sample_count = sum(len(arr) for arr in self.new_data_labels)
        if new_sample_count >= self.min_samples:
            return True

        return False

    def add_new_data(
        self,
        features: np.ndarray,
        labels: np.ndarray
    ) -> None:
        """
        添加新数据

        Args:
            features: 新特征数据
            labels: 新标签数据
        """
        self.new_data_features.append(features)
        self.new_data_labels.append(labels)
        self.total_samples += len(labels)

    def incremental_train(
        self,
        model: Any,
        X_old: np.ndarray,
        y_old: np.ndarray,
        X_new: np.ndarray,
        y_new: np.ndarray
    ) -> Dict[str, Any]:
        """
        增量训练模型

        Args:
            model: 要更新的模型
            X_old: 旧特征数据
            y_old: 旧标签数据
            X_new: 新特征数据
            y_new: 新标签数据

        Returns:
            训练结果字典
        """
        # 合并数据
        X_combined = np.concatenate([X_old, X_new], axis=0)
        y_combined = np.concatenate([y_old, y_new], axis=0)

        # 可选：使用遗忘因子减少旧数据权重
        if self.forget_ratio > 0:
            # 样本权重
            n_old = len(X_old)
            n_new = len(X_new)

            weights_old = np.ones(n_old) * (1 - self.forget_ratio)
            weights_new = np.ones(n_new)

            sample_weights = np.concatenate([weights_old, weights_new])
        else:
            sample_weights = None

        # 重新训练模型
        training_start = datetime.now()

        try:
            if hasattr(model, 'fit'):
                model.fit(
                    X_combined,
                    y_combined,
                    sample_weight=sample_weights
                )
            else:
                raise ValueError("模型不支持fit方法")

            training_time = (datetime.now() - training_start).total_seconds()

            # 计算训练前后性能对比（这里简化处理）
            result = {
                "success": True,
                "old_samples": len(X_old),
                "new_samples": len(X_new),
                "total_samples": len(X_combined),
                "training_time": training_time,
                "trained_at": datetime.now().isoformat()
            }

        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "trained_at": datetime.now().isoformat()
            }

        return result

    def save_model(
        self,
        model: Any,
        model_name: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        保存模型

        Args:
            model: 模型对象
            model_name: 模型名称
            metadata: 元数据

        Returns:
            模型文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{model_name}_{timestamp}.pkl"
        filepath = self.model_dir / filename

        # 保存模型
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': model,
                'metadata': metadata or {},
                'saved_at': datetime.now().isoformat()
            }, f)

        return str(filepath)

    def load_model(
        self,
        filepath: str
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        加载模型

        Args:
            filepath: 模型文件路径

        Returns:
            (模型对象, 元数据)
        """
        with open(filepath, 'rb') as f:
            data = pickle.load(f)

        return data['model'], data.get('metadata', {})

    def get_model_version(self, model_name: str) -> List[str]:
        """获取模型所有版本"""
        pattern = f"{model_name}_*.pkl"
        model_files = list(self.model_dir.glob(pattern))

        # 按修改时间排序
        model_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        return [str(f) for f in model_files]

    def get_latest_model(self, model_name: str) -> Optional[Tuple[Any, Dict]]:
        """获取最新模型"""
        versions = self.get_model_version(model_name)

        if not versions:
            return None

        return self.load_model(versions[0])
```

**验收标准**：
- [ ] 增量训练正确
- [ ] 模型保存加载正常
- [ ] 版本管理有效
- [ ] 测试用例通过

---

### 3.5 第五阶段：ML策略模板实现（1人天）

#### 任务5.1：A股ML策略基类

**文件位置**：`vnpy_china_ml/strategy/china_ml_strategy.py`

```python
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from vnpy.ctastrategy import CtaTemplate
from vnpy.trader.object import BarData, TickData, OrderData, TradeData
from vnpy.trader.object import PositionData, AccountData
from vnpy.trader.event import Event

from vnpy_china_ml.model.china_model import ChinaAlphaModel
from vnpy_china_ml.evaluation.ic_ir import ICIRAnalyzer


class ChinaMLStrategy(CtaTemplate):
    """
    A股机器学习策略基类

    提供ML策略的基础框架，
    包括特征工程、模型预测、信号生成等。
    """

    # 策略参数
    parameters = [
        "model_type",              # 模型类型
        "retrain_interval",        # 重训练间隔
        "prediction_threshold",    # 预测阈值
        "position_size",           # 仓位大小
        "max_position",            # 最大持仓
        "stop_loss",               # 止损比例
        "take_profit"               # 止盈比例
        "feature_list"             # 使用哪些特征
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """构造函数"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 模型相关
        self.model: Optional[ChinaAlphaModel] = None
        self.model_type: str = setting.get("model_type", "lightgbm")

        # 训练配置
        self.retrain_interval: int = setting.get("retrain_interval", 30)
        self.last_train_date: Optional[datetime] = None

        # 预测阈值
        self.prediction_threshold: float = setting.get("prediction_threshold", 0.5)
        self.confidence_threshold: float = 0.6

        # 仓位管理
        self.position_size: int = setting.get("position_size", 100)
        self.max_position: int = setting.get("max_position", 5)

        # 风控
        self.stop_loss: float = setting.get("stop_loss", 0.05)
        self.take_profit: float = setting.get("take_profit", 0.15)

        # 特征工程
        self.feature_list: List[str] = setting.get("feature_list", [])
        self.feature_window: int = 20  # 特征计算窗口

        # 状态跟踪
        self.predictions: List[float] = []
        self.actual_returns: List[float] = []

        # IC/IR分析
        self.ic_ir_analyzer = ICIRAnalyzer()

    def on_init(self):
        """策略初始化回调"""
        # 加载模型
        self.load_model()

        # 写入日志
        self.write_log("策略初始化完成")

    def on_bar(self, bar: BarData):
        """K线数据推送"""
        # 1. 准备特征
        try:
            features = self.prepare_features(bar)

            if features is None or len(features) == 0:
                return

            # 2. 模型预测
            prediction, probability = self.predict(features)

            # 3. 生成交易信号
            signal = self.generate_signal(prediction, probability)

            # 4. 执行交易
            self.execute_signal(signal, bar)

            # 5. 记录预测
            self.predictions.append(prediction)

            # 6. 风控检查
            self.check_risk_management(bar)

            # 7. 检查是否需要重训练
            self.check_retrain_needed(bar)

        except Exception as e:
            self.write_log(f"on_bar错误: {e}")

    def prepare_features(self, bar: BarData) -> Optional[np.ndarray]:
        """
        准备特征

        Args:
            bar: K线数据

        Returns:
            特征数组，如果特征不足返回None
        """
        # 获取历史数据
        bars = self.get_history_bars(self.feature_window)

        if len(bars) < self.feature_window:
            return None

        # 这里需要根据feature_list计算特征
        # 简化实现：使用基本技术指标
        import polars as pl

        df = pl.DataFrame({
            "open": [b.open_price for b in bars],
            "high": [b.high_price for b in bars],
            "low": [b.low_price for b in bars],
            "close": [b.close_price for b in bars],
            "volume": [b.volume for b in bars],
            "datetime": [b.datetime for b in bars]
        })

        # 计算收益率
        df = df.with_columns([
            pl.col("close").pct_change().alias("return_1d"),
            (pl.col("close") / pl.col("close").shift(5) - 1).alias("return_5d"),
            (pl.col("close") / pl.col("close").shift(10) - 1).alias("return_10d"),
            (pl.col("close") / pl.col("close").shift(20) - 1).alias("return_20d"),
            pl.col("volume").pct_change().alias("volume_change"),
            pl.col("volume").rolling(5).mean().alias("volume_ma5"),
        ])

        # 添加波动率
        df = df.with_columns([
            pl.col("return_1d").rolling(5).std().alias("volatility_5"),
            pl.col("return_1d").rolling(20).std().alias("volatility_20"),
        ])

        # 添加RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).fill_null(0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).fill_null(0).rolling(14).mean()
        rs = gain / loss
        df = df.with_columns([
            (100 - (100 / (1 + rs))).alias("rsi")
        ])

        # 填充缺失值
        df = df.fill_null(0)

        # 选择特征
        feature_cols = self._select_feature_columns(df)
        features_array = df[feature_cols].to_numpy()

        return features_array[-1]  # 返回最后一行的特征

    def _select_feature_columns(self, df: pl.DataFrame) -> List[str]:
        """选择特征列"""
        available_features = [
            "return_1d", "return_5d", "return_10d", "return_20d",
            "volume_change", "volume_ma5",
            "volatility_5", "volatility_20",
            "rsi"
        ]

        # 根据self.feature_list过滤
        if self.feature_list:
            selected = [f for f in self.feature_list if f in available_features]
        else:
            selected = available_features

        return selected

    def predict(self, features: np.ndarray) -> Tuple[float, float]:
        """
        模型预测

        Args:
            features: 特征数组

        Returns:
            (预测值, 置信度)
        """
        if self.model is None:
            return 0.0, 0.0

        try:
            if hasattr(self.model, 'predict_proba'):
                # 分类模型（返回概率）
                proba = self.model.predict_proba(features.reshape(1, -1))[0]
                prediction = proba[1]  # 上涨概率
                confidence = max(proba)
            else:
                # 回归模型（返回收益率）
                prediction = self.model.predict(features.reshape(1, -1))[0]
                confidence = 0.5  # 回归模型没有置信度

            return float(prediction), float(confidence)

        except Exception as e:
            self.write_log(f"预测错误: {e}")
            return 0.0, 0.0

    def generate_signal(self, prediction: float, confidence: float) -> float:
        """
        生成交易信号

        Args:
            prediction: 预测值
            confidence: 置信度

        Returns:
            信号强度 (-1到1)
        """
        # 置信度不足，不交易
        if confidence < self.confidence_threshold:
            return 0.0

        # 预测值转信号
        if prediction > 0.01:
            # 预测上涨
            signal = min(prediction / 0.10, 1.0)  # 假设0.10为强买入
        elif prediction < -0.01:
            # 预测下跌
            signal = max(prediction / 0.10, -1.0)
        else:
            signal = 0.0

        return signal

    def execute_signal(self, signal: float, bar: BarData):
        """
        执行交易信号

        Args:
            signal: 信号强度
            bar: K线数据
        """
        if abs(signal) < 0.3:  # 信号太弱，不交易
            return

        # 检查持仓
        pos = self.get_position(bar.symbol)

        if signal > 0:  # 买入信号
            current_pos = pos.pos if pos else 0

            # 计算目标仓位
            target_pos = self.position_size

            # 限制最大持仓
            if current_pos >= self.max_position * self.position_size:
                return

            # 发送买入委托
            if current_pos < target_pos:
                volume = min(target_pos - current_pos, self.position_size)
                volume = self.round_lot_volume(volume)

                if volume >= 100:
                    self.buy(bar.close_price, volume)

        elif signal < 0:  # 卖出信号
            current_pos = pos.pos if pos else 0

            if current_pos > 0:
                # 检查止损/止盈
                if self.should_close_position(pos, bar):
                    self.sell(bar.close_price, current_pos)

    def check_retrain_needed(self, bar: BarData):
        """检查是否需要重训练"""
        if not self.retrain_interval:
            return

        current_date = bar.datetime

        # 检查是否到了重训练时间
        if self.should_retrain(current_date):
            self.write_log("开始重训练模型")
            self.retrain_model(bar)
            self.last_train_date = current_date

    def retrain_model(self, bar: BarData):
        """重训练模型"""
        # 准备训练数据
        X, y = self.prepare_training_data(bar)

        if X is None or len(X) < 252:  # 至少1年数据
            self.write_log("训练数据不足，跳过重训练")
            return

        # 训练模型
        try:
            if hasattr(self.model, 'fit'):
                self.model.fit(X, y)

            # 保存模型
            self.save_model()

            self.write_log("模型重训练完成")

        except Exception as e:
            self.write_log(f"重训练失败: {e}")

    def prepare_training_data(self, bar: BarData) -> tuple:
        """准备训练数据（简化版）"""
        # 这里需要实现完整的训练数据准备逻辑
        # 包括特征计算、标签生成等

        # 简化实现：返回模拟数据
        import numpy as np

        X = np.random.randn(252, 10)  # 1年数据，10个特征
        y = np.random.randn(252)

        return X, y

    def load_model(self):
        """加载模型"""
        # 从文件加载已训练模型
        # 这里简化处理
        pass

    def save_model(self):
        """保存模型"""
        # 保存当前模型到文件
        # 这里简化处理
        pass

    def should_close_position(self, pos: PositionData, bar: BarData) -> bool:
        """判断是否应该平仓"""
        if not pos:
            return False

        # 检查止损
        current_price = bar.close_price
        cost_price = pos.avg_price * (1 + self.stop_loss)

        if current_price <= cost_price:
            return True

        # 检查止盈
        target_price = pos.avg_price * (1 + self.take_profit)
        if current_price >= target_price:
            return True

        return False

    def round_lot_volume(self, volume: int) -> int:
        """取整到交易单位（100股）"""
        return int(volume / 100) * 100

    def get_history_bars(self, window: int) -> List[BarData]:
        """获取历史K线数据"""
        # 从主引擎获取历史数据
        bars: List[BarData] = []

        # 简化实现：这里需要调用主引擎API
        return bars

    def check_risk_management(self, bar: BarData):
        """风控检查"""
        pos = self.get_position(bar.symbol)

        if pos:
            # 检查单只股票仓位
            total_value = self.available capital + pos.market_value
            single_position_ratio = pos.market_value / total_value if total_value > 0 else 0

            if single_position_ratio > 0.2:  # 单只股票超过20%
                self.write_log(f"单只股票仓位过高: {single_position_ratio:.2%}")

            # 检查亏损
            unrealized_pnl = (bar.close_price - pos.avg_price) / pos.avg_price
            if unrealized_pnl < -self.stop_loss:
                self.write_log(f"触发止损: {unrealized_pnl:.2%}")
```

#### 任务5.2：信号生成器

**文件位置**：`vnpy_china_ml/strategy/signal_generator.py`

```python
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from enum import Enum


class SignalStrength(Enum):
    """信号强度"""
    VERY_WEAK = 0.2
    WEAK = 0.4
    NORMAL = 0.6
    STRONG = 0.8
    VERY_STRONG = 1.0


class SignalType(Enum):
    """信号类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class TradingSignal:
    """交易信号"""
    signal_type: SignalType
    strength: SignalStrength
    confidence: float               # 0-1
    prediction: float             # 原始预测值
    reason: str                    # 信号原因
    suggested_size: int           # 建议仓位
    stop_loss: float = 0.0        # 止损价
    take_profit: float = 0.0      # 止盈价


class SignalGenerator:
    """
    信号生成器

    将模型预测转换为交易信号。
    """

    def __init__(
        self,
        buy_threshold: float = 0.5,
        sell_threshold: float = -0.5,
        confidence_threshold: float = 0.6
    ):
        """
        初始化信号生成器

        Args:
            buy_threshold: 买入阈值
            sell_threshold: 卖出阈值
            confidence_threshold: 置信度阈值
        """
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.confidence_threshold = confidence_threshold

    def generate(
        self,
        prediction: float,
        probability: float,
        current_position: float = 0,
        position_value: float = 0.0
    ) -> TradingSignal:
        """
        生成交易信号

        Args:
            prediction: 预测值（收益率）
            probability: 置信度（概率或归一化值）
            current_position: 当前持仓
            position_value: 持仓市值

        Returns:
            TradingSignal对象
        """
        # 确定信号类型
        if prediction > self.buy_threshold:
            signal_type = SignalType.BUY
            strength = self._calculate_strength(prediction, probability, True)
        elif prediction < self.sell_threshold:
            signal_type = SignalType.SELL
            strength = self._calculate_strength(prediction, probability, False)
        else:
            signal_type = SignalType.HOLD
            strength = SignalStrength.NORMAL

        # 计算建议仓位
        if signal_type == SignalType.BUY:
            suggested_size = self._calculate_buy_size(
                prediction, probability, position_value
            )
        elif signal_type == SignalType.SELL:
            suggested_size = self._calculate_sell_size(
                prediction, current_position
            )
        else:
            suggested_size = 0

        # 计算止损止盈
        stop_loss, take_profit = self._calculate_stop_take_profit(
            prediction, current_position, position_value
        )

        # 生成信号原因
        reason = self._generate_reason(
            prediction, probability, signal_type, strength
        )

        return TradingSignal(
            signal_type=signal_type,
            strength=strength,
            confidence=probability,
            prediction=prediction,
            reason=reason,
            suggested_size=suggested_size,
            stop_loss=stop_loss,
            take_profit=take_profit
        )

    def _calculate_strength(
        self,
        prediction: float,
        probability: float,
        is_buy: bool
    ) -> SignalStrength:
        """计算信号强度"""
        # 预测值和置信度都高时，信号最强
        if is_buy:
            if prediction > 0.05 and probability > 0.8:
                return SignalStrength.VERY_STRONG
            elif prediction > 0.02 and probability > 0.6:
                return SignalStrength.STRONG
            elif prediction > 0.01 and probability > 0.5:
                return SignalStrength.NORMAL
            else:
                return SignalStrength.WEAK
        else:
            # 卖出逻辑
            if prediction < -0.05 and probability > 0.8:
                return SignalStrength.VERY_STRONG
            elif prediction < -0.02 and probability > 0.6:
                return SignalStrength.STRONG
            elif prediction < -0.01 and probability > 0.5:
                return SignalStrength.NORMAL
            else:
                return SignalStrength.WEAK

    def _calculate_buy_size(
        self,
        prediction: float,
        probability: float,
        position_value: float
    ) -> int:
        """计算买入数量"""
        # 基于预测值和置信度计算仓位
        base_size = 100  # 基础100股

        # 预测值越大、置信度越高，仓位越大
        size_multiplier = (prediction * 10) * probability

        # 限制仓位
        max_size = 1000  # 最大1000股
        size_multiplier = min(size_multiplier, max_size / base_size)

        suggested_size = int(base_size * size_multiplier)

        # 取整到100股
        return (suggested_size // 100) * 100

    def _calculate_sell_size(
        self,
        prediction: float,
        current_position: float
    ) -> int:
        """计算卖出数量"""
        if current_position <= 0:
            return 0

        # 预测值越负，卖出比例越高
        sell_ratio = min(abs(prediction) * 2, 1.0)

        return int(current_position * sell_ratio / 100) * 100

    def _calculate_stop_take_profit(
        self,
        prediction: float,
        current_position: float,
        position_value: float
    ) -> Tuple[float, float]:
        """计算止损止盈"""
        # 简化：基于预测收益的百分比
        stop_loss_pct = max(prediction * 2, -0.05)  # 止损
        take_profit_pct = max(prediction * 3, 0.05)  # 止盈

        # 计算价格
        entry_price = position_value / current_position if current_position > 0 else 0
        stop_loss = entry_price * (1 + stop_loss_pct)
        take_profit = entry_price * (1 + take_profit_pct)

        return stop_loss, take_profit

    def _generate_reason(
        self,
        prediction: float,
        probability: float,
        signal_type: SignalType,
        strength: SignalStrength
    ) -> str:
        """生成信号原因"""
        parts = []

        # 信号类型
        if signal_type == SignalType.BUY:
            parts.append(f"模型预测上涨{prediction:.2%}")
        elif signal_type == SignalType.SELL:
            parts.append(f"模型预测下跌{prediction:.2%}")
        else:
            parts.append("模型预测震荡，建议观望")

        # 置信度
        parts.append(f"，置信度{probability:.0%}")

        # 强度
        strength_map = {
            SignalStrength.VERY_WEAK: "极弱",
            SignalStrength.WEAK: "弱",
            SignalStrength.NORMAL: "中等",
            SignalStrength.STRONG: "强",
            SignalStrength.VERY_STRONG: "极强"
        }
        parts.append(f"，信号{strength_map[strength]}")

        return "".join(parts)
```

**验收标准**：
- [ ] 策略基类功能完整
- [ ] 特征工程正确
- [ ] 信号生成合理
- [ ] 风控检查有效
- [ ] 测试用例通过

---

### 3.6 第六阶段：评估工具实现（1人天）

#### 任务6.1：IC/IR分析器

**文件位置**：`vnpy_china_ml/evaluation/ic_ir.py`

```python
from typing import List, Dict, Tuple, Optional
import numpy as np
from scipy.stats import spearmanr
from datetime import datetime


class ICIRAnalyzer:
    """
    IC/IR分析器

    计算和分析信息系数（IC）和信息比率（IR），
    这是量化投资中最重要的因子评价指标。
    """

    def __init__(self):
        """初始化分析器"""
        self.ic_history: List[float] = []
        self.rank_ic_history: List[float] = []

    def calculate_ic(
        self,
        predictions: np.ndarray,
        actual_returns: np.ndarray,
        method: str = "pearson"
    ) -> float:
        """
        计算IC（Information Coefficient）

        Args:
            predictions: 预测值（如预测收益率）
            actual_returns: 实际值
            method: "pearson" 或 "spearman"

        Returns:
            IC值
        """
        if len(predictions) != len(actual_returns):
            raise ValueError("预测值和实际值长度不匹配")

        if method == "pearson":
            # 皮尔逊相关系数
            ic = np.corrcoef(predictions, actual_returns)[0, 1]
        elif method == "spearman":
            # 斯皮尔曼相关系数
            ic, _ = spearmanr(predictions, actual_returns)
        else:
            raise ValueError(f"未知的IC计算方法: {method}")

        return ic

    def calculate_rank_ic(
        self,
        predictions: np.ndarray,
        actual_returns: np.ndarray
    ) -> float:
        """
        计算Rank IC

        Rank IC是将预测值和实际值分别排名后计算IC，
        对异常值更稳健。

        Args:
            predictions: 预测值
            actual_returns: 实际值

        Returns:
            Rank IC值
        """
        # 计算排名
        pred_ranks = np.argsort(np.argsort(predictions)[::-1])
        actual_ranks = np.argsort(np.argsort(actual_returns)[::-1])

        # 计算排名相关系数
        rank_ic = np.corrcoef(pred_ranks, actual_ranks)[0, 1]

        return rank_ic

    def calculate_ir(
        self,
        ic_series: List[float],
        annualized: bool = False
    ) -> float:
        """
        计算IR（Information Ratio）

        IR = IC均值 / IC标准差
        反映IC的稳定性。

        Args:
            ic_series: IC值序列
            annualized: 是否年化

        Returns:
            IR值
        """
        if not ic_series:
            return 0.0

        ic_array = np.array(ic_series)
        mean_ic = np.mean(ic_array)
        std_ic = np.std(ic_array)

        if std_ic == 0:
            return 0.0

        ir = mean_ic / std_ic

        # 年化处理
        if annualized:
            # 假设每年252个交易日
            trading_days = 252
            ir = ir * np.sqrt(trading_days)

        return ir

    def analyze(
        self,
        prediction_series: List[np.ndarray],
        return_series: List[np.ndarray],
        dates: Optional[List[datetime]] = None
    ) -> Dict[str, Any]:
        """
        综合IC/IR分析

        Args:
            prediction_series: 预测值序列（每个时间点的预测数组）
            return_series: 实际值序列
            dates: 日期列表（可选）

        Returns:
            分析结果字典
        """
        if len(prediction_series) != len(return_series):
            raise ValueError("预测序列和实际序列长度不匹配")

        # 计算每个时间点的IC
        ic_values = []
        rank_ic_values = []

        for pred, ret in zip(prediction_series, return_series):
            if len(pred) > 0 and len(ret) > 0:
                ic = self.calculate_ic(pred, ret, "pearson")
                rank_ic = self.calculate_rank_ic(pred, ret)

                ic_values.append(ic)
                rank_ic_values.append(rank_ic)

        if not ic_values:
            return {
                "error": "无法计算IC值"
            }

        # 计算统计量
        ic_mean = np.mean(ic_values)
        ic_std = np.std(ic_values)
        ic_min = np.min(ic_values)
        ic_max = np.max(ic_values)

        rank_ic_mean = np.mean(rank_ic_values)

        # 计算IC>0的比例
        positive_ic_ratio = sum(1 for ic in ic_values if ic > 0) / len(ic_values)

        # 计算IR
        ir = self.calculate_ir(ic_values)

        # 计算年化IR
        ir_annual = self.calculate_ir(ic_values, annualized=True)

        # 计算t统计显著性
        # t检验：IC均值 / (IC标准差 / sqrt(n))
        t_stat = ic_mean / (ic_std / np.sqrt(len(ic_values))) if ic_std > 0 else 0

        # 判断IC是否显著（|t|>2为显著）
        ic_significant = abs(t_stat) > 2

        result = {
            "ic_mean": ic_mean,
            "ic_std": ic_std,
            "ic_min": ic_min,
            "ic_max": ic_max,
            "rank_ic_mean": rank_ic_mean,
            "positive_ic_ratio": positive_ic_ratio,
            "ir": ir,
            "ir_annual": ir_annual,
            "t_stat": t_stat,
            "ic_significant": ic_significant,
            "n_observations": len(ic_values)
        }

        # 添加日期信息
        if dates:
            result["dates"] = [d.strftime("%Y-%m-%d") for d in dates[:len(ic_values)]]

        return result

    def generate_ic_report(self, result: Dict[str, Any]) -> str:
        """生成IC分析报告"""
        lines = []
        lines.append("=" * 60)
        lines.append(" "IC/IR分析报告")
        lines.append("=" * 60)
        lines.append("")

        lines.append("一、IC统计")
        lines.append("-" * 40)
        lines.append(f"IC均值: {result['ic_mean']:.4f}")
        lines.append(f"IC标准差: {result['ic_std']:.4f}")
        lines.append(f"IC最小值: {result['ic_min']:.4f}")
        lines.append(f"IC最大值: {result['ic_max']:.4f}")
        lines.append("")

        lines.append("二、Rank IC")
        lines.append("-" * 40)
        lines.append(f"Rank IC均值: {result['rank_ic_mean']:.4f}")
        lines.append("")

        lines.append("三、IR指标")
        lines.append("-" * 40)
        lines.append(f"IR: {result['ir']:.4f}")
        lines.append(f"年化IR: {result['ir_annual']:.4f}")
        lines.append("")

        lines.append("四、IC有效性")
        lines.append("-" * 40)
        lines.append(f"IC>0占比: {result['positive_ic_ratio']:.2%}")
        lines.append(f"IC显著: {'是' if result['ic_significant'] else '否'}")
        lines.append(f"t统计量: {result['t_stat']:.2f}")
        lines.append(f"样本数: {result['n_observations']}")
        lines.append("")

        # IC等级评估
        ic_abs = abs(result['ic_mean'])
        if ic_abs > 0.1:
            grade = "优秀"
        elif ic_abs > 0.05:
            grade = "良好"
        elif ic_abs > 0.03:
            grade = "一般"
        else:
            grade = "较差"

        lines.append("五、综合评价")
        lines.append("-" * 40)
        lines.append(f"IC等级: {grade}")

        lines.append("=" * 60)

        return "\n".join(lines)
```

#### 任务6.2：模型评估器

**文件位置**：`vnpy_china_ml/evaluation/validator.py`

```python
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sklearn.model_selection import cross_val_score, TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from ..evaluation.ic_ir import ICIRAnalyzer
from ..base.result import ModelPerformance


class ModelValidator:
    """
    模型验证器

    提供模型性能评估、交叉验证、稳定性分析等功能。
    """

    def __init__(self):
        """初始化验证器"""
        self.ic_ir_analyzer = ICIRAnalyzer()

    def validate_performance(
        self,
        model: Any,
        X: np.ndarray,
        y: np.ndarray,
        model_type: str = "classification",
        cv: int = 5
    ) -> ModelPerformance:
        """
        验证模型性能

        Args:
            model: 机器学习模型
            X: 特征数据
            y: 标签数据
            model_type: "classification" 或 "regression"
            cv: 交叉验证折数

        Returns:
            ModelPerformance对象
        """
        # 使用时间序列交叉验证
        tscv = TimeSeriesSplit(n_splits=cv)

        if model_type == "classification":
            # 分类指标
            scores = cross_val_score(model, X, y, cv=tscv, scoring='accuracy')
            accuracy = scores.mean()
            f1 = cross_val_score(model, X, y, cv=tscv, scoring='f1').mean()

            performance = ModelPerformance(
                return_value=0.0,  # 分类模型不使用return_value
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                accuracy=accuracy,
                f1_score=f1,
                precision=precision_score(model, X, y).mean(),
                recall=recall_score(model, X, y).mean(),
                mse=mean_squared_error(model, X, y),
                mae=mean_absolute_error(model, X, y),
                r2_score=r2_score(model, X, y)
            )

        else:
            # 回归指标
            scores = cross_val_score(model, X, y, cv=tscv, scoring='neg_mean_squared_error')
            mse = -scores.mean()  # 转为正值

            # 计算预测收益率序列
            y_pred = model.predict(X)
            returns = y_pred * 100  # 假设预测的是收益率

            # 计算回测指标（简化版）
            total_return = np.sum(returns) / len(returns)
            max_dd = self._calculate_max_drawdown(returns)
            sharpe = self._calculate_sharpe(returns)

            performance = ModelPerformance(
                return_value=total_return,
                sharpe_ratio=sharpe,
                max_drawdown=max_dd,
                calmar_ratio=total_return / max_dd if max_dd != 0 else 0,
                accuracy=0.0,
                f1_score=0.0,
                precision=0.0,
                recall=0.0,
                mse=mse,
                mae=mean_absolute_error(model, X, y),
                r2_score=r2_score(model, X, y)
            )

        return performance

    def _calculate_max_drawdown(self, returns: np.ndarray) -> float:
        """计算最大回撤"""
        peak = returns[0]
        max_dd = 0.0

        for r in returns:
            if r > peak:
                peak = r

            dd = (peak - r) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return max_dd

    def _calculate_sharpe(self, returns: np.ndarray) -> float:
        """计算夏普比率"""
        if len(returns) == 0:
            return 0.0

        avg_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # 年化
        annual_return = avg_return * 252
        annual_std = std_return * np.sqrt(252)

        sharpe = annual_return / annual_std if annual_std != 0 else 0
        return sharpe

    def calculate_ic_ir(
        self,
        model: Any,
        X: np.ndarray,
        y: np.ndarray
    ) -> Dict[str, float]:
        """
        计算IC/IR指标

        Args:
            model: 模型
            X: 特征数据
            y: 真实收益率

        Returns:
            IC/IR指标字典
        """
        # 获取预测
        predictions = model.predict(X)

        # 按时间序列组织（假设X已按时间排序）
        n_samples = len(predictions)
        n_dates = n_samples // 20  # 假设20个交易日为一个月

        prediction_series = []
        return_series = []

        for i in range(n_dates):
            start_idx = i * 20
            end_idx = start_idx + 20

            if end_idx <= n_samples:
                pred_month = predictions[start_idx:end_idx]
                ret_month = y[start_idx:end_idx]

                if len(pred_month) > 0 and len(ret_month) > 0:
                    prediction_series.append(pred_month)
                    return_series.append(ret_month)

        if prediction_series and return_series:
            result = self.ic_ir_analyzer.analyze(
                prediction_series, return_series
            )
            return {
                "ic_mean": result.get("ic_mean", 0),
                "rank_ic_mean": result.get("rank_ic_mean", 0),
                "ir": result.get("ir", 0),
                "positive_ic_ratio": result.get("positive_ic_ratio", 0)
            }
        else:
            return {
                "ic_mean": 0.0,
                "rank_ic_mean": 0.0,
                "ir": 0.0,
                "positive_ic_ratio": 0.0
            }

    def analyze_stability(
        self,
        model: Any,
        X: np.ndarray,
        y: np.ndarray,
        n_splits: int = 5
    ) -> Dict[str, Any]:
        """
        分析模型稳定性

        Args:
            model: 模型
            X: 特征数据
            y: 标签数据
            n_splits: 分割数

        Returns:
            稳定性分析结果
        """
        scores = []

        # 时间序列分割验证
        tscv = TimeSeriesSplit(n_splits=n_splits)

        for train_idx, test_idx in tscv.split(X):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y_test_idx]

            model_copy = self._clone_model(model)
            model_copy.fit(X_train, y_train)

            score = model_copy.score(X_test, y_test)
            scores.append(score)

        scores_array = np.array(scores)

        return {
            "mean_score": np.mean(scores_array),
            "std_score": np.std(scores_array),
            "min_score": np.min(scores_array),
            "max_score": np.max(scores_array),
            "score_range": np.max(scores_array) - np.min(scores_array),
            "stability_coefficient": np.std(scores_array) / np.mean(scores_array)
            if np.mean(scores_array) != 0 else 0
        }

    def _clone_model(self, model: Any) -> Any:
        """克隆模型"""
        # 使用sklearn的clone功能
        try:
            from sklearn.base import clone
            return clone(model)
        except:
            # 如果无法克隆，返回原模型
            return model

    def generate_validation_report(
        self,
        performance: ModelPerformance,
        ic_ir: Dict[str, float],
        stability: Dict[str, Any] = None
    ) -> str:
        """生成验证报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("模型验证报告")
        lines.append("=" * 60)
        lines.append("")

        # 1. 基础性能指标
        lines.append("一、基础性能")
        lines.append("-" * 40)
        if performance.accuracy > 0:
            lines.append(f"准确率: {performance.accuracy:.4f}")
            lines.append(f"精确率: {performance.precision:.4f}")
            lines.append(f"召回率: {performance.recall:.4f}")
            lines.append(f"F1分数: {performance.f1_score:.4f}")
        else:
            lines.append("收益率:")
            lines.append(f"总收益率: {performance.return_value:.2%}")
            lines.append(f"夏普比率: {performance.sharpe_ratio:.2f}")
            lines.append(f"最大回撤: {performance.max_drawdown:.2%}")
            lines.append(f"卡玛比率: {performance.calmar_ratio:.2f}")

        lines.append("")

        # 2. 预测误差
        lines.append("二、预测误差")
        lines.append("-" * 40)
        lines.append(f"均方误差(MSE): {performance.mse:.6f}")
        lines.append(f"平均绝对误差(MAE): {performance.mae:.6f}")
        lines.append(f"R²决定系数: {performance.r2_score:.4f}")

        lines.append("")

        # 3. IC/IR指标
        lines.append("三、IC/IR指标")
        lines.append("-" * 40)
        lines.append(f"IC均值: {ic_ir['ic_mean']:.4f}")
        lines.append(f"Rank IC均值: {ic_ir['rank_ic_mean']:.4f}")
        lines.append(f"IR: {ic_ir['ir']:.4f}")
        lines.append(f"IC>0占比: {ic_ir['positive_ic_ratio']:.2%}")

        lines.append()

        # 4. 稳定性分析
        if stability:
            lines.append("四、稳定性分析")
            lines.append("-" * 40)
            lines.append(f"稳定性系数: {stability['stability_coefficient']:.4f}")
            lines.append(f"分数范围: {stability['score_range']:.4f}")
            lines.append(f"最低分: {stability['min_score']:.4f}")
            lines.append(f"最高分: {stability['max_score']:.4f}")

        lines.append("=" * 60)

        return "\n".join(lines)
```

**验收标准**：
- [ ] IC/IR计算正确
- [ ] 模型验证全面
- [ ] 稳定性分析有效
- [ ] 测试用例通过

---

## 4. 测试计划

### 4.1 单元测试矩阵

| 模块 | 测试文件 | 用例数 | 覆盖目标 |
|------|---------|--------|---------|
| factors/base | test_base.py | 3 | 100% |
| factors/dragon_tiger | test_dragon_tiger.py | 5 | 90% |
| factors/northbound | test_northbound.py | 4 | 90% |
| factors/sector_rotation | test_sector_rotation.py | 4 | 90% |
| factors/limit_stats | test_limit_stats.py | 4 | 90% |
| model/adapters | test_adapters.py | 5 | 90% |
| model/online | test_online.py | 4 | 85% |
| strategy/china_ml_strategy | test_ml_strategy.py | 5 | 85% |
| evaluation/ic_ir | test_ic_ir.py | 4 | 95% |
| evaluation/validator | test_validator.py | 5 | 90% |
| **合计** | | **39** | **91%** |

### 4.2 集成测试

```python
# tests/ml_strategy/test_integration.py
import pytest
from datetime import datetime, timedelta
from vnpy_china_ml.dataset.china_dataset import ChinaAlphaDataset
from vnpy_china_ml.model.china_model import ChinaAlphaModel
from vnpy_china_ml.strategy.china_ml_strategy import ChinaMLStrategy
from vnpy_china_ml.evaluation.ic_ir import ICIRAnalyzer


def test_full_ml_workflow():
    """测试完整ML工作流程"""

    # 1. 创建数据集
    dataset = ChinaAlphaDataset()

    # 2. 添加A股因子
    dataset.add_dragon_tiger_factors(lookback=5)
    dataset.add_northbound_factors(lookback=5)
    dataset.add_sector_rotation_factors(lookback=20)

    # 3. 准备数据
    start_date = "2023-01-01"
    end_date = "2024-12-31"

    features = dataset.get_features(start_date, end_date)
    labels = dataset.get_labels(start_date, end_date)

    # 4. 训练模型
    model = ChinaAlphaModel(model_type="lightgbm")
    model.train_with_china_rules(
        dataset=dataset,
        start_date=start_date,
        end_date=end_date,
        consider_t1=True,
        consider_limit=True
    )

    # 5. 评估模型
    validator = ModelValidator()

    X_test = features[-252:]  # 最后一年作为测试集
    y_test = labels[-252:]

    performance = validator.validate_performance(
        model=model.get_model(),
        X=X_test,
        y=y_test,
        model_type="regression"
    )

    assert performance.return_value > 0

    # 6. IC/IR分析
    ic_ir = validator.calculate_ic_ir(
        model=model.get_model(),
        X=X_test,
        y=y_test
    )

    assert ic_ir["ic_mean"] > 0.03  # IC均值应大于3%

    print(f"测试完成！收益率: {performance.return_value:.2%}, IC: {ic_ir['ic_mean']:.4f}")


def test_online_learning():
    """测试在线学习"""

    # 模拟在线学习场景
    from vnpy_china_ml.model.online import OnlineLearningManager

    manager = OnlineLearningManager(
        retrain_interval=30,
        forget_ratio=0.1
    )

    # 模拟数据更新
    X_new = np.random.randn(30, 10)
    y_new = np.random.randn(30)

    manager.add_new_data(X_new, y_new)

    # 检查是否需要重训练
    should_retrain = manager.should_retrain(datetime.now())

    # 模拟重训练
    if should_retrain:
        print("需要重训练模型")
        # 这里会调用实际的incremental_train方法
```

---

## 5. 时间安排

### 5.1 日程计划

| 日期 | 任务 | 工时 |
|------|------|------|
| Day 1 | 基础框架+A股因子 | 8h |
| Day 2 | 龙虎榜+北向资金因子 | 8h |
| Day 3 | 板块轮动+涨跌停因子 | 8h |
| Day 4 | 模型适配器+在线学习 | 8h |
| Day 5 | ML策略模板+评估工具 | 8h |
| Day 6-7 | 集成测试+文档 | 16h |
| Day 8 | 与vnpy_china_data集成 | 8h |
| **合计** | | **64h (8人天)** |

### 5.2 里程碑

| 里程碑 | 时间 | 交付内容 |
|--------|------|---------|
| M1 | Day 1结束 | 基础框架+因子基类 |
| M2 | Day 3结束 | 所有A股因子实现 |
| M3 | Day 4结束 | 模型适配完成 |
| M4 | Day 5结束 | 策略模板+评估完成 |
| M5 | Day 7结束 | 集成测试完成 |
| M6 | Day 8结束 | 数据集成完成 |

---

## 6. 风险管理

### 6.1 技术风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| vnpy.alpha版本兼容 | 中 | 高 | 检查版本，提供兼容层 |
| 数据依赖 | 中 | 中 | 清晰定义数据接口 |
| 模型性能 | 高 | 高 | 充分测试和验证 |
| 过拟合风险 | 高 | 高 | 严格的过拟合检测 |

### 6.2 业务风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| 预测失效 | 高 | 高 | 设置置信度阈值 |
| 数据质量 | 中 | 中 | 数据清洗和验证 |
| A股规则变化 | 中 | 中 | 规则引擎抽象化 |

---

## 7. 验收标准

### 7.1 功能验收

- [ ] A股因子数量≥15个
- [ ] T+1规则适配正确
- [ ] 涨跌停适配正确
- [ ] 在线学习功能完整
- [ ] ML策略模板可用
- [ ] IC/IR分析准确

### 7.2 性能验收

| 指标 | 要求 | 测试方法 |
|------|------|---------|
| IC均值 | >0.03 | 历史数据回测 |
| IR | >1.0 | 历史数据回测 |
| 预测准确率 | >55% | 分类模型 |
| 在线学习延迟 | <10分钟 | 增量训练 |

### 7.3 质量验收

- [ ] 单元测试覆盖率≥90%
- [ ] 所有测试通过
- [ ] 代码通过类型检查
- [ ] 文档完整

---

## 8. 使用示例

### 8.1 完整工作流示例

```python
from vnpy_china_ml.dataset.china_dataset import ChinaAlphaDataset
from vnpy_china_ml.model.china_model import ChinaAlphaModel
from vnpy_china_ml.strategy.china_ml_strategy import ChinaMLStrategy


def main():
    """完整的ML策略训练和使用流程"""

    # 1. 创建数据集
    dataset = ChinaAlphaDataset()

    # 2. 添加A股特色因子
    dataset.add_dragon_tiger_factors(lookback=5)
    dataset.add_northbound_factors(lookback=5)
    dataset.add_sector_rotation_factors(lookback=20)
    dataset.add_technical_indicators()

    # 3. 准备训练数据
    start_date = "2023-01-01"
    end_date = "2024-12-31"

    X_train = dataset.get_features(start_date, end_date)
    y_train = dataset.get_labels(start_date, end_date)

    # 4. 训练模型（考虑A股规则）
    model = ChinaAlphaModel(model_type="lightgbm")
    model.train_with_china_rules(
        dataset=dataset,
        start_date=start_date,
        end_date=end_date,
        consider_t1=True,
        consider_limit=True
    )

    # 5. 评估模型
    from vnpy_china_ml.evaluation.validator import ModelValidator
    validator = ModelValidator()

    X_test = X_train[-252:]  # 最后一年作为测试集
    y_test = y_train[-252:]

    performance = validator.validate_performance(
        model=model.get_model(),
        X=X_test,
        y=y_test,
        model_type="regression"
    )

    print(f"模型收益率: {performance.return_value:.2%}")
    print(f"夏普比率: {performance.sharpe_ratio:.2f}")
    print(f"最大回撤: {performance.max_drawdown:.2%}")

    # 6. 保存模型
    from vnpy_china_ml.model.online import OnlineLearningManager
    manager = OnlineLearningManager()

    model_path = manager.save_model(
        model.get_model(),
        model_name="china_alpha_model",
        metadata={
            "trained_on": end_date,
            "factors": ["dragon_tiger", "northbound", "sector_rotation", "technical"],
            "performance": performance.to_dict()
        }
    )

    print(f"模型已保存到: {model_path}")

    # 7. 策略中使用
    # 实际使用中，ChinaMLStrategy会自动加载模型并生成交易信号


if __name__ == "__main__":
    main()
```

### 8.2 因子使用示例

```python
from vnpy_china_ml.factors.dragon_tiger import InstitutionNetBuyFactor
from vnpy_china_ml.factors.northbound import NorthboundNetInflowFactor
from vnpy_china_ml.factors.sector_rotation import SectorRelativeStrengthFactor

# 创建因子
institution_factor = InstitutionNetBuyFactor(lookback=5)
northbound_factor = NorthboundNetInflowFactor(lookback=5)
sector_factor = SectorRelativeStrengthFactor(lookback=20)

# 假设有DataFrame df包含必要的数据
# factor_values = institution_factor.calculate(df)
```

---

## 9. 后续计划

### 9.1 功能扩展

- [ ] 添加深度学习模型（Transformer、LSTM）
- [ ] 支持多因子模型集成
- [ ] 实现实盘自动重训练
- [ ] 添加特征重要性自动分析

### 9.2 优化方向

- [ ] 使用GPU加速训练
- [ ] 实现分布式训练
- [   优化因子计算效率
- [   支持实时因子更新

---

**文档版本**：v1.0
**创建日期**：2026-02-24
**维护者**：AI Assistant
**下次更新**：实施完成后更新
