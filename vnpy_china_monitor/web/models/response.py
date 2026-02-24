"""
响应数据模型

定义API响应的数据结构
"""

from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime


class ApiResponse(BaseModel):
    """统一API响应"""
    success: bool = Field(..., description="是否成功")
    message: Optional[str] = Field(None, description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")
    error: Optional[str] = Field(None, description="错误信息")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="响应时间"
    )


class TickData(BaseModel):
    """行情数据"""
    symbol: str = Field(..., description="代码")
    exchange: str = Field(..., description="交易所")
    vt_symbol: str = Field(..., description="合约代码")
    last_price: float = Field(..., description="最新价")
    open_price: float = Field(..., description="开盘价")
    high_price: float = Field(..., description="最高价")
    low_price: float = Field(..., description="最低价")
    volume: float = Field(..., description="成交量")
    turnover: float = Field(..., description="成交额")
    bid_price_1: float = Field(..., description="买一价")
    ask_price_1: float = Field(..., description="卖一价")
    bid_volume_1: float = Field(..., description="买一量")
    ask_volume_1: float = Field(..., description="卖一量")
    datetime: str = Field(..., description="时间")


class BarData(BaseModel):
    """K线数据"""
    symbol: str = Field(..., description="代码")
    exchange: str = Field(..., description="交易所")
    vt_symbol: str = Field(..., description="合约代码")
    interval: str = Field(..., description="周期")
    open_price: float = Field(..., description="开盘价")
    high_price: float = Field(..., description="最高价")
    low_price: float = Field(..., description="最低价")
    close_price: float = Field(..., description="收盘价")
    volume: float = Field(..., description="成交量")
    turnover: float = Field(..., description="成交额")
    datetime: str = Field(..., description="时间")


class AccountData(BaseModel):
    """账户数据"""
    accountid: str = Field(..., description="账户ID")
    balance: float = Field(..., description="余额")
    available: float = Field(..., description="可用资金")
    frozen: float = Field(..., description="冻结资金")
    position_profit: float = Field(..., description="持仓盈亏")
    close_profit: float = Field(..., description="平仓盈亏")
    datetime: str = Field(..., description="更新时间")


class PositionData(BaseModel):
    """持仓数据"""
    vt_symbol: str = Field(..., description="合约代码")
    symbol: str = Field(..., description="代码")
    exchange: str = Field(..., description="交易所")
    direction: str = Field(..., description="方向")
    volume: float = Field(..., description="持仓量")
    yd_volume: float = Field(..., description="昨仓")
    available: float = Field(..., description="可用")
    price: float = Field(..., description="持仓均价")
    pnl: float = Field(..., description="浮动盈亏")
    datetime: str = Field(..., description="更新时间")


class OrderData(BaseModel):
    """委托数据"""
    vt_orderid: str = Field(..., description="委托ID")
    symbol: str = Field(..., description="代码")
    exchange: str = Field(..., description="交易所")
    vt_symbol: str = Field(..., description="合约代码")
    direction: str = Field(..., description="方向")
    order_type: str = Field(..., description="委托类型")
    volume: float = Field(..., description="委托量")
    traded: float = Field(..., description="成交数量")
    price: float = Field(..., description="委托价格")
    status: str = Field(..., description="状态")
    order_time: str = Field(..., description="委托时间")
    cancel_time: Optional[str] = Field(None, description="撤销时间")


class TradeData(BaseModel):
    """成交数据"""
    vt_tradeid: str = Field(..., description="成交ID")
    vt_orderid: str = Field(..., description="委托ID")
    symbol: str = Field(..., description="代码")
    exchange: str = Field(..., description="交易所")
    vt_symbol: str = Field(..., description="合约代码")
    direction: str = Field(..., description="方向")
    volume: float = Field(..., description="成交量")
    price: float = Field(..., description="成交价格")
    trade_time: str = Field(..., description="成交时间")


class StrategyData(BaseModel):
    """策略数据"""
    name: str = Field(..., description="策略名称")
    class_name: str = Field(..., description="策略类名")
    vt_symbol: str = Field(..., description="交易合约")
    status: str = Field(..., description="状态")
    params: dict[str, Any] = Field(default_factory=dict, description="参数")
    var_names: list[str] = Field(default_factory=list, description="变量名")
    var_values: dict[str, Any] = Field(default_factory=dict, description="变量值")


class AlertData(BaseModel):
    """告警数据"""
    alert_id: str = Field(..., description="告警ID")
    title: str = Field(..., description="标题")
    message: str = Field(..., description="消息")
    severity: str = Field(..., description="严重级别")
    priority: str = Field(..., description="优先级")
    source: str = Field(..., description="来源")
    timestamp: str = Field(..., description="时间")
    acknowledged: bool = Field(False, description="是否已确认")
    acknowledged_by: Optional[str] = Field(None, description="确认人")
