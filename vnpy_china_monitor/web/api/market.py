"""
行情API

提供行情查询、订阅等接口
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from vnpy_china_monitor.web.models.response import ApiResponse, TickData, BarData
from vnpy_china_monitor.web.services.market_service import MarketService

logger = logging.getLogger(__name__)

# 创建路由器
market_router = APIRouter(
    prefix="/api/market",
    tags=["行情"],
)


# 依赖注入：获取行情服务
async def get_market_service(request: Request) -> MarketService:
    """获取行情服务实例（从 app.state 读取）"""
    service = getattr(request.app.state, "market_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="行情服务未初始化")
    return service


@market_router.get("/tick/{vt_symbol}", response_model=ApiResponse)
async def get_tick(
    vt_symbol: str,
    service: MarketService = Depends(get_market_service),
) -> ApiResponse:
    """获取实时行情

    Args:
        vt_symbol: 合约代码
        service: 行情服务

    Returns:
        API响应
    """
    tick = service.format_tick(vt_symbol)

    if tick is None:
        raise HTTPException(status_code=404, detail="行情数据不存在")

    return ApiResponse(success=True, data=tick)


@market_router.get("/ticks", response_model=ApiResponse)
async def get_all_ticks(
    service: MarketService = Depends(get_market_service),
) -> ApiResponse:
    """获取所有行情

    Args:
        service: 行情服务

    Returns:
        API响应
    """
    ticks = service.get_all_ticks()
    formatted_ticks = [service.format_tick(k) for k in ticks.keys()]

    return ApiResponse(
        success=True,
        data={"ticks": formatted_ticks},
    )


@market_router.get("/bars/{vt_symbol}", response_model=ApiResponse)
async def get_bars(
    vt_symbol: str,
    interval: str = Query("1m", description="K线周期"),
    count: int = Query(100, ge=1, le=1000, description="数量"),
    service: MarketService = Depends(get_market_service),
) -> ApiResponse:
    """获取历史K线

    Args:
        vt_symbol: 合约代码
        interval: K线周期
        count: 数量
        service: 行情服务

    Returns:
        API响应
    """
    bars = service.get_history_bars(vt_symbol, interval, count)

    return ApiResponse(
        success=True,
        data={
            "vt_symbol": vt_symbol,
            "interval": interval,
            "bars": bars,
        },
    )


@market_router.post("/subscribe", response_model=ApiResponse)
async def subscribe_market(
    vt_symbol: str,
    service: MarketService = Depends(get_market_service),
) -> ApiResponse:
    """订阅行情

    Args:
        vt_symbol: 合约代码
        service: 行情服务

    Returns:
        API响应
    """
    success = service.subscribe(vt_symbol)

    return ApiResponse(
        success=success,
        message=f"{'订阅成功' if success else '订阅失败'}: {vt_symbol}",
    )


@market_router.delete("/subscribe/{vt_symbol}", response_model=ApiResponse)
async def unsubscribe_market(
    vt_symbol: str,
    service: MarketService = Depends(get_market_service),
) -> ApiResponse:
    """取消订阅

    Args:
        vt_symbol: 合约代码
        service: 行情服务

    Returns:
        API响应
    """
    success = service.unsubscribe(vt_symbol)

    return ApiResponse(
        success=success,
        message=f"{'取消订阅成功' if success else '取消订阅失败'}: {vt_symbol}",
    )


@market_router.get("/subscribed", response_model=ApiResponse)
async def get_subscribed_symbols(
    service: MarketService = Depends(get_market_service),
) -> ApiResponse:
    """获取已订阅的合约列表

    Args:
        service: 行情服务

    Returns:
        API响应
    """
    symbols = service.get_subscribed_symbols()

    return ApiResponse(
        success=True,
        data={"symbols": symbols},
    )
