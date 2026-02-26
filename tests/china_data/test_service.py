"""
ChinaDataService 单元测试

测试数据服务的核心功能：
1. get_stock_list() - 获取股票列表
2. _convert_to_ts_code() - 转换股票代码格式
3. _convert_from_ts_code() - 从 tushare 格式转换
"""

import os
import unittest
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


if __name__ == "__main__":
    unittest.main()