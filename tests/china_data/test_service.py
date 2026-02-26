"""
ChinaDataService 单元测试

测试数据服务的核心功能：
1. get_stock_list() - 获取股票列表
2. _convert_to_ts_code() - 转换股票代码格式
3. _convert_from_ts_code() - 从 tushare 格式转换
4. get_hk_sh_symbols() - 获取沪港通标的列表
5. get_hk_sz_symbols() - 获取深港通标的列表
6. get_hk_all_symbols() - 合并获取所有港股通标的
"""

import os
import unittest
import unittest.mock
from datetime import datetime, date
from unittest.mock import MagicMock, Mock

os.environ["VNPY_ENV"] = "testing"

from vnpy.trader.constant import Exchange
from vnpy_china_data.service import ChinaDataService


class MockCache:
    """Mock 缓存类"""
    def __init__(self):
        self._data = {}

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value, ttl=3600):
        self._data[key] = value

    def delete(self, key):
        self._data.pop(key, None)

    def clear(self):
        self._data.clear()


class MockTushareAdapter:
    """Mock Tushare 适配器"""
    def __init__(self, token=None):
        self.token = token

    def get_stock_list(self, list_status="L"):
        return [
            {"ts_code": "000001.SZ", "symbol": "000001", "name": "平安银行"},
            {"ts_code": "600000.SH", "symbol": "600000", "name": "浦发银行"},
        ]

    def get_hk_sh_symbols(self, date=None):
        """Mock 沪港通标的列表"""
        return ["00700.SHHK", "09988.SHHK", "2318.SHHK"]

    def get_hk_sz_symbols(self, date=None):
        """Mock 深港通标的列表"""
        return ["0700.SZHK", "09988.SZHK", "2318.SZHK"]

    def get_trade_calendar(self, exchange="SSE", start_date=None, end_date=None):
        """Mock 获取交易日历"""
        # 返回一些测试交易日
        if start_date and end_date:
            # 简单返回一些日期
            return ["20260219", "20260220", "20260221", "20260224", "20260225"]
        return ["20260219", "20260220", "20260221"]

    def get_hk_trade_calendar(self, start_date=None, end_date=None):
        """Mock 获取香港交易日历"""
        # 返回一些测试交易日（与内地有部分重叠）
        if start_date and end_date:
            # 注意：香港和内地的假期不同，这里模拟一些重叠的交易日
            return ["20260219", "20260220", "20260221", "20260224", "20260225"]
        return ["20260219", "20260220", "20260221"]


class MockQmtAdapter:
    """Mock QMT 适配器"""
    def __init__(self):
        self._connected = True

    @property
    def connected(self):
        return self._connected

    def get_hk_sh_symbols(self, date=None):
        """Mock 沪港通标的列表"""
        return ["00700.SHHK", "09988.SHHK", "0960.SHHK", "2318.SHHK", "2628.SHHK"]

    def get_hk_sz_symbols(self, date=None):
        """Mock 深港通标的列表"""
        return ["0700.SZHK", "09988.SZHK", "1810.SZHK", "2318.SZHK", "2628.SZHK"]


class TestChinaDataService(unittest.TestCase):
    """测试 ChinaDataService 类"""

    def setUp(self):
        """测试前准备"""
        # 使用 mock 避免真实数据库和 API 调用
        mock_cache = MockCache()
        mock_tushare = MockTushareAdapter()

        with unittest.mock.patch("vnpy_china_data.service.DataQueryCache", return_value=mock_cache):
            self.service = ChinaDataService()
            # 替换 Tushare 适配器为 mock
            self.service.tushare_adapter = mock_tushare
            # 替换缓存为 mock
            self.service.cache = mock_cache
            # 替换 QMT 适配器为 mock
            self.service.qmt_adapter = MockQmtAdapter()

    def test_convert_to_ts_code_basic(self):
        """测试基础股票代码转换"""
        # 不含后缀的代码
        self.assertEqual(self.service._convert_to_ts_code("000001", Exchange.SZSE), "000001.SZ")
        self.assertEqual(self.service._convert_to_ts_code("600000", Exchange.SSE), "600000.SH")
        self.assertEqual(self.service._convert_to_ts_code("430001", Exchange.BSE), "430001.BJ")

    def test_convert_to_ts_code_with_suffix(self):
        """测试已包含后缀的代码转换（修复双重后缀问题）"""
        # 已包含 .SZ 后缀的代码，应该去除后再添加正确的后缀
        self.assertEqual(self.service._convert_to_ts_code("000001.SZ", Exchange.SZSE), "000001.SZ")
        self.assertEqual(self.service._convert_to_ts_code("600000.SH", Exchange.SSE), "600000.SH")
        self.assertEqual(self.service._convert_to_ts_code("430001.BJ", Exchange.BSE), "430001.BJ")

    def test_convert_to_ts_code_double_suffix_prevention(self):
        """测试防止双重后缀"""
        # 这测试了修复双重后缀问题的逻辑
        symbol = "000333.SZ"
        result = self.service._convert_to_ts_code(symbol, Exchange.SZSE)
        # 应该返回 "000333.SZ"，而不是 "000333.SZ.SZ"
        self.assertEqual(result, "000333.SZ")
        self.assertNotEqual(result, "000333.SZ.SZ")

    def test_convert_from_ts_code_basic(self):
        """测试从 tushare 格式转换"""
        symbol, exchange = self.service._convert_from_ts_code("000001.SZ")
        self.assertEqual(symbol, "000001")
        self.assertEqual(exchange, Exchange.SZSE)

        symbol, exchange = self.service._convert_from_ts_code("600000.SH")
        self.assertEqual(symbol, "600000")
        self.assertEqual(exchange, Exchange.SSE)

    def test_convert_from_ts_code_without_suffix(self):
        """测试不带后缀的代码转换"""
        symbol, exchange = self.service._convert_from_ts_code("000001")
        self.assertEqual(symbol, "000001")
        self.assertEqual(exchange, Exchange.SZSE)  # 默认深圳

    def test_get_stock_list_with_cache(self):
        """测试从缓存获取股票列表"""
        # 设置缓存
        mock_data = [
            {"ts_code": "000001.SZ", "symbol": "000001", "name": "平安银行"},
            {"ts_code": "600000.SH", "symbol": "600000", "name": "浦发银行"},
        ]
        self.service.cache.set("stock_list_L", mock_data)

        # 从缓存获取
        result = self.service.get_stock_list()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["ts_code"], "000001.SZ")

    def test_get_stock_list_without_cache(self):
        """测试从 API 获取股票列表"""
        # 清除缓存
        self.service.cache.clear()

        # 从 API 获取
        result = self.service.get_stock_list()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["ts_code"], "000001.SZ")

        # 验证缓存被设置
        cached = self.service.cache.get("stock_list_L")
        self.assertEqual(len(cached), 2)

    def test_get_stock_list_list_status(self):
        """测试按上市状态筛选股票列表"""
        # 从 API 获取
        result = self.service.get_stock_list(list_status="L")
        self.assertEqual(len(result), 2)

    def test_convert_round_trip(self):
        """测试往返转换的一致性"""
        # 上交所
        symbol1 = "600000"
        ts_code1 = self.service._convert_to_ts_code(symbol1, Exchange.SSE)
        symbol_back1, exchange_back1 = self.service._convert_from_ts_code(ts_code1)
        self.assertEqual(symbol1, symbol_back1)
        self.assertEqual(Exchange.SSE, exchange_back1)

        # 深交所
        symbol2 = "000001"
        ts_code2 = self.service._convert_to_ts_code(symbol2, Exchange.SZSE)
        symbol_back2, exchange_back2 = self.service._convert_from_ts_code(ts_code2)
        self.assertEqual(symbol2, symbol_back2)
        self.assertEqual(Exchange.SZSE, exchange_back2)

    def test_all_exchanges_supported(self):
        """测试所有交易所的转换"""
        # 上交所
        self.assertEqual(self.service._convert_to_ts_code("600000", Exchange.SSE), "600000.SH")

        # 深交所
        self.assertEqual(self.service._convert_to_ts_code("000001", Exchange.SZSE), "000001.SZ")

        # 北交所
        self.assertEqual(self.service._convert_to_ts_code("430001", Exchange.BSE), "430001.BJ")

    def test_convert_to_ts_code_stock_connect(self):
        """测试港股通股票代码转换"""
        # 沪港通
        self.assertEqual(self.service._convert_to_ts_code("00700", Exchange.SHHK), "00700.HK")

        # 深港通
        self.assertEqual(self.service._convert_to_ts_code("00941", Exchange.SZHK), "00941.HK")

        # 港交所直接
        self.assertEqual(self.service._convert_to_ts_code("00700", Exchange.SEHK), "00700.HK")

        # 测试已包含后缀的港股通代码
        self.assertEqual(self.service._convert_to_ts_code("00700.HK", Exchange.SHHK), "00700.HK")
        self.assertEqual(self.service._convert_to_ts_code("00700.HK", Exchange.SEHK), "00700.HK")

    def test_convert_from_ts_code_hk(self):
        """测试从tushare格式转换港股代码"""
        symbol, exchange = self.service._convert_from_ts_code("00700.HK")
        self.assertEqual(symbol, "00700")
        self.assertEqual(exchange, Exchange.SEHK)  # 默认映射到SEHK

    def test_convert_hk_round_trip(self):
        """测试港股往返转换的一致性"""
        # 港股通 - 沪港通
        symbol1 = "00700"
        ts_code1 = self.service._convert_to_ts_code(symbol1, Exchange.SHHK)
        symbol_back1, exchange_back1 = self.service._convert_from_ts_code(ts_code1)
        self.assertEqual(symbol1, symbol_back1)
        # 注意：反向转换默认为SEHK，这是设计决定
        self.assertEqual(Exchange.SEHK, exchange_back1)

        # 港股通 - 深港通
        symbol2 = "00941"
        ts_code2 = self.service._convert_to_ts_code(symbol2, Exchange.SZHK)
        symbol_back2, exchange_back2 = self.service._convert_from_ts_code(ts_code2)
        self.assertEqual(symbol2, symbol_back2)
        self.assertEqual(Exchange.SEHK, exchange_back2)

    # ========== 港股通标的列表测试 ==========

    def test_get_hk_sh_symbols_from_qmt(self):
        """测试从 QMT 获取沪港通标的列表"""
        # 清除缓存
        self.service.cache.clear()

        # 从 QMT 获取
        result = self.service.get_hk_sh_symbols()

        # 验证结果
        self.assertTrue(len(result) > 0)
        # 检查格式是否正确（应该以 .SHHK 结尾）
        for symbol in result:
            self.assertTrue(symbol.endswith(".SHHK"), f"股票代码 {symbol} 应该以 .SHHK 结尾")

        # 验证缓存被设置
        date_param = datetime.now().strftime("%Y%m%d")
        cache_key = f"hk_sh_symbols_{date_param}"
        cached = self.service.cache.get(cache_key)
        self.assertEqual(len(cached), len(result))

    def test_get_hk_sh_symbols_from_cache(self):
        """测试从缓存获取沪港通标的列表"""
        # 设置缓存
        date_param = datetime.now().strftime("%Y%m%d")
        cache_key = f"hk_sh_symbols_{date_param}"
        mock_data = ["00700.SHHK", "09988.SHHK", "2318.SHHK"]
        self.service.cache.set(cache_key, mock_data)

        # 从缓存获取
        result = self.service.get_hk_sh_symbols()

        # 验证结果
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "00700.SHHK")

    def test_get_hk_sh_symbols_with_date(self):
        """测试指定日期获取沪港通标的列表"""
        # 清除缓存
        self.service.cache.clear()

        # 指定日期获取
        test_date = date(2026, 2, 20)
        result = self.service.get_hk_sh_symbols(date=test_date)

        # 验证结果
        self.assertTrue(len(result) > 0)

        # 验证缓存被设置（使用正确的日期格式）
        cache_key = f"hk_sh_symbols_20260220"
        cached = self.service.cache.get(cache_key)
        self.assertIsNotNone(cached)

    def test_get_hk_sh_symbols_with_date_str(self):
        """测试使用字符串日期获取沪港通标的列表"""
        # 清除缓存
        self.service.cache.clear()

        # 使用字符串日期
        result = self.service.get_hk_sh_symbols(date="20260220")

        # 验证结果
        self.assertTrue(len(result) > 0)

        # 验证缓存被设置
        cache_key = f"hk_sh_symbols_20260220"
        cached = self.service.cache.get(cache_key)
        self.assertIsNotNone(cached)

    def test_get_hk_sz_symbols_from_qmt(self):
        """测试从 QMT 获取深港通标的列表"""
        # 清除缓存
        self.service.cache.clear()

        # 从 QMT 获取
        result = self.service.get_hk_sz_symbols()

        # 验证结果
        self.assertTrue(len(result) > 0)
        # 检查格式是否正确（应该以 .SZHK 结尾）
        for symbol in result:
            self.assertTrue(symbol.endswith(".SZHK"), f"股票代码 {symbol} 应该以 .SZHK 结尾")

        # 验证缓存被设置
        date_param = datetime.now().strftime("%Y%m%d")
        cache_key = f"hk_sz_symbols_{date_param}"
        cached = self.service.cache.get(cache_key)
        self.assertEqual(len(cached), len(result))

    def test_get_hk_sz_symbols_from_cache(self):
        """测试从缓存获取深港通标的列表"""
        # 设置缓存
        date_param = datetime.now().strftime("%Y%m%d")
        cache_key = f"hk_sz_symbols_{date_param}"
        mock_data = ["0700.SZHK", "09988.SZHK", "2318.SZHK"]
        self.service.cache.set(cache_key, mock_data)

        # 从缓存获取
        result = self.service.get_hk_sz_symbols()

        # 验证结果
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "0700.SZHK")

    def test_get_hk_sz_symbols_with_date(self):
        """测试指定日期获取深港通标的列表"""
        # 清除缓存
        self.service.cache.clear()

        # 指定日期获取
        test_date = date(2026, 2, 20)
        result = self.service.get_hk_sz_symbols(date=test_date)

        # 验证结果
        self.assertTrue(len(result) > 0)

        # 验证缓存被设置
        cache_key = f"hk_sz_symbols_20260220"
        cached = self.service.cache.get(cache_key)
        self.assertIsNotNone(cached)

    def test_get_hk_all_symbols(self):
        """测试获取所有港股通标的"""
        # 清除缓存
        self.service.cache.clear()

        # 获取所有港股通标的
        result = self.service.get_hk_all_symbols()

        # 验证结果
        self.assertTrue(len(result) > 0)

        # 统计沪港通和深港通数量
        sh_count = sum(1 for s in result if s.endswith(".SHHK"))
        sz_count = sum(1 for s in result if s.endswith(".SZHK"))

        self.assertTrue(sh_count > 0, "应该有沪港通标的")
        self.assertTrue(sz_count > 0, "应该有深港通标的")

        # 验证总数（应该去重）
        # 因为有些股票同时在沪港通和深港通
        self.assertLessEqual(len(result), sh_count + sz_count)

    def test_get_hk_all_symbols_dedup(self):
        """测试港股通标的去重功能"""
        # 清除缓存
        self.service.cache.clear()

        # 获取所有港股通标的
        result = self.service.get_hk_all_symbols()

        # 验证去重
        self.assertEqual(len(result), len(set(result)), "港股通标的应该去重")

    def test_get_hk_all_symbols_with_date(self):
        """测试指定日期获取所有港股通标的"""
        # 清除缓存
        self.service.cache.clear()

        # 指定日期获取
        test_date = date(2026, 2, 20)
        result = self.service.get_hk_all_symbols(date=test_date)

        # 验证结果
        self.assertTrue(len(result) > 0)

    def test_get_hk_symbols_format(self):
        """测试港股通标的格式"""
        # 清除缓存
        self.service.cache.clear()

        # 获取沪港通标的
        sh_symbols = self.service.get_hk_sh_symbols()
        for symbol in sh_symbols:
            # 验证格式
            self.assertTrue(symbol.count(".") == 1, f"股票代码 {symbol} 应该只有一个点号")
            code, exchange = symbol.split(".")
            self.assertEqual(exchange, "SHHK")
            # 港股代码通常是4或5位数字
            self.assertTrue(code.isdigit(), f"股票代码 {code} 应该全是数字")

        # 获取深港通标的
        sz_symbols = self.service.get_hk_sz_symbols()
        for symbol in sz_symbols:
            # 验证格式
            self.assertTrue(symbol.count(".") == 1, f"股票代码 {symbol} 应该只有一个点号")
            code, exchange = symbol.split(".")
            self.assertEqual(exchange, "SZHK")
            # 港股代码通常是4或5位数字
            self.assertTrue(code.isdigit(), f"股票代码 {code} 应该全是数字")

    # ========== 港股通交易日历测试 ==========

    def test_is_hk_sh_trading_day_with_string(self):
        """测试使用字符串格式判断沪港通交易日"""
        # 测试 YYYYMMDD 格式
        result = self.service.is_hk_sh_trading_day("20260220")
        self.assertTrue(result, "20260220 应该是沪港通交易日")

    def test_is_hk_sh_trading_day_with_date_object(self):
        """测试使用 date 对象判断沪港通交易日"""
        test_date = date(2026, 2, 20)
        result = self.service.is_hk_sh_trading_day(test_date)
        self.assertTrue(result, "2026-02-20 应该是沪港通交易日")

    def test_is_hk_sh_trading_day_with_datetime_object(self):
        """测试使用 datetime 对象判断沪港通交易日"""
        test_datetime = datetime(2026, 2, 20, 10, 30, 0)
        result = self.service.is_hk_sh_trading_day(test_datetime)
        self.assertTrue(result, "2026-02-20 应该是沪港通交易日")

    def test_is_hk_sh_trading_day_with_hyphen_format(self):
        """测试使用连字符格式判断沪港通交易日"""
        # 测试 YYYY-MM-DD 格式
        result = self.service.is_hk_sh_trading_day("2026-02-20")
        self.assertTrue(result, "2026-02-20 应该是沪港通交易日")

    def test_is_hk_sh_trading_day_cache(self):
        """测试沪港通交易日缓存功能"""
        # 第一次调用
        result1 = self.service.is_hk_sh_trading_day("20260220")
        self.assertTrue(result1)

        # 第二次调用（应该从缓存获取）
        result2 = self.service.is_hk_sh_trading_day("20260220")
        self.assertTrue(result2)
        self.assertEqual(result1, result2)

    def test_is_hk_sz_trading_day_with_string(self):
        """测试使用字符串格式判断深港通交易日"""
        # 测试 YYYYMMDD 格式
        result = self.service.is_hk_sz_trading_day("20260220")
        self.assertTrue(result, "20260220 应该是深港通交易日")

    def test_is_hk_sz_trading_day_with_date_object(self):
        """测试使用 date 对象判断深港通交易日"""
        test_date = date(2026, 2, 20)
        result = self.service.is_hk_sz_trading_day(test_date)
        self.assertTrue(result, "2026-02-20 应该是深港通交易日")

    def test_is_hk_sz_trading_day_with_datetime_object(self):
        """测试使用 datetime 对象判断深港通交易日"""
        test_datetime = datetime(2026, 2, 20, 10, 30, 0)
        result = self.service.is_hk_sz_trading_day(test_datetime)
        self.assertTrue(result, "2026-02-20 应该是深港通交易日")

    def test_is_hk_sz_trading_day_with_hyphen_format(self):
        """测试使用连字符格式判断深港通交易日"""
        # 测试 YYYY-MM-DD 格式
        result = self.service.is_hk_sz_trading_day("2026-02-20")
        self.assertTrue(result, "2026-02-20 应该是深港通交易日")

    def test_is_hk_sz_trading_day_cache(self):
        """测试深港通交易日缓存功能"""
        # 第一次调用
        result1 = self.service.is_hk_sz_trading_day("20260220")
        self.assertTrue(result1)

        # 第二次调用（应该从缓存获取）
        result2 = self.service.is_hk_sz_trading_day("20260220")
        self.assertTrue(result2)
        self.assertEqual(result1, result2)

    def test_hk_trading_calendar_format(self):
        """测试港股通交易日历格式"""
        # 清除缓存
        self.service.cache.clear()

        # 测试几个交易日
        test_dates = ["20260219", "20260220", "20260221"]
        for test_date in test_dates:
            result = self.service.is_hk_sh_trading_day(test_date)
            self.assertTrue(result, f"{test_date} 应该是沪港通交易日")

            result_sz = self.service.is_hk_sz_trading_day(test_date)
            self.assertTrue(result_sz, f"{test_date} 应该是深港通交易日")

    def test_get_hk_sh_trading_calendar_internal(self):
        """测试内部获取沪港通交易日历方法"""
        # 清除缓存
        self.service.cache.clear()

        start_date = "20260101"
        end_date = "20260228"

        calendar = self.service._get_hk_sh_trading_calendar(start_date, end_date)

        # 验证返回的是集合类型
        self.assertIsInstance(calendar, set)

        # 验证有交易日
        self.assertTrue(len(calendar) > 0, "应该有交易日")

        # 验证缓存被设置
        cache_key = f"hk_sh_calendar_{start_date}_{end_date}"
        cached = self.service.cache.get(cache_key)
        self.assertIsNotNone(cached)

    def test_get_hk_sz_trading_calendar_internal(self):
        """测试内部获取深港通交易日历方法"""
        # 清除缓存
        self.service.cache.clear()

        start_date = "20260101"
        end_date = "20260228"

        calendar = self.service._get_hk_sz_trading_calendar(start_date, end_date)

        # 验证返回的是集合类型
        self.assertIsInstance(calendar, set)

        # 验证有交易日
        self.assertTrue(len(calendar) > 0, "应该有交易日")

        # 验证缓存被设置
        cache_key = f"hk_sz_calendar_{start_date}_{end_date}"
        cached = self.service.cache.get(cache_key)
        self.assertIsNotNone(cached)


if __name__ == "__main__":
    unittest.main()