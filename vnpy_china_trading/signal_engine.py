# -*- coding: utf-8 -*-
"""
信号引擎模块

提供信号管理、状态跟踪和回调机制。
"""

import logging
import threading
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional, Any

from vnpy_china_trading.object import (
    TradingSignal,
    SignalStatus,
    SignalSource,
    SignalDirection,
    RiskCheckResult,
)


class SignalEngine:
    """信号引擎

    负责管理交易信号的收集、状态跟踪和回调通知。
    使用线程锁保证操作的线程安全性。

    Attributes:
        signals: 所有信号的字典，key为signal_id
        callbacks: 注册的回调函数列表
    """

    def __init__(self, main_engine: Any, event_engine: Any) -> None:
        """初始化信号引擎

        Args:
            main_engine: 主引擎实例
            event_engine: 事件引擎实例
        """
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.signals: Dict[str, TradingSignal] = {}
        self.callbacks: List[Callable[[TradingSignal], None]] = []
        self.lock = threading.Lock()

    def add_signal(
        self,
        symbol: str,
        exchange: str,
        direction: SignalDirection,
        source: SignalSource = SignalSource.CUSTOM,
        strength: float = 1.0,
        model_name: Optional[str] = None,
        predicted_return: Optional[float] = None,
        confidence: Optional[float] = None,
    ) -> TradingSignal:
        """添加新信号

        Args:
            symbol: 股票代码
            exchange: 交易所
            direction: 交易方向
            source: 信号来源
            strength: 信号强度
            model_name: 模型名称
            predicted_return: 预测收益率
            confidence: 置信度

        Returns:
            TradingSignal: 创建的信号对象
        """
        signal_id = self._generate_signal_id()

        signal = TradingSignal(
            signal_id=signal_id,
            symbol=symbol,
            exchange=exchange,
            direction=direction,
            source=source,
            strength=strength,
            model_name=model_name,
            predicted_return=predicted_return,
            confidence=confidence,
            created_time=datetime.now(),
            status=SignalStatus.PENDING,
        )

        with self.lock:
            self.signals[signal_id] = signal

        # 触发回调
        self._trigger_callback(signal)

        return signal

    def get_pending_signals(self) -> List[TradingSignal]:
        """获取待处理信号

        Returns:
            List[TradingSignal]: 待处理的信号列表（按创建时间排序）
        """
        with self.lock:
            pending = [
                s for s in self.signals.values()
                if s.status in (SignalStatus.PENDING, SignalStatus.RISK_CHECKING)
            ]
            pending.sort(key=lambda x: x.created_time)
            return pending

    def get_signals_by_status(self, status: SignalStatus) -> List[TradingSignal]:
        """获取指定状态的信号

        Args:
            status: 信号状态

        Returns:
            List[TradingSignal]: 指定状态的信号列表
        """
        with self.lock:
            return [s for s in self.signals.values() if s.status == status]

    def get_signal(self, signal_id: str) -> Optional[TradingSignal]:
        """根据ID获取信号

        Args:
            signal_id: 信号ID

        Returns:
            Optional[TradingSignal]: 信号对象，不存在则返回None
        """
        with self.lock:
            return self.signals.get(signal_id)

    def update_signal_status(
        self,
        signal_id: str,
        status: SignalStatus,
        risk_result: Optional[RiskCheckResult] = None,
    ) -> bool:
        """更新信号状态

        Args:
            signal_id: 信号ID
            status: 新状态
            risk_result: 风控检查结果（可选）

        Returns:
            bool: 更新是否成功
        """
        with self.lock:
            signal = self.signals.get(signal_id)
            if not signal:
                return False

            signal.status = status
            if risk_result:
                signal.risk_check_result = risk_result

        # 触发回调
        self._trigger_callback(signal)
        return True

    def cancel_signal(self, signal_id: str) -> bool:
        """取消信号

        Args:
            signal_id: 信号ID

        Returns:
            bool: 取消是否成功
        """
        return self.update_signal_status(signal_id, SignalStatus.CANCELLED)

    def confirm_signal(self, signal_id: str) -> bool:
        """确认信号（人工确认后）

        Args:
            signal_id: 信号ID

        Returns:
            bool: 确认是否成功

        Note:
            只有以下情况可以确认：
            - 状态为 RISK_PASSED（风控通过）
            - 状态为 PENDING（待处理）
            - 来源为 MANUAL（人工信号）
        """
        signal = self.get_signal(signal_id)
        if not signal:
            return False

        # 检查是否满足确认条件
        if signal.status not in (SignalStatus.RISK_PASSED, SignalStatus.PENDING):
            if signal.source != SignalSource.MANUAL:
                return False

        return self.update_signal_status(signal_id, SignalStatus.CONFIRMED)

    def execute_signal(self, signal_id: str) -> bool:
        """执行信号（已下单）

        Args:
            signal_id: 信号ID

        Returns:
            bool: 执行是否成功
        """
        return self.update_signal_status(signal_id, SignalStatus.EXECUTED)

    def register_callback(self, callback: Callable[[TradingSignal], None]) -> None:
        """注册信号回调函数

        Args:
            callback: 回调函数，接收TradingSignal参数
        """
        with self.lock:
            if callback not in self.callbacks:
                self.callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[TradingSignal], None]) -> None:
        """注销信号回调函数

        Args:
            callback: 回调函数
        """
        with self.lock:
            if callback in self.callbacks:
                self.callbacks.remove(callback)

    def clear_history(self, before_status: Optional[SignalStatus] = None) -> int:
        """清理历史信号

        Args:
            before_status: 已弃用参数，保留向后兼容。清理逻辑现在基于显式状态列表。

        Returns:
            int: 清理的信号数量
        """
        # 需要清理的历史状态列表（显式定义，不依赖枚举值顺序）
        historical_statuses = {
            SignalStatus.EXECUTED,      # 已执行（已完成交易）
            SignalStatus.CANCELLED,      # 已取消
            SignalStatus.RISK_REJECTED, # 风控拒绝
        }

        with self.lock:
            signal_ids = [
                sid for sid, s in self.signals.items()
                if s.status in historical_statuses
            ]
            for sid in signal_ids:
                del self.signals[sid]

            return len(signal_ids)

    def get_all_signals(self) -> List[TradingSignal]:
        """获取所有信号

        Returns:
            List[TradingSignal]: 所有信号列表
        """
        with self.lock:
            return list(self.signals.values())

    def _generate_signal_id(self) -> str:
        """生成唯一的信号ID

        Returns:
            str: 信号ID
        """
        return f"SIG-{uuid.uuid4().hex[:12].upper()}"

    def _trigger_callback(self, signal: TradingSignal) -> None:
        """触发所有注册的回调函数

        Args:
            signal: 发生变化的信号对象
        """
        # 使用锁保护callbacks列表的迭代操作
        with self.lock:
            callbacks_copy = list(self.callbacks)

        for callback in callbacks_copy:
            try:
                callback(signal)
            except Exception as e:
                # 记录异常但不影响其他回调
                logging.warning(f"信号回调执行异常: {e}")


__all__ = ["SignalEngine"]
