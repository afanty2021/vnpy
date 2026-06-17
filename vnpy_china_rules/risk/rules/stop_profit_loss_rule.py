"""
止损止盈风控规则

实现单笔/移动/组合止损
"""

from vnpy.trader.object import OrderRequest, TradeData, OrderData, TickData
from vnpy.trader.constant import Direction, Status
from vnpy_riskmanager.template import RuleTemplate
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from vnpy_china_rules.risk._helpers import get_first_account


@dataclass
class StopLossRecord:
    """止损止盈记录"""
    vt_symbol: str
    direction: Direction
    entry_price: float           # 入场价格
    volume: int                  # 持仓数量
    stop_loss_price: float       # 止损价
    stop_profit_price: float     # 止盈价
    trailing_stop_price: float   # 移动止损价
    entry_time: datetime         # 入场时间
    highest_price: float = 0    # 最高价（用于移动止损）
    lowest_price: float = 0     # 最低价（用于移动止损）


class StopProfitLossRule(RuleTemplate):
    """止损止盈风控规则"""

    name: str = "A股止损止盈"

    parameters: dict[str, str] = {
        "enable_stop_loss": "启用止损",
        "stop_loss_ratio": "止损比例",
        "enable_stop_profit": "启用止盈",
        "stop_profit_ratio": "止盈比例",
        "enable_trailing_stop": "启用移动止损",
        "trailing_stop_ratio": "移动止损比例",
        "enable_combo_stop": "启用组合止损",
        "combo_stop_ratio": "组合止损比例",
    }

    variables: dict[str, str] = {
        "total_pnl": "总盈亏",
        "daily_pnl": "当日盈亏",
        "stop_loss_count": "止损次数",
        "stop_profit_count": "止盈次数",
    }

    def on_init(self) -> None:
        """初始化"""
        # 参数
        self.enable_stop_loss: bool = True
        self.stop_loss_ratio: float = 0.05          # 止损5%

        self.enable_stop_profit: bool = True
        self.stop_profit_ratio: float = 0.10        # 止盈10%

        self.enable_trailing_stop: bool = False
        self.trailing_stop_ratio: float = 0.03      # 移动止损3%

        self.enable_combo_stop: bool = False
        self.combo_stop_ratio: float = 0.08         # 组合止损8%

        # 运行时状态
        self.positions: dict[str, StopLossRecord] = {}
        self.total_pnl: float = 0.0
        self.daily_pnl: float = 0.0
        self.stop_loss_count: int = 0
        self.stop_profit_count: int = 0
        self.consecutive_losses: int = 0            # 连续亏损次数
        self.last_trade_pnl: float = 0.0            # 上笔交易盈亏
        self.last_date: datetime = datetime.now()  # 上次检查日期

    def check_allowed(self, req: OrderRequest, gateway_name: str) -> bool:
        """开仓前检查"""
        # 开仓不涉及止损止盈检查
        return True

    def on_trade(self, trade: TradeData) -> None:
        """成交推送 - 记录入场"""
        key = f"{trade.vt_symbol}_{trade.direction}"

        if trade.direction == Direction.LONG:
            # 买入开仓 - 记录入场信息
            self.positions[key] = StopLossRecord(
                vt_symbol=trade.vt_symbol,
                direction=trade.direction,
                entry_price=trade.price,
                volume=trade.volume,
                stop_loss_price=trade.price * (1 - self.stop_loss_ratio),
                stop_profit_price=trade.price * (1 + self.stop_profit_ratio),
                trailing_stop_price=0,
                entry_time=trade.datetime,
                highest_price=trade.price,
                lowest_price=trade.price,
            )
        else:
            # 卖出平仓 - 清除入场记录
            if key in self.positions:
                # 计算盈亏
                record = self.positions[key]
                pnl = (trade.price - record.entry_price) * trade.volume
                self.total_pnl += pnl
                self.daily_pnl += pnl
                self.last_trade_pnl = pnl

                # 更新连续亏损计数
                if pnl < 0:
                    self.consecutive_losses += 1
                else:
                    self.consecutive_losses = 0

                # 更新止损止盈统计
                if pnl < 0:
                    self.stop_loss_count += 1
                else:
                    self.stop_profit_count += 1

                del self.positions[key]

        self.put_event()

    def on_tick(self, tick: TickData) -> None:
        """行情推送 - 检查止损止盈"""
        # 遍历所有持仓，检查是否触发止损止盈
        keys_to_close = []

        for key, record in self.positions.items():
            if record.direction != Direction.LONG:
                continue

            # 更新最高/最低价
            if tick.last_price > record.highest_price:
                record.highest_price = tick.last_price

                # 更新移动止损价
                if self.enable_trailing_stop:
                    record.trailing_stop_price = record.highest_price * (
                        1 - self.trailing_stop_ratio
                    )

            # 检查止损
            if self.enable_stop_loss:
                if tick.last_price <= record.stop_loss_price:
                    keys_to_close.append((key, "止损"))

            # 检查止盈
            if self.enable_stop_profit:
                if tick.last_price >= record.stop_profit_price:
                    keys_to_close.append((key, "止盈"))

            # 检查移动止损
            if self.enable_trailing_stop and record.trailing_stop_price > 0:
                if tick.last_price <= record.trailing_stop_price:
                    keys_to_close.append((key, "移动止损"))

        # 执行平仓（这里只是记录日志，实际平仓由策略执行）
        for key, reason in keys_to_close:
            record = self.positions[key]
            self.write_log(
                f"触发{reason}：{record.vt_symbol}，当前价{tick.last_price}，"
                f"止损价{record.stop_loss_price}，止盈价{record.stop_profit_price}"
            )

    def on_timer(self) -> None:
        """定时检查组合止损"""
        if self.enable_combo_stop:
            account = get_first_account(self.risk_engine.main_engine)
            if account:
                # 计算当前资金比例
                current_ratio = (account.balance - account.frozen) / account.balance

                if current_ratio < (1 - self.combo_stop_ratio):
                    self.write_log(
                        f"触发组合止损：资金比例{current_ratio:.2%}，"
                        f"低于止损比例{self.combo_stop_ratio:.2%}"
                    )
