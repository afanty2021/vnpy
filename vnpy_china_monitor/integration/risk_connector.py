"""
风控连接器

用于连接 AStockRiskManager 和监控系统
"""

from typing import Optional, Any, Dict
from loguru import logger

# 尝试导入风控模块
try:
    from vnpy_china_rules.risk import AStockRiskManager
    RISK_MODULE_AVAILABLE = True
except ImportError:
    RISK_MODULE_AVAILABLE = False
    AStockRiskManager = None


class RiskConnector:
    """风控连接器

    负责将 AStockRiskManager 连接到监控系统
    """

    def __init__(self, monitor_system: Any):
        """初始化连接器

        Args:
            monitor_system: 监控系统实例
        """
        self.monitor_system = monitor_system

        # 风控管理器引用
        self._risk_manager: Optional[AStockRiskManager] = None

        # 连接状态
        self._connected = False

        logger.info("RiskConnector 初始化完成")

    def connect(self, risk_manager: AStockRiskManager) -> bool:
        """连接到风控管理器

        Args:
            risk_manager: AStockRiskManager实例

        Returns:
            是否连接成功
        """
        if not RISK_MODULE_AVAILABLE:
            logger.error("风控模块不可用，无法连接")
            return False

        if not isinstance(risk_manager, AStockRiskManager):
            logger.error("无效的风控管理器实例")
            return False

        try:
            self._risk_manager = risk_manager

            # 连接告警引擎
            if hasattr(self.monitor_system, "alert_engine"):
                self.monitor_system.alert_engine.connect_risk_manager(risk_manager)

            # 连接监控引擎
            if hasattr(self.monitor_system, "monitor_engine"):
                # 可以在这里设置额外的监控
                pass

            self._connected = True
            logger.info("成功连接到风控管理器")

            return True

        except Exception as e:
            logger.error(f"连接风控管理器失败: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        """断开与风控管理器的连接"""
        if self._risk_manager:
            # 清理引用
            self._risk_manager = None

        self._connected = False
        logger.info("已断开与风控管理器的连接")

    def is_connected(self) -> bool:
        """检查连接状态

        Returns:
            是否已连接
        """
        return self._connected

    def get_risk_manager(self) -> Optional[AStockRiskManager]:
        """获取风控管理器实例

        Returns:
            AStockRiskManager实例或None
        """
        return self._risk_manager

    def get_risk_status(self) -> Dict[str, Any]:
        """获取风控状态

        Returns:
            风控状态字典
        """
        if not self._connected or not self._risk_manager:
            return {"connected": False, "message": "未连接风控管理器"}

        try:
            if hasattr(self._risk_manager, "get_risk_status"):
                return {
                    "connected": True,
                    **self._risk_manager.get_risk_status(),
                }
            return {"connected": True, "message": "风控管理器不支持状态查询"}

        except Exception as e:
            logger.error(f"获取风控状态失败: {e}")
            return {"connected": False, "error": str(e)}

    def get_active_risk_alerts(self) -> list:
        """获取活跃的风控告警

        Returns:
            活跃告警列表
        """
        if not self._connected or not self._risk_manager:
            return []

        try:
            if hasattr(self._risk_manager, "get_active_risk_alerts"):
                return self._risk_manager.get_active_risk_alerts()
            return []

        except Exception as e:
            logger.error(f"获取风控告警失败: {e}")
            return []
