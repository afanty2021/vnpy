"""Web API模块

提供机器学习相关的Web API接口。
"""

from .ml import ml_router, init_ml_api

__all__ = ["ml_router", "init_ml_api"]
