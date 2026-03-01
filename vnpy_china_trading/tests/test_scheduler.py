# -*- coding: utf-8 -*-
"""
策略调度器测试

测试StrategyScheduler类的各项功能。
"""

import time
import unittest
from datetime import datetime, time as dt_time
from unittest.mock import Mock, patch

from vnpy_china_trading.scheduler import StrategyScheduler, StrategyConfig


class TestStrategyScheduler(unittest.TestCase):
    """测试StrategyScheduler调度器"""

    def setUp(self):
        """测试前准备"""
        self.scheduler = StrategyScheduler()

    def tearDown(self):
        """测试后清理"""
        if self.scheduler.is_running():
            self.scheduler.stop()

    def test_add_strategy(self):
        """测试添加策略"""
        callback = Mock()

        config = StrategyConfig(
            name="test_strategy",
            callback=callback,
            enabled=True,
            run_interval=10,
        )

        self.scheduler.add_strategy(config)

        # 验证策略已添加
        retrieved = self.scheduler.get_strategy("test_strategy")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "test_strategy")
        self.assertEqual(retrieved.run_interval, 10)
        self.assertTrue(retrieved.enabled)

    def test_add_duplicate_strategy(self):
        """测试添加重复策略"""
        callback = Mock()

        config1 = StrategyConfig(name="test_strategy", callback=callback)
        config2 = StrategyConfig(name="test_strategy", callback=callback)

        self.scheduler.add_strategy(config1)

        # 应该抛出异常
        with self.assertRaises(ValueError):
            self.scheduler.add_strategy(config2)

    def test_remove_strategy(self):
        """测试移除策略"""
        callback = Mock()

        config = StrategyConfig(name="test_strategy", callback=callback)
        self.scheduler.add_strategy(config)

        # 移除策略
        result = self.scheduler.remove_strategy("test_strategy")

        # 验证
        self.assertTrue(result)
        self.assertIsNone(self.scheduler.get_strategy("test_strategy"))

    def test_remove_nonexistent_strategy(self):
        """测试移除不存在的策略"""
        result = self.scheduler.remove_strategy("nonexistent")
        self.assertFalse(result)

    def test_get_all_strategies(self):
        """测试获取所有策略"""
        callback = Mock()

        config1 = StrategyConfig(name="strategy1", callback=callback)
        config2 = StrategyConfig(name="strategy2", callback=callback)

        self.scheduler.add_strategy(config1)
        self.scheduler.add_strategy(config2)

        strategies = self.scheduler.get_all_strategies()

        # 验证
        self.assertEqual(len(strategies), 2)
        self.assertIn("strategy1", strategies)
        self.assertIn("strategy2", strategies)

    def test_start_stop(self):
        """测试启动和停止调度器"""
        callback = Mock()

        config = StrategyConfig(
            name="test_strategy",
            callback=callback,
            enabled=True,
            run_interval=1,
        )
        self.scheduler.add_strategy(config)

        # 启动调度器
        self.scheduler.start()
        self.assertTrue(self.scheduler.is_running())

        # 等待策略执行
        time.sleep(2)

        # 验证回调被调用
        self.assertTrue(callback.called)

        # 停止调度器
        self.scheduler.stop()
        self.assertFalse(self.scheduler.is_running())

    def test_start_stop_no_strategies(self):
        """测试空调度器启动停止"""
        self.scheduler.start()
        self.assertTrue(self.scheduler.is_running())

        self.scheduler.stop()
        self.assertFalse(self.scheduler.is_running())

    def test_run_at_time(self):
        """测试时间控制"""
        # 使用当前时间作为时间窗口
        current_time = datetime.now().time()

        # 创建一个时间窗口包含当前时间
        config = StrategyConfig(
            name="time_test",
            callback=Mock(),
            enabled=True,
            run_interval=1,
            run_time_start=dt_time(0, 0),  # 00:00
            run_time_end=dt_time(23, 59, 59),  # 23:59:59
        )

        self.assertTrue(
            self.scheduler._is_within_time_window(current_time, config)
        )

    def test_run_at_time_outside_window(self):
        """测试时间窗口外"""
        # 设置一个不可能包含当前时间的窗口
        config = StrategyConfig(
            name="time_test",
            callback=Mock(),
            enabled=True,
            run_interval=1,
            run_time_start=dt_time(3, 0),  # 03:00
            run_time_end=dt_time(4, 0),  # 04:00
        )

        current_time = datetime.now().time()

        # 如果当前时间不在3-4点之间，应该返回False
        # 注意：这个测试取决于运行时间
        if not (dt_time(3, 0) <= current_time <= dt_time(4, 0)):
            self.assertFalse(
                self.scheduler._is_within_time_window(current_time, config)
            )

    def test_run_at_time_cross_midnight(self):
        """测试跨午夜时间窗口"""
        config = StrategyConfig(
            name="cross_midnight",
            callback=Mock(),
            enabled=True,
            run_interval=1,
            run_time_start=dt_time(22, 0),  # 22:00
            run_time_end=dt_time(2, 0),  # 02:00 (次日)
        )

        # 测试22:30应该在窗口内
        self.assertTrue(
            self.scheduler._is_within_time_window(dt_time(22, 30), config)
        )

        # 测试01:30应该在窗口内（次日）
        self.assertTrue(
            self.scheduler._is_within_time_window(dt_time(1, 30), config)
        )

        # 测试12:00不应该在窗口内
        self.assertFalse(
            self.scheduler._is_within_time_window(dt_time(12, 0), config)
        )

    def test_start_already_running(self):
        """测试重复启动"""
        self.scheduler.start()
        self.assertTrue(self.scheduler.is_running())

        # 再次启动应该没有效果
        self.scheduler.start()
        self.assertTrue(self.scheduler.is_running())

        self.scheduler.stop()

    def test_stop_not_running(self):
        """测试停止未运行的调度器"""
        # 未启动直接停止应该没有效果
        self.scheduler.stop()
        self.assertFalse(self.scheduler.is_running())

    def test_disabled_strategy_not_run(self):
        """测试禁用的策略不会运行"""
        callback = Mock()

        config = StrategyConfig(
            name="disabled_strategy",
            callback=callback,
            enabled=False,  # 禁用
            run_interval=1,
        )
        self.scheduler.add_strategy(config)

        self.scheduler.start()
        time.sleep(2)

        # 验证回调未被调用
        self.assertFalse(callback.called)

        self.scheduler.stop()

    def test_multiple_strategies(self):
        """测试多个策略同时运行"""
        callback1 = Mock()
        callback2 = Mock()

        config1 = StrategyConfig(
            name="strategy1",
            callback=callback1,
            enabled=True,
            run_interval=1,
        )
        config2 = StrategyConfig(
            name="strategy2",
            callback=callback2,
            enabled=True,
            run_interval=1,
        )

        self.scheduler.add_strategy(config1)
        self.scheduler.add_strategy(config2)

        self.scheduler.start()
        time.sleep(3)

        # 两个回调都应该被调用
        self.assertTrue(callback1.called)
        self.assertTrue(callback2.called)

        self.scheduler.stop()

    def test_get_running_strategies(self):
        """测试获取运行中的策略"""
        callback = Mock()

        config = StrategyConfig(
            name="running_test",
            callback=callback,
            enabled=True,
            run_interval=1,
        )
        self.scheduler.add_strategy(config)

        self.scheduler.start()
        time.sleep(1)

        running = self.scheduler.get_running_strategies()
        self.assertIn("running_test", running)

        self.scheduler.stop()


class TestStrategyConfig(unittest.TestCase):
    """测试StrategyConfig数据类"""

    def test_create_basic_config(self):
        """测试创建基础配置"""
        callback = Mock()

        config = StrategyConfig(
            name="test",
            callback=callback,
        )

        self.assertEqual(config.name, "test")
        self.assertEqual(config.callback, callback)
        self.assertTrue(config.enabled)
        self.assertEqual(config.run_interval, 60)  # 默认值
        self.assertIsNone(config.run_time_start)
        self.assertIsNone(config.run_time_end)

    def test_create_full_config(self):
        """测试创建完整配置"""
        callback = Mock()

        config = StrategyConfig(
            name="full_test",
            callback=callback,
            enabled=False,
            run_interval=300,
            run_time_start=dt_time(9, 30),
            run_time_end=dt_time(15, 0),
        )

        self.assertEqual(config.name, "full_test")
        self.assertFalse(config.enabled)
        self.assertEqual(config.run_interval, 300)
        self.assertEqual(config.run_time_start, dt_time(9, 30))
        self.assertEqual(config.run_time_end, dt_time(15, 0))


class TestStrategySchedulerEdgeCases(unittest.TestCase):
    """测试调度器边界情况"""

    def setUp(self):
        """测试前准备"""
        self.scheduler = StrategyScheduler()

    def tearDown(self):
        """测试后清理"""
        if self.scheduler.is_running():
            self.scheduler.stop()

    def test_strategy_exception_handling(self):
        """测试策略异常处理"""
        def raise_error():
            raise ValueError("测试异常")

        config = StrategyConfig(
            name="exception_strategy",
            callback=raise_error,
            enabled=True,
            run_interval=1,
        )
        self.scheduler.add_strategy(config)

        # 调度器应该能够启动并运行，即使策略抛出异常
        self.scheduler.start()
        time.sleep(2)

        # 调度器应该仍然在运行
        self.assertTrue(self.scheduler.is_running())

        self.scheduler.stop()

    def test_add_strategy_while_running(self):
        """测试调度器运行时添加策略"""
        callback = Mock()

        config1 = StrategyConfig(
            name="strategy1",
            callback=callback,
            enabled=True,
            run_interval=1,
        )
        self.scheduler.add_strategy(config1)

        self.scheduler.start()
        time.sleep(1)

        # 在运行时添加第二个策略
        callback2 = Mock()
        config2 = StrategyConfig(
            name="strategy2",
            callback=callback2,
            enabled=True,
            run_interval=1,
        )
        self.scheduler.add_strategy(config2)

        time.sleep(2)

        # 两个回调都应该被调用
        self.assertTrue(callback.called)
        self.assertTrue(callback2.called)

        self.scheduler.stop()


if __name__ == "__main__":
    unittest.main()
