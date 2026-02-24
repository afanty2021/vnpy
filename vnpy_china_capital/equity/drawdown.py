"""
回撤控制器

根据当前回撤水平动态调整仓位，控制下行风险。
"""

from typing import Optional


class DrawdownController:
    """
    回撤控制器

    根据当前回撤水平动态调整仓位，控制下行风险。
    当回撤达到不同阈值时，自动调整仓位以降低风险。
    """

    def __init__(
        self,
        max_drawdown: float = 0.15,
        warning_level: float = 0.10,
        stop_level: Optional[float] = None
    ) -> None:
        """
        构造函数

        Args:
            max_drawdown: 最大允许回撤比例（默认15%）
            warning_level: 预警回撤水平（默认10%）
            stop_level: 停止交易回撤水平，默认为 max_drawdown
        """
        self.max_drawdown: float = max_drawdown
        self.warning_level: float = warning_level
        self.stop_level: float = stop_level if stop_level is not None else max_drawdown

    def get_position_multiplier(self, current_drawdown: float) -> float:
        """
        根据当前回撤计算仓位调整系数

        Args:
            current_drawdown: 当前回撤比例

        Returns:
            仓位调整系数（0-1）
        """
        if current_drawdown < self.warning_level:
            # 正常状态，满仓
            return 1.0
        elif current_drawdown < self.max_drawdown * 0.75:
            # 预警状态，7成仓
            return 0.7
        elif current_drawdown < self.max_drawdown:
            # 风险状态，5成仓
            return 0.5
        else:
            # 超过最大回撤，清仓
            return 0.0

    def should_stop_trading(self, current_drawdown: float) -> bool:
        """
        判断是否应该停止交易

        Args:
            current_drawdown: 当前回撤比例

        Returns:
            是否应该停止交易
        """
        return current_drawdown >= self.stop_level

    def should_reduce_position(self, current_drawdown: float) -> bool:
        """
        判断是否应该减少仓位

        Args:
            current_drawdown: 当前回撤比例

        Returns:
            是否应该减少仓位
        """
        return current_drawdown >= self.warning_level

    def get_risk_level(self, current_drawdown: float) -> str:
        """
        获取当前风险等级

        Args:
            current_drawdown: 当前回撤比例

        Returns:
            风险等级：'normal', 'warning', 'danger', 'stop'
        """
        if current_drawdown < self.warning_level:
            return "normal"
        elif current_drawdown < self.max_drawdown * 0.75:
            return "warning"
        elif current_drawdown < self.max_drawdown:
            return "danger"
        else:
            return "stop"

    def get_risk_status(self, current_drawdown: float) -> dict:
        """
        获取风险状态详细信息

        Args:
            current_drawdown: 当前回撤比例

        Returns:
            风险状态字典
        """
        return {
            "current_drawdown": current_drawdown,
            "risk_level": self.get_risk_level(current_drawdown),
            "position_multiplier": self.get_position_multiplier(current_drawdown),
            "should_stop_trading": self.should_stop_trading(current_drawdown),
            "should_reduce_position": self.should_reduce_position(current_drawdown),
            "max_drawdown": self.max_drawdown,
            "warning_level": self.warning_level,
            "stop_level": self.stop_level
        }

    def calculate_new_position(
        self,
        original_position: float,
        current_drawdown: float
    ) -> float:
        """
        计算调整后的仓位

        Args:
            original_position: 原始目标仓位
            current_drawdown: 当前回撤比例

        Returns:
            调整后的仓位
        """
        multiplier = self.get_position_multiplier(current_drawdown)
        return original_position * multiplier
