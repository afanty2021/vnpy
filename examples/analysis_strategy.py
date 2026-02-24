"""
vnpy_china_analysis 策略示例

展示如何使用行情分析模块构建交易策略。
"""
from datetime import datetime
from vnpy_china_analysis.level2 import Level2Analyzer
from vnpy_china_analysis.money_flow import MoneyFlowAnalyzer
from vnpy_china_analysis.objects.types import TickFlowData


class MainForceInflowStrategy:
    """
    主力流入策略

    当主力资金持续流入且主力方向为买入时，产生买入信号。
    """

    def __init__(self, inflow_threshold: float = 1000000):
        """
        Args:
            inflow_threshold: 主力流入阈值（元）
        """
        self.level2 = Level2Analyzer()
        self.money_flow = MoneyFlowAnalyzer()
        self.inflow_threshold = inflow_threshold
        self.tick_history = {}

    def on_tick(self, symbol: str, tick_data: dict) -> str:
        """
        处理tick数据

        Args:
            symbol: 股票代码
            tick_data: tick数据字典

        Returns:
            交易信号: BUY/SELL/HOLD
        """
        # 更新Level-2分析
        self.level2.update(symbol, tick_data)

        # 更新资金流向
        tick = TickFlowData(
            symbol=symbol,
            datetime=tick_data.get("datetime", datetime.now()),
            price=tick_data.get("price", 0.0),
            volume=tick_data.get("volume", 0),
            amount=tick_data.get("amount", 0.0),
            direction=tick_data.get("direction", "buy"),
            function_code=tick_data.get("function_code", 1)
        )

        if symbol not in self.tick_history:
            self.tick_history[symbol] = []
        self.tick_history[symbol].append(tick)

        # 分析
        main_force = self.level2.get_main_force(symbol)
        money_flow = self.money_flow.analyze(symbol, self.tick_history[symbol][-100:])

        # 判断信号
        if (main_force.direction == "buy" and
            money_flow.main_inflow > self.inflow_threshold):
            return "BUY"
        elif (main_force.direction == "sell" and
              money_flow.main_inflow < -self.inflow_threshold):
            return "SELL"

        return "HOLD"


class LimitUpBreakoutStrategy:
    """
    涨停突破策略

    检测涨停板突破和连板机会。
    """

    def __init__(self):
        from vnpy_china_analysis.technical import LimitStatsAnalyzer
        self.analyzer = LimitStatsAnalyzer()

    def on_bar(self, symbol: str, bar_data: dict) -> str:
        """
        处理K线数据

        Args:
            symbol: 股票代码
            bar_data: K线数据

        Returns:
            交易信号
        """
        # 更新涨跌停统计
        is_limit_up = bar_data.get("is_limit_up", False)
        is_limit_down = bar_data.get("is_limit_down", False)

        self.analyzer.update(symbol, is_limit_up, is_limit_down)

        # 获取统计数据
        stats = self.analyzer.get_limit_stats(symbol)

        # 连板买入
        if stats.continuous_limit_up >= 2:
            return "BUY"

        # 跌停止损
        if stats.is_limit_down:
            return "SELL"

        return "HOLD"


class AuctionOpeningStrategy:
    """
    竞价开盘策略

    基于集合竞价数据预测开盘并制定交易计划。
    """

    def __init__(self):
        from vnpy_china_analysis.auction import AuctionAnalyzer
        self.analyzer = AuctionAnalyzer()

    def on_auction(self, symbol: str, auction_data: dict) -> dict:
        """
        处理竞价数据

        Args:
            symbol: 股票代码
            auction_data: 竞价数据

        Returns:
            交易计划字典
        """
        # 分析竞价
        auction = self.analyzer.analyze(symbol, auction_data)

        # 生成交易计划
        plan = {
            "symbol": symbol,
            "predicted_open": auction.open_prediction,
            "volume_ratio": auction.volume_ratio,
            "action": "HOLD",
            "reason": ""
        }

        # 量比大且高开
        if auction.volume_ratio > 2.0 and auction.open_prediction > auction.pre_close:
            plan["action"] = "BUY"
            plan["reason"] = "高开量比大，看多"

        # 量比大且低开
        elif auction.volume_ratio > 2.0 and auction.open_prediction < auction.pre_close:
            plan["action"] = "SELL"
            plan["reason"] = "低开量比大，看空"

        return plan


# 使用示例
if __name__ == "__main__":
    # 创建策略实例
    strategy = MainForceInflowStrategy(inflow_threshold=5000000)

    # 模拟tick数据
    tick_data = {
        "datetime": datetime.now(),
        "price": 10.5,
        "volume": 10000,
        "amount": 105000,
        "direction": "buy",
        "function_code": 1
    }

    # 处理tick
    signal = strategy.on_tick("000001", tick_data)
    print(f"交易信号: {signal}")
