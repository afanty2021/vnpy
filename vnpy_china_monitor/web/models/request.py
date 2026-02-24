"""
请求数据模型

定义API请求的数据结构
"""

from pydantic import BaseModel, Field, field_validator
from typing import Any, Optional
from enum import Enum


class Direction(str, Enum):
    """交易方向"""
    LONG = "long"
    SHORT = "short"


class OrderType(str, Enum):
    """委托类型"""
    LIMIT = "limit"
    MARKET = "market"
    STOP = "stop"


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)


class OrderRequest(BaseModel):
    """委托请求"""
    vt_symbol: str = Field(..., description="合约代码")
    direction: Direction = Field(..., description="交易方向")
    volume: float = Field(..., gt=0, description="数量")
    price: float = Field(0, ge=0, description="价格（0表示市价）")
    order_type: OrderType = Field(OrderType.LIMIT, description="委托类型")

    @field_validator('vt_symbol')
    @classmethod
    def validate_vt_symbol(cls, v: str) -> str:
        """验证合约代码格式"""
        if not v:
            raise ValueError('vt_symbol cannot be empty')
        parts = v.split('.')
        if len(parts) != 2:
            raise ValueError('vt_symbol must be in format: SYMBOL.EXCHANGE')
        return v.upper()


class CancelRequest(BaseModel):
    """撤单请求"""
    vt_orderid: str = Field(..., min_length=1, description="委托ID")


class StrategyControlRequest(BaseModel):
    """策略控制请求"""
    action: str = Field(..., description="操作：start/stop")


class ParamUpdateRequest(BaseModel):
    """参数更新请求"""
    param_name: str = Field(..., min_length=1, description="参数名称")
    value: Any = Field(..., description="参数值")


class SubscribeRequest(BaseModel):
    """订阅请求"""
    topic: str = Field(..., min_length=1, description="订阅主题")
    symbols: Optional[list[str]] = Field(None, description="订阅合约列表")
