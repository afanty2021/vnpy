"""
认证API

提供登录、登出、令牌刷新等接口
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """获取当前用户（校验 JWT 签名与有效期）

    Args:
        request: 请求对象（取 app.state.auth_manager）
        credentials: HTTP认证凭据

    Returns:
        用户信息

    Raises:
        HTTPException: 认证失败
    """
    auth_manager = getattr(request.app.state, "auth_manager", None)
    if auth_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="认证服务未初始化",
        )
    payload = auth_manager.verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的访问令牌",
        )
    return {"sub": payload.get("sub")}


@auth_router.post("/login", response_model=ApiResponse)
async def login(
    request: Request,
    login_req: LoginRequest,
) -> ApiResponse:
    """用户登录（校验用户名/密码，签发 JWT）

    Args:
        request: 请求对象（取 app.state.auth_manager）
        login_req: 登录请求（username/password）

    Returns:
        API响应
    """
    auth_manager = getattr(request.app.state, "auth_manager", None)
    if auth_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="认证服务未初始化",
        )
    token = auth_manager.authenticate(login_req.username, login_req.password)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    return ApiResponse(
        success=True,
        message="登录成功",
        data={
            "access_token": token,
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
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> ApiResponse:
    """刷新令牌（凭有效 access token 重新签发）

    Args:
        request: 请求对象（取 app.state.auth_manager）
        current_user: 当前用户（已由 get_current_user 校验）

    Returns:
        API响应
    """
    auth_manager = getattr(request.app.state, "auth_manager", None)
    if auth_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="认证服务未初始化",
        )
    token = auth_manager.jwt_manager.create_access_token(
        {"sub": current_user.get("sub")}
    )
    return ApiResponse(
        success=True,
        data={
            "access_token": token,
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
