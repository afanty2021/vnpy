"""
告警模块测试
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from vnpy_china_monitor.alert.engine import (
    AlertEngine,
    AlertPriority,
    AlertSeverity,
    AlertEvent,
)
from vnpy_china_monitor.alert.deduplicator import AlertDeduplicator, DedupeConfig
from vnpy_china_monitor.alert.priority_queue import AlertPriorityQueue
from vnpy_china_monitor.alert.channels.base import AlertChannel, AlertMessage
from vnpy_china_monitor.alert.channels.ui import UIChannel
from vnpy_china_monitor.alert.channels.email import EmailChannel
from vnpy_china_monitor.alert.channels.wechat import WechatChannel


class TestAlertEngine(unittest.TestCase):
    """AlertEngine 测试"""

    def setUp(self):
        """测试前置设置"""
        self.main_engine = Mock()
        self.event_engine = Mock()
        self.event_engine.put = Mock()
        self.alert_engine = AlertEngine(self.main_engine, self.event_engine)

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.alert_engine)
        self.assertFalse(self.alert_engine.is_running())

    def test_send_alert(self):
        """测试发送告警"""
        alert_id = self.alert_engine.send_alert(
            title="测试告警",
            message="这是一条测试告警",
            severity=AlertSeverity.INFO,
            priority=AlertPriority.NORMAL,
            source="test",
        )

        self.assertIsNotNone(alert_id)
        self.assertEqual(len(self.alert_engine.get_active_alerts()), 1)

    def test_send_alert_no_dedupe(self):
        """测试发送告警（去重）"""
        # 发送相同告警
        self.alert_engine.send_alert(
            title="测试告警",
            message="这是一条测试告警",
            severity=AlertSeverity.INFO,
            priority=AlertPriority.NORMAL,
            source="test",
        )

        # 再发送一次相同告警，应该被去重
        alert_id2 = self.alert_engine.send_alert(
            title="测试告警",
            message="这是一条测试告警",
            severity=AlertSeverity.INFO,
            priority=AlertPriority.NORMAL,
            source="test",
        )

        # 去重后返回None
        self.assertIsNone(alert_id2)

    def test_acknowledge_alert(self):
        """测试确认告警"""
        alert_id = self.alert_engine.send_alert(
            title="测试告警",
            message="这是一条测试告警",
        )

        success = self.alert_engine.acknowledge_alert(alert_id, "user1")
        self.assertTrue(success)

        # 确认后应该不在活跃告警中
        self.assertEqual(len(self.alert_engine.get_active_alerts()), 0)

    def test_acknowledge_alert_not_found(self):
        """测试确认不存在的告警"""
        success = self.alert_engine.acknowledge_alert("not_exist", "user1")
        self.assertFalse(success)

    def test_get_alert_history(self):
        """测试获取告警历史"""
        # 发送并确认告警
        alert_id = self.alert_engine.send_alert(title="测试", message="消息")
        self.alert_engine.acknowledge_alert(alert_id)

        history = self.alert_engine.get_alert_history()
        self.assertEqual(len(history), 1)

    def test_register_channel(self):
        """测试注册通道"""
        channel = Mock(spec=AlertChannel)
        self.alert_engine.register_channel(channel)

        self.assertEqual(len(self.alert_engine._channels), 1)

    def test_get_stats(self):
        """测试获取统计信息"""
        self.alert_engine.send_alert(
            title="告警1",
            message="消息1",
            severity=AlertSeverity.INFO,
        )
        self.alert_engine.send_alert(
            title="告警2",
            message="消息2",
            severity=AlertSeverity.WARNING,
        )

        stats = self.alert_engine.get_stats()
        self.assertEqual(stats["total_sent"], 2)

    def test_start_stop(self):
        """测试启动停止"""
        self.alert_engine.start()
        self.assertTrue(self.alert_engine.is_running())

        self.alert_engine.stop()
        self.assertFalse(self.alert_engine.is_running())


class TestAlertDeduplicator(unittest.TestCase):
    """AlertDeduplicator 测试"""

    def setUp(self):
        """测试前置设置"""
        self.config = DedupeConfig(
            window_seconds=300,
            cooldown_seconds=600,
            max_same_alerts=3,
        )
        self.deduplicator = AlertDeduplicator(self.config)

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.deduplicator)

    def test_should_send_first(self):
        """测试首次发送"""
        alert = AlertEvent(
            id="1",
            title="测试",
            message="消息",
            severity=AlertSeverity.INFO,
            priority=AlertPriority.NORMAL,
            source="test",
        )

        result = self.deduplicator.should_send(alert)
        self.assertTrue(result)

    def test_dedupe_within_window(self):
        """测试时间窗口内去重"""
        alert = AlertEvent(
            id="1",
            title="测试",
            message="消息",
            severity=AlertSeverity.INFO,
            priority=AlertPriority.NORMAL,
            source="test",
        )

        # 首次发送
        self.deduplicator.should_send(alert)
        self.deduplicator.record_alert(self.deduplicator.get_fingerprint(alert))

        # 再次发送，应该被去重
        result = self.deduplicator.should_send(alert)
        self.assertFalse(result)

    def test_dedupe_max_reached(self):
        """测试达到最大次数"""
        # 创建新的去重器，避免之前的记录干扰
        dedup = AlertDeduplicator(DedupeConfig(window_seconds=300, cooldown_seconds=600, max_same_alerts=3))

        alert = AlertEvent(
            id="1",
            title="测试",
            message="消息",
            severity=AlertSeverity.INFO,
            priority=AlertPriority.NORMAL,
            source="test",
        )

        # 第一次：允许发送
        self.assertTrue(dedup.should_send(alert))
        dedup.record_alert(dedup.get_fingerprint(alert))

        # 第二次：在时间窗口内，去重
        self.assertFalse(dedup.should_send(alert))

    def test_get_fingerprint(self):
        """测试指纹生成"""
        alert = AlertEvent(
            id="1",
            title="测试",
            message="消息",
            severity=AlertSeverity.INFO,
            priority=AlertPriority.NORMAL,
            source="test",
        )

        fp1 = self.deduplicator.get_fingerprint(alert)

        # 相同内容应该生成相同指纹
        alert2 = AlertEvent(
            id="2",
            title="测试",
            message="消息",
            severity=AlertSeverity.INFO,
            priority=AlertPriority.NORMAL,
            source="test",
        )
        fp2 = self.deduplicator.get_fingerprint(alert2)

        self.assertEqual(fp1, fp2)

    def test_get_stats(self):
        """测试获取统计"""
        alert = AlertEvent(
            id="1",
            title="测试",
            message="消息",
            severity=AlertSeverity.INFO,
            priority=AlertPriority.NORMAL,
            source="test",
        )

        self.deduplicator.should_send(alert)
        stats = self.deduplicator.get_stats()

        self.assertEqual(stats["total_alerts"], 1)


class TestAlertPriorityQueue(unittest.TestCase):
    """AlertPriorityQueue 测试"""

    def setUp(self):
        """测试前置设置"""
        self.queue = AlertPriorityQueue()

    def test_init(self):
        """测试初始化"""
        self.assertTrue(self.queue.is_empty())

    def test_put_and_pop(self):
        """测试放入和弹出"""
        alert1 = AlertEvent(
            id="1",
            title="低优先级",
            message="消息",
            severity=AlertSeverity.INFO,
            priority=AlertPriority.LOW,
            source="test",
        )

        alert2 = AlertEvent(
            id="2",
            title="高优先级",
            message="消息",
            severity=AlertSeverity.CRITICAL,
            priority=AlertPriority.CRITICAL,
            source="test",
        )

        self.queue.put(alert1)
        self.queue.put(alert2)

        # 高优先级应该先出来
        popped = self.queue.pop()
        self.assertEqual(popped.id, "2")

    def test_remove(self):
        """测试移除"""
        alert = AlertEvent(
            id="1",
            title="测试",
            message="消息",
            severity=AlertSeverity.INFO,
            priority=AlertPriority.NORMAL,
            source="test",
        )

        self.queue.put(alert)
        self.assertEqual(self.queue.size(), 1)

        self.queue.remove("1")
        self.assertEqual(self.queue.size(), 0)

    def test_clear(self):
        """测试清空"""
        alert = AlertEvent(
            id="1",
            title="测试",
            message="消息",
            severity=AlertSeverity.INFO,
            priority=AlertPriority.NORMAL,
            source="test",
        )

        self.queue.put(alert)
        self.queue.clear()
        self.assertTrue(self.queue.is_empty())


class TestAlertChannels(unittest.TestCase):
    """告警通道测试"""

    def test_ui_channel_init(self):
        """测试UI通道初始化"""
        channel = UIChannel(enabled=True, popup_duration=5)
        self.assertTrue(channel.enabled)
        self.assertEqual(channel.popup_duration, 5)

    def test_email_channel_init(self):
        """测试邮件通道初始化"""
        channel = EmailChannel(
            enabled=True,
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="test@test.com",
            smtp_password="password",
            email_to=["receiver@test.com"],
        )
        self.assertTrue(channel.enabled)
        self.assertEqual(len(channel.email_to), 1)

    def test_wechat_channel_init(self):
        """测试微信通道初始化"""
        channel = WechatChannel(
            enabled=True,
            webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
        )
        self.assertTrue(channel.enabled)
        self.assertIsNotNone(channel.webhook_url)


class TestAlertMessage(unittest.TestCase):
    """AlertMessage 测试"""

    def test_format_text(self):
        """测试格式化文本"""
        message = AlertMessage(
            title="测试告警",
            message="这是一条测试告警",
            severity="info",
            priority=30,
            timestamp=datetime.now(),
            source="test",
        )

        text = message.format_text()
        self.assertIn("测试告警", text)
        self.assertIn("info", text)

    def test_format_html(self):
        """测试格式化HTML"""
        message = AlertMessage(
            title="测试告警",
            message="这是一条测试告警",
            severity="warning",
            priority=50,
            timestamp=datetime.now(),
            source="test",
        )

        html = message.format_html()
        self.assertIn("测试告警", html)
        self.assertIn("warning", html)


if __name__ == "__main__":
    unittest.main()
