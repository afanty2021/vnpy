"""数据验证器单元测试"""

from datetime import datetime

from vnpy.trader.object import BarData
from vnpy.trader.constant import Exchange, Interval

from vnpy_china_data.validator import DataValidator


def make_bar(
    symbol: str = "000001",
    open_price: float = 10.0,
    high_price: float = 11.0,
    low_price: float = 9.0,
    close_price: float = 10.5,
    volume: float = 1000.0,
) -> BarData:
    """构造测试用 BarData"""
    return BarData(
        gateway_name="TEST",
        symbol=symbol,
        exchange=Exchange.SZSE,
        datetime=datetime(2024, 1, 1),
        interval=Interval.DAILY,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        volume=volume,
    )


class TestDataValidator:
    """DataValidator 测试"""

    def test_valid_bar(self):
        """合法 bar 返回 True"""
        assert DataValidator.validate_bar_data(make_bar()) is True

    def test_volume_negative_rejected(self):
        """volume<0 拒绝"""
        assert DataValidator.validate_bar_data(make_bar(volume=-1)) is False

    def test_volume_zero_allowed(self):
        """volume==0 放行（停牌/空 bar）"""
        assert DataValidator.validate_bar_data(make_bar(volume=0)) is True

    def test_price_zero_rejected(self):
        """任一价格<=0 拒绝"""
        assert DataValidator.validate_bar_data(make_bar(open_price=0)) is False
        assert DataValidator.validate_bar_data(make_bar(high_price=0)) is False
        assert DataValidator.validate_bar_data(make_bar(low_price=-1)) is False
        assert DataValidator.validate_bar_data(make_bar(close_price=0)) is False

    def test_high_lt_low_rejected(self):
        """high<low 拒绝"""
        assert DataValidator.validate_bar_data(
            make_bar(high_price=8.0, low_price=9.0)
        ) is False

    def test_empty_symbol_rejected(self):
        """空 symbol 拒绝"""
        assert DataValidator.validate_bar_data(make_bar(symbol="")) is False

    def test_validate_bar_list_filters_invalid(self):
        """validate_bar_list 过滤混合列表"""
        bars = [
            make_bar(symbol="000001"),
            make_bar(symbol="000002", volume=-5),
            make_bar(symbol="000003"),
            make_bar(symbol="000004", high_price=1, low_price=9),
        ]
        valid = DataValidator.validate_bar_list(bars)
        assert len(valid) == 2
        assert valid[0].symbol == "000001"
        assert valid[1].symbol == "000003"

    def test_validate_exchange_hk_connect(self):
        """validate_exchange 支持港股通"""
        assert DataValidator.validate_exchange(Exchange.SHHK) is True
        assert DataValidator.validate_exchange(Exchange.SZHK) is True
        assert DataValidator.validate_exchange(Exchange.SEHK) is True
        assert DataValidator.validate_exchange(Exchange.SSE) is True
        assert DataValidator.validate_exchange(Exchange.SZSE) is True

    def test_validate_interval_actual_enums(self):
        """validate_interval 使用实际 Interval 枚举"""
        assert DataValidator.validate_interval(Interval.MINUTE) is True
        assert DataValidator.validate_interval(Interval.HOUR) is True
        assert DataValidator.validate_interval(Interval.DAILY) is True
        assert DataValidator.validate_interval(Interval.WEEKLY) is True


class TestSaveBarDataValidation:
    """save_bar_data 接入校验的集成测试"""

    def test_save_bar_data_filters_invalid_bars(self, caplog):
        """save_bar_data 过滤无效 bar，仅存有效项"""
        import logging
        from unittest.mock import MagicMock
        from loguru import logger as loguru_logger
        from vnpy_china_data.database import MySQLDatabaseLayer

        # vnpy 使用 loguru，caplog 只捕获标准 logging；
        # 加一个把 loguru 消息转发到标准 logging 的 sink，让 caplog 可见
        std_logger = logging.getLogger("vnpy_china_data.bridge")

        def loguru_to_std(message):
            record = message.record
            std_logger.log(
                record["level"].no,
                record["message"],
            )

        handler_id = loguru_logger.add(loguru_to_std, level="WARNING")

        db = MySQLDatabaseLayer(
            host="localhost", port=3306, user="root",
            password="", database="test"
        )

        # mock 连接池与游标（is_connected property 会调 pool.connection().ping()，
        # mock 默认不抛异常，自然返回 True，无需覆盖 property）
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn
        db._pool = mock_pool
        db._connected = True

        # 混合数据：2 有效 + 2 无效
        bars = [
            make_bar(symbol="000001"),                                 # 有效
            make_bar(symbol="BAD01", volume=-1),                       # 无效
            make_bar(symbol="000002"),                                 # 有效
            make_bar(symbol="BAD02", high_price=1, low_price=9),       # 无效
        ]

        try:
            with caplog.at_level(logging.WARNING):
                result = db.save_bar_data(bars)
        finally:
            loguru_logger.remove(handler_id)

        assert result is True
        # 验证过滤日志被触发
        assert "过滤" in caplog.text
        # executemany 只接收有效的 2 条
        mock_cursor.executemany.assert_called_once()
        executed_values = mock_cursor.executemany.call_args[0][1]
        assert len(executed_values) == 2
        assert executed_values[0][0] == "000001"
        assert executed_values[1][0] == "000002"

    def test_save_bar_data_all_invalid_returns_true(self):
        """全部无效 bar 时 return True，不调用 executemany"""
        from unittest.mock import MagicMock
        from vnpy_china_data.database import MySQLDatabaseLayer

        db = MySQLDatabaseLayer(
            host="localhost", port=3306, user="root",
            password="", database="test"
        )
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn
        db._pool = mock_pool
        db._connected = True

        bars = [
            make_bar(symbol="BAD01", volume=-1),
            make_bar(symbol="BAD02", high_price=1, low_price=9),
        ]

        result = db.save_bar_data(bars)

        assert result is True
        mock_cursor.executemany.assert_not_called()
