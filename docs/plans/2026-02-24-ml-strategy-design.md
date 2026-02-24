# 机器学习策略设计文档

> 文档版本：v1.1
> 创建日期：2026-02-24
> 更新日期：2026-02-24
> 需求编号：REQ-011
> 优先级：P2
> 预计工时：8人天（原12人天，因复用vnpy.alpha减少4人天）
>
> **变更记录**:
> - v1.1: 明确扩展vnpy.alpha模块而非重新实现
> - v1.0: 初始版本

---

## 1. 设计目标

**扩展VeighNa现有的vnpy.alpha模块**，添加A股特色功能：

1. **A股特征扩展**：龙虎榜因子、北向资金因子、板块轮动因子
2. **A股模型适配**：适应T+1、涨跌停等交易规则
3. **在线学习支持**：增量训练、模型更新
4. **A股评估指标**：A股特有的IC/IR分析、换手率等

### 1.1 与vnpy.alpha的关系

VeighNa的alpha模块已提供：
- `AlphaDataset`：特征工程和数据管理
- `AlphaModel`：模型训练和预测
- `BacktestingEngine`：回测引擎

**本模块将扩展而非替代**：

| vnpy.alpha现有功能 | 本模块扩展内容 |
|------------------|--------------|
| Alpha 158因子集 | 添加A股特色因子（龙虎榜、北向资金） |
| Lasso/LightGBM/MLP | 添加A股交易规则适配器 |
| 基础回测 | 集成A股交易成本和规则 |
| 基础评估 | 扩展IC/IR分析、A股特有指标 |

---

## 2. 架构设计

### 2.1 整体架构（扩展模式）

```
┌─────────────────────────────────────────────────────────────────┐
│                   vnpy.alpha 扩展架构                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  【vnpy.alpha 原有模块】                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ AlphaDataset: 158因子集、表达式引擎、时序/截面函数       │   │
│  │ AlphaModel: Lasso/LightGBM/MLP 模型训练                  │   │
│  │ BacktestingEngine: 标准回测引擎                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  【本模块扩展内容】                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ChinaAlphaDataset: 扩展数据集                             │   │
│  │  • add_dragon_tiger_factors()    龙虎榜因子              │   │
│  │  • add_northbound_factors()      北向资金因子            │   │
│  │  • add_sector_rotation_factors() 板块轮动因子           │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ChinaAlphaModel: 扩展模型                                │   │
│  │  • train_with_china_rules()     考虑A股交易规则          │   │
│  │  • predict_with_t1()           T+1规则预测               │   │
│  │  • incremental_train()         在线学习                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ChinaBacktesting: 扩展回测                               │   │
│  │  • ChinaTradingCost()          A股交易成本               │   │
│  │  • T1Rule()                    T+1规则                   │   │
│  │  • PriceLimitRule()            涨跌停处理               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块结构

```
vnpy_china_ml/
├── __init__.py
├── dataset/
│   ├── __init__.py
│   └── china_dataset.py      # 扩展AlphaDataset，添加A股因子
├── model/
│   ├── __init__.py
│   └── china_model.py        # 扩展AlphaModel，适配A股规则
├── factors/
│   ├── __init__.py
│   ├── dragon_tiger.py      # 龙虎榜因子
│   ├── northbound.py        # 北向资金因子
│   ├── sector_rotation.py   # 板块轮动因子
│   └── limit_stats.py       # 涨跌停统计因子
├── evaluation/
│   ├── __init__.py
│   └── china_metrics.py     # A股特有评估指标
└── strategy/
    ├── __init__.py
    └── china_ml_strategy.py # A股ML策略模板
```

---

## 3. 核心类设计

### 3.1 扩展数据集类

```python
from vnpy.alpha.dataset import AlphaDataset
from vnpy_china_interface import IDragonTigerProvider, INorthboundProvider
from vnpy_china_data import ChinaDataService


class ChinaAlphaDataset(AlphaDataset):
    """A股数据集 - 扩展AlphaDataset"""

    def __init__(self):
        super().__init__()
        # 获取A股特色数据服务
        self.dragon_tiger_provider: IDragonTigerProvider = ChinaDataService()
        self.northbound_provider: INorthboundProvider = ChinaDataService()

    def add_dragon_tiger_factors(self, lookback: int = 5):
        """添加龙虎榜因子"""
        from .factors.dragon_tiger import (
            InstitutionNetBuyFactor,
            BrokerNetBuyFactor,
            BuyRatioFactor
        )

        self.add_feature(InstitutionNetBuyFactor(lookback=lookback))
        self.add_feature(BrokerNetBuyFactor(lookback=lookback))
        self.add_feature(BuyRatioFactor(lookback=lookback))

    def add_northbound_factors(self, lookback: int = 5):
        """添加北向资金因子"""
        from .factors.northbound import (
            NorthboundNetInflowFactor,
            HoldingChangeFactor,
            SectorPreferenceFactor
        )

        self.add_feature(NorthboundNetInflowFactor(lookback=lookback))
        self.add_feature(HoldingChangeFactor(lookback=lookback))
        self.add_feature(SectorPreferenceFactor(lookback=lookback))

    def add_sector_rotation_factors(self, lookback: int = 20):
        """添加板块轮动因子"""
        from .factors.sector_rotation import (
            SectorRelativeStrengthFactor,
            SectorMomentumFactor,
            SectorFlowFactor
        )

        self.add_feature(SectorRelativeStrengthFactor(lookback=lookback))
        self.add_feature(SectorMomentumFactor(lookback=lookback))
        self.add_feature(SectorFlowFactor(lookback=lookback))
```

### 3.2 A股因子示例

```python
import polars as pl
from vnpy.alpha.dataset import BaseFactor


class InstitutionNetBuyFactor(BaseFactor):
    """机构净买入因子"""

    def __init__(self, lookback: int = 5):
        super().__init__()
        self.lookback = lookback

    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """计算机构净买入因子"""
        # 从vnpy_china_data获取龙虎榜数据
        # 这里简化为示例
        return df["institution_net_buy"].rolling(self.lookback).sum()


class NorthboundNetInflowFactor(BaseFactor):
    """北向资金净流入因子"""

    def __init__(self, lookback: int = 5):
        super().__init__()
        self.lookback = lookback

    def calculate(self, df: pl.DataFrame) -> pl.Series:
        """计算北向资金净流入因子"""
        return df["northbound_net_inflow"].rolling(self.lookback).sum()
```

### 3.3 扩展模型类

```python
from vnpy.alpha.model import AlphaModel
from typing import Optional
import numpy as np


class ChinaAlphaModel(AlphaModel):
    """A股模型 - 扩展AlphaModel"""

    def __init__(self, model_type: str = "lightgbm", **kwargs):
        super().__init__(model_type, **kwargs)

    def train_with_china_rules(
        self,
        dataset: ChinaAlphaDataset,
        start_date: str,
        end_date: str,
        consider_t1: bool = True,
        consider_limit: bool = True
    ):
        """考虑A股交易规则进行训练"""

        # 获取基础特征和标签
        X = dataset.get_features(start_date, end_date)
        y = dataset.get_labels(start_date, end_date)

        # 如果考虑T+1规则，调整标签
        if consider_t1:
            y = self._adjust_t1_label(y)

        # 如果考虑涨跌停，调整样本权重
        sample_weight = None
        if consider_limit:
            sample_weight = self._get_limit_sample_weight(X)

        # 训练模型
        self.model.fit(X, y, sample_weight=sample_weight)

    def _adjust_t1_label(self, y: np.ndarray) -> np.ndarray:
        """调整标签以适应T+1规则"""
        # T+1：当日买入次日才能卖出
        # 将标签向后移动一天
        return np.roll(y, 1)

    def _get_limit_sample_weight(self, X: np.ndarray) -> np.ndarray:
        """获取涨跌停样本权重"""
        # 涨跌停日的样本权重降低
        # 因为这些日子无法交易
        weights = np.ones(len(X))
        # 实现细节...
        return weights

    def incremental_train(
        self,
        X_new: np.ndarray,
        y_new: np.ndarray,
        forget_ratio: float = 0.1
    ):
        """增量训练"""
        # 获取当前模型参数
        if hasattr(self.model, "feature_importances_"):
            # 使用现有模型作为热启动
            pass

        # 合并新旧数据
        # 可选：遗忘部分旧数据
        # 训练更新
        self.model.fit(X_new, y_new)
```

### 3.4 技术指标特征（保留原设计）

```python
import pandas as pd
import numpy as np


class TechnicalFeature(BaseFeature):
    """技术指标特征"""

    name = "technical"

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标特征"""

        features = pd.DataFrame(index=data.index)

        # 移动平均
        features['ma5'] = data['close'].rolling(5).mean()
        features['ma10'] = data['close'].rolling(10).mean()
        features['ma20'] = data['close'].rolling(20).mean()

        # 动量指标
        features['momentum_5'] = data['close'] / data['close'].shift(5) - 1
        features['momentum_10'] = data['close'] / data['close'].shift(10) - 1
        features['momentum_20'] = data['close'] / data['close'].shift(20) - 1

        # 波动率
        features['volatility_5'] = data['close'].pct_change().rolling(5).std()
        features['volatility_20'] = data['close'].pct_change().rolling(20).std()

        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = data['close'].ewm(span=12).mean()
        ema26 = data['close'].ewm(span=26).mean()
        features['macd'] = ema12 - ema26
        features['macd_signal'] = features['macd'].ewm(span=9).mean()

        # 成交量特征
        features['volume_ma5'] = data['volume'].rolling(5).mean()
        features['volume_ratio'] = data['volume'] / features['volume_ma5']

        return features
```

### 3.3 分类模型

```python
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from xgboost import XGBClassifier


class MLClassifier:
    """机器学习分类器"""

    def __init__(self, model_type: str = "xgboost", **params):
        self.model_type = model_type

        if model_type == "random_forest":
            self.model = RandomForestClassifier(**params)
        elif model_type == "xgboost":
            self.model = XGBClassifier(**params, use_label_encoder=False, eval_metric='logloss')
        elif model_type == "svm":
            self.model = SVC(**params)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def train(self, X_train: np.ndarray, y_train: np.ndarray):
        """训练模型"""
        self.model.fit(X_train, y_train)

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        """预测"""
        return self.model.predict(X_test)

    def predict_proba(self, X_test: np.ndarray) -> np.ndarray:
        """预测概率"""
        if hasattr(self.model, 'predict_proba'):
            return self.model.predict_proba(X_test)
        else:
            # 对于SVM等不支持概率的模型
            predictions = self.predict(X_test)
            return np.column_stack([1 - predictions, predictions])
```

### 3.4 回归模型

```python
from sklearn.linear_model import Lasso, Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from lightgbm import LGBMRegressor


class MLRegressor:
    """机器学习回归器"""

    def __init__(self, model_type: str = "lightgbm", **params):
        self.model_type = model_type

        if model_type == "lasso":
            self.model = Lasso(**params)
        elif model_type == "ridge":
            self.model = Ridge(**params)
        elif model_type == "random_forest":
            self.model = RandomForestRegressor(**params)
        elif model_type == "lightgbm":
            self.model = LGBMRegressor(**params)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def train(self, X_train: np.ndarray, y_train: np.ndarray):
        """训练模型"""
        self.model.fit(X_train, y_train)

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        """预测"""
        return self.model.predict(X_test)

    def get_feature_importance(self) -> np.ndarray:
        """获取特征重要性"""
        if hasattr(self.model, 'feature_importances_'):
            return self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            return np.abs(self.model.coef_)
        return None
```

### 3.5 深度学习模型

```python
import torch
import torch.nn as nn


class LSTMModel(nn.Module):
    """LSTM预测模型"""

    def __init__(self, input_size: int, hidden_size: int = 64, num_layers: int = 2):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True
        )

        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        # x shape: (batch, seq_len, input_size)
        lstm_out, _ = self.lstm(x)
        # 取最后一个时刻的输出
        out = self.fc(lstm_out[:, -1, :])
        return out


class TransformerModel(nn.Module):
    """Transformer预测模型"""

    def __init__(self, input_size: int, d_model: int = 64, nhead: int = 4):
        super().__init__()

        self.embedding = nn.Linear(input_size, d_model)
        self.transformer = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(d_model, nhead),
            num_layers=2
        )
        self.fc = nn.Linear(d_model, 1)

    def forward(self, x):
        # x shape: (batch, seq_len, input_size)
        x = self.embedding(x)
        x = self.transformer(x)
        out = self.fc(x[:, -1, :])
        return out
```

### 3.6 IC/IR分析

```python
import numpy as np
from typing import List


class ICIRAnalyzer:
    """IC/IR分析器"""

    def __init__(self):
        self.ic_values: List[float] = []
        self.ir_values: List[float] = []

    def calculate_ic(
        self,
        predictions: np.ndarray,
        actual_returns: np.ndarray
    ) -> float:
        """计算IC（Information Coefficient）"""
        return np.corrcoef(predictions, actual_returns)[0, 1]

    def calculate_rank_ic(
        self,
        predictions: np.ndarray,
        actual_returns: np.ndarray
    ) -> float:
        """计算Rank IC"""
        from scipy.stats import spearmanr
        return spearmanr(predictions, actual_returns)[0]

    def calculate_ir(
        self,
        ic_series: List[float]
    ) -> float:
        """计算IR（Information Ratio）"""
        ic_array = np.array(ic_series)
        return np.mean(ic_array) / np.std(ic_array) if np.std(ic_array) != 0 else 0

    def analyze(
        self,
        prediction_series: List[np.ndarray],
        return_series: List[np.ndarray]
    ) -> dict:
        """综合分析"""

        # 计算每个时间点的IC
        ic_values = []
        for pred, ret in zip(prediction_series, return_series):
            if len(pred) > 0 and len(ret) > 0:
                ic = self.calculate_ic(pred, ret)
                ic_values.append(ic)

        return {
            "ic_mean": np.mean(ic_values),
            "ic_std": np.std(ic_values),
            "ic_ir": self.calculate_ir(ic_values),
            "ic_positive_ratio": np.mean([ic > 0 for ic in ic_values]),
            "rank_ic_mean": np.mean([self.calculate_rank_ic(p, r)
                                     for p, r in zip(prediction_series, return_series)])
        }
```

### 3.7 ML策略模板

```python
from vnpy_ctastrategy import CtaTemplate


class MLStrategy(CtaTemplate):
    """机器学习策略模板"""

    parameters = [
        "model_type",           # 模型类型
        "features",             # 特征列表
        "prediction_window",   # 预测窗口
        "train_interval",      # 训练间隔
        "position_size",       # 仓位大小
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.model = None
        self.feature_engine = FeatureEngine()
        self.last_train_time = None

    def on_bar(self, bar: BarData):
        """K线推送"""

        # 1. 准备特征
        features = self.prepare_features(bar)

        # 2. 模型预测
        signal = self.predict_signal(features)

        # 3. 执行交易
        if signal > 0.5:
            self.buy(bar.close_price, self.position_size)
        elif signal < -0.5:
            self.sell(bar.close_price, self.position_size)

        # 4. 定期重训练
        if self.should_retrain():
            self.retrain_model()

    def prepare_features(self, bar: BarData) -> np.ndarray:
        """准备特征"""
        # 获取历史数据并计算特征
        pass

    def predict_signal(self, features: np.ndarray) -> float:
        """预测信号"""
        if self.model is None:
            return 0
        return self.model.predict(features)[0]

    def should_retrain(self) -> bool:
        """是否应该重训练"""
        return False

    def retrain_model(self):
        """重训练模型"""
        # 获取训练数据
        X, y = self.prepare_training_data()

        # 训练模型
        self.model.train(X, y)
        self.last_train_time = datetime.now()
```

---

## 4. 实施计划

| 阶段 | 任务 | 预估工时 |
|------|------|---------|
| 1 | 创建目录结构和基类 | 0.5人天 |
| 2 | 实现龙虎榜因子 | 1人天 |
| 3 | 实现北向资金和板块因子 | 1人天 |
| 4 | 扩展AlphaModel，添加A股规则适配 | 1.5人天 |
| 5 | 实现A股ML策略模板 | 1人天 |
| 6 | 集成测试和文档 | 2人天 |
| 7 | 与vnpy_china_data集成 | 1人天 |
| 合计 | | **8人天** |

> 注：由于复用vnpy.alpha现有功能，工时从12人天减少到8人天

---

## 5. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.1 | 2026-02-24 | 明确扩展vnpy.alpha而非重新实现 |
| v1.0 | 2026-02-24 | 初始版本 |
