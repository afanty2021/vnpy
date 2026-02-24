"""
交易API

提供委托、撤单、查询等交易接口
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from vnpy_china_monitor.web.models.request import OrderRequest, CancelRequest
from vnpy_china_monitor.web.models.response import (
    ApiResponse,
    AccountData,
    PositionData,
    OrderData,
    TradeData,
)
from vnpy_china_monitor.web.services.trade_service import TradeService

logger = logging.getLogger(__name__)

# 创建路由器
trade_router = APIRouter(
    prefix="/api/trade",
    tags=["交易"],
)


# 依赖注入：获取交易服务
async def get_trade_service() -> TradeService:
    """获取交易服务实例

    实际应用中应该从应用状态中获取
    """
    raise HTTPException(status_code=501, detail="服务未初始化")


@trade_router.get("/account", response_model=ApiResponse)
async def get_account(
    service: TradeService = Depends(get_trade_service),
) -> ApiResponse:
    """获取账户资金

    Args:
        service: 交易服务

    Returns:
        API响应
    """
    account = service.get_account()

    if account is None:
        raise HTTPException(status_code=404, detail="账户数据不存在")

    return ApiResponse(success=True, data=service.format_account(account))


@trade_router.get("/positions", response_model=ApiResponse)
async def get_positions(
    service: TradeService = Depends(get_trade_service),
) -> ApiResponse:
    """获取持仓列表

    Args:
        service: 交易服务

    Returns:
        API响应
    """
    positions = service.get_positions()
    formatted = [service.format_position(p) for p in positions]

    return ApiResponse(
        success=True,
        data={"positions": formatted},
    )


@trade_router.get("/orders", response_model=ApiResponse)
async def get_orders(
    vt_orderid: Optional[str] = Query(None, description="委托ID"),
    service: TradeService = Depends(get_trade_service),
) -> ApiResponse:
    """获取委托列表

    Args:
        vt_orderid: 委托ID
        service: 交易服务

    Returns:
        API响应
    """
    orders = service.get_orders(vt_orderid)
    formatted = [service.format_order(o) for o in orders]

    return ApiResponse(
        success=True,
        data={"orders": formatted},
    )


@trade_router.get("/trades", response_model=ApiResponse)
async def get_trades(
    vt_orderid: Optional[str] = Query(None, description="委托ID"),
    service: TradeService = Depends(get_trade_service),
) -> ApiResponse:
    """获取成交列表

    Args:
        vt_orderid: 委托ID
        service: 交易服务

    Returns:
        API响应
    """
    trades = service.get_trades(vt_orderid)

    return ApiResponse(
        success=True,
        data={"trades": trades},
    )


@trade_router.post("/order/send", response_model=ApiResponse)
async def send_order(
    request: OrderRequest,
    service: TradeService = Depends(get_trade_service),
) -> ApiResponse:
    """发送委托

    Args:
        request: 委托请求
        service: 交易服务

    Returns:
        API响应
    """
    vt_orderid = service.send_order(
        vt_symbol=request.vt_symbol,
        direction=request.direction.value,
        volume=request.volume,
        price=request.price,
        order_type=request.order_type.value,
    )

    if vt_orderid is None:
        return ApiResponse(
            success=False,
            message="委托失败",
        )

    return ApiResponse(
        success=True,
        message="委托成功",
        data={"vt_orderid": vt_orderid},
    )


@trade_router.post("/order/cancel", response_model=ApiResponse)
async def cancel_order(
    request: CancelRequest,
    service: TradeService = Depends(get_trade_service),
) -> ApiResponse:
    """撤销委托

    Args:
        request: 撤单请求
        service: 交易服务

    Returns:
        API响应
    """
    success = service.cancel_order(request.vt_orderid)

    return ApiResponse(
        success=success,
        message=f"{'撤单成功' if success else '撤单失败'}: {request.vt_orderid}",
    )
