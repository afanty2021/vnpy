"""
数据管理模块单元测试

测试数据预加载和定时更新功能。
"""

import unittest
import time
from datetime import date, datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from vnpy_china_ml.data.data_manager import (
    DataPreloader,
    DataUpdateScheduler,
    PreloadConfig,
    UpdateConfig,
)


class TestPreloadConfig(unittest.TestCase):
    """测试预加载配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = PreloadConfig()

        # 默认3年历史
        expected_start = date.today() - timedelta(days=365*3)
        self.assertEqual(config.start_date, expected_start)
        self.assertEqual(config.end_date, date.today())
        self.assertIsNone(config.symbols)
        self.assertTrue(config.enable_bar_data)
        self.assertTrue(config.enable_dragon_tiger)
        self.assertTrue(config.enable_northbound)
        self.assertTrue(config.enable_sector)
        self.assertTrue(config.concurrent)
        self.assertEqual(config.batch_size, 50)

    def test_custom_config(self):
        """测试自定义配置"""
        start = date(2024, 1, 1)
        end = date(2024, 12, 31)
        symbols = ["000001.SZ", "600000.SH"]

        config = PreloadConfig(
            start_date=start,
            end_date=end,
            symbols=symbols,
            enable_bar_data=False,
            batch_size=100
        )

        self.assertEqual(config.start_date, start)
        self.assertEqual(config.end_date, end)
        self.assertEqual(config.symbols, symbols)
        self.assertFalse(config.enable_bar_data)
        self.assertEqual(config.batch_size, 100)


class TestUpdateConfig(unittest.TestCase):
    """测试更新配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = UpdateConfig()

        self.assertEqual(config.update_time, "15:30")
        self.assertEqual(config.update_weekdays, [1, 2, 3, 4, 5])
        self.assertEqual(config.lookback_days, 5)
        self.assertTrue(config.enable_dragon_tiger)
        self.assertTrue(config.enable_northbound)
        self.assertTrue(config.enable_sector)

    def test_custom_config(self):
        """测试自定义配置"""
        config = UpdateConfig(
            update_time="16:00",
            update_weekdays=[1, 2, 3, 4, 5, 6],  # 包含周六
            lookback_days=10,
            enable_dragon_tiger=False
        )

        self.assertEqual(config.update_time, "16:00")
        self.assertEqual(config.update_weekdays, [1, 2, 3, 4, 5, 6])
        self.assertEqual(config.lookback_days, 10)
        self.assertFalse(config.enable_dragon_tiger)


class TestDataPreloader(unittest.TestCase):
    """测试数据预加载器"""

    def setUp(self):
        """设置测试环境"""
        self.mock_data_service = Mock()
        self.mock_event_engine = Mock()
        self.preloader = DataPreloader(
            data_service=self.mock_data_service,
            event_engine=self.mock_event_engine
        )

    def test_initialization(self):
        """测试初始化"""
        self.assertFalse(self.preloader.is_preloading())
        progress = self.preloader.get_preload_progress()
        self.assertFalse(progress["is_preloading"])
        self.assertEqual(progress["progress"]["total"], 0)
        self.assertEqual(progress["progress"]["completed"], 0)

    def test_preload_without_data_service(self):
        """测试无数据服务时预加载"""
        preloader = DataPreloader(data_service=None)

        config = PreloadConfig()
        stats = preloader.preload(config)

        self.assertEqual(stats, {})

    def test_preload_with_mock_service(self):
        """测试使用Mock服务预加载"""
        # Mock数据服务返回空数据
        self.mock_data_service.get_bar_data.return_value = []
        self.mock_data_service.get_dragon_tiger_data.return_value = []
        self.mock_data_service.get_northbound_flow.return_value = None
        self.mock_data_service.get_sector_list.return_value = []

        config = PreloadConfig(
            start_date=date.today() - timedelta(days=5),
            end_date=date.today(),
            enable_bar_data=False,  # 跳过K线数据（需要更复杂的mock）
            enable_dragon_tiger=True,
            enable_northbound=True,
            enable_sector=True
        )

        stats = self.preloader.preload(config)

        # 验证返回结果
        self.assertIn("dragon_tiger", stats)
        self.assertIn("northbound", stats)
        self.assertIn("sector", stats)

        # 验证事件发送
        self.mock_event_engine.put.assert_called()

    def test_progress_callback(self):
        """测试进度回调"""
        callback_results = []

        def progress_callback(completed, total, task):
            callback_results.append((completed, total, task))

        self.mock_data_service.get_dragon_tiger_data.return_value = []
        self.mock_data_service.get_northbound_flow.return_value = None
        self.mock_data_service.get_sector_list.return_value = []

        config = PreloadConfig(
            start_date=date.today() - timedelta(days=2),
            end_date=date.today(),
            enable_bar_data=False,
            enable_dragon_tiger=True,
            enable_northbound=False,
            enable_sector=False
        )

        self.preloader.preload(config, progress_callback)

        # 验证回调被调用
        self.assertGreater(len(callback_results), 0)

    def test_get_preload_progress(self):
        """测试获取预加载进度"""
        progress = self.preloader.get_preload_progress()

        self.assertIn("is_preloading", progress)
        self.assertIn("progress", progress)
        self.assertIn("stats", progress)


class TestDataUpdateScheduler(unittest.TestCase):
    """测试数据更新调度器"""

    def setUp(self):
        """设置测试环境"""
        self.mock_data_service = Mock()
        self.mock_event_engine = Mock()
        self.scheduler = DataUpdateScheduler(
            data_service=self.mock_data_service,
            event_engine=self.mock_event_engine
        )

    def tearDown(self):
        """清理测试环境"""
        if self.scheduler.is_running():
            self.scheduler.stop()

    def test_initialization(self):
        """测试初始化"""
        self.assertFalse(self.scheduler.is_running())
        stats = self.scheduler.get_stats()
        self.assertIsNone(stats["last_update_time"])
        self.assertEqual(stats["total_updates"], 0)

    def test_start_without_data_service(self):
        """测试无数据服务时启动"""
        scheduler = DataUpdateScheduler(data_service=None)

        result = scheduler.start()

        self.assertFalse(result)

    def test_get_config(self):
        """测试获取配置"""
        config = self.scheduler.get_config()

        self.assertEqual(config.update_time, "15:30")
        self.assertEqual(config.lookback_days, 5)

    def test_update_config(self):
        """测试更新配置"""
        new_config = UpdateConfig(
            update_time="14:30",
            lookback_days=10
        )

        self.scheduler.update_config(new_config)

        config = self.scheduler.get_config()
        self.assertEqual(config.update_time, "14:30")
        self.assertEqual(config.lookback_days, 10)

    def test_trigger_update_now(self):
        """测试立即触发更新"""
        # Mock数据服务
        self.mock_data_service.get_dragon_tiger_data.return_value = []
        self.mock_data_service.get_northbound_flow.return_value = None
        self.mock_data_service.get_sector_list.return_value = []

        # 启动调度器
        self.scheduler.start()

        # 等待启动完成
        time.sleep(0.1)

        # 触发更新
        result = self.scheduler.trigger_update_now()

        self.assertTrue(result)

        # 等待更新完成
        time.sleep(0.5)

        self.scheduler.stop()

    def test_should_update_today(self):
        """测试判断今天是否需要更新"""
        # 周一到周五应该更新
        result = self.scheduler._should_update_today()
        expected = datetime.now().weekday() in [1, 2, 3, 4, 5]
        self.assertEqual(result, expected)


class TestCreateDataManager(unittest.TestCase):
    """测试数据管理器工厂函数"""

    @patch('vnpy_china_ml.data.data_manager.CHINA_DATA_AVAILABLE', True)
    def test_create_data_manager(self):
        """测试创建数据管理器"""
        mock_data_service = Mock()
        mock_event_engine = Mock()

        from vnpy_china_ml.data.data_manager import create_data_manager

        preloader, scheduler = create_data_manager(
            data_service=mock_data_service,
            event_engine=mock_event_engine
        )

        self.assertIsInstance(preloader, DataPreloader)
        self.assertIsInstance(scheduler, DataUpdateScheduler)


if __name__ == "__main__":
    unittest.main()
