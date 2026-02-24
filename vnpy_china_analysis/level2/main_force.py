"""
主力动向分析模块

分析主力资金的买卖情况，识别主力行为模式。
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from ..objects.types import MainForceData, TickFlowData
from ..base import RealtimeAnalyzer


class MainForceAnalyzer(RealtimeAnalyzer):
    """
    主力动向分析器

    分析主力资金的买卖情况，识别主力行为模式。
    """

    # 主力资金阈值配置
    LARGE_TRADE_THRESHOLD = 200000     # 大单阈值（元）
    MEDIUM_TRADE_THRESHOLD = 50000      # 中单阈值（元）

    def __init__(self, cache_size: int = 2000) -> None:
        super().__init__(cache_size)
        self.main_force_history: Dict[str, List[MainForceData]] = {}
        self.tick_data: Dict[str, List[TickFlowData]] = {}

    def analyze(self, symbol: str, data: Dict[str, Any]) -> MainForceData:
        """分析主力动向

        Args:
            symbol: 股票代码
            data: 包含逐笔成交数据的字典

        Returns:
            MainForceData对象
        """
        # 先更新逐笔数据
        if "tick" in data:
            tick = TickFlowData(
                symbol=symbol,
                datetime=data["tick"].get("datetime", datetime.now()),
                price=data["tick"].get("price", 0.0),
                volume=data["tick"].get("volume", 0),
                amount=data["tick"].get("amount", 0.0),
                direction=data["tick"].get("direction", "buy"),
                function_code=data["tick"].get("function_code", 0)
            )

            if symbol not in self.tick_data:
                self.tick_data[symbol] = []
            self.tick_data[symbol].append(tick)

            # 限制历史大小
            if len(self.tick_data[symbol]) > self.cache_size:
                self.tick_data[symbol] = self.tick_data[symbol][-self.cache_size:]

        # 计算主力动向
        return self.calculate_main_force(symbol)

    def calculate_main_force(self, symbol: str, minutes: int = 5) -> MainForceData:
        """计算主力动向

        根据逐笔成交数据计算主力资金动向。

        Args:
            symbol: 股票代码
            minutes: 统计分钟数

        Returns:
            MainForceData对象
        """
        if symbol not in self.tick_data or not self.tick_data[symbol]:
            return MainForceData(
                symbol=symbol,
                datetime=datetime.now()
            )

        now = datetime.now()
        cutoff_time = now - timedelta(minutes=minutes)

        # 筛选近期数据
        recent_ticks = [
            t for t in self.tick_data[symbol]
            if t.datetime >= cutoff_time
        ]

        if not recent_ticks:
            return MainForceData(
                symbol=symbol,
                datetime=now
            )

        # 分类统计
        buy_volume = 0
        sell_volume = 0

        for tick in recent_ticks:
            if tick.amount >= self.LARGE_TRADE_THRESHOLD:
                # 大单以上算作主力
                if tick.direction == "buy":
                    buy_volume += tick.volume
                else:
                    sell_volume += tick.volume

        net_volume = buy_volume - sell_volume
        total_volume = buy_volume + sell_volume

        # 计算主力净流入比例
        main_force_ratio = (net_volume / total_volume * 100) if total_volume > 0 else 0

        # 判断主力方向
        if net_volume > 0:
            direction = "buy"
        elif net_volume < 0:
            direction = "sell"
        else:
            direction = "neutral"

        main_force = MainForceData(
            symbol=symbol,
            datetime=now,
            buy_volume=buy_volume,
            sell_volume=sell_volume,
            net_volume=net_volume,
            main_force_ratio=main_force_ratio,
            direction=direction
        )

        # 保存到历史
        if symbol not in self.main_force_history:
            self.main_force_history[symbol] = []
        self.main_force_history[symbol].append(main_force)

        # 限制历史大小
        if len(self.main_force_history[symbol]) > self.cache_size:
            self.main_force_history[symbol] = self.main_force_history[symbol][-self.cache_size:]

        return main_force

    def get_main_force_trend(self, symbol: str, periods: int = 10) -> Dict[str, Any]:
        """获取主力动向趋势

        分析主力资金的持续情况。

        Args:
            symbol: 股票代码
            periods: 统计周期数

        Returns:
            主力动向趋势字典
        """
        if symbol not in self.main_force_history or not self.main_force_history[symbol]:
            return {}

        history = self.main_force_history[symbol][-periods:]

        if not history:
            return {}

        # 统计各方向的周期数
        buy_periods = sum(1 for h in history if h.direction == "buy")
        sell_periods = sum(1 for h in history if h.direction == "sell")
        neutral_periods = sum(1 for h in history if h.direction == "neutral")

        # 计算平均净流入
        avg_net = sum(h.net_volume for h in history) / len(history)

        # 判断趋势
        if buy_periods >= periods * 0.7:
            trend = "strong_buy"
        elif buy_periods > sell_periods:
            trend = "moderate_buy"
        elif sell_periods >= periods * 0.7:
            trend = "strong_sell"
        elif sell_periods > buy_periods:
            trend = "moderate_sell"
        else:
            trend = "neutral"

        return {
            "symbol": symbol,
            "periods": periods,
            "buy_periods": buy_periods,
            "sell_periods": sell_periods,
            "neutral_periods": neutral_periods,
            "avg_net_volume": avg_net,
            "trend": trend,
            "continuity": max(buy_periods, sell_periods) / periods if periods > 0 else 0
        }

    def detect_main_force_action(self, symbol: str) -> Dict[str, Any]:
        """检测主力动作

        识别主力是否在积极建仓或出货。

        Args:
            symbol: 股票代码

        Returns:
            主力动作字典
        """
        if symbol not in self.main_force_history or not self.main_force_history[symbol]:
            return {"action": "unknown"}

        recent = self.main_force_history[symbol][-5:]  # 最近5个周期
        if not recent:
            return {"action": "unknown"}

        # 计算总净流入
        total_net = sum(h.net_volume for h in recent)
        total_volume = sum(h.buy_volume + h.sell_volume for h in recent)

        # 计算流入强度
        intensity = abs(total_net) / total_volume * 100 if total_volume > 0 else 0

        if total_net > 0 and intensity > 30:
            action = "accumulating"  # 建仓
        elif total_net < 0 and intensity > 30:
            action = "distributing"  # 出货
        elif intensity > 50:
            action = "active"        # 活跃
        else:
            action = "quiet"         # 观望

        return {
            "action": action,
            "net_volume": total_net,
            "intensity": intensity,
            "direction": "buy" if total_net > 0 else "sell" if total_net < 0 else "neutral"
        }

    def compare_with_market(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """与市场对比

        对比个股主力动向与市场整体情况。

        Args:
            symbol: 股票代码
            market_data: 市场数据字典

        Returns:
            对比结果字典
        """
        if symbol not in self.main_force_history or not self.main_force_history[symbol]:
            return {}

        latest = self.main_force_history[symbol][-1]
        market_direction = market_data.get("direction", "neutral")

        # 计算相对强度
        relative_strength = 0
        if latest.direction == market_direction:
            relative_strength = 1.0
        elif latest.direction == "neutral" or market_direction == "neutral":
            relative_strength = 0.5
        else:
            relative_strength = -1.0

        return {
            "symbol": symbol,
            "main_force_direction": latest.direction,
            "market_direction": market_direction,
            "relative_strength": relative_strength,
            "outperforming": latest.direction == market_direction and latest.direction != "neutral"
        }
