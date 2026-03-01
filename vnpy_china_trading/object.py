# -*- coding: utf-8 -*-
"""
A股交易引擎数据对象定义

包含信号、风险检查等相关的数据结构和枚举类型。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List


class SignalSource(Enum):
    """信号来源枚举"""
    ALPHA158 = "alpha158"  # Alpha158模型信号
    CUSTOM = "custom"       # 自定义信号
    MANUAL = "manual"       # 人工手动信号
    ML_MODEL = "ml_model"  # 机器学习模型信号


class SignalDirection(Enum):
    """信号方向枚举"""
    LONG = "long"     # 做多
    SHORT = "short"    # 做空
    CLOSE = "close"   # 平仓
    HOLD = "hold"     # 持仓不动


class SignalStatus(Enum):
    """信号状态枚举"""
    PENDING = "pending"              # 待处理
    RISK_CHECKING = "risk_checking"  # 风控检查中
    RISK_PASSED = "risk_passed"      # 风控通过
    RISK_REJECTED = "risk_rejected"  # 风控拒绝
    CONFIRMED = "confirmed"          # 已确认（人工确认）
    EXECUTED = "executed"            # 已执行（已下单）
    CANCELLED = "cancelled"          # 已取消


@dataclass
class TradingSignal:
    """交易信号数据类

    Attributes:
        signal_id: 信号唯一标识
        symbol: 股票代码
        exchange: 交易所（SHSE/SZSE）
        direction: 交易方向
        strength: 信号强度 (0-1)
        source: 信号来源
        model_name: 模型名称（可选）
        predicted_return: 预测收益率（可选）
        confidence: 置信度 (0-1)（可选）
        created_time: 信号创建时间
        status: 信号当前状态
        risk_check_result: 风控检查结果（可选）
    """
    signal_id: str
    symbol: str
    exchange: str
    direction: SignalDirection
    strength: float = 1.0
    source: SignalSource = SignalSource.CUSTOM
    model_name: Optional[str] = None
    predicted_return: Optional[float] = None
    confidence: Optional[float] = None
    created_time: datetime = field(default_factory=datetime.now)
    status: SignalStatus = SignalStatus.PENDING
    risk_check_result: Optional["RiskCheckResult"] = None

    def __post_init__(self):
        """验证数据有效性"""
        if not self.signal_id:
            raise ValueError("signal_id不能为空")
        if not self.symbol:
            raise ValueError("symbol不能为空")
        if not self.exchange:
            raise ValueError("exchange不能为空")
        if not isinstance(self.direction, SignalDirection):
            raise ValueError(f"无效的direction: {self.direction}")
        if not isinstance(self.status, SignalStatus):
            raise ValueError(f"无效的status: {self.status}")
        if not 0 <= self.strength <= 1:
            raise ValueError("strength必须在0-1之间")

    @property
    def vt_symbol(self) -> str:
        """获取VeighNa格式的合约代码"""
        return f"{self.symbol}.{self.exchange}"


@dataclass
class RiskCheckResult:
    """风险检查结果数据类

    Attributes:
        passed: 是否通过风控检查
        reasons: 拒绝原因列表
        warnings: 警告信息列表
        limit_up: 是否涨停
        limit_down: 是否跌停
        t1_restriction: 是否受T+1限制
        insufficient_capital: 资金是否不足
        position_limit: 是否达到持仓上限
    """
    passed: bool
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    limit_up: bool = False
    limit_down: bool = False
    t1_restriction: bool = False
    insufficient_capital: bool = False
    position_limit: bool = False

    def __post_init__(self):
        """验证数据有效性"""
        if not isinstance(self.passed, bool):
            raise ValueError("passed必须是布尔类型")
        if not isinstance(self.reasons, list):
            raise ValueError("reasons必须是列表")
        if not isinstance(self.warnings, list):
            raise ValueError("warnings必须是列表")

    @property
    def message(self) -> str:
        """获取检查结果的消息描述"""
        if self.passed:
            if self.warnings:
                return f"通过（有警告: {'; '.join(self.warnings)}）"
            return "通过"
        return "; ".join(self.reasons) if self.reasons else "未通过"


__all__ = [
    "SignalSource",
    "SignalDirection",
    "SignalStatus",
    "TradingSignal",
    "RiskCheckResult",
]
