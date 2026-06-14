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
