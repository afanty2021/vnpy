"""
监控模块测试
"""

import unittest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from vnpy_china_monitor.monitor.engine import MonitorEngine, MonitorType, MonitorData
from vnpy_china_monitor.monitor.system_monitor import SystemMonitor
from vnpy_china_monitor.monitor.trade_monitor import TradeMonitor


class TestMonitorEngine(unittest.TestCase):
    """MonitorEngine 测试"""

    def setUp(self):
        """测试前置设置"""
        self.main_engine = Mock()
        self.event_engine = Mock()
        self.event_engine.put = Mock()
        self.monitor_engine = MonitorEngine(self.main_engine, self.event_engine)

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.monitor_engine)
        self.assertFalse(self.monitor_engine.is_running())

    def test_register_system_monitor(self):
        """测试注册系统监控器"""
        system_monitor = Mock()
        self.monitor_engine.register_system_monitor(system_monitor)
        self.assertEqual(self.monitor_engine.get_system_monitor(), system_monitor)

    def test_register_trade_monitor(self):
        """测试注册交易监控器"""
        trade_monitor = Mock()
        self.monitor_engine.register_trade_monitor(trade_monitor)
        self.assertEqual(self.monitor_engine.get_trade_monitor(), trade_monitor)

    def test_update_monitor(self):
        """测试更新监控数据"""
        self.monitor_engine.update_monitor(
            name="test_metric",
            monitor_type=MonitorType.SYSTEM,
            value=100,
            status="normal",
            unit="%",
            description="测试指标",
        )

        data = self.monitor_engine.get_monitor_data("test_metric")
        self.assertIsNotNone(data)
        self.assertEqual(data.value, 100)
        self.assertEqual(data.status, "normal")

    def test_get_monitor_data_not_found(self):
        """测试获取不存在的监控数据"""
        data = self.monitor_engine.get_monitor_data("not_exist")
        self.assertIsNone(data)

    def test_get_all_monitors(self):
        """测试获取所有监控数据"""
        self.monitor_engine.update_monitor(
            name="metric1",
            monitor_type=MonitorType.SYSTEM,
            value=10,
        )
        self.monitor_engine.update_monitor(
            name="metric2",
            monitor_type=MonitorType.TRADE,
            value=20,
        )

        all_monitors = self.monitor_engine.get_all_monitors()
        self.assertEqual(len(all_monitors), 2)

    def test_get_monitors_by_type(self):
        """测试按类型获取监控数据"""
        self.monitor_engine.update_monitor(
            name="sys_metric",
            monitor_type=MonitorType.SYSTEM,
            value=10,
        )
        self.monitor_engine.update_monitor(
            name="trade_metric",
            monitor_type=MonitorType.TRADE,
            value=20,
        )

        system_monitors = self.monitor_engine.get_monitors_by_type(MonitorType.SYSTEM)
        self.assertEqual(len(system_monitors), 1)
        self.assertEqual(system_monitors[0].name, "sys_metric")

    def test_callback_registration(self):
        """测试回调注册"""
        callback_called = {"called": False}

        def callback(data):
            callback_called["called"] = True

        self.monitor_engine.register_callback(callback)

        # 更新监控数据触发回调
        self.monitor_engine.update_monitor(
            name="test",
            monitor_type=MonitorType.SYSTEM,
            value=100,
        )

        self.assertTrue(callback_called["called"])

    def test_start_stop(self):
        """测试启动停止"""
        self.monitor_engine.start()
        self.assertTrue(self.monitor_engine.is_running())

        self.monitor_engine.stop()
        self.assertFalse(self.monitor_engine.is_running())

    def test_get_monitor_summary(self):
        """测试获取监控摘要"""
        self.monitor_engine.update_monitor(
            name="normal",
            monitor_type=MonitorType.SYSTEM,
            value=10,
            status="normal",
        )
        self.monitor_engine.update_monitor(
            name="warning",
            monitor_type=MonitorType.SYSTEM,
            value=20,
            status="warning",
        )
        self.monitor_engine.update_monitor(
            name="critical",
            monitor_type=MonitorType.SYSTEM,
            value=30,
            status="critical",
        )

        summary = self.monitor_engine.get_monitor_summary()
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["normal"], 1)
        self.assertEqual(summary["warning"], 1)
        self.assertEqual(summary["critical"], 1)


class TestSystemMonitor(unittest.TestCase):
    """SystemMonitor 测试"""

    def setUp(self):
        """测试前置设置"""
        self.main_engine = Mock()
        self.event_engine = Mock()
        self.monitor_engine = MonitorEngine(self.main_engine, self.event_engine)
        self.system_monitor = SystemMonitor(self.monitor_engine, check_interval=60)

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.system_monitor)
        self.assertEqual(self.system_monitor.check_interval, 60)

    @patch("vnpy_china_monitor.monitor.system_monitor.psutil")
    def test_check_memory_usage(self, mock_psutil):
        """测试内存检查"""
        mock_psutil.virtual_memory.return_value = Mock(
            percent=50.0,
            total=16000000000,
            available=8000000000,
            used=8000000000,
        )

        result = self.system_monitor.check_memory_usage()
        self.assertEqual(result["percent"], 50.0)
        self.assertEqual(result["status"], "normal")

    @patch("vnpy_china_monitor.monitor.system_monitor.psutil")
    def test_check_memory_warning(self, mock_psutil):
        """测试内存警告"""
        mock_psutil.virtual_memory.return_value = Mock(
            percent=85.0,
            total=16000000000,
            available=2400000000,
            used=13600000000,
        )

        result = self.system_monitor.check_memory_usage()
        self.assertEqual(result["status"], "warning")

    @patch("vnpy_china_monitor.monitor.system_monitor.psutil")
    def test_check_memory_critical(self, mock_psutil):
        """测试内存严重"""
        mock_psutil.virtual_memory.return_value = Mock(
            percent=95.0,
            total=16000000000,
            available=800000000,
            used=15200000000,
        )

        result = self.system_monitor.check_memory_usage()
        self.assertEqual(result["status"], "critical")

    def test_check_qmt_connection_no_gateway(self):
        """测试QMT连接检查（无网关）"""
        result = self.system_monitor.check_qmt_connection()
        self.assertFalse(result["connected"])
        self.assertEqual(result["status"], "unknown")

    def test_check_qmt_connection_connected(self):
        """测试QMT连接检查（已连接）"""
        gateway = Mock()
        gateway.is_connected = Mock(return_value=True)
        self.system_monitor.set_qmt_gateway(gateway)

        result = self.system_monitor.check_qmt_connection()
        self.assertTrue(result["connected"])
        self.assertEqual(result["status"], "connected")

    def test_start_stop(self):
        """测试启动停止"""
        self.system_monitor.start()
        self.assertTrue(self.system_monitor._running)

        self.system_monitor.stop()
        self.assertFalse(self.system_monitor._running)


class TestTradeMonitor(unittest.TestCase):
    """TradeMonitor 测试"""

    def setUp(self):
        """测试前置设置"""
        self.main_engine = Mock()
        self.event_engine = Mock()
        self.monitor_engine = MonitorEngine(self.main_engine, self.event_engine)
        self.trade_monitor = TradeMonitor(
            self.main_engine, self.event_engine, self.monitor_engine
        )

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.trade_monitor)

    def test_get_positions(self):
        """测试获取持仓"""
        positions = self.trade_monitor.get_positions()
        self.assertEqual(len(positions), 0)

    def test_get_account(self):
        """测试获取账户"""
        account = self.trade_monitor.get_account()
        self.assertIsNone(account)

    def test_get_daily_stats(self):
        """测试获取日统计"""
        stats = self.trade_monitor.get_daily_stats()
        self.assertEqual(stats["trade_count"], 0)
        self.assertEqual(stats["order_count"], 0)

    def test_get_position_summary(self):
        """测试获取持仓汇总"""
        summary = self.trade_monitor.get_position_summary()
        self.assertEqual(summary["total_positions"], 0)

    def test_get_order_stats(self):
        """测试获取委托统计"""
        stats = self.trade_monitor.get_order_stats()
        self.assertEqual(stats["total_orders"], 0)

    def test_start_stop(self):
        """测试启动停止"""
        self.trade_monitor.start()
        self.assertTrue(self.trade_monitor._running)

        self.trade_monitor.stop()
        self.assertFalse(self.trade_monitor._running)


if __name__ == "__main__":
    unittest.main()
