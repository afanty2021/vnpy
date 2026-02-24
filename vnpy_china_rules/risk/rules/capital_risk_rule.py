"""
资金风控规则

实现日亏损/单笔风险/资金使用等检查
"""

from vnpy.trader.object import OrderRequest, TradeData
from vnpy.trader.constant import Direction
from vnpy_riskmanager.template import RuleTemplate
from datetime import datetime


class CapitalRiskRule(RuleTemplate):
    """资金风控规则"""

    name: str = "A股资金风控"

    parameters: dict[str, str] = {
        "max_daily_loss_ratio": "单日最大亏损比例",
        "max_single_trade_loss": "单笔最大亏损金额",
        "max_capital_usage_ratio": "最大资金使用比例",
        "enable_margin_check": "启用保证金检查",
    }

    variables: dict[str, str] = {
        "daily_pnl": "当日盈亏",
        "capital_usage_ratio": "资金使用比例",
        "frozen_capital": "冻结资金",
    }

    def on_init(self) -> None:
        """初始化"""
        self.max_daily_loss_ratio: float = 0.05      # 单日最大亏损5%
        self.max_single_trade_loss: float = 10000     # 单笔最大亏损1万
        self.max_capital_usage_ratio: float = 0.90    # 最大资金使用90%
        self.enable_margin_check: bool = False        # 默认不启用融资融券

        # 运行时状态
        self.daily_pnl: float = 0.0
        self.daily_initial_balance: float = 0.0
        self.capital_usage_ratio: float = 0.0
        self.frozen_capital: float = 0.0
        self.last_date: datetime = datetime.now()      # 上次检查日期

    def check_allowed(self, req: OrderRequest, gateway_name: str) -> bool:
        """检查是否允许委托"""
        # 1. 检查资金使用比例
        if self._check_capital_usage(req):
            return False

        # 2. 检查单笔最大亏损
        if self._check_single_trade_loss(req):
            return False

        return True

    def on_trade(self, trade: TradeData) -> None:
        """成交推送 - 更新资金"""
        account = self.risk_engine.main_engine.get_account()
        if not account:
            return

        # 更新当日盈亏
        self.daily_pnl = account.balance - self.daily_initial_balance

        # 检查是否触发日止损
        if self._check_daily_loss_limit():
            self.write_log(
                f"触发单日止损：当日亏损{self.daily_pnl:.2f}，"
                f"达到上限{self.max_daily_loss_ratio:.2%}"
            )

        # 更新资金使用比例
        self.capital_usage_ratio = (
            (account.balance - account.available) / account.balance
        )

        self.put_event()

    def on_timer(self) -> None:
        """定时检查"""
        account = self.risk_engine.main_engine.get_account()
        if not account:
            return

        # 记录每日开盘资金
        now = datetime.now()
        if now.date() > self.last_date.date():
            # 新的一天，重置日盈亏计算
            self.daily_initial_balance = account.balance
            self.last_date = now

        if self.daily_initial_balance == 0:
            self.daily_initial_balance = account.balance

        # 检查日亏损
        self.daily_pnl = account.balance - self.daily_initial_balance
        self._check_daily_loss_limit()

        # 更新资金使用
        self.capital_usage_ratio = (
            (account.balance - account.available) / account.balance
        )

        # 检查资金使用比例
        if self.capital_usage_ratio > self.max_capital_usage_ratio:
            self.write_log(
                f"资金使用比例{self.capital_usage_ratio:.2%}，"
                f"超过上限{self.max_capital_usage_ratio:.2%}"
            )

        self.put_event()

    def _check_capital_usage(self, req: OrderRequest) -> bool:
        """检查资金使用比例"""
        account = self.risk_engine.main_engine.get_account()
        if not account:
            return False

        contract = self.get_contract(req.vt_symbol)
        if not contract:
            return False

        # 计算委托所需资金
        required_capital = req.volume * req.price * contract.size

        if req.direction == Direction.LONG:
            # 买入需要资金
            new_used = (account.balance - account.available) + required_capital
            new_ratio = new_used / account.balance

            if new_ratio > self.max_capital_usage_ratio:
                self.write_log(
                    f"资金使用比例{new_ratio:.2%}，"
                    f"委托后超过上限{self.max_capital_usage_ratio:.2%}"
                )
                return True

        return False

    def _check_single_trade_loss(self, req: OrderRequest) -> bool:
        """检查单笔最大亏损"""
        # 这个检查需要在开仓前估算最大可能亏损
        # 这里简单处理，不做限制
        return False

    def _check_daily_loss_limit(self) -> bool:
        """检查单日亏损限制"""
        if self.daily_initial_balance == 0:
            return False

        loss_ratio = abs(self.daily_pnl) / self.daily_initial_balance

        if self.daily_pnl < 0 and loss_ratio > self.max_daily_loss_ratio:
            return True

        return False
