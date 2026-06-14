"""数据库层单元测试"""

from unittest.mock import MagicMock

import pytest

from vnpy_china_data.database import MySQLDatabaseLayer


@pytest.fixture
def db():
    """构造未连接的数据库层实例"""
    return MySQLDatabaseLayer(
        host="localhost", port=3306, user="root",
        password="", database="test"
    )


class TestGetConnection:
    """get_connection 连接归还测试"""

    def test_get_connection_closes_conn_after_with_block(self, db):
        """with 块结束后连接应归还（close 被调用）"""
        mock_conn = MagicMock()
        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn
        db._pool = mock_pool

        with db.get_connection() as conn:
            assert conn is mock_conn

        mock_conn.close.assert_called_once()

    def test_get_connection_closes_conn_on_exception(self, db):
        """with 块内抛异常时连接仍应归还"""
        mock_conn = MagicMock()
        mock_pool = MagicMock()
        mock_pool.connection.return_value = mock_conn
        db._pool = mock_pool

        with pytest.raises(ValueError):
            with db.get_connection() as conn:
                raise ValueError("test")

        mock_conn.close.assert_called_once()


class TestDatabaseStatsTableNameValidation:
    """get_database_stats 表名白名单校验测试"""

    def test_valid_table_names_accepted(self):
        """合法表名通过白名单"""
        assert MySQLDatabaseLayer._is_valid_table_name("db_bar_data") is True
        assert MySQLDatabaseLayer._is_valid_table_name("db_stock_info") is True
        assert MySQLDatabaseLayer._is_valid_table_name("db_hk_connect_stocks") is True

    def test_invalid_table_names_rejected(self):
        """恶意表名被白名单拒绝"""
        # SQL 注入尝试
        assert MySQLDatabaseLayer._is_valid_table_name("db_evil; DROP TABLE x") is False
        assert MySQLDatabaseLayer._is_valid_table_name("db_x'); --") is False
        assert MySQLDatabaseLayer._is_valid_table_name("db_x` OR 1=1") is False
        # 非法前缀
        assert MySQLDatabaseLayer._is_valid_table_name("information_schema") is False
        assert MySQLDatabaseLayer._is_valid_table_name("mysql.user") is False
        # 含大写/特殊字符
        assert MySQLDatabaseLayer._is_valid_table_name("db_BarData") is False
