"""
资金流水数据对象

用于记录A股交易的资金流水信息，包括交易、转账、手续费、出入金等操作。
"""

from dataclasses import dataclass, field
from datetime import datetime

from vnpy.trader.constant import Direction, Offset
from vnpy.trader.object import BaseData


@dataclass
class CapitalFlowData(BaseData):
    """
    资金流水数据

    记录每一笔资金变动，包括：
    - 交易成交（买入/卖出）
    - 资金转账
    - 手续费
    - 出入金
    """

    # 基本信息
    flow_id: str                       # 流水唯一标识
    trade_id: str                      # 成交ID（关联TradeData）

    # 交易信息
    symbol: str                        # 股票代码
    exchange: str                      # 交易所
    direction: Direction               # 方向
    offset: Offset                     # 开平

    # 数量金额
    price: float                       # 成交价格
    volume: float                      # 成交数量
    amount: float                      # 成交金额

    # 账户状态
    balance: float                     # 总资金
    available: float                   # 可用资金

    # 时间
    trade_time: datetime               # 成交时间
    created_at: datetime               # 记录创建时间

    # 分类
    flow_type: str                     # 流水类型：trade/transfer/fee/withdraw/deposit
    description: str = field(default_factory=str)  # 说明

    def __post_init__(self) -> None:
        """
        后处理：生成流水唯一标识
        """
        # 如果没有提供flow_id，自动生成
        if not self.flow_id:
            self.flow_id = f"{self.gateway_name}_{self.trade_id}"

    @property
    def vt_symbol(self) -> str:
        """返回股票代码的统一标识"""
        return f"{self.symbol}.{self.exchange}"

    def to_db_dict(self) -> dict:
        """
        转换为数据库字典格式

        Returns:
            dict: 数据库记录字典
        """
        return {
            "flow_id": self.flow_id,
            "gateway_name": self.gateway_name,
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "direction": self.direction.value,
            "offset": self.offset.value,
            "price": self.price,
            "volume": self.volume,
            "amount": self.amount,
            "balance": self.balance,
            "available": self.available,
            "trade_time": self.trade_time,
            "created_at": self.created_at,
            "flow_type": self.flow_type,
            "description": self.description,
        }

    @classmethod
    def from_db_dict(cls, data: dict) -> "CapitalFlowData":
        """
        从数据库字典创建对象

        Args:
            data: 数据库记录字典

        Returns:
            CapitalFlowData: 资金流水对象
        """
        return cls(
            flow_id=data["flow_id"],
            gateway_name=data["gateway_name"],
            trade_id=data["trade_id"],
            symbol=data["symbol"],
            exchange=data["exchange"],
            direction=Direction(data["direction"]) if data.get("direction") else None,
            offset=Offset(data["offset"]) if data.get("offset") else None,
            price=data["price"],
            volume=data["volume"],
            amount=data["amount"],
            balance=data["balance"],
            available=data["available"],
            trade_time=data["trade_time"],
            created_at=data["created_at"],
            flow_type=data["flow_type"],
            description=data.get("description", ""),
        )

    @classmethod
    def from_trade_data(
        cls,
        trade_data: "TradeData",
        account_data: "AccountData",
        flow_type: str = "trade",
        description: str = "",
    ) -> "CapitalFlowData":
        """
        从TradeData和AccountData创建资金流水

        Args:
            trade_data: 成交数据
            account_data: 账户数据
            flow_type: 流水类型
            description: 说明

        Returns:
            CapitalFlowData: 资金流水对象
        """
        # 计算可用资金（balance - frozen）
        available = account_data.balance - account_data.frozen if account_data.balance is not None else 0.0

        return cls(
            flow_id="",  # 自动生成
            gateway_name=trade_data.gateway_name,
            trade_id=trade_data.tradeid,
            symbol=trade_data.symbol,
            exchange=trade_data.exchange.value,
            direction=trade_data.direction,
            offset=trade_data.offset,
            price=trade_data.price,
            volume=trade_data.volume,
            amount=trade_data.price * trade_data.volume,
            balance=account_data.balance,
            available=available,
            trade_time=trade_data.datetime or datetime.now(),
            created_at=datetime.now(),
            flow_type=flow_type,
            description=description,
        )
