"""数据服务层单元测试"""

import logging
from datetime import date
from unittest.mock import Mock

import pytest

from vnpy.trader.constant import Exchange, Interval

from vnpy_china_data.service import ChinaDataService


def make_service_bypass_init(
    qmt_connected: bool,
    tushare_connected: bool = True,
):
    """绕过单例 __init__ 构造 service 实例（仅设置测试所需属性）"""
    service = ChinaDataService.__new__(ChinaDataService)
    service.qmt_adapter = Mock()
    service.qmt_adapter.connected = qmt_connected
    service.tushare_adapter = Mock()
    service.tushare_adapter.connected = tushare_connected
    service.database = Mock()
    # mock _fetch_bars_from_api 返回空（模拟无数据返回）
    service._fetch_bars_from_api = Mock(return_value=[])
    return service


class TestDownloadBarDataSemantics:
    """download_bar_data 区分性日志测试"""

    def test_warns_when_all_sources_disconnected(self, caplog):
        """两个数据源均未连接时记录 warning"""
        service = make_service_bypass_init(
            qmt_connected=False, tushare_connected=False
        )

        with caplog.at_level(logging.WARNING):
            result = service.download_bar_data(
                symbol="000001",
                exchange=Exchange.SZSE,
                interval=Interval.DAILY,
                start=date(2024, 1, 1),
                end=date(2024, 1, 31),
            )

        assert result == []
        assert "均未连接" in caplog.text

    def test_info_when_connected_but_no_data(self, caplog):
        """数据源已连接但无数据时记录 info（非 warning）"""
        service = make_service_bypass_init(qmt_connected=True)

        with caplog.at_level(logging.INFO):
            result = service.download_bar_data(
                symbol="000001",
                exchange=Exchange.SZSE,
                interval=Interval.DAILY,
                start=date(2024, 1, 1),
                end=date(2024, 1, 31),
            )

        assert result == []
        assert "无新数据" in caplog.text
        # 不应同时出现未连接 warning
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 0

    def test_info_when_qmt_down_but_tushare_up(self, caplog):
        """QMT未连接但Tushare可用时记info（仍可回退获取，非warning）"""
        service = make_service_bypass_init(
            qmt_connected=False, tushare_connected=True
        )

        with caplog.at_level(logging.INFO):
            result = service.download_bar_data(
                symbol="000001",
                exchange=Exchange.SZSE,
                interval=Interval.DAILY,
                start=date(2024, 1, 1),
                end=date(2024, 1, 31),
            )

        assert result == []
        assert "无新数据" in caplog.text
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 0
