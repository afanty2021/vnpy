"""
策略API

提供策略管理、启停、参数调整等接口
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from vnpy_china_monitor.web.models.request import StrategyControlRequest, ParamUpdateRequest
from vnpy_china_monitor.web.models.response import ApiResponse, StrategyData
from vnpy_china_monitor.web.services.strategy_service import StrategyService

logger = logging.getLogger(__name__)

# 创建路由器
strategy_router = APIRouter(
    prefix="/api/strategy",
    tags=["策略"],
)


# 依赖注入：获取策略服务
async def get_strategy_service() -> StrategyService:
    """获取策略服务实例

    实际应用中应该从应用状态中获取
    """
    raise HTTPException(status_code=501, detail="服务未初始化")


@strategy_router.get("", response_model=ApiResponse)
async def get_strategies(
    service: StrategyService = Depends(get_strategy_service),
) -> ApiResponse:
    """获取所有策略

    Args:
        service: 策略服务

    Returns:
        API响应
    """
    strategies = service.get_all_strategies()
    formatted = [service.format_strategy(s) for s in strategies]

    return ApiResponse(
        success=True,
        data={"strategies": formatted},
    )


@strategy_router.get("/{strategy_name}", response_model=ApiResponse)
async def get_strategy(
    strategy_name: str,
    service: StrategyService = Depends(get_strategy_service),
) -> ApiResponse:
    """获取策略详情

    Args:
        strategy_name: 策略名称
        service: 策略服务

    Returns:
        API响应
    """
    strategies = service.get_all_strategies()

    for strategy in strategies:
        if strategy.get("name") == strategy_name:
            return ApiResponse(
                success=True,
                data=service.format_strategy(strategy),
            )

    raise HTTPException(status_code=404, detail="策略不存在")


@strategy_router.post("/{strategy_name}/start", response_model=ApiResponse)
async def start_strategy(
    strategy_name: str,
    service: StrategyService = Depends(get_strategy_service),
) -> ApiResponse:
    """启动策略

    Args:
        strategy_name: 策略名称
        service: 策略服务

    Returns:
        API响应
    """
    success = service.start_strategy(strategy_name)

    return ApiResponse(
        success=success,
        message=f"{'启动成功' if success else '启动失败'}: {strategy_name}",
    )


@strategy_router.post("/{strategy_name}/stop", response_model=ApiResponse)
async def stop_strategy(
    strategy_name: str,
    service: StrategyService = Depends(get_strategy_service),
) -> ApiResponse:
    """停止策略

    Args:
        strategy_name: 策略名称
        service: 策略服务

    Returns:
        API响应
    """
    success = service.stop_strategy(strategy_name)

    return ApiResponse(
        success=success,
        message=f"{'停止成功' if success else '停止失败'}: {strategy_name}",
    )


@strategy_router.put("/{strategy_name}/param", response_model=ApiResponse)
async def update_strategy_param(
    strategy_name: str,
    request: ParamUpdateRequest,
    service: StrategyService = Depends(get_strategy_service),
) -> ApiResponse:
    """更新策略参数

    Args:
        strategy_name: 策略名称
        request: 参数更新请求
        service: 策略服务

    Returns:
        API响应
    """
    success = service.set_strategy_param(
        strategy_name=strategy_name,
        param_name=request.param_name,
        value=request.value,
    )

    return ApiResponse(
        success=success,
        message=f"{'参数更新成功' if success else '参数更新失败'}: {request.param_name}",
    )


@strategy_router.get("/{strategy_name}/params", response_model=ApiResponse)
async def get_strategy_params(
    strategy_name: str,
    service: StrategyService = Depends(get_strategy_service),
) -> ApiResponse:
    """获取策略参数

    Args:
        strategy_name: 策略名称
        service: 策略服务

    Returns:
        API响应
    """
    params = service.get_strategy_params(strategy_name)

    return ApiResponse(
        success=True,
        data={"params": params},
    )
