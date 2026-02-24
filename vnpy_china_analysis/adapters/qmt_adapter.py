"""
QMT数据适配器

适配QMT行情数据到分析模块。
"""

from typing import Dict, Any, Optional, List
from datetime import datetime


class QmtDataAdapter:
    """
    QMT数据适配器

    将QMT的行情数据转换为分析模块所需的格式。
    """

    def __init__(self) -> None:
        """构造函数"""
        pass

    def adapt_tick_data(self, qmt_data: Dict[str, Any]) -> Dict[str, Any]:
        """适配分时数据

        Args:
            qmt_data: QMT原始数据

        Returns:
            适配后的数据字典
        """
        return {
            "symbol": qmt_data.get("stock_code", ""),
            "datetime": qmt_data.get("time", datetime.now()),
            "price": qmt_data.get("price", 0.0),
            "volume": qmt_data.get("volume", 0),
            "amount": qmt_data.get("turnover", 0.0),
            "open": qmt_data.get("open", 0.0),
            "high": qmt_data.get("high", 0.0),
            "low": qmt_data.get("low", 0.0),
            "close": qmt_data.get("close", 0.0),
            "pre_close": qmt_data.get("pre_close", 0.0)
        }

    def adapt_order_queue(self, qmt_data: Dict[str, Any]) -> Dict[str, Any]:
        """适配委托队列数据

        Args:
            qmt_data: QMT原始数据

        Returns:
            适配后的数据字典
        """
        # 提取十档数据
        ask_prices = []
        ask_volumes = []
        bid_prices = []
        bid_volumes = []

        for i in range(1, 11):
            ask_price = qmt_data.get(f"ask_{i}_price", 0.0)
            ask_volume = qmt_data.get(f"ask_{i}_volume", 0)
            bid_price = qmt_data.get(f"bid_{i}_price", 0.0)
            bid_volume = qmt_data.get(f"bid_{i}_volume", 0)

            ask_prices.append(ask_price)
            ask_volumes.append(ask_volume)
            bid_prices.append(bid_price)
            bid_volumes.append(bid_volume)

        return {
            "symbol": qmt_data.get("stock_code", ""),
            "datetime": qmt_data.get("time", datetime.now()),
            "ask_prices": ask_prices,
            "ask_volumes": ask_volumes,
            "bid_prices": bid_prices,
            "bid_volumes": bid_volumes,
            "ask_queue": [],  # QMT可能不提供明细
            "bid_queue": []
        }

    def adapt_tick_flow(self, qmt_data: Dict[str, Any]) -> Dict[str, Any]:
        """适配逐笔成交数据

        Args:
            qmt_data: QMT原始数据

        Returns:
            适配后的数据字典
        """
        direction = "buy"
        if qmt_data.get("trade_direction") == "S":
            direction = "sell"

        return {
            "symbol": qmt_data.get("stock_code", ""),
            "datetime": qmt_data.get("time", datetime.now()),
            "price": qmt_data.get("price", 0.0),
            "volume": qmt_data.get("volume", 0),
            "amount": qmt_data.get("amount", 0.0),
            "direction": direction,
            "function_code": qmt_data.get("function_code", 0)
        }

    def adapt_auction_data(self, qmt_data: Dict[str, Any]) -> Dict[str, Any]:
        """适配集合竞价数据

        Args:
            qmt_data: QMT原始数据

        Returns:
            适配后的数据字典
        """
        return {
            "symbol": qmt_data.get("stock_code", ""),
            "date": qmt_data.get("date", datetime.now().date()),
            "pre_close": qmt_data.get("pre_close", 0.0),
            "auction_price": qmt_data.get("auction_price", qmt_data.get("pre_close", 0.0)),
            "auction_volume": qmt_data.get("auction_volume", 0),
            "auction_amount": qmt_data.get("auction_amount", 0.0),
            "total_buy_volume": qmt_data.get("total_buy_volume", 0),
            "total_sell_volume": qmt_data.get("total_sell_volume", 0),
            "buy_orders": qmt_data.get("buy_orders", 0),
            "sell_orders": qmt_data.get("sell_orders", 0)
        }

    def adapt_level2_data(self, qmt_data: Dict[str, Any]) -> Dict[str, Any]:
        """适配完整的Level-2数据

        Args:
            qmt_data: QMT原始数据

        Returns:
            适配后的数据字典
        """
        return {
            "symbol": qmt_data.get("stock_code", ""),
            "datetime": qmt_data.get("time", datetime.now()),
            "order_queue": self.adapt_order_queue(qmt_data),
            "tick": self.adapt_tick_flow(qmt_data)
        }

    def convert_to_analysis_format(self, qmt_data: Dict[str, Any], data_type: str = "tick") -> Dict[str, Any]:
        """转换为分析模块所需格式

        Args:
            qmt_data: QMT原始数据
            data_type: 数据类型 (tick, order_queue, tick_flow, auction)

        Returns:
            适配后的数据字典
        """
        if data_type == "tick":
            return self.adapt_tick_data(qmt_data)
        elif data_type == "order_queue":
            return self.adapt_order_queue(qmt_data)
        elif data_type == "tick_flow":
            return self.adapt_tick_flow(qmt_data)
        elif data_type == "auction":
            return self.adapt_auction_data(qmt_data)
        elif data_type == "level2":
            return self.adapt_level2_data(qmt_data)
        else:
            return qmt_data
