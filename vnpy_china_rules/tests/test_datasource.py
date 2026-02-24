"""
测试数据源管理层
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from vnpy.trader.object import TickData, BarData
from vnpy.trader.constant import Exchange

from vnpy_china_rules.datasource import (
    StockInfo,
    DataSource,
    QMTDataSource,
    TushareDataSource,
    DataSourceManager,
)


@dataclass
class MockSeries:
    """模拟pandas Series"""
    ts_code: str
    symbol: str
    name: str
    market: str
    list_date: str

    def __getitem__(self, key):
        """支持字典式访问"""
        return getattr(self, key)


@dataclass
class MockSeriesDaily:
    """模拟日线数据的pandas Series"""
    ts_code: str
    trade_date: str
    open: float
    high: float
    low: float
    close: float
    vol: int
    amount: float

    def __getitem__(self, key):
        """支持字典式访问"""
        return getattr(self, key)


class MockDataFrame:
    """模拟pandas DataFrame"""
    def __init__(self, data: list, empty: bool = False):
        self.data = data
        self.empty = empty
        self.iloc = self

    def __getitem__(self, key):
        if self.empty or not self.data:
            raise IndexError("No data")
        return self.data[0] if key == 0 else self.data[key]


class TestStockInfo(unittest.TestCase):
    """测试StockInfo数据类"""

    def test_stockinfo_creation(self):
        """测试StockInfo对象创建"""
        info = StockInfo(
            symbol="000001",
            exchange=Exchange.SZSE,
            name="平安银行",
            market_type="主板",
            is_st=False,
            list_date="19910403",
            limit_ratio=0.10
        )

        self.assertEqual(info.symbol, "000001")
        self.assertEqual(info.exchange, Exchange.SZSE)
        self.assertEqual(info.name, "平安银行")
        self.assertEqual(info.market_type, "主板")
        self.assertFalse(info.is_st)
        self.assertEqual(info.list_date, "19910403")
        self.assertEqual(info.limit_ratio, 0.10)


class TestQMTDataSource(unittest.TestCase):
    """测试QMT数据源"""

    def setUp(self):
        """测试前准备"""
        self.mock_gateway = Mock()
        self.mock_gateway.gateway_name = "TEST_QMT"
        self.datasource = QMTDataSource(self.mock_gateway)

    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.datasource.gateway, self.mock_gateway)

    def test_get_stock_info_success(self):
        """测试成功获取股票信息"""
        # 模拟网关返回合约数据
        mock_contract = Mock()
        mock_contract.symbol = "000001"
        mock_contract.exchange = Exchange.SZSE
        mock_contract.name = "平安银行"

        # 模拟网关get_contract方法
        self.mock_gateway.get_contract.return_value = mock_contract

        # 调用方法
        result = self.datasource.get_stock_info("000001")

        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result.symbol, "000001")
        self.assertEqual(result.exchange, Exchange.SZSE)
        self.assertEqual(result.name, "平安银行")
        self.assertEqual(result.market_type, "主板")  # SZSE默认主板
        self.assertFalse(result.is_st)
        self.assertEqual(result.limit_ratio, 0.10)  # 主板10%

    def test_get_stock_info_failure(self):
        """测试获取股票信息失败"""
        # 模拟网关返回None
        self.mock_gateway.get_contract.return_value = None

        # 调用方法
        result = self.datasource.get_stock_info("000001")

        # 验证结果
        self.assertIsNone(result)

    def test_get_stock_info_st_stock(self):
        """测试ST股票识别"""
        # 模拟ST股票合约
        mock_contract = Mock()
        mock_contract.symbol = "000001"
        mock_contract.exchange = Exchange.SZSE
        mock_contract.name = "ST平安"  # 名称包含ST

        self.mock_gateway.get_contract.return_value = mock_contract

        # 调用方法
        result = self.datasource.get_stock_info("000001")

        # 验证ST标识和涨跌停比例
        self.assertTrue(result.is_st)
        self.assertEqual(result.limit_ratio, 0.05)  # ST股票5%

    def test_get_market_data_success(self):
        """测试成功获取实时行情"""
        # 创建模拟Tick数据
        mock_tick = TickData(
            gateway_name="TEST_QMT",
            symbol="000001",
            exchange=Exchange.SZSE,
            datetime=datetime.now(),
            last_price=10.50,
            volume=100000,
            pre_close=10.00,
            limit_up=11.00,
            limit_down=9.00
        )

        # 模拟网关返回tick数据
        self.mock_gateway.get_tick.return_value = mock_tick

        # 调用方法
        result = self.datasource.get_market_data("000001")

        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result.symbol, "000001")
        self.assertEqual(result.last_price, 10.50)
        self.assertEqual(result.pre_close, 10.00)

    def test_get_market_data_failure(self):
        """测试获取实时行情失败"""
        # 模拟网关返回None
        self.mock_gateway.get_tick.return_value = None

        # 调用方法
        result = self.datasource.get_market_data("000001")

        # 验证结果
        self.assertIsNone(result)


class TestTushareDataSource(unittest.TestCase):
    """测试Tushare数据源"""

    def setUp(self):
        """测试前准备"""
        self.test_token = "test_token_123"
        self.datasource = TushareDataSource(self.test_token)

    @patch('vnpy_china_rules.datasource.ts')
    def test_init(self, mock_ts):
        """测试初始化"""
        # 重新创建datasource以触发patch
        datasource = TushareDataSource(self.test_token)

        # 验证pro_api被正确调用
        mock_ts.pro_api.assert_called_once_with(self.test_token)

    @patch('vnpy_china_rules.datasource.ts')
    def test_get_stock_info_success(self, mock_ts):
        """测试成功获取股票信息"""
        # 创建模拟数据
        mock_series = MockSeries(
            ts_code='000001.SZ',
            symbol='000001',
            name='平安银行',
            market='主板',
            list_date='19910403'
        )

        mock_df = MockDataFrame([mock_series], empty=False)

        mock_pro = Mock()
        mock_pro.stock_basic.return_value = mock_df
        mock_ts.pro_api.return_value = mock_pro

        # 创建datasource
        datasource = TushareDataSource(self.test_token)
        datasource.pro = mock_pro  # 直接设置pro属性

        # 调用方法
        result = datasource.get_stock_info("000001")

        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result.symbol, "000001")
        self.assertEqual(result.name, "平安银行")
        mock_pro.stock_basic.assert_called()

    @patch('vnpy_china_rules.datasource.ts')
    def test_get_stock_info_failure(self, mock_ts):
        """测试获取股票信息失败"""
        # 模拟空数据响应
        mock_pro = Mock()
        mock_df = Mock()
        mock_df.empty = True
        mock_pro.query.return_value = mock_df
        mock_ts.pro_api.return_value = mock_pro

        # 创建datasource
        datasource = TushareDataSource(self.test_token)
        datasource.pro = mock_pro

        # 调用方法
        result = datasource.get_stock_info("000001")

        # 验证返回None
        self.assertIsNone(result)

    @patch('vnpy_china_rules.datasource.ts')
    def test_get_market_data_success(self, mock_ts):
        """测试成功获取历史行情"""
        # 创建模拟数据
        mock_series = MockSeriesDaily(
            ts_code='000001.SZ',
            trade_date='20240201',
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            vol=100000,
            amount=1020000.0
        )

        mock_df = MockDataFrame([mock_series], empty=False)

        mock_pro = Mock()
        mock_pro.daily.return_value = mock_df
        mock_ts.pro_api.return_value = mock_pro

        # 创建datasource
        datasource = TushareDataSource(self.test_token)
        datasource.pro = mock_pro

        # 调用方法
        result = datasource.get_market_data("000001")

        # 验证结果（返回BarData）
        self.assertIsInstance(result, BarData)
        self.assertEqual(result.symbol, "000001")
        self.assertEqual(result.close_price, 10.2)
        mock_pro.daily.assert_called()

    @patch('vnpy_china_rules.datasource.ts')
    def test_get_market_data_failure(self, mock_ts):
        """测试获取历史行情失败"""
        # 模拟空数据响应
        mock_pro = Mock()
        mock_df = Mock()
        mock_df.empty = True
        mock_pro.daily.return_value = mock_df
        mock_ts.pro_api.return_value = mock_pro

        # 创建datasource
        datasource = TushareDataSource(self.test_token)
        datasource.pro = mock_pro

        # 调用方法
        result = datasource.get_market_data("000001")

        # 验证返回None
        self.assertIsNone(result)


class TestDataSourceManager(unittest.TestCase):
    """测试数据源管理器"""

    def setUp(self):
        """测试前准备"""
        self.manager = DataSourceManager()

        # 创建模拟数据源
        self.mock_qmt_source = Mock(spec=DataSource)
        self.mock_tushare_source = Mock(spec=DataSource)

        # 模拟股票信息
        self.stock_info_qmt = StockInfo(
            symbol="000001",
            exchange=Exchange.SZSE,
            name="平安银行",
            market_type="主板",
            is_st=False,
            list_date="19910403",
            limit_ratio=0.10
        )

        self.stock_info_tushare = StockInfo(
            symbol="000001",
            exchange=Exchange.SZSE,
            name="平安银行",
            market_type="主板",
            is_st=False,
            list_date="19910403",
            limit_ratio=0.10
        )

        # 模拟行情数据
        self.tick_data = TickData(
            gateway_name="TEST",
            symbol="000001",
            exchange=Exchange.SZSE,
            datetime=datetime.now(),
            last_price=10.50
        )

    def test_register_source(self):
        """测试注册数据源"""
        # 注册普通数据源
        self.manager.register_source("tushare", self.mock_tushare_source)
        self.assertIn("tushare", self.manager.sources)

        # 注册主数据源
        self.manager.register_source("qmt", self.mock_qmt_source, primary=True)
        self.assertEqual(self.manager.primary_source, "qmt")

    def test_get_stock_info_from_primary(self):
        """测试从主数据源获取股票信息"""
        # 注册数据源
        self.mock_qmt_source.get_stock_info.return_value = self.stock_info_qmt
        self.manager.register_source("qmt", self.mock_qmt_source, primary=True)
        self.manager.register_source("tushare", self.mock_tushare_source)

        # 调用方法
        result = self.manager.get_stock_info("000001")

        # 验证只调用了主数据源
        self.mock_qmt_source.get_stock_info.assert_called_once_with("000001")
        self.mock_tushare_source.get_stock_info.assert_not_called()
        self.assertEqual(result, self.stock_info_qmt)

    def test_get_stock_info_fallback(self):
        """测试数据源降级机制"""
        # 注册数据源，主数据源返回None
        self.mock_qmt_source.get_stock_info.return_value = None
        self.mock_tushare_source.get_stock_info.return_value = self.stock_info_tushare
        self.manager.register_source("qmt", self.mock_qmt_source, primary=True)
        self.manager.register_source("tushare", self.mock_tushare_source)

        # 调用方法
        result = self.manager.get_stock_info("000001")

        # 验证降级调用
        self.mock_qmt_source.get_stock_info.assert_called_once_with("000001")
        self.mock_tushare_source.get_stock_info.assert_called_once_with("000001")
        self.assertEqual(result, self.stock_info_tushare)

    def test_get_stock_info_all_failed(self):
        """测试所有数据源都失败"""
        # 所有数据源返回None
        self.mock_qmt_source.get_stock_info.return_value = None
        self.mock_tushare_source.get_stock_info.return_value = None
        self.manager.register_source("qmt", self.mock_qmt_source, primary=True)
        self.manager.register_source("tushare", self.mock_tushare_source)

        # 调用方法
        result = self.manager.get_stock_info("000001")

        # 验证返回None
        self.assertIsNone(result)

    def test_get_market_data_from_primary(self):
        """测试从主数据源获取行情"""
        # 注册数据源
        self.mock_qmt_source.get_market_data.return_value = self.tick_data
        self.manager.register_source("qmt", self.mock_qmt_source, primary=True)
        self.manager.register_source("tushare", self.mock_tushare_source)

        # 调用方法
        result = self.manager.get_market_data("000001")

        # 验证只调用了主数据源
        self.mock_qmt_source.get_market_data.assert_called_once_with("000001")
        self.mock_tushare_source.get_market_data.assert_not_called()
        self.assertEqual(result, self.tick_data)

    def test_get_market_data_fallback(self):
        """测试行情数据源降级机制"""
        # 注册数据源，主数据源返回None
        self.mock_qmt_source.get_market_data.return_value = None
        self.mock_tushare_source.get_market_data.return_value = self.tick_data
        self.manager.register_source("qmt", self.mock_qmt_source, primary=True)
        self.manager.register_source("tushare", self.mock_tushare_source)

        # 调用方法
        result = self.manager.get_market_data("000001")

        # 验证降级调用
        self.mock_qmt_source.get_market_data.assert_called_once_with("000001")
        self.mock_tushare_source.get_market_data.assert_called_once_with("000001")
        self.assertEqual(result, self.tick_data)

    def test_no_primary_source(self):
        """测试没有设置主数据源时使用第一个注册的数据源"""
        # 只注册普通数据源
        self.mock_tushare_source.get_stock_info.return_value = self.stock_info_tushare
        self.manager.register_source("tushare", self.mock_tushare_source)

        # 调用方法
        result = self.manager.get_stock_info("000001")

        # 验证使用第一个注册的数据源
        self.mock_tushare_source.get_stock_info.assert_called_once_with("000001")
        self.assertEqual(result, self.stock_info_tushare)

    def test_empty_manager(self):
        """测试空管理器返回None"""
        # 没有注册任何数据源
        result = self.manager.get_stock_info("000001")
        self.assertIsNone(result)

        result = self.manager.get_market_data("000001")
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
