"""港股通股票数据模型单元测试"""

import sys
import pytest
from datetime import date

sys.path.insert(0, '/Users/berton/Github/vnpy')

from vnpy_china_data.models.hk_connect import HkConnectStock
from vnpy.trader.constant import Exchange


class TestHkConnectStock:
    """港股通股票数据模型测试"""

    def test_model_creation(self):
        """测试模型创建"""
        stock = HkConnectStock(
            symbol="00700",
            name="腾讯控股",
            channel="SHHK",
            channel_type="SH",
            category="沪港通",
            industry="科技",
            status="active",
            list_date=date(2024, 1, 1),
            source="sse"
        )

        assert stock.symbol == "00700"
        assert stock.name == "腾讯控股"
        assert stock.channel == "SHHK"
        assert stock.channel_type == "SH"

    def test_vnpy_symbol_property(self):
        """测试VeighNa格式代码属性"""
        # 沪港通
        stock_sh = HkConnectStock(
            symbol="00700",
            name="腾讯控股",
            channel="SHHK",
            channel_type="SH"
        )
        assert stock_sh.vnpy_symbol == "00700.SHHK"

        # 深港通
        stock_sz = HkConnectStock(
            symbol="01810",
            name="小米集团",
            channel="SZHK",
            channel_type="SZ"
        )
        assert stock_sz.vnpy_symbol == "01810.SZHK"

    def test_qmt_symbol_property(self):
        """测试QMT格式代码属性

        重要：港股通股票使用香港本地交易所后缀
        """
        stock = HkConnectStock(
            symbol="00700",
            name="腾讯控股",
            channel="SHHK",
            channel_type="SH"
        )

        # QMT格式统一使用.HK后缀
        assert stock.qmt_symbol == "00700.HK"

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "symbol": "09988",
            "name": "阿里巴巴",
            "channel": "SZHK",
            "channel_type": "SZ",
            "category": "深港通",
            "status": "active",
            "source": "szse"
        }

        stock = HkConnectStock.from_dict(data)

        assert stock.symbol == "09988"
        assert stock.name == "阿里巴巴"
        assert stock.channel == "SZHK"

    def test_to_dict(self):
        """测试转换为字典"""
        stock = HkConnectStock(
            symbol="00700",
            name="腾讯控股",
            channel="SHHK",
            channel_type="SH",
            list_date=date(2024, 1, 1)
        )

        data = stock.to_dict()

        assert data["symbol"] == "00700"
        assert data["name"] == "腾讯控股"
        assert data["channel"] == "SHHK"
        assert data["list_date"] == "2024-01-01"
