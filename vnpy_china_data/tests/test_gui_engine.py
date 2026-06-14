"""GUI引擎港股通功能单元测试"""

import sys
from unittest.mock import Mock, MagicMock
from datetime import date

import pytest

sys.path.insert(0, '/Users/berton/Github/vnpy')

from vnpy_china_data.gui_engine import ChinaDataGuiEngine
from vnpy.trader.constant import Exchange, Interval


class TestChinaDataGuiEngineHkConnect:
    """GUI引擎港股通功能测试"""

    @pytest.fixture
    def mock_main_engine(self):
        """模拟主引擎"""
        main_engine = Mock()
        main_engine.write_log = Mock()
        return main_engine

    @pytest.fixture
    def mock_event_engine(self):
        """模拟事件引擎"""
        return Mock()

    @pytest.fixture
    def mock_data_service(self):
        """模拟数据服务"""
        service = Mock()
        service.database = Mock()
        service.connect = Mock(return_value=True)
        return service

    @pytest.fixture
    def gui_engine(self, mock_main_engine, mock_event_engine, mock_data_service):
        """创建GUI引擎实例"""
        # 将数据服务注入到单例中
        import vnpy_china_data.service as service_module
        original_get_data_service = service_module.get_data_service
        service_module.get_data_service = Mock(return_value=mock_data_service)

        engine = ChinaDataGuiEngine(mock_main_engine, mock_event_engine)
        engine.data_service = mock_data_service

        yield engine

        # 恢复原始函数
        service_module.get_data_service = original_get_data_service

    def test_parse_exchange_hk_connect(self, gui_engine):
        """测试港股通交易所解析

        重要：港股通代码应该转换为香港本地交易所（SEHK）
        """
        # 沪港通
        assert gui_engine._parse_exchange("00700.SHHK") == Exchange.SEHK

        # 深港通
        assert gui_engine._parse_exchange("01810.SZHK") == Exchange.SEHK

        # 香港本地
        assert gui_engine._parse_exchange("00700.HK") == Exchange.SEHK

    def test_parse_exchange_a股(self, gui_engine):
        """测试A股交易所解析"""
        assert gui_engine._parse_exchange("600000.SH") == Exchange.SSE
        assert gui_engine._parse_exchange("000001.SZ") == Exchange.SZSE

    def test_parse_exchange_edge_cases(self, gui_engine):
        """测试 _parse_exchange 边缘用例（标准格式，纯 endswith 行为）"""
        # 港股通各后缀 → SEHK
        assert gui_engine._parse_exchange("0700.SHHK") == Exchange.SEHK
        assert gui_engine._parse_exchange("2318.SZHK") == Exchange.SEHK
        assert gui_engine._parse_exchange("09988.SEHK") == Exchange.SEHK
        assert gui_engine._parse_exchange("00700.HK") == Exchange.SEHK
        # A股各后缀
        assert gui_engine._parse_exchange("600000.SH") == Exchange.SSE
        assert gui_engine._parse_exchange("000001.SZ") == Exchange.SZSE
        # 无后缀纯代码（按首位判断）
        assert gui_engine._parse_exchange("600000") == Exchange.SSE
        assert gui_engine._parse_exchange("000001") == Exchange.SZSE

    def test_get_hk_symbols_from_database(self, gui_engine, mock_data_service):
        """测试从数据库获取港股通股票列表"""
        # Mock数据库返回
        mock_data_service.database.get_hk_connect_symbols.return_value = [
            "00700.HK",
            "01810.HK",
            "09988.HK"
        ]

        symbols = gui_engine.get_hk_symbols("HK_ALL")

        # 应该转换为显示格式（.SEHK）
        assert len(symbols) == 3
        assert "00700.SEHK" in symbols
        assert "01810.SEHK" in symbols
        assert "09988.SEHK" in symbols

    def test_get_hk_symbols_by_channel(self, gui_engine, mock_data_service):
        """测试按通道获取港股通股票"""
        # 沪港通
        mock_data_service.database.get_hk_connect_symbols.return_value = [
            "00700.HK",
            "09988.HK"
        ]

        sh_symbols = gui_engine.get_hk_symbols("HK_SH")
        assert len(sh_symbols) == 2
        assert "00700.SEHK" in sh_symbols

        # 深港通
        mock_data_service.database.get_hk_connect_symbols.return_value = [
            "01810.HK"
        ]

        sz_symbols = gui_engine.get_hk_symbols("HK_SZ")
        assert len(sz_symbols) == 1
        assert "01810.SEHK" in sz_symbols

    def test_update_hk_connect_stocks(self, gui_engine, mock_data_service):
        """测试更新港股通名单"""
        mock_data_service.update_hk_connect_stocks.return_value = {
            "success": True,
            "count": 550,
            "sh_count": 300,
            "sz_count": 250,
            "error": None
        }

        result = gui_engine.update_hk_connect_stocks()

        assert result["success"] == True
        assert result["count"] == 550
        assert result["sh_count"] == 300
        assert result["sz_count"] == 250

    def test_get_hk_connect_update_info(self, gui_engine, mock_data_service):
        """测试获取港股通更新信息"""
        # 直接在 database mock 上设置返回值
        mock_data_service.get_hk_connect_update_info.return_value = {
            "last_updated": "2024-01-01",
            "days_since_update": 5,
            "total_count": 550,
            "sh_count": 300,
            "sz_count": 250,
            "exists": True
        }

        info = gui_engine.get_hk_connect_update_info()

        assert info["days_since_update"] == 5
        assert info["total_count"] == 550

    def test_download_history_data_hk_connect(self, gui_engine, mock_data_service):
        """测试下载港股通历史数据

        验证港股通代码正确转换为纯代码+SEHK交易所
        """
        # Mock数据下载
        mock_bar = Mock()
        mock_bar.datetime = "2024-01-01"
        mock_data_service.download_bar_data.return_value = [mock_bar]

        gui_engine._downloading = False

        # 使用港股通格式代码（.SEHK）
        symbols = ["00700.SEHK", "01810.SEHK"]
        result = gui_engine.download_history_data(
            symbols=symbols,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            interval=Interval.DAILY
        )

        # 验证调用
        assert result["success"] == True
        assert result["downloaded_count"] == 2

        # 验证数据服务被正确调用
        # 应该使用纯代码 + SEHK交易所
        calls = mock_data_service.download_bar_data.call_args_list
        assert len(calls) == 2

        # 第一次调用：00700 + SEHK
        # calls[0][0] 是位置参数元组，calls[0][1] 是关键字参数字典
        first_call_args = calls[0][0]  # 位置参数
        first_call_kwargs = calls[0][1]  # 关键字参数
        assert first_call_kwargs["symbol"] == "00700"
        assert first_call_kwargs["exchange"] == Exchange.SEHK

        # 第二次调用：01810 + SEHK
        second_call_kwargs = calls[1][1]
        assert second_call_kwargs["symbol"] == "01810"
        assert second_call_kwargs["exchange"] == Exchange.SEHK

    def test_get_index_symbols_no_duplicates(self, gui_engine):
        """指数成分股列表无重复项"""
        for index in ["HS300", "ZZ500", "ZZ1000"]:
            symbols = gui_engine.get_index_symbols(index)
            assert len(symbols) == len(set(symbols)), \
                f"{index} 成分股存在重复: {symbols}"

    def test_get_index_symbols_unknown_returns_empty(self, gui_engine):
        """未知指数返回空列表"""
        assert gui_engine.get_index_symbols("UNKNOWN") == []


class TestGuiEngineHelperMethods:
    """GUI引擎辅助方法测试"""

    @pytest.fixture
    def mock_main_engine(self):
        """模拟主引擎"""
        return Mock(write_log=Mock())

    @pytest.fixture
    def mock_event_engine(self):
        """模拟事件引擎"""
        return Mock()

    @pytest.fixture
    def gui_engine(self, mock_main_engine, mock_event_engine):
        """创建GUI引擎实例"""
        return ChinaDataGuiEngine(mock_main_engine, mock_event_engine)

    def test_get_hk_sh_symbols(self, gui_engine):
        """测试获取沪港通股票"""
        gui_engine.data_service = Mock()
        gui_engine.data_service.database = Mock()
        gui_engine.data_service.database.get_hk_connect_symbols.return_value = [
            "00700.HK",
            "09988.HK"
        ]

        symbols = gui_engine.get_hk_sh_symbols()
        assert len(symbols) == 2
        assert "00700.SEHK" in symbols

    def test_get_hk_sz_symbols(self, gui_engine):
        """测试获取深港通股票"""
        gui_engine.data_service = Mock()
        gui_engine.data_service.database = Mock()
        gui_engine.data_service.database.get_hk_connect_symbols.return_value = [
            "01810.HK"
        ]

        symbols = gui_engine.get_hk_sz_symbols()
        assert len(symbols) == 1
        assert "01810.SEHK" in symbols
