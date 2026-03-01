# -*- coding: utf-8 -*-
"""
VeighNa A股实盘交易引擎模块

提供信号收集、风控检查、人工确认、下单执行的完整流程。
"""

from vnpy_china_trading.object import (
    SignalSource,
    SignalDirection,
    SignalStatus,
    TradingSignal,
    RiskCheckResult,
)

from vnpy_china_trading.signal_engine import SignalEngine

# GUI应用
from vnpy_china_trading.app import ChinaTradingApp


__all__ = [
    # 枚举类型
    "SignalSource",
    "SignalDirection",
    "SignalStatus",
    # 数据类
    "TradingSignal",
    "RiskCheckResult",
    # 引擎
    "SignalEngine",
    # GUI应用
    "ChinaTradingApp",
]


__version__ = "1.0.0"
__author__ = "VeighNa Team"
