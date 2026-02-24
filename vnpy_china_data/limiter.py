"""
API限流器模块

实现令牌桶算法的API调用限流功能，用于控制Tushare等API的调用频率。
"""

import time
from collections import deque
from threading import Lock
from typing import Optional


class TokenBucket:
    """令牌桶算法实现

    用于实现平滑的速率限制，支持突发流量。
    """

    def __init__(self, rate: float, capacity: int):
        """初始化令牌桶

        Args:
            rate: 每秒添加的令牌数
            capacity: 令牌桶容量
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_time = time.time()
        self.lock = Lock()

    def acquire(self, tokens: int = 1) -> bool:
        """尝试获取令牌

        Args:
            tokens: 要获取的令牌数

        Returns:
            是否成功获取令牌
        """
        with self.lock:
            now = time.time()
            # 计算应该添加的令牌数
            elapsed = now - self.last_time
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_time = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def wait_for_token(self, tokens: int = 1) -> None:
        """等待直到获取到令牌

        Args:
            tokens: 要获取的令牌数
        """
        while not self.acquire(tokens):
            time.sleep(0.01)


class TushareRateLimiter:
    """Tushare API限流器

    基于滑动窗口算法实现，支持每分钟调用次数限制。
    """

    def __init__(self, max_calls: int = 200, period: int = 60):
        """初始化限流器

        Args:
            max_calls: 时间周期内最大调用次数
            period: 时间周期（秒）
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()
        self.lock = Lock()

    def acquire(self) -> bool:
        """尝试获取调用许可

        Returns:
            是否成功获取调用许可
        """
        with self.lock:
            now = time.time()

            # 清理过期的调用记录
            while self.calls and now - self.calls[0] > self.period:
                self.calls.popleft()

            # 检查是否还可以调用
            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True

            return False

    def wait_for_permission(self, timeout: Optional[float] = None) -> bool:
        """等待获取调用许可

        Args:
            timeout: 超时时间（秒），None表示无限等待

        Returns:
            是否成功获取调用许可
        """
        start_time = time.time()

        while True:
            if self.acquire():
                return True

            # 检查超时
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False

            # 短暂等待后重试
            time.sleep(0.1)

    def get_remaining_calls(self) -> int:
        """获取剩余可用调用次数

        Returns:
            剩余调用次数
        """
        with self.lock:
            now = time.time()

            # 清理过期的调用记录
            while self.calls and now - self.calls[0] > self.period:
                self.calls.popleft()

            return max(0, self.max_calls - len(self.calls))

    def get_wait_time(self) -> float:
        """获取距离下次可调用需要等待的时间

        Returns:
            等待时间（秒）
        """
        with self.lock:
            if len(self.calls) < self.max_calls:
                return 0.0

            # 计算最旧的调用过期时间
            oldest = self.calls[0]
            wait_time = self.period - (time.time() - oldest)
            return max(0.0, wait_time)

    def reset(self) -> None:
        """重置限流器"""
        with self.lock:
            self.calls.clear()


class AdaptiveRateLimiter:
    """自适应限流器

    根据API响应情况自动调整限流策略。
    """

    def __init__(
        self,
        initial_rate: int = 200,
        min_rate: int = 50,
        max_rate: int = 500,
        period: int = 60
    ):
        """初始化自适应限流器

        Args:
            initial_rate: 初始速率（每分钟调用次数）
            min_rate: 最小速率
            max_rate: 最大速率
            period: 时间周期（秒）
        """
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.period = period

        self._limiter = TushareRateLimiter(initial_rate, period)
        self._error_count = 0
        self._success_count = 0
        self._last_adjust_time = time.time()

    def acquire(self) -> bool:
        """尝试获取调用许可"""
        return self._limiter.acquire()

    def report_success(self) -> None:
        """报告调用成功"""
        self._success_count += 1
        self._error_count = max(0, self._error_count - 1)
        self._maybe_adjust_rate()

    def report_error(self) -> None:
        """报告调用失败"""
        self._error_count += 1
        self._maybe_adjust_rate()

    def _maybe_adjust_rate(self) -> None:
        """根据错误率调整速率"""
        now = time.time()

        # 每10秒调整一次
        if now - self._last_adjust_time < 10:
            return

        total = self._success_count + self._error_count
        if total == 0:
            return

        error_rate = self._error_count / total

        # 错误率超过20%，降低速率
        if error_rate > 0.2:
            new_rate = max(self.min_rate, int(self.current_rate * 0.8))
            if new_rate != self.current_rate:
                self.current_rate = new_rate
                self._limiter = TushareRateLimiter(new_rate, self.period)
                print(f"限流器调整: 降低速率到 {new_rate}/min")

        # 连续成功，降低速率
        elif self._error_count == 0 and self._success_count > 100:
            new_rate = min(self.max_rate, int(self.current_rate * 1.1))
            if new_rate != self.current_rate:
                self.current_rate = new_rate
                self._limiter = TushareRateLimiter(new_rate, self.period)
                print(f"限流器调整: 提高速率到 {new_rate}/min")

        # 重置计数
        self._success_count = 0
        self._error_count = 0
        self._last_adjust_time = now
