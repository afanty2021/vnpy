"""
核心数据类型定义模块

本模块定义了机器学习策略系统中使用的所有核心数据类型，包括：
- 因子类型枚举
- 模型类型枚举
- 信号类型枚举
- 因子数据结构
- 预测结果结构
- 训练配置结构
- 回测结果结构
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Union
from enum import Enum


class FactorType(Enum):
    """因子类型枚举

    定义了策略中使用的各种因子类型：
    - TECHNICAL: 技术指标因子（如MACD、RSI、布林带等）
    - FUNDAMENTAL: 基本面因子（如市盈率、市净率等）
    - DRAGON_TIGER: 龙虎榜因子（龙虎榜机构买卖数据）
    - NORTHBOUND: 北向资金因子（沪股通/深股通资金流向）
    - SECTOR_ROTATION: 板块轮动因子（行业轮动特征）
    - LIMIT_STATS: 涨跌停统计因子（涨跌停相关统计）
    """

    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    DRAGON_TIGER = "dragon_tiger"
    NORTHBOUND = "northbound"
    SECTOR_ROTATION = "sector_rotation"
    LIMIT_STATS = "limit_stats"


class ModelType(Enum):
    """模型类型枚举

    定义了支持的机器学习/统计模型类型：
    - LIGHTGBM: LightGBM梯度提升模型
    - XGBOOST: XGBoost梯度提升模型
    - RANDOM_FOREST: 随机森林模型
    - LASSO: Lasso回归模型
    - RIDGE: Ridge回归模型
    - LSTM: LSTM神经网络模型
    """

    LIGHTGBM = "lightgbm"
    XGBOOST = "xgboost"
    RANDOM_FOREST = "random_forest"
    LASSO = "lasso"
    RIDGE = "ridge"
    LSTM = "lstm"


class SignalType(Enum):
    """交易信号类型枚举

    定义了模型输出的交易信号类型：
    - BUY: 买入信号
    - SELL: 卖出信号
    - HOLD: 持有信号
    - CLOSE: 平仓信号
    """

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


@dataclass
class FactorData:
    """因子数据

    用于存储单个因子的完整信息。

    Attributes:
        symbol: 股票代码（如 '000001.SZ'）
        datetime: 数据时间戳
        factor_name: 因子名称（如 'macd', 'rsi'）
        factor_type: 因子类型（来自FactorType枚举）
        value: 因子值
        importance: 因子重要性得分（0.0-1.0），默认0.0
    """

    symbol: str
    datetime: datetime
    factor_name: str
    factor_type: FactorType
    value: float
    importance: float = 0.0

    def __post_init__(self) -> None:
        """验证数据有效性"""
        if not self.symbol:
            raise ValueError("symbol不能为空")
        if self.importance < 0.0 or self.importance > 1.0:
            raise ValueError("importance必须在0.0-1.0之间")


@dataclass
class PredictionResult:
    """预测结果

    用于存储模型预测的完整结果。

    Attributes:
        symbol: 股票代码
        datetime: 预测时间戳
        predicted_return: 预测收益率（百分比或小数）
        confidence: 预测置信度（0.0-1.0）
        signal: 交易信号类型
        model_name: 模型名称
    """

    symbol: str
    datetime: datetime
    predicted_return: float
    confidence: float
    signal: SignalType
    model_name: str

    def __post_init__(self) -> None:
        """验证数据有效性"""
        if not self.symbol:
            raise ValueError("symbol不能为空")
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("confidence必须在0.0-1.0之间")
        if not isinstance(self.signal, SignalType):
            raise ValueError("signal必须是SignalType枚举类型")


@dataclass
class TrainingConfig:
    """训练配置

    用于配置模型训练的各项参数。

    Attributes:
        model_type: 模型类型（来自ModelType枚举）
        train_start: 训练集开始日期
        train_end: 训练集结束日期
        test_start: 测试集开始日期
        test_end: 测试集结束日期
        lookback_days: 回看天数（用于构建特征窗口），默认60天
        forward_days: 预测天数（预测未来N天的收益），默认5天
        min_samples: 最小样本数量要求，默认1000
    """

    model_type: ModelType
    train_start: date
    train_end: date
    test_start: date
    test_end: date
    lookback_days: int = 60
    forward_days: int = 5
    min_samples: int = 1000

    def __post_init__(self) -> None:
        """验证配置有效性"""
        if self.train_start >= self.train_end:
            raise ValueError("train_start必须早于train_end")
        if self.test_start >= self.test_end:
            raise ValueError("test_start必须早于test_end")
        if self.train_end > self.test_start:
            raise ValueError("训练集结束日期必须早于或等于测试集开始日期")
        if self.lookback_days <= 0:
            raise ValueError("lookback_days必须大于0")
        if self.forward_days <= 0:
            raise ValueError("forward_days必须大于0")
        if self.min_samples <= 0:
            raise ValueError("min_samples必须大于0")
        if not isinstance(self.model_type, ModelType):
            raise ValueError("model_type必须是ModelType枚举类型")

    @property
    def train_period_days(self) -> int:
        """训练周期天数"""
        return (self.train_end - self.train_start).days

    @property
    def test_period_days(self) -> int:
        """测试周期天数"""
        return (self.test_end - self.test_start).days


@dataclass
class BacktestResult:
    """回测结果

    用于存储完整的回测绩效指标。

    Attributes:
        start_date: 回测开始日期
        end_date: 回测结束日期
        total_return: 总收益率（百分比或小数）
        annual_return: 年化收益率（百分比或小数）
        sharpe_ratio: 夏普比率
        max_drawdown: 最大回撤（百分比或小数）
        win_rate: 胜率（0.0-1.0）
        total_trades: 总交易次数
    """

    start_date: date
    end_date: date
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int

    def __post_init__(self) -> None:
        """验证数据有效性"""
        if self.total_trades < 0:
            raise ValueError("total_trades不能为负数")
        if self.win_rate < 0.0 or self.win_rate > 1.0:
            raise ValueError("win_rate必须在0.0-1.0之间")

    @property
    def backtest_period_days(self) -> int:
        """回测周期天数"""
        return (self.end_date - self.start_date).days

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            包含所有回测指标的字典
        """
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_return": self.total_return,
            "annual_return": self.annual_return,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "period_days": self.backtest_period_days,
        }
