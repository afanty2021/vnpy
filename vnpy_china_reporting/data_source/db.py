"""
报表数据源 - MySQL 存储连接层

复用 vnpy_china_config.GlobalConfig 的数据库配置，采用 pymysql + DBUtils 连接池
（与 vnpy_china_data.database 一致），为权益快照与行业映射提供持久化。
"""

from contextlib import contextmanager
from typing import Optional, List, Dict, Any
import logging

try:
    import pymysql
    from pymysql.cursors import DictCursor
    from dbutils.pooled_db import PooledDB
    _DB_AVAILABLE = True
except ImportError:
    pymysql = None
    DictCursor = None
    PooledDB = None
    _DB_AVAILABLE = False

logger = logging.getLogger(__name__)


class DataSourceDB:
    """报表数据源 MySQL 连接（DBUtils 连接池）"""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        charset: str = "utf8mb4",
        pool_size: int = 5,
        max_overflow: int = 10,
    ):
        """初始化连接配置

        Args:
            host: 主机
            port: 端口
            user: 用户名
            password: 密码
            database: 数据库名
            charset: 字符集
            pool_size: 连接池常驻连接数
            max_overflow: 最大溢出连接数
        """
        if not _DB_AVAILABLE:
            raise ImportError(
                "pymysql/dbutils 未安装，无法启用数据源持久化。"
                "请 pip install pymysql dbutils"
            )
        self._config: Dict[str, Any] = dict(
            host=host, port=port, user=user, password=password,
            database=database, charset=charset, autocommit=True,
        )
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._pool: Optional[Any] = None

    @classmethod
    def from_global_config(cls, config: Any) -> "DataSourceDB":
        """从 vnpy_china_config.GlobalConfig 构造

        Args:
            config: GlobalConfig 实例（需含 database 字段）

        Returns:
            DataSourceDB 实例
        """
        db = config.database
        return cls(
            host=db.mysql_host, port=db.mysql_port,
            user=db.mysql_user, password=db.mysql_password,
            database=db.mysql_database,
            pool_size=db.pool_size, max_overflow=db.max_overflow,
        )

    def connect(self) -> bool:
        """建立连接池（幂等）"""
        if self._pool is not None:
            return True
        self._pool = PooledDB(
            pymysql,
            mincached=self._pool_size,
            maxcached=self._pool_size,
            maxshared=0,
            maxconnections=self._pool_size + self._max_overflow,
            blocking=True,
            **self._config,
        )
        logger.info(
            "报表数据源 DB 连接池已建立: %s/%s",
            self._config["host"], self._config["database"]
        )
        return True

    @contextmanager
    def connection(self):
        """获取一个连接（上下文管理，自动归还连接池）"""
        if self._pool is None:
            self.connect()
        conn = self._pool.connection()
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, sql: str, args: Any = None) -> int:
        """执行写/DDL，返回受影响行数"""
        with self.connection() as conn:
            with conn.cursor() as cur:
                return cur.execute(sql, args)

    def executemany(self, sql: str, args_list: List[Any]) -> int:
        """批量执行写操作"""
        with self.connection() as conn:
            with conn.cursor() as cur:
                return cur.executemany(sql, args_list)

    def query(self, sql: str, args: Any = None) -> List[Dict[str, Any]]:
        """查询，返回 dict 列表"""
        with self.connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute(sql, args)
                return list(cur.fetchall())
