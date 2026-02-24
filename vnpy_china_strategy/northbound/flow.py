"""
北向资金流向策略

根据北向资金整体净流入情况调整仓位。
"""

from typing import Dict, Optional, List
from datetime import datetime, date, timedelta

from vnpy.trader.object import BarData

from vnpy_china_strategy.template import ChinaStrategyTemplate
from vnpy_china_strategy.base import RiskControlMixin, PositionManager
from vnpy_china_strategy.northbound.models import NorthboundFlow
from vnpy_china_strategy.config import NorthboundConfig


class NorthboundFlowStrategy(ChinaStrategyTemplate, RiskControlMixin):
    """北向资金流向策略

    策略逻辑：
    1. 监控北向资金整体净流入
    2. 净流入放大时买入大盘股
    3. 净流出时减仓

    参数：
    - net_inflow_threshold: 净流入阈值(亿)
    - market_filter: 市场筛选 (沪深300/中证500/全部)
    - position_ratio: 仓位比例
    """

    parameters = [
        "net_inflow_threshold",
        "market_filter",
        "position_ratio",
    ]

    variables = [
        "daily_net_inflow",
        "signal",
        "position",
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 策略参数
        self.net_inflow_threshold = setting.get("net_inflow_threshold", 10.0)  # 10亿
        self.market_filter = setting.get("market_filter", "沪深300")
        self.position_ratio = setting.get("position_ratio", 0.15)

        # 策略变量
        self.daily_net_inflow: float = 0.0
        self.signal: str = "HOLD"
        self.position: int = 0

        # 持仓管理
        self.position_manager = PositionManager()

        # 配置
        self.config = NorthboundConfig()

    def on_init(self):
        """策略初始化"""
        self.write_log("北向资金流向策略初始化")

    def on_start(self):
        """策略启动"""
        self.write_log("北向资金流向策略启动")

    def on_bar(self, bar: BarData):
        """K线推送"""
        current_date = bar.datetime.date()

        # 获取北向资金流向
        flow = self._get_northbound_flow(current_date)

        if not flow:
            return

        # 判断信号
        self._process_flow_signal(flow)

    def _get_northbound_flow(self, trade_date: date) -> Optional[NorthboundFlow]:
        """获取北向资金流向"""
        if not self.data_service:
            return None

        try:
            data = self.data_service.get_northbound_flow(trade_date)
            if data:
                return NorthboundFlow.from_dict(data)
        except Exception:
            pass
        return None

    def _process_flow_signal(self, flow: NorthboundFlow):
        """处理资金流向信号

        Args:
            flow: 北向资金流向数据
        """
        # 转换为亿元
        net_inflow_billion = float(flow.net_inflow) / 1e8

        # 记录
        self.daily_net_inflow = net_inflow_billion

        # 判断信号
        if net_inflow_billion > self.net_inflow_threshold:
            # 大额净流入 - 买入
            self.signal = "BUY"
            self._adjust_position(1)
        elif net_inflow_billion < -self.net_inflow_threshold:
            # 大额净流出 - 卖出
            self.signal = "SELL"
            self._adjust_position(-1)
        else:
            # 观望
            self.signal = "HOLD"

        self.write_log(
            f"北向资金: {net_inflow_billion:.2f}亿, 信号: {self.signal}"
        )

    def _adjust_position(self, direction: int):
        """调整仓位

        Args:
            direction: 1=买入, -1=卖出, 0=保持
        """
        if direction == 0:
            return

        # 获取标的代码
        target_symbol = self._get_target_symbol()
        if not target_symbol:
            return

        current_price = self.get_current_price(target_symbol)
        if not current_price:
            return

        # 计算目标仓位
        account = self.cta_engine.get_account() if self.cta_engine else None
        if not account:
            return

        target_value = account.available * self.position_ratio * direction
        target_volume = int(target_value / current_price / 100) * 100

        if target_volume <= 0:
            return

        # 执行交易
        exchange = self._get_exchange_from_symbol(target_symbol)
        vt_symbol = f"{target_symbol}.{exchange.value}"

        if direction > 0:
            # 买入
            if hasattr(self, "buy"):
                self.buy(current_price, target_volume, vt_symbol)
            self.position = target_volume
        else:
            # 卖出
            if hasattr(self, "sell"):
                self.sell(current_price, abs(target_volume), vt_symbol)
            self.position = 0

    def _get_target_symbol(self) -> str:
        """获取目标股票代码

        根据市场筛选条件返回对应的ETF或大盘股代码。
        """
        # 这里简化实现，返回沪深300ETF
        if self.market_filter == "沪深300":
            return "510300"  # 沪深300ETF
        elif self.market_filter == "中证500":
            return "510500"  # 中证500ETF
        else:
            return "510300"  # 默认沪深300ETF
