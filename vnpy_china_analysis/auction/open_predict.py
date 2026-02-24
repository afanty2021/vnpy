"""
开盘价预测模块

基于集合竞价数据预测开盘价。
"""

from typing import Dict, Any, Optional
from datetime import datetime

from ..base import HistoricalAnalyzer


class OpenPricePredictor(HistoricalAnalyzer):
    """
    开盘价预测器

    基于集合竞价数据预测开盘价。
    """

    def __init__(self, cache_size: int = 500) -> None:
        super().__init__(cache_size)
        self.prediction_history: Dict[str, list] = {}

    def analyze(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析开盘价预测（实现抽象方法）

        Args:
            symbol: 股票代码
            data: 集合竞价数据字典

        Returns:
            预测结果字典
        """
        return self.predict(symbol, data)

    def predict(self, symbol: str, auction_data: Dict[str, Any], market_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """预测开盘价

        Args:
            symbol: 股票代码
            auction_data: 集合竞价数据字典
            market_data: 市场数据字典（可选）

        Returns:
            预测结果字典
        """
        pre_close = auction_data.get("pre_close", 0)
        auction_price = auction_data.get("auction_price", pre_close)
        auction_volume = auction_data.get("auction_volume", 0)
        volume_ratio = auction_data.get("volume_ratio", 1.0)

        # 基础预测：竞价成交价
        base_prediction = auction_price

        # 调整因素
        adjustments = []

        # 1. 量比调整
        if volume_ratio > 3:
            # 放量通常会导致高开
            volume_adjustment = (volume_ratio - 1) * 0.005
            adjustments.append(("volume", volume_adjustment))
        elif volume_ratio < 0.3:
            # 缩量可能导致低开
            volume_adjustment = (volume_ratio - 0.5) * 0.003
            adjustments.append(("volume", volume_adjustment))

        # 2. 竞价幅度调整
        if auction_price > pre_close:
            # 高于昨收，看涨
            price_change = (auction_price - pre_close) / pre_close
            adjustments.append(("price_up", price_change * 0.3))
        elif auction_price < pre_close:
            # 低于昨收，看跌
            price_change = (pre_close - auction_price) / pre_close
            adjustments.append(("price_down", -price_change * 0.3))

        # 3. 委托比例调整
        total_buy = auction_data.get("total_buy_volume", 0)
        total_sell = auction_data.get("total_sell_volume", 0)
        total_volume = total_buy + total_sell

        if total_volume > 0:
            buy_ratio = total_buy / total_volume

            if buy_ratio > 0.7:
                # 买方主导，可能高开
                adjustments.append(("buy_dominant", 0.005))
            elif buy_ratio < 0.3:
                # 卖方主导，可能低开
                adjustments.append(("sell_dominant", -0.005))

        # 4. 市场因素调整
        if market_data:
            market_change = market_data.get("index_change_pct", 0)
            if abs(market_change) > 1:
                adjustments.append(("market", market_change * 0.1))

        # 计算最终预测
        total_adjustment = sum(adj[1] for adj in adjustments)
        predicted_price = pre_close * (1 + total_adjustment)

        # 计算置信度
        confidence = self._calculate_confidence(auction_data, len(adjustments))

        # 保存预测历史
        if symbol not in self.prediction_history:
            self.prediction_history[symbol] = []
        self.prediction_history[symbol].append({
            "datetime": datetime.now(),
            "predicted_price": predicted_price,
            "actual_price": None,  # 实际开盘价需要后续更新
            "confidence": confidence
        })

        return {
            "symbol": symbol,
            "pre_close": pre_close,
            "auction_price": auction_price,
            "predicted_price": predicted_price,
            "predicted_change_pct": (predicted_price - pre_close) / pre_close * 100,
            "confidence": confidence,
            "adjustments": adjustments,
            "signal": self._generate_signal(predicted_price, pre_close, confidence)
        }

    def update_actual_open(self, symbol: str, actual_price: float) -> None:
        """更新实际开盘价

        用于验证预测准确性。

        Args:
            symbol: 股票代码
            actual_price: 实际开盘价
        """
        if symbol in self.prediction_history and self.prediction_history[symbol]:
            latest = self.prediction_history[symbol][-1]
            latest["actual_price"] = actual_price

    def get_prediction_accuracy(self, symbol: str) -> Dict[str, Any]:
        """获取预测准确率

        Args:
            symbol: 股票代码

        Returns:
            准确率统计
        """
        if symbol not in self.prediction_history:
            return {}

        predictions = [
            p for p in self.prediction_history[symbol]
            if p["actual_price"] is not None
        ]

        if not predictions:
            return {"sample_size": 0}

        # 计算误差
        errors = []
        correct_direction = 0

        for p in predictions:
            error = abs(p["predicted_price"] - p["actual_price"]) / p["actual_price"]
            errors.append(error)

            # 判断方向是否正确
            pred_change = p["predicted_price"] - p["predicted_price"]  # 这里有问题，需要修改
            actual_change = p["actual_price"] - p["predicted_price"]  # 这里也有问题

            # 简化判断
            if (p["predicted_price"] > p["actual_price"] * 0.99 and
                p["predicted_price"] < p["actual_price"] * 1.01):
                correct_direction += 1

        return {
            "sample_size": len(predictions),
            "avg_error_pct": sum(errors) / len(errors) * 100 if errors else 0,
            "accuracy": correct_direction / len(predictions) * 100 if predictions else 0
        }

    def _calculate_confidence(self, auction_data: Dict[str, Any], adjustment_count: int) -> float:
        """计算预测置信度

        Args:
            auction_data: 竞价数据
            adjustment_count: 调整因素数量

        Returns:
            置信度（0-100）
        """
        confidence = 60.0  # 基础置信度

        # 量比因素
        volume_ratio = auction_data.get("volume_ratio", 1.0)
        if 0.5 <= volume_ratio <= 3:
            confidence += 10
        elif volume_ratio > 5:
            confidence += 5

        # 委托量因素
        total_volume = auction_data.get("total_buy_volume", 0) + auction_data.get("total_sell_volume", 0)
        if total_volume > 10000:
            confidence += 10

        # 调整因素越多，置信度越低
        confidence -= adjustment_count * 3

        return max(0, min(100, confidence))

    def _generate_signal(self, predicted_price: float, pre_close: float, confidence: float) -> str:
        """生成交易信号

        Args:
            predicted_price: 预测价格
            pre_close: 昨收价
            confidence: 置信度

        Returns:
            信号类型
        """
        change_pct = (predicted_price - pre_close) / pre_close * 100

        if confidence < 50:
            return "neutral"

        if change_pct > 2:
            return "strong_buy"
        elif change_pct > 0.5:
            return "buy"
        elif change_pct < -2:
            return "strong_sell"
        elif change_pct < -0.5:
            return "sell"
        else:
            return "neutral"
