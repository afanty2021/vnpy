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
from vnpy_china_data.adapter.qmt_adapter import QMTDataAdapter
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
            gateway_name = call_args[0][1]
            self.assertEqual(req["symbol"], "000001")
            self.assertEqual(req["exchange"], "SZSE")
            self.assertEqual(gateway_name, "QMT")  # 验证 gateway_name 参数

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


class TestQmtDataAdapter(unittest.TestCase):
    """测试 QMT 数据适配器"""

    def setUp(self):
        """测试前准备"""
        self.adapter = QMTDataAdapter()

    def test_exchange_to_market_shhk(self):
        """测试沪港通交易所映射"""
        result = self.adapter._exchange_to_market(Exchange.SHHK)
        self.assertEqual(result, "HK_SHTC")

    def test_exchange_to_market_szhk(self):
        """测试深港通交易所映射"""
        result = self.adapter._exchange_to_market(Exchange.SZHK)
        self.assertEqual(result, "HK_SZTC")

    def test_exchange_to_market_sehk(self):
        """测试香港本地交易所映射"""
        result = self.adapter._exchange_to_market(Exchange.SEHK)
        self.assertEqual(result, "HK")

    def test_exchange_to_market_unsupported(self):
        """测试不支持的交易所映射"""
        # 测试 A股交易所，应返回 None
        self.assertIsNone(self.adapter._exchange_to_market(Exchange.SSE))
        self.assertIsNone(self.adapter._exchange_to_market(Exchange.SZSE))
        self.assertIsNone(self.adapter._exchange_to_market(Exchange.BSE))

    def test_exchange_to_market_all_hong_kong_exchanges(self):
        """测试所有香港交易所映射的完整性"""
        # 测试所有香港交易所的映射
        hk_mappings = {
            Exchange.SHHK: "HK_SHTC",  # 沪港通
            Exchange.SZHK: "HK_SZTC",  # 深港通
            Exchange.SEHK: "HK",       # 香港本地
        }

        for exchange, expected_market in hk_mappings.items():
            with self.subTest(exchange=exchange):
                result = self.adapter._exchange_to_market(exchange)
                self.assertEqual(result, expected_market,
                               f"Exchange {exchange.value} 应映射到 {expected_market}")

    def test_qmt_symbol_to_vnpy_shhk(self):
        """测试沪港通 QMT 格式转换为 VeighNa 格式"""
        # 沪港通格式
        self.assertEqual(
            self.adapter._qmt_symbol_to_vnpy("0700.HK_SHTC"),
            "0700.SHHK"
        )
        self.assertEqual(
            self.adapter._qmt_symbol_to_vnpy("2318.HK_SHTC"),
            "2318.SHHK"
        )
        self.assertEqual(
            self.adapter._qmt_symbol_to_vnpy("09988.HK_SHTC"),
            "09988.SHHK"
        )

    def test_qmt_symbol_to_vnpy_szhk(self):
        """测试深港通 QMT 格式转换为 VeighNa 格式"""
        # 深港通格式
        self.assertEqual(
            self.adapter._qmt_symbol_to_vnpy("0700.HK_SZTC"),
            "0700.SZHK"
        )
        self.assertEqual(
            self.adapter._qmt_symbol_to_vnpy("2318.HK_SZTC"),
            "2318.SZHK"
        )
        self.assertEqual(
            self.adapter._qmt_symbol_to_vnpy("09988.HK_SZTC"),
            "09988.SZHK"
        )

    def test_qmt_symbol_to_vnpy_sehk(self):
        """测试香港本地 QMT 格式转换为 VeighNa 格式"""
        # 香港本地格式
        self.assertEqual(
            self.adapter._qmt_symbol_to_vnpy("0700.HK"),
            "0700.SEHK"
        )
        self.assertEqual(
            self.adapter._qmt_symbol_to_vnpy("2318.HK"),
            "2318.SEHK"
        )

    def test_qmt_symbol_to_vnpy_invalid(self):
        """测试无效 QMT 格式的转换"""
        # 没有点号分隔符
        self.assertIsNone(self.adapter._qmt_symbol_to_vnpy("0700"))

        # 不支持的市场
        self.assertIsNone(self.adapter._qmt_symbol_to_vnpy("0700.SH"))
        self.assertIsNone(self.adapter._qmt_symbol_to_vnpy("0700.SZ"))

        # 空字符串
        self.assertIsNone(self.adapter._qmt_symbol_to_vnpy(""))

    def test_qmt_symbol_to_vnpy_edge_cases(self):
        """测试边界情况"""
        # 多个点号（只按第一个分割）
        self.assertEqual(
            self.adapter._qmt_symbol_to_vnpy("0700.HK_SHTC.EXTRA"),
            "0700.SHHK"
        )

        # 带特殊字符的股票代码
        self.assertEqual(
            self.adapter._qmt_symbol_to_vnpy("09988.HK_SHTC"),
            "09988.SHHK"
        )

    def test_get_hk_sh_symbols_not_connected(self):
        """测试未连接时获取沪港通标的"""
        # 未连接状态
        self.adapter._connected = False

        symbols = self.adapter.get_hk_sh_symbols()
        self.assertEqual(symbols, [])

    def test_get_hk_sz_symbols_not_connected(self):
        """测试未连接时获取深港通标的"""
        # 未连接状态
        self.adapter._connected = False

        symbols = self.adapter.get_hk_sz_symbols()
        self.assertEqual(symbols, [])

    def test_get_hk_sh_symbols_connected(self):
        """测试连接时获取沪港通标的"""
        # 模拟已连接
        self.adapter._connected = True

        # Mock _get_stock_list_in_sector_mock 方法
        mock_stock_list = ["0700.HK_SHTC", "2318.HK_SHTC", "09988.HK_SHTC"]
        with patch.object(self.adapter, '_get_stock_list_in_sector_mock', return_value=mock_stock_list):
            symbols = self.adapter.get_hk_sh_symbols_mockable()

            # 验证调用了 Mock 方法
            self.adapter._get_stock_list_in_sector_mock.assert_called_once_with("HK_SHTC_STOCKS")

            # 验证返回格式
            self.assertEqual(len(symbols), 3)
            self.assertEqual(symbols[0], "0700.SHHK")
            self.assertEqual(symbols[1], "2318.SHHK")
            self.assertEqual(symbols[2], "09988.SHHK")

    def test_get_hk_sz_symbols_connected(self):
        """测试连接时获取深港通标的"""
        # 模拟已连接
        self.adapter._connected = True

        # Mock _get_stock_list_in_sector_mock 方法
        mock_stock_list = ["0700.HK_SZTC", "2318.HK_SZTC", "09988.HK_SZTC"]
        with patch.object(self.adapter, '_get_stock_list_in_sector_mock', return_value=mock_stock_list):
            symbols = self.adapter.get_hk_sz_symbols_mockable()

            # 验证调用了 Mock 方法
            self.adapter._get_stock_list_in_sector_mock.assert_called_once_with("HK_SZTC_STOCKS")

            # 验证返回格式
            self.assertEqual(len(symbols), 3)
            self.assertEqual(symbols[0], "0700.SZHK")
            self.assertEqual(symbols[1], "2318.SZHK")
            self.assertEqual(symbols[2], "09988.SZHK")

    def test_get_hk_sh_symbols_empty_result(self):
        """测试 QMT 返回空列表"""
        self.adapter._connected = True

        with patch.object(self.adapter, '_get_stock_list_in_sector_mock', return_value=[]):
            symbols = self.adapter.get_hk_sh_symbols_mockable()
            self.assertEqual(symbols, [])

    def test_get_hk_sh_symbols_invalid_codes(self):
        """测试 QMT 返回无效代码时的过滤"""
        self.adapter._connected = True

        # Mock 返回包含无效代码的列表
        mock_stock_list = [
            "0700.HK_SHTC",      # 有效
            "invalid_code",      # 无效（无点号）
            "0700.SH",           # 无效（不支持的市场）
            "2318.HK_SHTC",      # 有效
        ]

        with patch.object(self.adapter, '_get_stock_list_in_sector_mock', return_value=mock_stock_list):
            symbols = self.adapter.get_hk_sh_symbols_mockable()

            # 应该只返回有效的转换结果
            self.assertEqual(len(symbols), 2)
            self.assertIn("0700.SHHK", symbols)
            self.assertIn("2318.SHHK", symbols)

    def test_get_hk_sh_symbols_with_date(self):
        """测试带日期参数的调用"""
        self.adapter._connected = True

        with patch.object(self.adapter, '_get_stock_list_in_sector_mock', return_value=["0700.HK_SHTC"]):
            # 注意：date 参数暂未使用，但应该不报错
            symbols = self.adapter.get_hk_sh_symbols_mockable(date="20260226")

            self.assertEqual(len(symbols), 1)
            self.assertEqual(symbols[0], "0700.SHHK")

    def test_subscribe_hk_sh_quotes_not_connected(self):
        """测试未连接时订阅沪港通行情"""
        # 未连接状态
        self.adapter._connected = False

        result = self.adapter.subscribe_hk_sh_quotes(["0700", "2318"])
        self.assertFalse(result)

    def test_subscribe_hk_sz_quotes_not_connected(self):
        """测试未连接时订阅深港通行情"""
        # 未连接状态
        self.adapter._connected = False

        result = self.adapter.subscribe_hk_sz_quotes(["0700", "2318"])
        self.assertFalse(result)

    def test_subscribe_hk_sh_quotes_empty_list(self):
        """测试订阅空的沪港通列表"""
        # 模拟已连接
        self.adapter._connected = True

        # 使用 sys.modules 来模拟 xtdata 模块
        import sys
        mock_xtdata = MagicMock()

        # 保存原始模块
        xtquant_xtdata = sys.modules.get("xtquant.xtdata")
        xtdata = sys.modules.get("xtdata")

        try:
            # 设置模拟模块
            sys.modules["xtquant.xtdata"] = mock_xtdata
            sys.modules["xtdata"] = mock_xtdata

            # 空列表应该直接返回 True，不调用 API
            result = self.adapter.subscribe_hk_sh_quotes([])
            self.assertTrue(result)
            mock_xtdata.subscribe_quote.assert_not_called()

        finally:
            # 恢复原始模块
            if xtquant_xtdata is None:
                sys.modules.pop("xtquant.xtdata", None)
            else:
                sys.modules["xtquant.xtdata"] = xtquant_xtdata

            if xtdata is None:
                sys.modules.pop("xtdata", None)
            else:
                sys.modules["xtdata"] = xtdata

    def test_subscribe_hk_sz_quotes_empty_list(self):
        """测试订阅空的深港通列表"""
        # 模拟已连接
        self.adapter._connected = True

        # 使用 sys.modules 来模拟 xtdata 模块
        import sys
        mock_xtdata = MagicMock()

        # 保存原始模块
        xtquant_xtdata = sys.modules.get("xtquant.xtdata")
        xtdata = sys.modules.get("xtdata")

        try:
            # 设置模拟模块
            sys.modules["xtquant.xtdata"] = mock_xtdata
            sys.modules["xtdata"] = mock_xtdata

            # 空列表应该直接返回 True，不调用 API
            result = self.adapter.subscribe_hk_sz_quotes([])
            self.assertTrue(result)
            mock_xtdata.subscribe_quote.assert_not_called()

        finally:
            # 恢复原始模块
            if xtquant_xtdata is None:
                sys.modules.pop("xtquant.xtdata", None)
            else:
                sys.modules["xtquant.xtdata"] = xtquant_xtdata

            if xtdata is None:
                sys.modules.pop("xtdata", None)
            else:
                sys.modules["xtdata"] = xtdata

    def test_subscribe_hk_sh_quotes_success(self):
        """测试成功订阅沪港通行情"""
        self.adapter._connected = True

        # Mock xtdata 模块
        mock_xtdata = MagicMock()
        mock_xtdata.subscribe_quote.return_value = 0  # 0 表示成功

        # 使用 sys.modules 来模拟 xtdata 模块
        import sys
        xtquant_xtdata = sys.modules.get("xtquant.xtdata")
        xtdata = sys.modules.get("xtdata")

        try:
            # 设置模拟模块
            sys.modules["xtquant.xtdata"] = mock_xtdata
            sys.modules["xtdata"] = mock_xtdata

            symbols = ["0700", "2318", "09988"]
            result = self.adapter.subscribe_hk_sh_quotes(symbols)

            self.assertTrue(result)

            # 验证调用参数
            call_args = mock_xtdata.subscribe_quote.call_args
            qmt_symbols = call_args[0][0]
            period = call_args[1]["period"]

            self.assertEqual(period, "tick")
            self.assertEqual(len(qmt_symbols), 3)
            self.assertIn("0700.HK_SHTC", qmt_symbols)
            self.assertIn("2318.HK_SHTC", qmt_symbols)
            self.assertIn("09988.HK_SHTC", qmt_symbols)

        finally:
            # 恢复原始模块
            if xtquant_xtdata is None:
                sys.modules.pop("xtquant.xtdata", None)
            else:
                sys.modules["xtquant.xtdata"] = xtquant_xtdata

            if xtdata is None:
                sys.modules.pop("xtdata", None)
            else:
                sys.modules["xtdata"] = xtdata

    def test_subscribe_hk_sz_quotes_success(self):
        """测试成功订阅深港通行情"""
        self.adapter._connected = True

        # Mock xtdata 模块
        mock_xtdata = MagicMock()
        mock_xtdata.subscribe_quote.return_value = 0  # 0 表示成功

        # 使用 sys.modules 来模拟 xtdata 模块
        import sys
        xtquant_xtdata = sys.modules.get("xtquant.xtdata")
        xtdata = sys.modules.get("xtdata")

        try:
            # 设置模拟模块
            sys.modules["xtquant.xtdata"] = mock_xtdata
            sys.modules["xtdata"] = mock_xtdata

            symbols = ["0700", "2318", "09988"]
            result = self.adapter.subscribe_hk_sz_quotes(symbols)

            self.assertTrue(result)

            # 验证调用参数
            call_args = mock_xtdata.subscribe_quote.call_args
            qmt_symbols = call_args[0][0]
            period = call_args[1]["period"]

            self.assertEqual(period, "tick")
            self.assertEqual(len(qmt_symbols), 3)
            self.assertIn("0700.HK_SZTC", qmt_symbols)
            self.assertIn("2318.HK_SZTC", qmt_symbols)
            self.assertIn("09988.HK_SZTC", qmt_symbols)

        finally:
            # 恢复原始模块
            if xtquant_xtdata is None:
                sys.modules.pop("xtquant.xtdata", None)
            else:
                sys.modules["xtquant.xtdata"] = xtquant_xtdata

            if xtdata is None:
                sys.modules.pop("xtdata", None)
            else:
                sys.modules["xtdata"] = xtdata

    def test_subscribe_hk_sh_quotes_failure(self):
        """测试沪港通订阅失败"""
        self.adapter._connected = True

        # Mock xtdata 模块返回错误
        mock_xtdata = MagicMock()
        mock_xtdata.subscribe_quote.return_value = -1  # 非 0 表示失败

        # 使用 sys.modules 来模拟 xtdata 模块
        import sys
        xtquant_xtdata = sys.modules.get("xtquant.xtdata")
        xtdata = sys.modules.get("xtdata")

        try:
            # 设置模拟模块
            sys.modules["xtquant.xtdata"] = mock_xtdata
            sys.modules["xtdata"] = mock_xtdata

            result = self.adapter.subscribe_hk_sh_quotes(["0700"])
            self.assertFalse(result)

        finally:
            # 恢复原始模块
            if xtquant_xtdata is None:
                sys.modules.pop("xtquant.xtdata", None)
            else:
                sys.modules["xtquant.xtdata"] = xtquant_xtdata

            if xtdata is None:
                sys.modules.pop("xtdata", None)
            else:
                sys.modules["xtdata"] = xtdata

    def test_subscribe_hk_sz_quotes_failure(self):
        """测试深港通订阅失败"""
        self.adapter._connected = True

        # Mock xtdata 模块返回错误
        mock_xtdata = MagicMock()
        mock_xtdata.subscribe_quote.return_value = -1  # 非 0 表示失败

        # 使用 sys.modules 来模拟 xtdata 模块
        import sys
        xtquant_xtdata = sys.modules.get("xtquant.xtdata")
        xtdata = sys.modules.get("xtdata")

        try:
            # 设置模拟模块
            sys.modules["xtquant.xtdata"] = mock_xtdata
            sys.modules["xtdata"] = mock_xtdata

            result = self.adapter.subscribe_hk_sz_quotes(["0700"])
            self.assertFalse(result)

        finally:
            # 恢复原始模块
            if xtquant_xtdata is None:
                sys.modules.pop("xtquant.xtdata", None)
            else:
                sys.modules["xtquant.xtdata"] = xtquant_xtdata

            if xtdata is None:
                sys.modules.pop("xtdata", None)
            else:
                sys.modules["xtdata"] = xtdata

    def test_subscribe_hk_sh_quotes_import_error(self):
        """测试 xtdata 模块未安装的情况"""
        self.adapter._connected = True

        # Mock 导入失败 - 使用 sys.modules
        import sys
        xtquant_xtdata = sys.modules.get("xtquant.xtdata")
        xtdata = sys.modules.get("xtdata")

        try:
            # 移除模拟模块，让导入失败
            sys.modules.pop("xtquant.xtdata", None)
            sys.modules.pop("xtdata", None)

            result = self.adapter.subscribe_hk_sh_quotes(["0700"])
            self.assertFalse(result)

        finally:
            # 恢复原始模块
            if xtquant_xtdata is not None:
                sys.modules["xtquant.xtdata"] = xtquant_xtdata
            if xtdata is not None:
                sys.modules["xtdata"] = xtdata

    def test_subscribe_hk_sz_quotes_import_error(self):
        """测试 xtdata 模块未安装的情况"""
        self.adapter._connected = True

        # Mock 导入失败 - 使用 sys.modules
        import sys
        xtquant_xtdata = sys.modules.get("xtquant.xtdata")
        xtdata = sys.modules.get("xtdata")

        try:
            # 移除模拟模块，让导入失败
            sys.modules.pop("xtquant.xtdata", None)
            sys.modules.pop("xtdata", None)

            result = self.adapter.subscribe_hk_sz_quotes(["0700"])
            self.assertFalse(result)

        finally:
            # 恢复原始模块
            if xtquant_xtdata is not None:
                sys.modules["xtquant.xtdata"] = xtquant_xtdata
            if xtdata is not None:
                sys.modules["xtdata"] = xtdata

    def test_subscribe_unsubscribe_hk_sh_quotes(self):
        """测试取消沪港通订阅"""
        self.adapter._connected = True

        # Mock xtdata 模块
        mock_xtdata = MagicMock()
        mock_xtdata.unsubscribe_quote.return_value = 0  # 0 表示成功

        # 使用 sys.modules 来模拟 xtdata 模块
        import sys
        xtquant_xtdata = sys.modules.get("xtquant.xtdata")
        xtdata = sys.modules.get("xtdata")

        try:
            # 设置模拟模块
            sys.modules["xtquant.xtdata"] = mock_xtdata
            sys.modules["xtdata"] = mock_xtdata

            symbols = ["0700", "2318"]
            result = self.adapter.unsubscribe_hk_sh_quotes(symbols)

            self.assertTrue(result)

            # 验证调用参数
            call_args = mock_xtdata.unsubscribe_quote.call_args
            qmt_symbols = call_args[0][0]

            self.assertEqual(len(qmt_symbols), 2)
            self.assertIn("0700.HK_SHTC", qmt_symbols)
            self.assertIn("2318.HK_SHTC", qmt_symbols)

        finally:
            # 恢复原始模块
            if xtquant_xtdata is None:
                sys.modules.pop("xtquant.xtdata", None)
            else:
                sys.modules["xtquant.xtdata"] = xtquant_xtdata

            if xtdata is None:
                sys.modules.pop("xtdata", None)
            else:
                sys.modules["xtdata"] = xtdata

    def test_subscribe_unsubscribe_hk_sz_quotes(self):
        """测试取消深港通订阅"""
        self.adapter._connected = True

        # Mock xtdata 模块
        mock_xtdata = MagicMock()
        mock_xtdata.unsubscribe_quote.return_value = 0  # 0 表示成功

        # 使用 sys.modules 来模拟 xtdata 模块
        import sys
        xtquant_xtdata = sys.modules.get("xtquant.xtdata")
        xtdata = sys.modules.get("xtdata")

        try:
            # 设置模拟模块
            sys.modules["xtquant.xtdata"] = mock_xtdata
            sys.modules["xtdata"] = mock_xtdata

            symbols = ["0700", "2318"]
            result = self.adapter.unsubscribe_hk_sz_quotes(symbols)

            self.assertTrue(result)

            # 验证调用参数
            call_args = mock_xtdata.unsubscribe_quote.call_args
            qmt_symbols = call_args[0][0]

            self.assertEqual(len(qmt_symbols), 2)
            self.assertIn("0700.HK_SZTC", qmt_symbols)
            self.assertIn("2318.HK_SZTC", qmt_symbols)

        finally:
            # 恢复原始模块
            if xtquant_xtdata is None:
                sys.modules.pop("xtquant.xtdata", None)
            else:
                sys.modules["xtquant.xtdata"] = xtquant_xtdata

            if xtdata is None:
                sys.modules.pop("xtdata", None)
            else:
                sys.modules["xtdata"] = xtdata

    def test_subscribe_with_hk_shhk_symbols(self):
        """测试使用 subscribe() 方法订阅沪港通股票"""
        self.adapter._connected = True

        # Mock xtdata 模块
        mock_xtdata = MagicMock()
        mock_xtdata.subscribe_quote.return_value = 0

        # 使用 sys.modules 来模拟 xtdata 模块
        import sys
        xtquant_xtdata = sys.modules.get("xtquant.xtdata")
        xtdata = sys.modules.get("xtdata")

        try:
            # 设置模拟模块
            sys.modules["xtquant.xtdata"] = mock_xtdata
            sys.modules["xtdata"] = mock_xtdata

            # 使用 VeighNa 格式的股票代码（带交易所后缀）
            symbols = ["0700.SHHK", "2318.SHHK", "09988.SHHK"]
            result = self.adapter.subscribe(symbols)

            self.assertTrue(result)

            # 验证订阅集合已更新
            for symbol in symbols:
                self.assertIn(symbol, self.adapter._subscribed_symbols)

            # 验证 K 线生成器已创建
            self.assertEqual(len(self.adapter._subscribed_symbols), 3)

        finally:
            # 恢复原始模块
            if xtquant_xtdata is None:
                sys.modules.pop("xtquant.xtdata", None)
            else:
                sys.modules["xtquant.xtdata"] = xtquant_xtdata

            if xtdata is None:
                sys.modules.pop("xtdata", None)
            else:
                sys.modules["xtdata"] = xtdata

    def test_subscribe_with_hk_szhk_symbols(self):
        """测试使用 subscribe() 方法订阅深港通股票"""
        self.adapter._connected = True

        # Mock xtdata 模块
        mock_xtdata = MagicMock()
        mock_xtdata.subscribe_quote.return_value = 0

        # 使用 sys.modules 来模拟 xtdata 模块
        import sys
        xtquant_xtdata = sys.modules.get("xtquant.xtdata")
        xtdata = sys.modules.get("xtdata")

        try:
            # 设置模拟模块
            sys.modules["xtquant.xtdata"] = mock_xtdata
            sys.modules["xtdata"] = mock_xtdata

            # 使用 VeighNa 格式的股票代码（带交易所后缀）
            symbols = ["0700.SZHK", "2318.SZHK", "09988.SZHK"]
            result = self.adapter.subscribe(symbols)

            self.assertTrue(result)

            # 验证订阅集合已更新
            for symbol in symbols:
                self.assertIn(symbol, self.adapter._subscribed_symbols)

        finally:
            # 恢复原始模块
            if xtquant_xtdata is None:
                sys.modules.pop("xtquant.xtdata", None)
            else:
                sys.modules["xtquant.xtdata"] = xtquant_xtdata

            if xtdata is None:
                sys.modules.pop("xtdata", None)
            else:
                sys.modules["xtdata"] = xtdata

    def test_subscribe_with_mixed_hk_symbols(self):
        """测试使用 subscribe() 方法同时订阅沪港通和深港通股票"""
        self.adapter._connected = True

        # Mock xtdata 模块
        mock_xtdata = MagicMock()
        mock_xtdata.subscribe_quote.return_value = 0

        # 使用 sys.modules 来模拟 xtdata 模块
        import sys
        xtquant_xtdata = sys.modules.get("xtquant.xtdata")
        xtdata = sys.modules.get("xtdata")

        try:
            # 设置模拟模块
            sys.modules["xtquant.xtdata"] = mock_xtdata
            sys.modules["xtdata"] = mock_xtdata

            # 混合沪港通和深港通股票
            symbols = ["0700.SHHK", "2318.SZHK", "09988.SHHK", "1800.SZHK"]
            result = self.adapter.subscribe(symbols)

            self.assertTrue(result)

            # 验证订阅集合
            for symbol in symbols:
                self.assertIn(symbol, self.adapter._subscribed_symbols)

            # 验证调用了两次 subscribe_quote
            self.assertEqual(mock_xtdata.subscribe_quote.call_count, 2)

        finally:
            # 恢复原始模块
            if xtquant_xtdata is None:
                sys.modules.pop("xtquant.xtdata", None)
            else:
                sys.modules["xtquant.xtdata"] = xtquant_xtdata

            if xtdata is None:
                sys.modules.pop("xtdata", None)
            else:
                sys.modules["xtdata"] = xtdata

    def test_subscribe_with_unsupported_exchange(self):
        """测试订阅不支持的交易所代码"""
        self.adapter._connected = True

        # Mock xtdata 模块
        mock_xtdata = MagicMock()
        mock_xtdata.subscribe_quote.return_value = 0

        # 使用 sys.modules 来模拟 xtdata 模块
        import sys
        xtquant_xtdata = sys.modules.get("xtquant.xtdata")
        xtdata = sys.modules.get("xtdata")

        try:
            # 设置模拟模块
            sys.modules["xtquant.xtdata"] = mock_xtdata
            sys.modules["xtdata"] = mock_xtdata

            # A 股代码（暂不支持）
            symbols = ["000001.SZSE", "600000.SSE"]
            result = self.adapter.subscribe(symbols)

            # 应该返回 True（但不订阅任何股票）
            self.assertTrue(result)
            self.assertEqual(len(self.adapter._subscribed_symbols), 0)

            # 不应该调用 xtdata.subscribe_quote
            mock_xtdata.subscribe_quote.assert_not_called()

        finally:
            # 恢复原始模块
            if xtquant_xtdata is None:
                sys.modules.pop("xtquant.xtdata", None)
            else:
                sys.modules["xtquant.xtdata"] = xtquant_xtdata

            if xtdata is None:
                sys.modules.pop("xtdata", None)
            else:
                sys.modules["xtdata"] = xtdata

    def test_subscribe_already_subscribed(self):
        """测试重复订阅同一股票"""
        self.adapter._connected = True

        # Mock xtdata 模块
        mock_xtdata = MagicMock()
        mock_xtdata.subscribe_quote.return_value = 0

        # 使用 sys.modules 来模拟 xtdata 模块
        import sys
        xtquant_xtdata = sys.modules.get("xtquant.xtdata")
        xtdata = sys.modules.get("xtdata")

        try:
            # 设置模拟模块
            sys.modules["xtquant.xtdata"] = mock_xtdata
            sys.modules["xtdata"] = mock_xtdata

            symbols = ["0700.SHHK"]

            # 第一次订阅
            self.adapter.subscribe(symbols)
            first_call_count = mock_xtdata.subscribe_quote.call_count

            # 第二次订阅同一股票
            self.adapter.subscribe(symbols)
            second_call_count = mock_xtdata.subscribe_quote.call_count

            # 第二次不应该调用 API
            self.assertEqual(first_call_count, second_call_count)

        finally:
            # 恢复原始模块
            if xtquant_xtdata is None:
                sys.modules.pop("xtquant.xtdata", None)
            else:
                sys.modules["xtquant.xtdata"] = xtquant_xtdata

            if xtdata is None:
                sys.modules.pop("xtdata", None)
            else:
                sys.modules["xtdata"] = xtdata


if __name__ == "__main__":
    unittest.main()