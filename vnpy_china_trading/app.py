# -*- coding: utf-8 -*-
"""
A股交易引擎应用模块

提供VeighNa GUI集成的应用入口。
"""

from pathlib import Path
from typing import Any, Optional, Type

from vnpy.trader.app import BaseApp

from vnpy_china_trading.signal_engine import SignalEngine


class ChinaTradingApp(BaseApp):
    """A股交易引擎应用

    提供信号收集、风控检查、人工确认、下单执行的完整流程。

    Attributes:
        app_name: 应用名称
        app_display_name: 显示名称
        app_version: 版本号
    """

    app_name: str = "china_trading"
    app_module: str = "vnpy_china_trading"
    app_path: Path = Path(__file__).parent
    display_name: str = "A股交易引擎"
    app_version: str = "1.0.0"
    engine_class: Optional[Type] = None  # 暂不使用GUI引擎

    def __init__(self, main_engine: Any, event_engine: Any) -> None:
        """初始化应用

        Args:
            main_engine: 主引擎实例
            event_engine: 事件引擎实例
        """
        super().__init__(main_engine, event_engine)

        self.signal_engine: Optional[SignalEngine] = None
        self.risk_engine: Optional[Any] = None

    def start(self) -> None:
        """启动应用模块

        初始化信号引擎和风控引擎。
        """
        if self.signal_engine is None:
            self.signal_engine = SignalEngine(self.main_engine, self.event_engine)

        # TODO: 初始化风控引擎
        # if self.risk_engine is None:
        #     self.risk_engine = RiskEngine(self.main_engine, self.event_engine)

    def close(self) -> None:
        """关闭应用模块

        清理资源并保存状态。
        """
        # 清理信号引擎
        if self.signal_engine:
            self.signal_engine.clear_history()
            self.signal_engine = None

        # 清理风控引擎
        if self.risk_engine:
            self.risk_engine = None

    def get_signal_engine(self) -> Optional[SignalEngine]:
        """获取信号引擎

        Returns:
            Optional[SignalEngine]: 信号引擎实例
        """
        return self.signal_engine

    def get_risk_engine(self) -> Any:
        """获取风控引擎

        Returns:
            Any: 风控引擎实例
        """
        return self.risk_engine


__all__ = ["ChinaTradingApp"]
