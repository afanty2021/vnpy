"""
MySQL数据库操作层

提供K线数据、股票信息、财务数据等的持久化存储和查询功能。
"""

from typing import List, Optional, Any, Dict, TYPE_CHECKING
from datetime import datetime
from contextlib import contextmanager
from threading import Lock

from vnpy.trader.logger import logger

if TYPE_CHECKING:
    from vnpy_china_capital.objects.capital_flow import CapitalFlowData

try:
    import pymysql
    from pymysql.cursors import DictCursor
    from pymysql.err import OperationalError, DatabaseError
    PYMYSQL_AVAILABLE = True
except ImportError:
    pymysql = None
    DictCursor = None
    OperationalError = Exception
    DatabaseError = Exception
    PYMYSQL_AVAILABLE = False

from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval


class MySQLDatabaseLayer:
    """MySQL数据库层

    提供数据持久化功能，包括：
    - K线数据存储和查询
    - 股票信息存储和查询
    - 财务数据存储和查询
    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        charset: str = "utf8mb4",
    ):
        """初始化数据库连接

        Args:
            host: 数据库主机
            port: 端口
            user: 用户名
            password: 密码
            database: 数据库名
            charset: 字符集
        """
        self.config = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "charset": charset,
            "autocommit": True,
        }
        self._connection: Optional[pymysql.Connection] = None
        self._lock = Lock()
        self._connected = False

    def connect(self) -> bool:
        """建立数据库连接

        Returns:
            是否连接成功
        """
        import logging
        import traceback
        logger = logging.getLogger("vnpy_china_data")

        # 记录调用栈以便追踪问题
        stack = traceback.format_stack()

        try:
            self._connection = pymysql.connect(**self.config)
            self._connected = True
            logger.info(f"MySQL数据库连接成功: {self.config['host']}:{self.config['port']}/{self.config['database']}")
            return True
        except (OperationalError, DatabaseError) as e:
            self._connected = False
            logger.warning(f"MySQL连接失败: {e}")
            logger.warning(f"调用栈:\n{''.join(stack[-5:])}")
            return False
        except Exception as e:
            self._connected = False
            logger.warning(f"MySQL连接异常: {e}")
            logger.warning(f"调用栈:\n{''.join(stack[-5:])}")
            return False

    def close(self) -> None:
        """关闭连接"""
        with self._lock:
            if self._connection:
                try:
                    self._connection.close()
                except Exception:
                    pass
                finally:
                    self._connection = None
                    self._connected = False

    @property
    def is_connected(self) -> bool:
        """检查连接状态"""
        if not self._connected or not self._connection:
            return False
        try:
            self._connection.ping(reconnect=True)
            return True
        except Exception:
            self._connected = False
            return False

    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = pymysql.connect(**self.config)
        try:
            yield conn
        finally:
            conn.close()

    def _ensure_connection(self) -> bool:
        """确保连接有效"""
        if not self.is_connected:
            return self.connect()
        return True

    # ========== K线数据操作 ==========

    def save_bar_data(self, bars: List[BarData]) -> bool:
        """批量保存K线数据

        Args:
            bars: K线数据列表

        Returns:
            是否保存成功
        """
        if not bars:
            return True

        if not self._ensure_connection():
            return False

        try:
            with self._lock:
                cursor = self._connection.cursor()

                sql = """
                INSERT INTO db_bar_data
                (symbol, exchange, interval, datetime, open_price, high_price,
                 low_price, close_price, volume, turnover)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    open_price = VALUES(open_price),
                    high_price = VALUES(high_price),
                    low_price = VALUES(low_price),
                    close_price = VALUES(close_price),
                    volume = VALUES(volume),
                    turnover = VALUES(turnover)
                """

                values = []
                for bar in bars:
                    values.append((
                        bar.symbol,
                        bar.exchange.value,
                        bar.interval.value,
                        bar.datetime,
                        bar.open_price,
                        bar.high_price,
                        bar.low_price,
                        bar.close_price,
                        bar.volume,
                        getattr(bar, 'turnover', 0) or 0
                    ))

                cursor.executemany(sql, values)
                self._connection.commit()
                return True

        except (OperationalError, DatabaseError) as e:
            logger.error(f"保存K线数据失败: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"保存K线数据异常: {e}", exc_info=True)
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()

    def load_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """加载K线数据

        Args:
            symbol: 股票代码
            exchange: 交易所
            interval: K线周期
            start: 开始时间
            end: 结束时间

        Returns:
            K线数据列表
        """
        if not self._ensure_connection():
            return []

        try:
            with self._lock:
                cursor = self._connection.cursor()

                sql = """
                SELECT symbol, exchange, interval, datetime,
                       open_price, high_price, low_price, close_price,
                       volume, turnover
                FROM db_bar_data
                WHERE symbol = %s
                  AND exchange = %s
                  AND interval = %s
                  AND datetime >= %s
                  AND datetime <= %s
                ORDER BY datetime ASC
                """

                cursor.execute(sql, (
                    symbol,
                    exchange.value,
                    interval.value,
                    start,
                    end
                ))

                results = cursor.fetchall()
                cursor.close()

                # 转换为BarData对象
                bars = []
                for row in results:
                    bars.append(BarData(
                        symbol=row[0],
                        exchange=Exchange(row[1]),
                        interval=Interval(row[2]),
                        datetime=row[3],
                        open_price=float(row[4]),
                        high_price=float(row[5]),
                        low_price=float(row[6]),
                        close_price=float(row[7]),
                        volume=float(row[8]),
                        turnover=float(row[9]) if row[9] else 0.0
                    ))

                return bars

        except (OperationalError, DatabaseError) as e:
            logger.error(f"加载K线数据失败: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"加载K线数据异常: {e}", exc_info=True)
            return []

    def get_latest_date(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval
    ) -> Optional[datetime]:
        """获取指定合约的最新数据日期

        Args:
            symbol: 股票代码
            exchange: 交易所
            interval: K线周期

        Returns:
            最新数据日期
        """
        if not self._ensure_connection():
            return None

        try:
            with self._lock:
                cursor = self._connection.cursor()

                sql = """
                SELECT MAX(datetime) as latest_date
                FROM db_bar_data
                WHERE symbol = %s
                  AND exchange = %s
                  AND interval = %s
                """

                cursor.execute(sql, (symbol, exchange.value, interval.value))
                result = cursor.fetchone()
                cursor.close()

                if result and result[0]:
                    return result[0]
                return None

        except (OperationalError, DatabaseError):
            return None
        except Exception:
            return None

    # ========== 股票信息操作 ==========

    def save_stock_info(self, info: Dict[str, Any]) -> bool:
        """保存股票信息

        Args:
            info: 股票信息字典

        Returns:
            是否保存成功
        """
        if not self._ensure_connection():
            return False

        try:
            with self._lock:
                cursor = self._connection.cursor()

                sql = """
                INSERT INTO db_stock_info
                (symbol, name, exchange, industry, area, list_date, is_st)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    exchange = VALUES(exchange),
                    industry = VALUES(industry),
                    area = VALUES(area),
                    list_date = VALUES(list_date),
                    is_st = VALUES(is_st)
                """

                cursor.execute(sql, (
                    info.get("symbol"),
                    info.get("name"),
                    info.get("exchange", ""),
                    info.get("industry", ""),
                    info.get("area", ""),
                    info.get("list_date"),
                    info.get("is_st", 0)
                ))
                self._connection.commit()
                cursor.close()
                return True

        except Exception as e:
            logger.error(f"保存股票信息失败: {e}", exc_info=True)
            return False

    def load_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """加载股票信息

        Args:
            symbol: 股票代码

        Returns:
            股票信息字典
        """
        if not self._ensure_connection():
            return None

        try:
            with self._lock:
                cursor = self._connection.cursor(DictCursor)

                sql = """
                SELECT symbol, name, exchange, industry, area, list_date, is_st
                FROM db_stock_info
                WHERE symbol = %s
                """

                cursor.execute(sql, (symbol,))
                result = cursor.fetchone()
                cursor.close()

                return dict(result) if result else None

        except Exception as e:
            logger.error(f"加载股票信息失败: {e}", exc_info=True)
            return None

    # ========== 财务数据操作 ==========

    def save_financial_data(self, data: Dict[str, Any]) -> bool:
        """保存财务数据

        Args:
            data: 财务数据字典

        Returns:
            是否保存成功
        """
        if not self._ensure_connection():
            return False

        try:
            with self._lock:
                cursor = self._connection.cursor()

                sql = """
                INSERT INTO db_financial_data
                (symbol, report_date, report_type, pe_ratio, pb_ratio,
                 roe, roa, gross_margin, net_margin, revenue, net_profit)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    pe_ratio = VALUES(pe_ratio),
                    pb_ratio = VALUES(pb_ratio),
                    roe = VALUES(roe),
                    roa = VALUES(roa),
                    gross_margin = VALUES(gross_margin),
                    net_margin = VALUES(net_margin),
                    revenue = VALUES(revenue),
                    net_profit = VALUES(net_profit)
                """

                cursor.execute(sql, (
                    data.get("symbol"),
                    data.get("report_date"),
                    data.get("report_type", "1"),
                    data.get("pe_ratio"),
                    data.get("pb_ratio"),
                    data.get("roe"),
                    data.get("roa"),
                    data.get("gross_margin"),
                    data.get("net_margin"),
                    data.get("revenue"),
                    data.get("net_profit")
                ))
                self._connection.commit()
                cursor.close()
                return True

        except Exception as e:
            logger.error(f"保存财务数据失败: {e}", exc_info=True)
            return False

    # ========== 资金流水操作 ==========

    def create_capital_flow_table(self) -> bool:
        """创建资金流水表

        Returns:
            是否创建成功
        """
        if not self._ensure_connection():
            return False

        try:
            with self._lock:
                cursor = self._connection.cursor()

                sql = """
                CREATE TABLE IF NOT EXISTS db_capital_flow (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    flow_id VARCHAR(128) NOT NULL,
                    gateway_name VARCHAR(32) NOT NULL,
                    trade_id VARCHAR(64) NOT NULL,
                    symbol VARCHAR(32) NOT NULL,
                    exchange VARCHAR(16) NOT NULL,
                    direction VARCHAR(8),
                    offset VARCHAR(8),
                    price DECIMAL(15, 4),
                    volume DECIMAL(15, 4),
                    amount DECIMAL(20, 4),
                    balance DECIMAL(20, 4),
                    available DECIMAL(20, 4),
                    trade_time DATETIME(3) NOT NULL,
                    created_at DATETIME(3),
                    flow_type VARCHAR(16),
                    description TEXT,

                    UNIQUE KEY uk_flow_id (flow_id),
                    KEY idx_symbol_time (symbol, trade_time),
                    KEY idx_trade_time (trade_time),
                    KEY idx_type_time (flow_type, trade_time)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """

                cursor.execute(sql)
                self._connection.commit()
                cursor.close()
                return True

        except (OperationalError, DatabaseError) as e:
            logger.error(f"创建资金流水表失败: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"创建资金流水表异常: {e}", exc_info=True)
            return False

    def _execute_sql(
        self,
        sql: str,
        params: Optional[tuple] = None,
        fetch_all: bool = False,
        many: bool = False
    ) -> Optional[Any]:
        """执行SQL语句的内部方法

        Args:
            sql: SQL语句
            params: 参数（可以是tuple或list）
            fetch_all: 是否获取所有结果
            many: 是否执行批量操作

        Returns:
            执行结果
        """
        if not self._ensure_connection():
            return None

        try:
            with self._lock:
                cursor = self._connection.cursor(DictCursor if fetch_all else None)

                if many and isinstance(params, list):
                    cursor.executemany(sql, params)
                    result = cursor.rowcount
                elif params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)

                if not many:
                    if fetch_all:
                        result = cursor.fetchall()
                    elif sql.strip().upper().startswith("SELECT"):
                        result = cursor.fetchone()
                    else:
                        result = cursor.rowcount

                self._connection.commit()
                cursor.close()
                return result if result is not None else [] if fetch_all else True

        except (OperationalError, DatabaseError) as e:
            logger.error(f"执行SQL失败: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"执行SQL异常: {e}", exc_info=True)
            return None

    def save_capital_flow(self, flow: "CapitalFlowData") -> bool:
        """保存资金流水

        Args:
            flow: CapitalFlowData对象

        Returns:
            是否保存成功
        """
        if not self._ensure_connection():
            return False

        try:
            with self._lock:
                cursor = self._connection.cursor()

                sql = """
                INSERT INTO db_capital_flow
                (flow_id, gateway_name, trade_id, symbol, exchange, direction, offset,
                 price, volume, amount, balance, available, trade_time, created_at,
                 flow_type, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    amount = VALUES(amount),
                    balance = VALUES(balance),
                    available = VALUES(available)
                """

                # 获取枚举值，处理None情况
                direction_value = flow.direction.value if hasattr(flow, 'direction') and flow.direction else None
                offset_value = flow.offset.value if hasattr(flow, 'offset') and flow.offset else None

                params = (
                    flow.flow_id,
                    flow.gateway_name,
                    flow.trade_id,
                    flow.symbol,
                    flow.exchange,
                    direction_value,
                    offset_value,
                    float(flow.price) if flow.price is not None else None,
                    float(flow.volume) if flow.volume is not None else None,
                    float(flow.amount) if flow.amount is not None else None,
                    float(flow.balance) if flow.balance is not None else None,
                    float(flow.available) if flow.available is not None else None,
                    flow.trade_time,
                    flow.created_at,
                    flow.flow_type,
                    flow.description
                )

                cursor.execute(sql, params)
                self._connection.commit()
                cursor.close()
                return True

        except (OperationalError, DatabaseError) as e:
            logger.error(f"保存资金流水失败: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"保存资金流水异常: {e}", exc_info=True)
            return False

    def query_capital_flow(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        symbol: Optional[str] = None,
        flow_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """查询资金流水

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            symbol: 股票代码
            flow_type: 流水类型

        Returns:
            资金流水字典列表
        """
        conditions = []
        params = []

        if start_date:
            conditions.append("trade_time >= %s")
            params.append(start_date)

        if end_date:
            conditions.append("trade_time <= %s")
            params.append(end_date)

        if symbol:
            conditions.append("symbol = %s")
            params.append(symbol)

        if flow_type:
            conditions.append("flow_type = %s")
            params.append(flow_type)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = f"""
        SELECT * FROM db_capital_flow
        WHERE {where_clause}
        ORDER BY trade_time DESC
        """

        results = self._execute_sql(sql, tuple(params) if params else None, fetch_all=True)
        return results if results else []
