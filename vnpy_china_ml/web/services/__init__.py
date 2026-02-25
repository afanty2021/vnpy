"""Web服务模块

提供机器学习相关的Web服务。
"""

from .ml_service import MLMonitorService, create_ml_monitor_service

__all__ = ["MLMonitorService", "create_ml_monitor_service"]
