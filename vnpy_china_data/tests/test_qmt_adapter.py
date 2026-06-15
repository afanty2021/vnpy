"""QMT适配器历史数据下载单元测试"""

import sys
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

import pytest

sys.path.insert(0, '/Users/berton/Github/vnpy')

from vnpy_china_data.adapter.qmt_adapter import QMTDataAdapter, RealtimeBarGenerator
from vnpy.trader.constant import Exchange, Interval


class TestQMTAdapterHistoryData:
    """QMT适配器历史数据下载测试"""

    @pytest.fixture
    def adapter(self):
        """创建适配器实例"""
        adapter = QMTDataAdapter(
            qmt_path="D:/QMT/userdata_mini/",
            account_id="test_account"
        )
        return adapter

    def test_convert_to_qmt_code_a股(self, adapter):
        """测试A股代码转换为QMT格式"""
        # 上海证券交易所
        assert adapter._convert_to_qmt_code("600000", Exchange.SSE) == "600000.SH"
        assert adapter._convert_to_qmt_code("000001", Exchange.SZSE) == "000001.SZ"

    def test_convert_to_qmt_code_hk(self, adapter):
        """测试港股代码转换为QMT格式

        重要：港股通股票应该转换为香港本地交易所（HK）
        """
        # 香港本地交易所
        assert adapter._convert_to_qmt_code("00700", Exchange.SEHK) == "00700.HK"
        assert adapter._convert_to_qmt_code("01810", Exchange.SEHK) == "01810.HK"

        # 港股通（应该转换为香港本地）
        assert adapter._convert_to_qmt_code("00700", Exchange.SHHK) == "00700.HK"
        assert adapter._convert_to_qmt_code("00700", Exchange.SZHK) == "00700.HK"

    def test_interval_to_period(self, adapter):
        """测试K线周期转换"""
        assert adapter._interval_to_period(Interval.MINUTE) == "1m"
        assert adapter._interval_to_period(Interval.HOUR) == "1h"
        assert adapter._interval_to_period(Interval.DAILY) == "1d"
        assert adapter._interval_to_period(Interval.WEEKLY) == "1w"

    def test_parse_qmt_time(self, adapter):
        """测试QMT时间解析"""
        # 字符串格式
        time1 = adapter._parse_qmt_time("20240101 09:30:00")
        assert time1 == datetime(2024, 1, 1, 9, 30, 0)

        time2 = adapter._parse_qmt_time("2024-01-01 09:30:00")
        assert time2 == datetime(2024, 1, 1, 9, 30, 0)

        # datetime对象
        dt = datetime(2024, 1, 1, 9, 30, 0)
        assert adapter._parse_qmt_time(dt) == dt

    def test_get_bar_data_not_connected(self, adapter):
        """测试未连接时返回空列表"""
        adapter._connected = False

        bars = adapter.get_bar_data(
            symbol="000001",
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31)
        )

        assert bars == []

    def test_get_bar_data_with_mock_xtdata(self, adapter):
        """测试使用mock xtdata获取K线数据"""
        # 创建mock的xtdata模块
        mock_xtdata = MagicMock()
        mock_xtdata.download_history_data2 = Mock(return_value=None)

        # 创建模拟的DataFrame数据（time 为毫秒时间戳，匹配 xtdata 真实返回）
        mock_df = Mock()
        mock_df.iterrows = Mock(return_value=[
            (0, {
                'time': 1704067200000,  # 2024-01-01 UTC 毫秒
                'open': 10.0,
                'high': 11.0,
                'low': 9.5,
                'close': 10.5,
                'volume': 1000,
                'amount': 10500.0
            })
        ])
        mock_df.__len__ = Mock(return_value=1)
        # xtdata.get_local_data 真实返回 dict[str, DataFrame]（key=stock_code）
        mock_xtdata.get_local_data = Mock(return_value={"000001.SZ": mock_df})

        # 创建mock的xtquant模块
        mock_xtquant = MagicMock()
        mock_xtquant.xtdata = mock_xtdata

        # 将mock注入到sys.modules
        original_xtquant = sys.modules.get('xtquant')
        sys.modules['xtquant'] = mock_xtquant

        try:
            adapter._connected = True

            bars = adapter.get_bar_data(
                symbol="000001",
                exchange=Exchange.SZSE,
                interval=Interval.DAILY,
                start=datetime(2024, 1, 1),
                end=datetime(2024, 1, 31)
            )

            # 验证
            assert len(bars) == 1
            assert bars[0].symbol == "000001"
            assert bars[0].exchange == Exchange.SZSE
            assert bars[0].open_price == 10.0
            assert bars[0].close_price == 10.5
            # 毫秒时间戳正确解析为 2024-01-01
            assert bars[0].datetime.year == 2024
            assert bars[0].datetime.month == 1
            assert bars[0].datetime.day == 1

        finally:
            # 恢复原始模块
            if original_xtquant:
                sys.modules['xtquant'] = original_xtquant
            else:
                sys.modules.pop('xtquant', None)

    def test_get_sector_index_two_step_download(self, adapter):
        """测试 get_sector_index 两步下载模式"""
        from unittest.mock import MagicMock
        import sys

        # mock xtdata 模块
        mock_xtdata = MagicMock()
        mock_xtdata.download_history_data2 = MagicMock(return_value=None)

        mock_df = MagicMock()
        mock_df.iterrows = MagicMock(return_value=[
            (0, {
                'time': 1704067200000,  # 毫秒时间戳（2024-01-01 UTC），匹配 xtdata 真实返回
                'open': 100.0,
                'high': 110.0,
                'low': 95.0,
                'close': 105.0,
                'volume': 10000,
                'amount': 1000000.0,
            })
        ])
        mock_df.__len__ = MagicMock(return_value=1)
        # xtdata.get_local_data 真实返回 dict[str, DataFrame]（key=stock_code）
        mock_xtdata.get_local_data = MagicMock(return_value={"801010": mock_df})

        mock_xtquant = MagicMock()
        mock_xtquant.xtdata = mock_xtdata

        original_xtquant = sys.modules.get('xtquant')
        sys.modules['xtquant'] = mock_xtquant

        try:
            adapter._connected = True

            bars = adapter.get_sector_index(
                sector_code="801010",
                start_date="20240101",
                end_date="20240131"
            )

            # 验证返回 1 条 BarData
            assert len(bars) == 1
            assert bars[0].symbol == "801010"
            assert bars[0].open_price == 100.0
            assert bars[0].close_price == 105.0
            assert bars[0].interval == Interval.DAILY
            # 毫秒时间戳正确解析为 2024-01-01
            assert bars[0].datetime.year == 2024
            assert bars[0].datetime.month == 1
            assert bars[0].datetime.day == 1

            # 验证两步调用链
            mock_xtdata.download_history_data2.assert_called_once()
            mock_xtdata.get_local_data.assert_called_once()

        finally:
            if original_xtquant:
                sys.modules['xtquant'] = original_xtquant
            else:
                sys.modules.pop('xtquant', None)

    def test_get_sector_index_not_connected(self, adapter):
        """未连接时返回空列表"""
        adapter._connected = False

        bars = adapter.get_sector_index(
            sector_code="801010",
            start_date="20240101",
            end_date="20240131"
        )
        assert bars == []


class TestRealtimeBarGenerator:
    """实时K线生成器测试"""

    def test_interval_mapping(self):
        """测试周期映射"""
        generator = RealtimeBarGenerator("000001", Interval.MINUTE, None)

        # 测试支持的周期
        assert generator._get_interval_seconds(Interval.MINUTE) == 60
        assert generator._get_interval_seconds(Interval.HOUR) == 3600
        assert generator._get_interval_seconds(Interval.DAILY) == 86400
        assert generator._get_interval_seconds(Interval.WEEKLY) == 604800

    def test_is_new_bar_minute(self):
        """测试分钟线新K线判断"""
        generator = RealtimeBarGenerator("000001", Interval.MINUTE, None)

        current = datetime(2024, 1, 1, 10, 30, 0)
        bar_time = datetime(2024, 1, 1, 10, 29, 0)

        # 分钟不同，是新K线
        assert generator._is_new_bar(current, bar_time) == True

        # 分钟相同，不是新K线
        bar_time = datetime(2024, 1, 1, 10, 30, 30)
        assert generator._is_new_bar(current, bar_time) == False

    def test_get_bar_time(self):
        """测试K线时间获取"""
        generator = RealtimeBarGenerator("000001", Interval.MINUTE, None)

        tick_time = datetime(2024, 1, 1, 10, 30, 45)

        bar_time = generator._get_bar_time(tick_time)
        assert bar_time == datetime(2024, 1, 1, 10, 30, 0)
