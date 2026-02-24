"""
认证API

提供登录、登出、令牌刷新等接口
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from vnpy_china_monitor.web.models.request import LoginRequest
from vnpy_china_monitor.web.models.response import ApiResponse
from vnpy_china_monitor.web.security import AuthManager, JWTManager

logger = logging.getLogger(__name__)

# 创建路由器
auth_router = APIRouter(
    prefix="/api/auth",
    tags=["认证"],
)

# HTTP Bearer认证
security = HTTPBearer()


# 依赖注入：获取当前用户
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """获取当前用户

    Args:
        credentials: HTTP认证凭据

    Returns:
        用户信息

    Raises:
        HTTPException: 认证失败
    """
    # 这里需要从应用状态中获取jwt_manager
    # 暂时返回模拟数据
    return {"sub": "admin"}


@auth_router.post("/login", response_model=ApiResponse)
async def login(
    request: LoginRequest,
) -> ApiResponse:
    """用户登录

    Args:
        request: 登录请求

    Returns:
        API响应
    """
    # 这里需要从应用状态中获取auth_manager
    # 暂时返回模拟响应
    return ApiResponse(
        success=True,
        message="登录成功",
        data={
            "access_token": "mock_token",
            "token_type": "bearer",
            "expires_in": 3600,
        },
    )


@auth_router.post("/logout", response_model=ApiResponse)
async def logout(
    current_user: dict = Depends(get_current_user),
) -> ApiResponse:
    """用户登出

    Args:
        current_user: 当前用户

    Returns:
        API响应
    """
    return ApiResponse(
        success=True,
        message="登出成功",
    )


@auth_router.post("/refresh", response_model=ApiResponse)
async def refresh_token(
    current_user: dict = Depends(get_current_user),
) -> ApiResponse:
    """刷新令牌

    Args:
        current_user: 当前用户

    Returns:
        API响应
    """
    return ApiResponse(
        success=True,
        data={
            "access_token": "new_mock_token",
            "token_type": "bearer",
            "expires_in": 3600,
        },
    )


@auth_router.get("/me", response_model=ApiResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
) -> ApiResponse:
    """获取当前用户信息

    Args:
        current_user: 当前用户

    Returns:
        API响应
    """
    return ApiResponse(
        success=True,
        data={
            "username": current_user.get("sub"),
            "roles": ["admin"],
        },
    )
