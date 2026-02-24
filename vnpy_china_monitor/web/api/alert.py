"""
告警API

提供告警查询、管理等接口
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from vnpy_china_monitor.web.models.response import ApiResponse, AlertData
from vnpy_china_monitor.web.services.alert_service import AlertService

logger = logging.getLogger(__name__)

# 创建路由器
alert_router = APIRouter(
    prefix="/api/alerts",
    tags=["告警"],
)


# 依赖注入：获取告警服务
async def get_alert_service() -> AlertService:
    """获取告警服务实例

    实际应用中应该从应用状态中获取
    """
    raise HTTPException(status_code=501, detail="服务未初始化")


@alert_router.get("", response_model=ApiResponse)
async def get_alerts(
    active: bool = Query(True, description="是否只获取活跃告警"),
    limit: int = Query(100, ge=1, le=1000, description="限制数量"),
    service: AlertService = Depends(get_alert_service),
) -> ApiResponse:
    """获取告警列表

    Args:
        active: 是否只获取活跃告警
        limit: 限制数量
        service: 告警服务

    Returns:
        API响应
    """
    if active:
        alerts = service.get_active_alerts(limit=limit)
    else:
        alerts = service.get_alert_history(limit=limit)

    formatted = [service.format_alert(a) for a in alerts]

    return ApiResponse(
        success=True,
        data={"alerts": formatted},
    )


@alert_router.get("/stats", response_model=ApiResponse)
async def get_alert_stats(
    service: AlertService = Depends(get_alert_service),
) -> ApiResponse:
    """获取告警统计

    Args:
        service: 告警服务

    Returns:
        API响应
    """
    stats = service.get_stats()

    return ApiResponse(
        success=True,
        data=stats,
    )


@alert_router.post("/{alert_id}/acknowledge", response_model=ApiResponse)
async def acknowledge_alert(
    alert_id: str,
    service: AlertService = Depends(get_alert_service),
    current_user: dict = None,  # 实际应用中从认证获取
) -> ApiResponse:
    """确认告警

    Args:
        alert_id: 告警ID
        service: 告警服务
        current_user: 当前用户

    Returns:
        API响应
    """
    acknowledged_by = current_user.get("sub", "unknown") if current_user else "unknown"

    success = service.acknowledge_alert(alert_id, acknowledged_by)

    return ApiResponse(
        success=success,
        message=f"{'确认成功' if success else '确认失败'}: {alert_id}",
    )
