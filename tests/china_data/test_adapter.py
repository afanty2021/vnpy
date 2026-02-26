"""
适配器单元测试

测试数据适配器的核心功能：
1. TushareDataAdapter - Tushare 数据适配器
2. RpcQmtDataAdapter - RPC QMT 数据适配器（重点测试交易时段判断）
"""

import os
import unittest
from datetime import datetime, time, timedelta
from unittest.mock import MagicMock, patch

os.environ["VNPY_ENV"] = "testing"

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, TickData

from vnpy_china_data.adapter.rpc_qmt_adapter import RpcQmtDataAdapter
from vnpy_china_data.adapter.tushare_adapter import TushareDataAdapter


class MockDataFrame:
    """Mock DataFrame 类"""
    def __init__(self, data=None):
        self._data = data or []

    @property
    def empty(self):
        return len(self._data) == 0

    def __len__(self):
        return len(self._data)


class TestRpcQmtDataAdapter(unittest.TestCase):
    """测试 RPC QMT 数据适配器"""

    def setUp(self):
        """测试前准备"""
        with patch("vnpy.rpc.RpcClient"):
            self.adapter = RpcQmtDataAdapter()

    def test_is_trading_time_weekday_morning(self):
        """测试工作日上午交易时段"""
        # 2026-02-26 是周四，在上午 10:00 是交易时段
        with patch("vnpy_china_data.adapter.rpc_qmt_adapter.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 2, 26, 10, 0)
            self.assertTrue(self.adapter._is_trading_time())

    def test_is_trading_time_weekday_afternoon(self):
        """测试工作日下午交易时段"""
        # 周四下午 14:00 是交易时段
        with patch("vnpy_china_data.adapter.rpc_qmt_adapter.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 2, 26, 14, 0)
            self.assertTrue(self.adapter._is_trading_time())

    def test_is_trading_time_weekday_outside_hours(self):
        """测试工作日非交易时段"""
        # 周四 12:00 是午休时段
        with patch("vnpy_china_data.adapter.rpc_qmt_adapter.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 2, 26, 12, 0)
            self.assertFalse(self.adapter._is_trading_time())

        # 周四 16:00 是盘后时段
        mock_datetime.now.return_value = datetime(2026, 2, 26, 16, 0)
        self.assertFalse(self.adapter._is_trading_time())

    def test_is_trading_time_weekend(self):
        """测试周末非交易时段"""
        # 周六上午 10:00
        with patch("vnpy_china_data.adapter.rpc_qmt_adapter.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 2, 28, 10, 0)  # 周六
            self.assertFalse(self.adapter._is_trading_time())

        # 周日下午 14:00
        with patch("vnpy_china_data.adapter.rpc_qmt_adapter.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 3, 1, 14, 0)  # 周日
            self.assertFalse(self.adapter._is_trading_time())

    def test_is_trading_time_boundary_cases(self):
        """测试交易时段边界情况"""
        with patch("vnpy_china_data.adapter.rpc_qmt_adapter.datetime") as mock_datetime:
            # 开盘前 9:29
            mock_datetime.now.return_value = datetime(2026, 2, 26, 9, 29)
            self.assertFalse(self.adapter._is_trading_time())

            # 开盘 9:30
            mock_datetime.now.return_value = datetime(2026, 2, 26, 9, 30)
            self.assertTrue(self.adapter._is_trading_time())

            # 上午收盘 11:30
            mock_datetime.now.return_value = datetime(2026, 2, 26, 11, 30)
            self.assertTrue(self.adapter._is_trading_time())

            # 上午收盘后 11:31
            mock_datetime.now.return_value = datetime(2026, 2, 26, 11, 31)
            self.assertFalse(self.adapter._is_trading_time())

            # 下午开盘 13:00
            mock_datetime.now.return_value = datetime(2026, 2, 26, 13, 0)
            self.assertTrue(self.adapter._is_trading_time())

            # 下午收盘 15:00
            mock_datetime.now.return_value = datetime(2026, 2, 26, 15, 0)
            self.assertTrue(self.adapter._is_trading_time())

            # 下午收盘后 15:01
            mock_datetime.now.return_value = datetime(2026, 2, 26, 15, 1)
            self.assertFalse(self.adapter._is_trading_time())

    def test_get_bar_data_during_trading_hours(self):
        """测试交易时段获取历史数据（应返回空列表）"""
        # 模拟交易时段
        with patch.object(self.adapter, "_is_trading_time", return_value=True):
            start = datetime(2026, 2, 20)
            end = datetime(2026, 2, 26)

            bars = self.adapter.get_bar_data(
                symbol="000001",
                exchange=Exchange.SZSE,
                interval=Interval.DAILY,
                start=start,
                end=end
            )

            # 交易时段应返回空列表
            self.assertEqual(bars, [])

    def test_get_bar_data_after_trading_hours(self):
        """测试盘后时段获取历史数据（应调用 RPC）"""
        # 模拟盘后时段
        with patch.object(self.adapter, "_is_trading_time", return_value=False):
            # Mock RPC 客户端
            self.adapter._connected = True
            self.adapter._rpc_client = MagicMock()
            self.adapter._rpc_client.query_history.return_value = []

            start = datetime(2026, 2, 20)
            end = datetime(2026, 2, 26)

            bars = self.adapter.get_bar_data(
                symbol="000001",
                exchange=Exchange.SZSE,
                interval=Interval.DAILY,
                start=start,
                end=end
            )

            # 应该调用 RPC 客户端的 query_history
            self.adapter._rpc_client.query_history.assert_called_once()

            # 检查请求参数
            call_args = self.adapter._rpc_client.query_history.call_args
            req = call_args[0][0]
            self.assertEqual(req["symbol"], "000001")
            self.assertEqual(req["exchange"], "SZSE")

    def test_get_bar_data_rpc_exception(self):
        """测试 RPC 调用异常情况"""
        # 模拟盘后时段
        with patch.object(self.adapter, "_is_trading_time", return_value=False):
            # Mock RPC 客户端抛出异常
            self.adapter._connected = True
            self.adapter._rpc_client = MagicMock()
            self.adapter._rpc_client.query_history.side_effect = Exception("RPC error")

            start = datetime(2026, 2, 20)
            end = datetime(2026, 2, 26)

            bars = self.adapter.get_bar_data(
                symbol="000001",
                exchange=Exchange.SZSE,
                interval=Interval.DAILY,
                start=start,
                end=end
            )

            # 应该返回空列表（fallback 到 Tushare）
            self.assertEqual(bars, [])

    def test_get_bar_data_not_connected(self):
        """测试 RPC 未连接情况"""
        # 模拟盘后时段但未连接
        with patch.object(self.adapter, "_is_trading_time", return_value=False):
            self.adapter._connected = False

            start = datetime(2026, 2, 20)
            end = datetime(2026, 2, 26)

            bars = self.adapter.get_bar_data(
                symbol="000001",
                exchange=Exchange.SZSE,
                interval=Interval.DAILY,
                start=start,
                end=end
            )

            # 应该返回空列表
            self.assertEqual(bars, [])

    def test_all_intervals_supported(self):
        """测试所有周期类型"""
        intervals = [Interval.MINUTE, Interval.HOUR, Interval.DAILY, Interval.WEEKLY]

        # 盘后时段测试
        with patch.object(self.adapter, "_is_trading_time", return_value=False):
            self.adapter._connected = True
            self.adapter._rpc_client = MagicMock()
            self.adapter._rpc_client.query_history.return_value = []

            start = datetime(2026, 2, 20)
            end = datetime(2026, 2, 26)

            for interval in intervals:
                bars = self.adapter.get_bar_data(
                    symbol="000001",
                    exchange=Exchange.SZSE,
                    interval=interval,
                    start=start,
                    end=end
                )
                # 不应该抛出异常
                self.assertIsNotNone(bars)
                self.assertIsInstance(bars, list)


class TestTushareDataAdapter(unittest.TestCase):
    """测试 Tushare 数据适配器"""

    def setUp(self):
        """测试前准备"""
        self.adapter = TushareDataAdapter(token="test_token")

    def test_symbol_to_ts_code_conversion(self):
        """测试股票代码到 Tushare 格式的转换"""
        # 上交所
        self.assertEqual(self.adapter.symbol_to_ts_code("600000", Exchange.SSE), "600000.SH")

        # 深交所
        self.assertEqual(self.adapter.symbol_to_ts_code("000001", Exchange.SZSE), "000001.SZ")

        # 北交所
        self.assertEqual(self.adapter.symbol_to_ts_code("430001", Exchange.BSE), "430001.BJ")

    def test_ts_code_to_symbol_conversion(self):
        """测试 Tushare 格式到股票代码的转换"""
        # 上交所
        symbol, exchange = self.adapter.ts_code_to_symbol("600000.SH")
        self.assertEqual(symbol, "600000")
        self.assertEqual(exchange, Exchange.SSE)

        # 深交所
        symbol, exchange = self.adapter.ts_code_to_symbol("000001.SZ")
        self.assertEqual(symbol, "000001")
        self.assertEqual(exchange, Exchange.SZSE)

        # 北交所
        symbol, exchange = self.adapter.ts_code_to_symbol("430001.BJ")
        self.assertEqual(symbol, "430001")
        self.assertEqual(exchange, Exchange.BSE)

    def test_get_bar_data_interval_daily(self):
        """测试获取日线数据"""
        # Mock Tushare API 调用，返回空 DataFrame
        with patch.object(self.adapter, "_call_api") as mock_api:
            mock_api.return_value = MockDataFrame([])

            bars = self.adapter.get_bar_data(
                symbol="000001",
                exchange=Exchange.SZSE,
                interval=Interval.DAILY,
                start=datetime(2026, 2, 20),
                end=datetime(2026, 2, 26)
            )

            # 应该调用日线接口
            self.assertIsNotNone(bars)
            self.assertIsInstance(bars, list)

    def test_get_bar_data_interval_minute(self):
        """测试获取分钟线数据"""
        # Mock Tushare API 调用，返回空 DataFrame
        with patch.object(self.adapter, "_call_api") as mock_api:
            mock_api.return_value = MockDataFrame([])

            bars = self.adapter.get_bar_data(
                symbol="000001",
                exchange=Exchange.SZSE,
                interval=Interval.MINUTE,
                start=datetime(2026, 2, 26),
                end=datetime(2026, 2, 26)
            )

            # 应该调用分钟线接口
            self.assertIsNotNone(bars)
            self.assertIsInstance(bars, list)


if __name__ == "__main__":
    unittest.main()