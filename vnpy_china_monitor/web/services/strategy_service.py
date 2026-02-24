"""
策略服务

提供策略管理、启停、参数调整等功能
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from vnpy_china_monitor.web.rpc.client import RpcClientWrapper

logger = logging.getLogger(__name__)


class StrategyStatus:
    """策略状态"""
    RUNNING = "running"
    STOPPED = "stopped"
    INITIALIZING = "initializing"
    EXCEPTION = "exception"


class StrategyService:
    """策略服务

    负责：
    - 策略列表
    - 策略启停
    - 参数修改
    - 策略状态监控
    - 策略日志查询
    """

    def __init__(self, rpc_client: RpcClientWrapper):
        """初始化策略服务

        Args:
            rpc_client: RPC客户端
        """
        self.rpc_client = rpc_client

        # 策略状态缓存
        self._strategy_status: Dict[str, Dict] = {}

        # 策略参数缓存
        self._strategy_params: Dict[str, Dict] = {}

        logger.info("StrategyService initialized")

    def start_strategy(self, strategy_name: str) -> bool:
        """启动策略

        Args:
            strategy_name: 策略名称

        Returns:
            是否成功
        """
        try:
            result = self.rpc_client.start_strategy(strategy_name)

            if result:
                self._strategy_status[strategy_name] = {
                    "status": StrategyStatus.RUNNING,
                    "start_time": datetime.now().isoformat(),
                }

                logger.info(f"Strategy started: {strategy_name}")
            else:
                logger.warning(f"Failed to start strategy: {strategy_name}")

            return result

        except Exception as e:
            logger.error(f"Error starting strategy {strategy_name}: {e}")
            return False

    def stop_strategy(self, strategy_name: str) -> bool:
        """停止策略

        Args:
            strategy_name: 策略名称

        Returns:
            是否成功
        """
        try:
            result = self.rpc_client.stop_strategy(strategy_name)

            if result:
                self._strategy_status[strategy_name] = {
                    "status": StrategyStatus.STOPPED,
                    "stop_time": datetime.now().isoformat(),
                }

                logger.info(f"Strategy stopped: {strategy_name}")
            else:
                logger.warning(f"Failed to stop strategy: {strategy_name}")

            return result

        except Exception as e:
            logger.error(f"Error stopping strategy {strategy_name}: {e}")
            return False

    def get_strategy_status(self, strategy_name: str) -> Optional[Dict]:
        """获取策略状态

        Args:
            strategy_name: 策略名称

        Returns:
            策略状态
        """
        return self._strategy_status.get(strategy_name)

    def get_all_strategies(self) -> List[Dict]:
        """获取所有策略

        Returns:
            策略列表
        """
        try:
            return self.rpc_client.get_all_strategies()
        except Exception as e:
            logger.error(f"Failed to get strategies: {e}")
            return []

    def set_strategy_param(
        self,
        strategy_name: str,
        param_name: str,
        value: Any,
    ) -> bool:
        """设置策略参数

        Args:
            strategy_name: 策略名称
            param_name: 参数名称
            value: 参数值

        Returns:
            是否成功
        """
        try:
            result = self.rpc_client.set_strategy_param(
                strategy_name=strategy_name,
                param_name=param_name,
                value=value,
            )

            if result:
                # 更新缓存
                if strategy_name not in self._strategy_params:
                    self._strategy_params[strategy_name] = {}
                self._strategy_params[strategy_name][param_name] = value

                logger.info(
                    f"Strategy param updated: {strategy_name}.{param_name}={value}"
                )
            else:
                logger.warning(
                    f"Failed to update strategy param: {strategy_name}.{param_name}"
                )

            return result

        except Exception as e:
            logger.error(f"Error setting strategy param: {e}")
            return False

    def get_strategy_params(self, strategy_name: str) -> Dict[str, Any]:
        """获取策略参数

        Args:
            strategy_name: 策略名称

        Returns:
            参数字典
        """
        return self._strategy_params.get(strategy_name, {})

    def format_strategy(self, strategy: Dict) -> Dict:
        """格式化策略给前端

        Args:
            strategy: 策略数据

        Returns:
            格式化后的数据
        """
        # 合并缓存的策略状态
        strategy_name = strategy.get("name")
        cached_status = self._strategy_status.get(strategy_name, {})

        return {
            "name": strategy.get("name"),
            "class_name": strategy.get("class_name"),
            "vt_symbol": strategy.get("vt_symbol"),
            "status": cached_status.get("status", strategy.get("status", "unknown")),
            "params": strategy.get("params", {}),
            "var_names": strategy.get("var_names", []),
            "var_values": strategy.get("var_values", {}),
        }
