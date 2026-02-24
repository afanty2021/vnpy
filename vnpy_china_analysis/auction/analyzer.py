"""
集合竞价综合分析器

整合所有集合竞价分析功能。
"""

from typing import Dict, Any, Optional
from datetime import datetime, date

from ..objects.types import AuctionData
from .volume_ratio import VolumeRatioCalculator
from .open_predict import OpenPricePredictor
from ..base import HistoricalAnalyzer


class AuctionAnalyzer(HistoricalAnalyzer):
    """
    集合竞价综合分析器

    整合集合竞价数据分析、量比计算、开盘预测等功能。
    """

    def __init__(self, cache_size: int = 500) -> None:
        super().__init__(cache_size)
        self.volume_ratio = VolumeRatioCalculator()
        self.predictor = OpenPricePredictor()

    def analyze(self, symbol: str, auction_data: Dict[str, Any]) -> AuctionData:
        """分析集合竞价数据

        Args:
            symbol: 股票代码
            auction_data: 集合竞价数据字典

        Returns:
            AuctionData对象
        """
        current_date = auction_data.get("date", date.today())
        pre_close = auction_data.get("pre_close", 0)
        auction_price = auction_data.get("auction_price", pre_close)
        auction_volume = auction_data.get("auction_volume", 0)
        auction_amount = auction_data.get("auction_amount", 0)

        # 计算量比
        volume_ratio = self.volume_ratio.calculate(
            symbol,
            auction_volume,
            auction_data.get("avg_volume")
        )

        # 委托数据
        total_buy = auction_data.get("total_buy_volume", 0)
        total_sell = auction_data.get("total_sell_volume", 0)

        # 计算竞价振幅
        amplitude = 0.0
        if pre_close > 0:
            amplitude = abs(auction_price - pre_close) / pre_close * 100

        # 买卖比
        buy_sell_ratio = 0.0
        if total_sell > 0:
            buy_sell_ratio = total_buy / total_sell

        # 创建数据对象
        data = AuctionData(
            symbol=symbol,
            date=current_date,
            pre_close=pre_close,
            auction_price=auction_price,
            auction_volume=auction_volume,
            auction_amount=auction_amount,
            total_buy_volume=total_buy,
            total_sell_volume=total_sell,
            buy_orders=auction_data.get("buy_orders", 0),
            sell_orders=auction_data.get("sell_orders", 0),
            volume_ratio=volume_ratio,
            amplitude=amplitude,
            buy_sell_ratio=buy_sell_ratio,
            open_prediction=auction_price  # 默认使用竞价成交价
        )

        # 保存到历史
        self.update_cache(symbol, {
            "date": current_date,
            "volume": auction_volume
        })

        return data

    def predict_open_price(self, symbol: str, auction_data: Dict[str, Any], market_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """预测开盘价

        Args:
            symbol: 股票代码
            auction_data: 集合竞价数据
            market_data: 市场数据（可选）

        Returns:
            预测结果
        """
        # 先分析竞价数据
        data = self.analyze(symbol, auction_data)

        # 添加量比数据
        auction_data["volume_ratio"] = data.volume_ratio

        # 预测开盘价
        prediction = self.predictor.predict(symbol, auction_data, market_data)

        # 更新开盘价预测
        data.open_prediction = prediction["predicted_price"]

        return prediction

    def get_auction_summary(self, symbol: str) -> Dict[str, Any]:
        """获取竞价汇总

        Args:
            symbol: 股票代码

        Returns:
            竞价汇总字典
        """
        cached = self.get_cached_data(symbol)

        if not cached:
            return {}

        # 获取最新数据
        latest = cached[-1]

        return {
            "symbol": symbol,
            "date": latest.get("date"),
            "volume_ratio_analysis": self.volume_ratio.analyze_volume_ratio(latest.get("volume_ratio", 1))
        }

    def get_volume_ratio(self, symbol: str, date: date) -> Optional[float]:
        """获取量比

        Args:
            symbol: 股票代码
            date: 日期

        Returns:
            量比值
        """
        # 这里需要实现具体的日期查询
        # 暂时返回None
        return None

    def get_comprehensive_analysis(self, symbol: str, auction_data: Dict[str, Any], market_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取综合分析

        Args:
            symbol: 股票代码
            auction_data: 集合竞价数据
            market_data: 市场数据（可选）

        Returns:
            综合分析字典
        """
        # 分析竞价数据
        data = self.analyze(symbol, auction_data)

        # 预测开盘价
        prediction = self.predict_open_price(symbol, auction_data, market_data)

        return {
            "symbol": symbol,
            "datetime": datetime.now(),
            "auction_data": {
                "pre_close": data.pre_close,
                "auction_price": data.auction_price,
                "auction_volume": data.auction_volume,
                "volume_ratio": data.volume_ratio,
                "amplitude": data.amplitude,
                "buy_sell_ratio": data.buy_sell_ratio,
                "total_buy_volume": data.total_buy_volume,
                "total_sell_volume": data.total_sell_volume
            },
            "prediction": prediction,
            "volume_analysis": self.volume_ratio.analyze_volume_ratio(data.volume_ratio)
        }
