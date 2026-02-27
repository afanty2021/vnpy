"""港股通股票名单爬虫单元测试"""

import sys
import io
from unittest.mock import Mock, patch, MagicMock

import pytest

sys.path.insert(0, '/Users/berton/Github/vnpy')

from vnpy_china_data.crawler.hk_connect_crawler import HkConnectCrawler
from vnpy_china_data.models.hk_connect import HkConnectStock


class TestHkConnectCrawler:
    """港股通爬虫测试"""

    @pytest.fixture
    def crawler(self):
        """创建爬虫实例"""
        return HkConnectCrawler(timeout=30)

    def test_crawler_creation(self, crawler):
        """测试爬虫创建"""
        assert crawler.timeout == 30
        assert crawler.session is None

    @patch('vnpy_china_data.crawler.hk_connect_crawler.HAS_DEPS', False)
    def test_crawl_all_no_deps(self, crawler):
        """测试缺少依赖时返回空列表"""
        result = crawler.crawl_all()
        assert result == []

    @patch('vnpy_china_data.crawler.hk_connect_crawler.openpyxl')
    @patch('vnpy_china_data.crawler.hk_connect_crawler.requests')
    def test_crawl_szse_success(self, mock_requests, mock_openpyxl, crawler):
        """测试成功爬取深交所深港通名单"""
        # Mock响应
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.content = b"fake excel content"
        mock_requests.get.return_value = mock_response

        # Mock Excel数据
        mock_wb = Mock()
        mock_ws = Mock()
        mock_wb.active = mock_ws

        # 模拟数据行：证券代码、中文简称、英文简称
        mock_rows = [
            (None, None, None),  # 表头
            ("1810", "小米集团", "XIAOMI"),  # 数据行
            ("2318", "中国平安", "PING AN"),
        ]
        mock_ws.iter_rows.return_value = iter(mock_rows)

        mock_openpyxl.load_workbook.return_value = mock_wb

        # 调用测试
        stocks = crawler.crawl_szse_hk_connect()

        # 验证
        assert len(stocks) == 2
        assert stocks[0].symbol == "01810"  # 补零到5位
        assert stocks[0].name == "小米集团"
        assert stocks[0].channel == "SZHK"
        assert stocks[0].source == "szse"

    @patch('vnpy_china_data.crawler.hk_connect_crawler.openpyxl')
    @patch('vnpy_china_data.crawler.hk_connect_crawler.requests')
    def test_crawl_sse_success(self, mock_requests, mock_openpyxl, crawler):
        """测试成功爬取上交所沪港通名单"""
        # Mock响应
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.content = b"fake excel content"
        mock_requests.get.return_value = mock_response

        # Mock Excel数据
        mock_wb = Mock()
        mock_ws = Mock()
        mock_wb.active = mock_ws

        # 模拟数据行：证券代码、中文简称、英文简称
        mock_rows = [
            (None, None, None),  # 表头
            ("700", "腾讯控股", "TENCENT"),
            ("9988", "阿里巴巴", "ALIBABA"),
        ]
        mock_ws.iter_rows.return_value = iter(mock_rows)

        mock_openpyxl.load_workbook.return_value = mock_wb

        # 调用测试
        stocks = crawler.crawl_sse_hk_connect()

        # 验证
        assert len(stocks) == 2
        assert stocks[0].symbol == "00700"  # 补零到5位
        assert stocks[0].name == "腾讯控股"
        assert stocks[0].channel == "SHHK"
        assert stocks[0].source == "sse"

    @patch('vnpy_china_data.crawler.hk_connect_crawler.openpyxl')
    @patch('vnpy_china_data.crawler.hk_connect_crawler.requests')
    def test_crawl_all_fallback(self, mock_requests, mock_openpyxl, crawler):
        """测试crawl_all使用备用数据源"""
        # Mock深交所失败
        mock_response_fail = Mock()
        mock_response_fail.raise_for_status = Mock(side_effect=Exception("DeepSeek API error"))
        mock_requests.get.side_effect = [
            mock_response_fail,  # 深交所失败
            mock_response_fail,  # 上交所也失败
        ]

        # 调用测试
        stocks = crawler.crawl_all()

        # 验证
        assert len(stocks) == 0  # 两个数据源都失败


class TestHkConnectCrawlerIntegration:
    """港股通爬虫集成测试（需要网络连接）"""

    def test_crawl_all_real(self):
        """真实网络爬取测试"""
        crawler = HkConnectCrawler()
        stocks = crawler.crawl_all()

        # 基本验证
        assert isinstance(stocks, list)
        if stocks:
            # 验证第一只股票的格式
            stock = stocks[0]
            assert isinstance(stock, HkConnectStock)
            assert len(stock.symbol) == 5
            assert stock.name  # 中文名称应该存在