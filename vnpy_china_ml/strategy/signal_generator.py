"""
信号生成器模块

本模块提供了交易信号的生成、过滤和合并功能：
- SignalGenerator: 基础信号生成器
- AdaptiveSignalGenerator: 自适应阈值信号生成器
- MultiSignalGenerator: 多因子信号生成器

主要功能：
- 基于预测收益率和置信度生成交易信号
- 根据持仓和交易限制过滤信号
- 合并多个信号源的信号
"""

from typing import Dict, List, Optional
import numpy as np

from ..utils.types import SignalType, PredictionResult


class SignalGenerator:
    """信号生成器

    基于模型预测结果生成交易信号的核心类。支持：
    - 可配置的买入/卖出阈值
    - 置信度过滤
    - 持仓和交易限制检查

    Attributes:
        threshold_buy: 买入信号阈值（预测收益率大于此值时考虑买入）
        threshold_sell: 卖出信号阈值（预测收益率小于此值时考虑卖出）
        min_confidence: 最小置信度要求

    Example:
        >>> from vnpy_china_ml.strategy.signal_generator import SignalGenerator
        >>> from vnpy_china_ml.utils.types import SignalType
        >>>
        >>> # 创建信号生成器
        >>> generator = SignalGenerator(threshold_buy=0.6, threshold_sell=-0.6)
        >>>
        >>> # 生成信号
        >>> signal = generator.generate_signal(predicted_return=0.8, confidence=0.7)
        >>> print(signal)  # SignalType.BUY
    """

    def __init__(
        self,
        threshold_buy: float = 0.6,
        threshold_sell: float = -0.6,
        min_confidence: float = 0.5
    ):
        """初始化信号生成器

        Args:
            threshold_buy: 买入信号阈值，默认为0.6（60%）
            threshold_sell: 卖出信号阈值，默认为-0.6（-60%）
            min_confidence: 最小置信度要求，默认为0.5（50%）
        """
        self.threshold_buy = threshold_buy
        self.threshold_sell = threshold_sell
        self.min_confidence = min_confidence

    def generate_signal(
        self,
        predicted_return: float,
        confidence: float
    ) -> SignalType:
        """生成交易信号

        基于预测收益率和置信度生成交易信号。

        Args:
            predicted_return: 预测收益率（-1.0到1.0之间，或使用百分比）
            confidence: 预测置信度（0.0到1.0之间）

        Returns:
            SignalType: 交易信号类型
        """
        # 置信度检查
        if confidence < self.min_confidence:
            return SignalType.HOLD

        # 买入条件：预测收益率大于买入阈值且置信度足够
        if predicted_return > self.threshold_buy and confidence >= self.min_confidence:
            return SignalType.BUY

        # 卖出条件：预测收益率小于卖出阈值且置信度足够
        if predicted_return < self.threshold_sell and confidence >= self.min_confidence:
            return SignalType.SELL

        # 其他情况持有
        return SignalType.HOLD

    def generate_signal_from_prediction(self, prediction: PredictionResult) -> SignalType:
        """从预测结果生成信号

        直接使用PredictionResult对象生成信号。

        Args:
            prediction: 预测结果对象

        Returns:
            SignalType: 交易信号类型
        """
        return self.generate_signal(prediction.predicted_return, prediction.confidence)

    def filter_signal(
        self,
        signal: SignalType,
        position: int,
        can_buy: bool,
        can_sell: bool
    ) -> SignalType:
        """过滤信号

        根据当前持仓状态和交易限制过滤信号。
        例如：有持仓时不允许买入，无持仓时不允许卖出。

        Args:
            signal: 原始交易信号
            position: 当前持仓数量
            can_buy: 是否允许买入
            can_sell: 是否允许卖出

        Returns:
            SignalType: 过滤后的信号
        """
        if signal == SignalType.BUY:
            # 有持仓时不再买入
            if position > 0:
                return SignalType.HOLD
            # 检查是否允许买入
            if not can_buy:
                return SignalType.HOLD

        if signal == SignalType.SELL:
            # 无持仓时无法卖出
            if position <= 0:
                return SignalType.HOLD
            # 检查是否允许卖出
            if not can_sell:
                return SignalType.HOLD

        if signal == SignalType.CLOSE:
            # 平仓信号：无持仓时转为HOLD
            if position <= 0:
                return SignalType.HOLD

        return signal

    def filter_signal_with_price_limit(
        self,
        signal: SignalType,
        is_limit_up: bool,
        is_limit_down: bool
    ) -> SignalType:
        """根据涨跌停状态过滤信号

        涨停时不能买入，跌停时不能卖出。

        Args:
            signal: 原始交易信号
            is_limit_up: 是否涨停
            is_limit_down: 是否跌停

        Returns:
            SignalType: 过滤后的信号
        """
        if signal == SignalType.BUY and is_limit_up:
            # 涨停时不能买入
            return SignalType.HOLD

        if signal == SignalType.SELL and is_limit_down:
            # 跌停时不能卖出
            return SignalType.HOLD

        return signal

    def combine_signals(self, signals: List[SignalType]) -> SignalType:
        """合并多个信号

        当存在多个信号时，采用以下优先级：
        1. 如果存在BUY信号，返回BUY
        2. 如果存在SELL信号，返回SELL
        3. 如果存在CLOSE信号，返回CLOSE
        4. 否则返回HOLD

        Args:
            signals: 信号列表

        Returns:
            SignalType: 合并后的信号
        """
        if not signals:
            return SignalType.HOLD

        # 优先级：BUY > SELL > CLOSE > HOLD
        if SignalType.BUY in signals:
            return SignalType.BUY
        if SignalType.SELL in signals:
            return SignalType.SELL
        if SignalType.CLOSE in signals:
            return SignalType.CLOSE

        return SignalType.HOLD

    def combine_signals_with_weight(
        self,
        signals: List[SignalType],
        weights: Optional[List[float]] = None
    ) -> SignalType:
        """加权合并多个信号

        根据权重计算综合信号得分，返回得分最高的信号。

        Args:
            signals: 信号列表
            weights: 权重列表，与signals一一对应

        Returns:
            SignalType: 加权合并后的信号
        """
        if not signals:
            return SignalType.HOLD

        # 如果没有提供权重，使用等权重
        if weights is None:
            weights = [1.0] * len(signals)

        if len(signals) != len(weights):
            raise ValueError("signals和weights长度必须一致")

        # 计算每种信号的加权得分
        signal_scores = {
            SignalType.BUY: 0.0,
            SignalType.SELL: 0.0,
            SignalType.CLOSE: 0.0,
            SignalType.HOLD: 0.0
        }

        for signal, weight in zip(signals, weights):
            signal_scores[signal] += weight

        # 返回得分最高的信号
        max_signal = SignalType.HOLD
        max_score = signal_scores[SignalType.HOLD]

        for signal, score in signal_scores.items():
            if score > max_score:
                max_score = score
                max_signal = signal

        return max_signal

    def get_signal_info(self) -> Dict[str, float]:
        """获取信号生成器配置信息

        Returns:
            Dict[str, float]: 配置信息字典
        """
        return {
            "threshold_buy": self.threshold_buy,
            "threshold_sell": self.threshold_sell,
            "min_confidence": self.min_confidence
        }

    def set_thresholds(self, threshold_buy: float, threshold_sell: float) -> None:
        """设置信号阈值

        Args:
            threshold_buy: 新的买入阈值
            threshold_sell: 新的卖出阈值
        """
        if threshold_buy <= threshold_sell:
            raise ValueError("买入阈值必须大于卖出阈值")
        self.threshold_buy = threshold_buy
        self.threshold_sell = threshold_sell

    def __repr__(self) -> str:
        """返回信号生成器的字符串表示"""
        return (
            f"SignalGenerator("
            f"threshold_buy={self.threshold_buy}, "
            f"threshold_sell={self.threshold_sell}, "
            f"min_confidence={self.min_confidence})"
        )


class AdaptiveSignalGenerator(SignalGenerator):
    """自适应阈值信号生成器

    根据市场状态动态调整阈值的信号生成器。
    在市场波动较大时自动收紧阈值，在市场平稳时放松阈值。

    Attributes:
        volatility: 市场波动率
        base_threshold_buy: 基础买入阈值
        base_threshold_sell: 基础卖出阈值
    """

    def __init__(
        self,
        threshold_buy: float = 0.6,
        threshold_sell: float = -0.6,
        min_confidence: float = 0.5,
        volatility_adjust: bool = True
    ):
        """初始化自适应信号生成器

        Args:
            threshold_buy: 基础买入阈值
            threshold_sell: 基础卖出阈值
            min_confidence: 最小置信度
            volatility_adjust: 是否启用波动率调整
        """
        super().__init__(threshold_buy, threshold_sell, min_confidence)
        self.volatility_adjust = volatility_adjust
        self.base_threshold_buy = threshold_buy
        self.base_threshold_sell = threshold_sell
        self.volatility: float = 0.0

    def update_volatility(self, returns: np.ndarray) -> None:
        """更新市场波动率

        Args:
            returns: 收益率数组
        """
        if len(returns) > 0:
            self.volatility = float(np.std(returns))

    def generate_signal(
        self,
        predicted_return: float,
        confidence: float
    ) -> SignalType:
        """生成交易信号（带波动率调整）

        如果启用波动率调整，会根据波动率调整阈值。

        Args:
            predicted_return: 预测收益率
            confidence: 置信度

        Returns:
            SignalType: 交易信号
        """
        if not self.volatility_adjust or self.volatility == 0:
            return super().generate_signal(predicted_return, confidence)

        # 波动率调整系数（波动率越大，阈值越高）
        adjustment_factor = 1.0 + self.volatility

        adjusted_threshold_buy = self.base_threshold_buy * adjustment_factor
        adjusted_threshold_sell = self.base_threshold_sell * adjustment_factor

        # 使用调整后的阈值生成信号
        if confidence < self.min_confidence:
            return SignalType.HOLD

        if predicted_return > adjusted_threshold_buy:
            return SignalType.BUY

        if predicted_return < adjusted_threshold_sell:
            return SignalType.SELL

        return SignalType.HOLD


class MultiSignalGenerator:
    """多信号生成器

    支持多个信号源的管理和组合。
    """

    def __init__(self):
        """初始化多信号生成器"""
        self.signal_generators: List[SignalGenerator] = []

    def add_generator(self, generator: SignalGenerator) -> None:
        """添加信号生成器

        Args:
            generator: 信号生成器实例
        """
        self.signal_generators.append(generator)

    def remove_generator(self, generator: SignalGenerator) -> None:
        """移除信号生成器

        Args:
            generator: 信号生成器实例
        """
        if generator in self.signal_generators:
            self.signal_generators.remove(generator)

    def generate_signals(
        self,
        predicted_return: float,
        confidence: float
    ) -> List[SignalType]:
        """生成所有信号的列表

        Args:
            predicted_return: 预测收益率
            confidence: 置信度

        Returns:
            List[SignalType]: 所有信号生成器的信号列表
        """
        return [
            gen.generate_signal(predicted_return, confidence)
            for gen in self.signal_generators
        ]

    def generate_combined_signal(
        self,
        predicted_return: float,
        confidence: float
    ) -> SignalType:
        """生成组合信号

        合并所有信号生成器的结果。

        Args:
            predicted_return: 预测收益率
            confidence: 置信度

        Returns:
            SignalType: 组合后的信号
        """
        signals = self.generate_signals(predicted_return, confidence)

        # 使用第一个生成器的合并逻辑
        if self.signal_generators:
            return self.signal_generators[0].combine_signals(signals)

        return SignalType.HOLD

    def __len__(self) -> int:
        """返回信号生成器数量"""
        return len(self.signal_generators)
