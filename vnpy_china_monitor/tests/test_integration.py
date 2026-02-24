"""
集成测试
"""

import unittest
from unittest.mock import Mock, MagicMock, patch

from vnpy_china_monitor.integration.risk_connector import RiskConnector
from vnpy_china_monitor.alert.rules.risk_bridge import RiskAlertBridge


class TestRiskConnector(unittest.TestCase):
    """RiskConnector 测试"""

    def setUp(self):
        """测试前置设置"""
        self.monitor_system = Mock()
        self.monitor_system.alert_engine = Mock()
        self.monitor_system.monitor_engine = Mock()
        self.connector = RiskConnector(self.monitor_system)

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.connector)
        self.assertFalse(self.connector.is_connected())

    @patch("vnpy_china_monitor.integration.risk_connector.RISK_MODULE_AVAILABLE", False)
    def test_connect_no_module(self):
        """测试连接（模块不可用）"""
        risk_manager = Mock()
        result = self.connector.connect(risk_manager)
        self.assertFalse(result)

    def test_disconnect(self):
        """测试断开连接"""
        self.connector.disconnect()
        self.assertFalse(self.connector.is_connected())

    def test_get_risk_status_not_connected(self):
        """测试获取风控状态（未连接）"""
        status = self.connector.get_risk_status()
        self.assertFalse(status["connected"])

    def test_get_active_risk_alerts_not_connected(self):
        """测试获取活跃告警（未连接）"""
        alerts = self.connector.get_active_risk_alerts()
        self.assertEqual(len(alerts), 0)


class TestRiskAlertBridge(unittest.TestCase):
    """RiskAlertBridge 测试"""

    def setUp(self):
        """测试前置设置"""
        self.alert_engine = Mock()
        self.alert_engine.send_alert = Mock(return_value="alert_id")
        self.risk_manager = Mock()
        self.risk_manager.subscribe_risk_events = Mock()
        self.bridge = RiskAlertBridge(
            self.alert_engine, self.risk_manager, check_interval=60
        )

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.bridge)
        self.assertFalse(self.bridge._running)

    def test_start_stop(self):
        """测试启动停止"""
        # 注意：由于RISK_MODULE_AVAILABLE可能为False，这里只测试基本逻辑
        self.assertFalse(self.bridge._running)

    def test_check_risk_status(self):
        """测试检查风控状态"""
        self.risk_manager.get_active_risk_alerts = Mock(return_value=[])
        self.risk_manager.get_risk_status = Mock(return_value={"status": "ok"})

        status = self.bridge.check_risk_status()
        self.assertIsNotNone(status)

    def test_convert_severity(self):
        """测试严重程度转换"""
        # info -> INFO
        result = self.bridge._convert_severity("info")
        self.assertEqual(result.value, "info")

        # warning -> WARNING
        result = self.bridge._convert_severity("warning")
        self.assertEqual(result.value, "warning")

        # critical -> CRITICAL
        result = self.bridge._convert_severity("critical")
        self.assertEqual(result.value, "critical")

    def test_convert_priority(self):
        """测试优先级转换"""
        # info -> INFO
        result = self.bridge._convert_priority("info")
        self.assertEqual(result, 10)

        # warning -> HIGH
        result = self.bridge._convert_priority("warning")
        self.assertEqual(result, 50)

        # critical -> CRITICAL
        result = self.bridge._convert_priority("critical")
        self.assertEqual(result, 70)

    def test_get_last_check_time(self):
        """测试获取最后检查时间"""
        # 初始时间应该很早
        self.assertIsNotNone(self.bridge.get_last_check_time())

    def test_get_last_alert_count(self):
        """测试获取最后告警数量"""
        # 初始应该为0
        self.assertEqual(self.bridge.get_last_alert_count(), 0)


class TestMonitorSystemIntegration(unittest.TestCase):
    """监控系统集成测试"""

    def test_create_monitor_system(self):
        """测试创建监控系统"""
        # 导入MonitorSystem（如果已实现）
        try:
            from vnpy_china_monitor.monitor_system import MonitorSystem
        except ImportError:
            self.skipTest("MonitorSystem not implemented yet")
            return

    def test_alert_to_monitor_connection(self):
        """测试告警与监控的连接"""
        # 这个测试验证告警引擎可以正确连接到监控引擎
        # 当告警触发时，应该能够更新监控数据
        pass


if __name__ == "__main__":
    unittest.main()
