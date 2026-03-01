# -*- coding: utf-8 -*-
"""
策略调度器模块

提供多策略定时执行功能，支持时间控制和线程管理。
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, time as dt_time
from typing import Callable, Dict, Optional

# 创建模块日志记录器
logger = logging.getLogger(__name__)


@dataclass
class StrategyConfig:
    """策略配置数据类

    用于配置单个策略的执行参数。

    Attributes:
        name: 策略名称
        enabled: 是否启用
        run_interval: 运行间隔（秒）
        run_time_start: 开始时间（可选）
        run_time_end: 结束时间（可选）
        callback: 回调函数
    """

    name: str
    callback: Callable
    enabled: bool = True
    run_interval: int = 60
    run_time_start: Optional[dt_time] = None
    run_time_end: Optional[dt_time] = None


class StrategyScheduler:
    """策略调度器

    管理多个策略的定时执行，支持时间窗口控制。
    使用独立线程执行每个策略，确保策略间相互隔离。

    Attributes:
        strategies: 策略配置字典
        running: 调度器运行状态
        threads: 策略执行线程字典
    """

    def __init__(self) -> None:
        """初始化策略调度器"""
        self.strategies: Dict[str, StrategyConfig] = {}
        self._running: bool = False
        self._stop_event: threading.Event = threading.Event()
        self._threads: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

        logger.info("策略调度器初始化完成")

    def add_strategy(self, config: StrategyConfig) -> None:
        """添加策略

        Args:
            config: 策略配置对象

        Raises:
            ValueError: 如果策略名称已存在
        """
        with self._lock:
            if config.name in self.strategies:
                raise ValueError(f"策略名称已存在: {config.name}")

            self.strategies[config.name] = config
            logger.info(
                f"添加策略: {config.name}, "
                f"间隔: {config.run_interval}秒, "
                f"启用: {config.enabled}"
            )

            # 如果调度器正在运行且策略已启用，立即启动
            if self._running and config.enabled:
                self._start_strategy_thread(config)

    def remove_strategy(self, name: str) -> bool:
        """移除策略

        Args:
            name: 策略名称

        Returns:
            bool: 移除是否成功
        """
        with self._lock:
            if name not in self.strategies:
                logger.warning(f"策略不存在: {name}")
                return False

            # 停止策略线程
            if name in self._threads:
                self._stop_strategy_thread(name)

            del self.strategies[name]
            logger.info(f"移除策略: {name}")
            return True

    def get_strategy(self, name: str) -> Optional[StrategyConfig]:
        """获取策略

        Args:
            name: 策略名称

        Returns:
            Optional[StrategyConfig]: 策略配置，不存在则返回None
        """
        with self._lock:
            return self.strategies.get(name)

    def get_all_strategies(self) -> Dict[str, StrategyConfig]:
        """获取所有策略

        Returns:
            Dict[str, StrategyConfig]: 所有策略的字典
        """
        with self._lock:
            return dict(self.strategies)

    def start(self) -> None:
        """启动调度器

        启动所有已启用的策略执行线程。
        """
        with self._lock:
            if self._running:
                logger.warning("调度器已在运行中")
                return

            self._running = True
            self._stop_event.clear()
            logger.info("调度器启动")

            # 启动所有已启用的策略
            for config in self.strategies.values():
                if config.enabled:
                    self._start_strategy_thread(config)

    def stop(self) -> None:
        """停止调度器

        停止所有策略执行线程。
        """
        with self._lock:
            if not self._running:
                logger.warning("调度器未在运行")
                return

            self._running = False
            self._stop_event.set()

            # 停止所有策略线程
            for name in list(self._threads.keys()):
                self._stop_strategy_thread(name)

            logger.info("调度器停止")

    def _start_strategy_thread(self, config: StrategyConfig) -> None:
        """启动策略执行线程

        Args:
            config: 策略配置
        """
        # 如果线程已存在，先停止
        if config.name in self._threads:
            self._stop_strategy_thread(config.name)

        # 创建并启动新线程
        thread = threading.Thread(
            target=self._run_strategy,
            args=(config,),
            name=f"Strategy-{config.name}",
            daemon=True,
        )
        self._threads[config.name] = thread
        thread.start()

        logger.debug(f"策略线程启动: {config.name}")

    def _stop_strategy_thread(self, name: str) -> None:
        """停止策略执行线程

        Args:
            name: 策略名称
        """
        if name not in self._threads:
            return

        # 设置策略的停止标志（通过修改配置实现）
        # 注意：由于策略执行循环检查调度器状态，这里只需等待线程结束
        thread = self._threads[name]
        if thread.is_alive():
            # 等待线程结束（最多等待5秒）
            thread.join(timeout=5.0)
            if thread.is_alive():
                logger.warning(f"策略线程无法正常结束: {name}")

        del self._threads[name]
        logger.debug(f"策略线程停止: {name}")

    def _run_strategy(self, config: StrategyConfig) -> None:
        """运行单个策略

        在指定时间窗口内按间隔执行策略回调函数。

        Args:
            config: 策略配置
        """
        logger.info(f"策略开始执行: {config.name}")

        while self._running and not self._stop_event.is_set():
            try:
                # 检查时间窗口
                current_time = datetime.now().time()
                if not self._is_within_time_window(current_time, config):
                    # 未在时间窗口内，sleep 60秒后重试
                    logger.debug(
                        f"策略 {config.name} 未在时间窗口内，当前时间: {current_time}"
                    )
                    time.sleep(60)
                    continue

                # 执行策略回调
                logger.debug(f"执行策略: {config.name}")
                config.callback()

            except Exception as e:
                # 捕获异常并记录日志，保持调度器继续运行
                logger.error(f"策略执行异常: {config.name}, 错误: {e}", exc_info=True)

            # 等待下一次执行
            time.sleep(config.run_interval)

        logger.info(f"策略停止执行: {config.name}")

    def _is_within_time_window(
        self, current_time: dt_time, config: StrategyConfig
    ) -> bool:
        """检查当前时间是否在时间窗口内

        Args:
            current_time: 当前时间
            config: 策略配置

        Returns:
            bool: 是否在时间窗口内
        """
        # 如果没有设置时间窗口，始终返回True
        if config.run_time_start is None and config.run_time_end is None:
            return True

        # 如果只设置了开始时间
        if config.run_time_start is not None and config.run_time_end is None:
            return current_time >= config.run_time_start

        # 如果只设置了结束时间
        if config.run_time_start is None and config.run_time_end is not None:
            return current_time <= config.run_time_end

        # 如果同时设置了开始时间和结束时间
        # 处理跨午夜的情况（如 22:00 - 02:00）
        if config.run_time_start > config.run_time_end:
            return current_time >= config.run_time_start or current_time <= config.run_time_end

        # 正常情况（同一天内）
        return (
            current_time >= config.run_time_start
            and current_time <= config.run_time_end
        )

    def is_running(self) -> bool:
        """检查调度器是否运行中

        Returns:
            bool: 是否运行中
        """
        return self._running

    def get_running_strategies(self) -> Dict[str, threading.Thread]:
        """获取正在运行的策略线程

        Returns:
            Dict[str, threading.Thread]: 策略名称到线程的映射
        """
        with self._lock:
            return {
                name: thread
                for name, thread in self._threads.items()
                if thread.is_alive()
            }


__all__ = ["StrategyScheduler", "StrategyConfig"]
