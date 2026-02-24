"""
仓位控制风控规则

实现单股/总仓位/行业/数量限制
"""

from vnpy.trader.object import OrderRequest, TradeData, PositionData, ContractData
from vnpy.trader.constant import Direction
from vnpy_riskmanager.template import RuleTemplate


class PositionControlRule(RuleTemplate):
    """仓位控制风控规则"""

    name: str = "A股仓位控制"

    parameters: dict[str, str] = {
        "max_single_position_ratio": "单股最大仓位比例",
        "max_total_position_ratio": "总仓位最大比例",
        "max_industry_ratio": "单一行业最大比例",
        "max_holdings": "最大持仓股票数",
        "enable_industry_check": "启用行业检查",
    }

    variables: dict[str, str] = {
        "current_total_ratio": "当前总仓位比例",
        "current_positions": "当前持仓数",
    }

    def on_init(self) -> None:
        """初始化参数"""
        # 默认配置
        self.max_single_position_ratio: float = 0.20      # 单股最大20%
        self.max_total_position_ratio: float = 0.80       # 总仓位最大80%
        self.max_industry_ratio: float = 0.40             # 单一行业最大40%
        self.max_holdings: int = 10                       # 最多持仓10只
        self.enable_industry_check: bool = False          # 默认不启用行业检查

        # 运行时状态
        self.current_total_ratio: float = 0.0
        self.current_positions: int = 0
        self.position_data: dict[str, PositionData] = {}

        # 引用风控管理器（用于发送告警）
        self._risk_manager = None

    def set_risk_manager(self, risk_manager):
        """设置风控管理器引用"""
        self._risk_manager = risk_manager

    def _trigger_alert(self, message: str, severity: str, data: dict = None):
        """触发告警到监控系统"""
        if self._risk_manager:
            self._risk_manager._trigger_alert(
                rule_name=self.name,
                rule_type="position_control",
                message=message,
                severity=severity,
                data=data or {}
            )

    def check_allowed(self, req: OrderRequest, gateway_name: str) -> bool:
        """检查是否允许委托"""
        # 1. 检查持仓数量限制
        if self._check_holdings_limit(req):
            return False

        # 2. 检查单股仓位限制
        if self._check_single_position_limit(req):
            return False

        # 3. 检查总仓位限制
        if self._check_total_position_limit(req):
            return False

        # 4. 检查行业仓位限制
        if self.enable_industry_check:
            if self._check_industry_limit(req):
                return False

        return True

    def on_trade(self, trade: TradeData) -> None:
        """成交推送 - 更新持仓"""
        # 更新持仓数据
        self._update_position(trade)
        self.put_event()

    def on_order(self, order) -> None:
        """委托推送"""
        self.put_event()

    def _check_holdings_limit(self, req: OrderRequest) -> bool:
        """检查持仓数量限制"""
        # 获取当前持仓股票数
        current_count = len([p for p in self.position_data.values()
                           if p.volume > 0])

        # 如果是新买入，检查是否超过持仓数量
        if req.direction == Direction.LONG and current_count >= self.max_holdings:
            # 检查是否在已有持仓中
            if req.vt_symbol not in self.position_data:
                msg = f"持仓数量{current_count}达到上限{self.max_holdings}，禁止新开仓"
                self.write_log(msg)
                self._trigger_alert(msg, "warning", {
                    "current_count": current_count,
                    "max_holdings": self.max_holdings,
                    "vt_symbol": req.vt_symbol
                })
                return True
        return False

    def _check_single_position_limit(self, req: OrderRequest) -> bool:
        """检查单股仓位限制"""
        contract = self.get_contract(req.vt_symbol)
        if not contract:
            return False

        # 计算当前持仓价值
        current_volume = 0
        if req.vt_symbol in self.position_data:
            pos = self.position_data[req.vt_symbol]
            current_volume = pos.volume

        # 计算委托后持仓
        if req.direction == Direction.LONG:
            new_volume = current_volume + req.volume
        else:
            new_volume = max(0, current_volume - req.volume)

        # 计算持仓比例
        position_value = new_volume * req.price * contract.size
        # 需要获取账户总资金
        account = self.risk_engine.main_engine.get_account()
        if not account:
            return False

        position_ratio = position_value / account.balance

        if position_ratio > self.max_single_position_ratio:
            msg = f"单股仓位比例{position_ratio:.2%}超过上限{self.max_single_position_ratio:.2%}"
            self.write_log(msg)
            self._trigger_alert(msg, "warning", {
                "position_ratio": position_ratio,
                "max_ratio": self.max_single_position_ratio,
                "vt_symbol": req.vt_symbol
            })
            return True
        return False

    def _check_total_position_limit(self, req: OrderRequest) -> bool:
        """检查总仓位限制"""
        contract = self.get_contract(req.vt_symbol)
        if not contract:
            return False

        # 计算当前总持仓价值
        total_value = 0
        for pos in self.position_data.values():
            if pos.volume > 0:
                total_value += pos.volume * pos.price * contract.size

        # 计算委托后总持仓
        order_value = req.volume * req.price * contract.size
        if req.direction == Direction.LONG:
            total_value += order_value

        # 获取账户总资金
        account = self.risk_engine.main_engine.get_account()
        if not account:
            return False

        total_ratio = total_value / account.balance

        if total_ratio > self.max_total_position_ratio:
            msg = f"总仓位比例{total_ratio:.2%}超过上限{self.max_total_position_ratio:.2%}"
            self.write_log(msg)
            self._trigger_alert(msg, "warning", {
                "total_ratio": total_ratio,
                "max_ratio": self.max_total_position_ratio,
                "vt_symbol": req.vt_symbol
            })
            return True
        return False

    def _check_industry_limit(self, req: OrderRequest) -> bool:
        """检查行业仓位限制"""
        # 获取股票行业信息
        industry = self._get_industry(req.vt_symbol)
        if not industry:
            return False

        # 计算当前行业持仓
        industry_value = 0
        for vt_symbol, pos in self.position_data.items():
            if pos.volume > 0 and self._get_industry(vt_symbol) == industry:
                industry_value += pos.volume * pos.price

        # 计算委托后行业持仓
        contract = self.get_contract(req.vt_symbol)
        if contract:
            order_value = req.volume * req.price * contract.size
            if req.direction == Direction.LONG:
                industry_value += order_value

        # 获取账户总资金
        account = self.risk_engine.main_engine.get_account()
        if not account:
            return False

        industry_ratio = industry_value / account.balance

        if industry_ratio > self.max_industry_ratio:
            msg = f"行业[{industry}]仓位比例{industry_ratio:.2%}超过上限{self.max_industry_ratio:.2%}"
            self.write_log(msg)
            self._trigger_alert(msg, "warning", {
                "industry": industry,
                "industry_ratio": industry_ratio,
                "max_ratio": self.max_industry_ratio,
                "vt_symbol": req.vt_symbol
            })
            return True
        return False

    def _get_industry(self, vt_symbol: str) -> str:
        """获取股票行业"""
        # 从数据源获取
        return "科技"  # TODO: 实现从数据源获取

    def get_contract(self, vt_symbol: str):
        """获取合约信息"""
        if hasattr(self, "risk_engine") and self.risk_engine:
            return self.risk_engine.main_engine.get_contract(vt_symbol)
        return None

    def _update_position(self, trade: TradeData) -> None:
        """更新持仓数据"""
        if trade.vt_symbol not in self.position_data:
            self.position_data[trade.vt_symbol] = PositionData(
                symbol=trade.symbol,
                exchange=trade.exchange,
                direction=trade.direction,
                volume=0,
                frozen=0,
                price=0,
                cost=0,
                PNL=0,
            )

        pos = self.position_data[trade.vt_symbol]

        if trade.direction == Direction.LONG:
            pos.volume += trade.volume
            pos.cost = (pos.cost * (pos.volume - trade.volume) +
                       trade.price * trade.volume) / pos.volume
        else:
            pos.volume -= trade.volume
            if pos.volume == 0:
                pos.cost = 0

        # 更新最新价格
        pos.price = trade.price
