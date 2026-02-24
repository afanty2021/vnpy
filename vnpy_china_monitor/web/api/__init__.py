"""
REST API路由

提供HTTP API接口
"""

from vnpy_china_monitor.web.api.auth import auth_router
from vnpy_china_monitor.web.api.market import market_router
from vnpy_china_monitor.web.api.trade import trade_router
from vnpy_china_monitor.web.api.strategy import strategy_router
from vnpy_china_monitor.web.api.alert import alert_router

__all__ = [
    "auth_router",
    "market_router",
    "trade_router",
    "strategy_router",
    "alert_router",
]
