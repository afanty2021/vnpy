"""
MySQL数据库操作层

提供K线数据、股票信息、财务数据等的持久化存储和查询功能。
"""

from typing import List, Optional, Any, Dict, TYPE_CHECKING
from datetime import datetime
from contextlib import contextmanager

from vnpy.trader.logger import logger

if TYPE_CHECKING:
    from vnpy_china_capital.objects.capital_flow import CapitalFlowData

try:
    import pymysql
    from pymysql.cursors import DictCursor
    from pymysql.err import OperationalError, DatabaseError
    from dbutils.pooled_db import PooledDB
    PYMYSQL_AVAILABLE = True
except ImportError:
    pymysql = None
    DictCursor = None
    OperationalError = Exception
    DatabaseError = Exception
    PooledDB = None
    PYMYSQL_AVAILABLE = False

# 连接池配置常量
DEFAULT_POOL_SIZE = 5
DEFAULT_MAX_OVERFLOW = 10

from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval

from .validator import DataValidator


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
        pool_size: int = DEFAULT_POOL_SIZE,
        max_overflow: int = DEFAULT_MAX_OVERFLOW,
    ):
        """初始化数据库连接

        Args:
            host: 数据库主机
            port: 端口
            user: 用户名
            password: 密码
            database: 数据库名
            charset: 字符集
            pool_size: 连接池大小（默认5）
            max_overflow: 最大溢出连接数（默认10）
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
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._pool: Optional[PooledDB] = None
        self._connected = False

    def connect(self) -> bool:
        """建立数据库连接池

        Returns:
            是否连接成功
        """
        import logging
        import traceback
        logger = logging.getLogger("vnpy_china_data")

        # 记录调用栈以便追踪问题
        stack = traceback.format_stack()

        try:
            self._pool = PooledDB(
                creator=pymysql,
                maxconnections=self._pool_size + self._max_overflow,
                mincached=2,
                maxcached=self._pool_size,
                maxshared=self._pool_size,
                blocking=True,
                ping=1,
                **self.config
            )
            self._connected = True
            logger.info(f"MySQL连接池创建成功: {self.config['host']}:{self.config['port']}/{self.config['database']}")
            logger.info(f"连接池配置: pool_size={self._pool_size}, max_overflow={self._max_overflow}")
            return True
        except (OperationalError, DatabaseError) as e:
            self._connected = False
            logger.warning(f"MySQL连接池创建失败: {e}")
            logger.warning(f"调用栈:\n{''.join(stack[-5:])}")
            return False
        except Exception as e:
            self._connected = False
            logger.warning(f"MySQL连接池创建异常: {e}")
            logger.warning(f"调用栈:\n{''.join(stack[-5:])}")
            return False

    def close(self) -> None:
        """关闭连接池"""
        if self._pool:
            try:
                # DBUtils的PooledDB会自动管理连接，无需手动关闭
                self._pool = None
                self._connected = False
                logger.info("MySQL连接池已关闭")
            except Exception as e:
                logger.warning(f"关闭连接池异常: {e}")

    @property
    def is_connected(self) -> bool:
        """检查连接池状态"""
        if not self._connected or not self._pool:
            return False
        try:
            # 从连接池获取连接进行测试
            conn = self._pool.connection()
            conn.ping(reconnect=True)
            # 连接会在函数返回时自动归还到池中，无需手动close()
            # DBUtils的PooledDB会自动管理连接的生命周期
            return True
        except Exception:
            self._connected = False
            return False

    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）

        从连接池获取连接，使用后自动归还。
        """
        if not self._pool:
            raise RuntimeError("连接池未初始化，请先调用connect()方法")

        conn = self._pool.connection()
        try:
            yield conn
        finally:
            # 连接自动归还到池中，无需显式关闭
            pass

    def _ensure_connection(self) -> bool:
        """确保连接池有效"""
        if not self.is_connected:
            return self.connect()
        return True

    def get_pool_status(self) -> Dict[str, Any]:
        """获取连接池状态信息

        Returns:
            连接池状态字典
        """
        if not self._pool:
            return {
                "status": "not_initialized",
                "pool_size": self._pool_size,
                "max_overflow": self._max_overflow,
            }

        # DBUtils的PooledDB没有直接的API查询当前连接数
        # 但我们可以返回配置信息和状态
        return {
            "status": "active" if self._connected else "inactive",
            "pool_size": self._pool_size,
            "max_overflow": self._max_overflow,
            "max_connections": self._pool_size + self._max_overflow,
            "database": self.config["database"],
            "host": self.config["host"],
            "port": self.config["port"],
        }

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

        # 数据校验：过滤无效 bar
        original_count = len(bars)
        bars = DataValidator.validate_bar_list(bars)
        filtered_count = original_count - len(bars)
        if filtered_count > 0:
            sample_symbols = [b.symbol for b in bars[:5]] if bars else []
            logger.warning(
                f"save_bar_data 过滤 {filtered_count}/{original_count} 条无效 bar，"
                f"保留示例: {sample_symbols}"
            )

        if not bars:
            return True

        if not self._ensure_connection():
            return False

        try:
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor()

            sql = """
            INSERT INTO db_bar_data
            (symbol, exchange, `interval`, `datetime`, open_price, high_price,
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
            conn.commit()
            cursor.close()
            # 连接自动归还到池中
            return True

        except (OperationalError, DatabaseError) as e:
            logger.error(f"保存K线数据失败: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"保存K线数据异常: {e}", exc_info=True)
            return False

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
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor()

            sql = """
            SELECT symbol, exchange, `interval`, `datetime`,
                   open_price, high_price, low_price, close_price,
                   volume, turnover
            FROM db_bar_data
            WHERE symbol = %s
              AND exchange = %s
              AND `interval` = %s
              AND `datetime` >= %s
              AND `datetime` <= %s
            ORDER BY `datetime` ASC
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
            # 连接自动归还到池中

            # 转换为BarData对象
            bars = []
            for row in results:
                bars.append(BarData(
                    gateway_name="MYSQL",
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
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor()

            sql = """
            SELECT MAX(`datetime`) as latest_date
            FROM db_bar_data
            WHERE symbol = %s
              AND exchange = %s
              AND interval = %s
            """

            cursor.execute(sql, (symbol, exchange.value, interval.value))
            result = cursor.fetchone()
            cursor.close()
            # 连接自动归还到池中

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
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor()

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
            conn.commit()
            cursor.close()
            # 连接自动归还到池中
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
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor(DictCursor)

            sql = """
            SELECT symbol, name, exchange, industry, area, list_date, is_st
            FROM db_stock_info
            WHERE symbol = %s
            """

            cursor.execute(sql, (symbol,))
            result = cursor.fetchone()
            cursor.close()
            # 连接自动归还到池中

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
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor()

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
            conn.commit()
            cursor.close()
            # 连接自动归还到池中
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
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor()

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
            conn.commit()
            cursor.close()
            # 连接自动归还到池中
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
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor(DictCursor if fetch_all else None)

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

            conn.commit()
            cursor.close()
            # 连接自动归还到池中
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
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor()

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
            conn.commit()
            cursor.close()
            # 连接自动归还到池中
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

    # ========== 港股通股票名单操作 ==========

    def create_hk_connect_table(self) -> bool:
        """创建港股通股票名单表

        Returns:
            是否创建成功
        """
        if not self._ensure_connection():
            return False

        try:
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor()

            sql = """
            CREATE TABLE IF NOT EXISTS db_hk_connect_stocks (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                symbol VARCHAR(16) NOT NULL COMMENT '股票代码（不含交易所后缀）',
                name VARCHAR(64) NOT NULL COMMENT '股票名称',
                channel VARCHAR(8) NOT NULL COMMENT '交易通道：SHHK/SZHK',
                channel_type VARCHAR(4) NOT NULL COMMENT '通道类型：SH/SZ',
                category VARCHAR(16) COMMENT '分类：沪港通/深港通',
                industry VARCHAR(64) COMMENT '行业分类',
                status VARCHAR(16) DEFAULT 'active' COMMENT '状态：active/suspended',
                list_date DATE COMMENT '纳入港股通日期',
                source VARCHAR(16) DEFAULT 'sse' COMMENT '数据来源：sse/szse',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

                UNIQUE KEY uk_symbol_channel (symbol, channel),
                KEY idx_channel (channel),
                KEY idx_status (status),
                KEY idx_updated_at (updated_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='港股通股票名单';
            """

            cursor.execute(sql)
            conn.commit()
            cursor.close()
            # 连接自动归还到池中
            return True

        except (OperationalError, DatabaseError) as e:
            logger.error(f"创建港股通名单表失败: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"创建港股通名单表异常: {e}", exc_info=True)
            return False

    def save_hk_connect_stocks(self, stocks: List) -> bool:
        """批量保存港股通股票名单

        Args:
            stocks: HkConnectStock 对象列表

        Returns:
            是否保存成功
        """
        if not stocks:
            return True

        if not self._ensure_connection():
            return False

        try:
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor()

            sql = """
            INSERT INTO db_hk_connect_stocks
            (symbol, name, channel, channel_type, category, industry, status, list_date, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                category = VALUES(category),
                industry = VALUES(industry),
                status = VALUES(status),
                list_date = VALUES(list_date),
                source = VALUES(source),
                updated_at = CURRENT_TIMESTAMP
            """

            values = []
            for stock in stocks:
                # 支持字典和对象两种格式
                if isinstance(stock, dict):
                    values.append((
                        stock.get("symbol"),
                        stock.get("name"),
                        stock.get("channel"),
                        stock.get("channel_type"),
                        stock.get("category"),
                        stock.get("industry"),
                        stock.get("status", "active"),
                        stock.get("list_date"),
                        stock.get("source", "sse"),
                    ))
                else:
                    # HkConnectStock 对象
                    values.append((
                        stock.symbol,
                        stock.name,
                        stock.channel,
                        stock.channel_type,
                        stock.category,
                        stock.industry,
                        stock.status,
                        stock.list_date,
                        stock.source,
                    ))

            cursor.executemany(sql, values)
            conn.commit()
            cursor.close()
            # 连接自动归还到池中
            return True

        except (OperationalError, DatabaseError) as e:
            logger.error(f"保存港股通名单失败: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"保存港股通名单异常: {e}", exc_info=True)
            return False

    def get_hk_connect_stocks(
        self,
        channel: Optional[str] = None,
        status: str = "active"
    ) -> List[Dict[str, Any]]:
        """获取港股通股票名单

        Args:
            channel: 交易通道筛选（None表示全部，SHHK表示沪港通，SZHK表示深港通）
            status: 状态筛选（默认 active）

        Returns:
            股票信息字典列表
        """
        if not self._ensure_connection():
            return []

        try:
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor(DictCursor)

            conditions = ["status = %s"]
            params = [status]

            if channel:
                conditions.append("channel = %s")
                params.append(channel)

            where_clause = " AND ".join(conditions)

            sql = f"""
            SELECT symbol, name, channel, channel_type, category,
                   industry, status, list_date, source, updated_at
            FROM db_hk_connect_stocks
            WHERE {where_clause}
            ORDER BY symbol ASC
            """

            cursor.execute(sql, tuple(params))
            results = cursor.fetchall()
            cursor.close()
            # 连接自动归还到池中

            return results if results else []

        except (OperationalError, DatabaseError) as e:
            logger.error(f"获取港股通名单失败: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"获取港股通名单异常: {e}", exc_info=True)
            return []

    def get_hk_connect_symbols(
        self,
        channel: Optional[str] = None,
        status: str = "active"
    ) -> List[str]:
        """获取港股通股票代码列表（用于历史数据下载）

        注意：返回的代码使用 SEHK（香港本地）后缀，
        因为港股通股票本身就是在香港联合交易所上市的。

        Args:
            channel: 交易通道筛选（None表示全部）
            status: 状态筛选（默认 active）

        Returns:
            QMT格式代码列表（如 ["00700.HK", "01810.HK"]）
        """
        stocks = self.get_hk_connect_stocks(channel, status)
        return [f"{s['symbol']}.HK" for s in stocks]

    def get_hk_connect_update_info(self) -> Optional[Dict[str, Any]]:
        """获取港股通名单更新信息

        Returns:
            更新信息字典，包含 last_updated, days_since_update, needs_update 等
        """
        if not self._ensure_connection():
            return None

        try:
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor(DictCursor)

            sql = """
            SELECT
                MAX(updated_at) as last_updated,
                COUNT(*) as total_count,
                SUM(CASE WHEN channel = 'SHHK' THEN 1 ELSE 0 END) as sh_count,
                SUM(CASE WHEN channel = 'SZHK' THEN 1 ELSE 0 END) as sz_count
            FROM db_hk_connect_stocks
            WHERE status = 'active'
            """

            cursor.execute(sql)
            result = cursor.fetchone()
            cursor.close()
            # 连接自动归还到池中

            if result and result.get("last_updated"):
                from datetime import datetime, timedelta

                last_updated = result["last_updated"]
                days_since = (datetime.now() - last_updated).days

                return {
                    "last_updated": last_updated,
                    "days_since_update": days_since,
                    "total_count": result["total_count"],
                    "sh_count": result["sh_count"] or 0,
                    "sz_count": result["sz_count"] or 0,
                    "exists": True,
                }
            else:
                # 数据不存在
                return {
                    "last_updated": None,
                    "days_since_update": 999,
                    "total_count": 0,
                    "sh_count": 0,
                    "sz_count": 0,
                    "exists": False,
                }

        except (OperationalError, DatabaseError) as e:
            logger.error(f"获取港股通更新信息失败: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"获取港股通更新信息异常: {e}", exc_info=True)
            return None

    # ========== 表创建和管理 ==========

    def create_bar_data_table(self) -> bool:
        """创建K线数据表

        Returns:
            是否创建成功
        """
        if not self._ensure_connection():
            return False

        try:
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor()

            sql = """
            CREATE TABLE IF NOT EXISTS db_bar_data (
                id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
                symbol VARCHAR(32) NOT NULL COMMENT '股票代码（不含交易所后缀）',
                exchange VARCHAR(16) NOT NULL COMMENT '交易所代码',
                `interval` VARCHAR(8) NOT NULL COMMENT 'K线周期',
                `datetime` DATETIME(3) NOT NULL COMMENT 'K线时间戳',
                open_price DECIMAL(15, 4) NOT NULL COMMENT '开盘价',
                high_price DECIMAL(15, 4) NOT NULL COMMENT '最高价',
                low_price DECIMAL(15, 4) NOT NULL COMMENT '最低价',
                close_price DECIMAL(15, 4) NOT NULL COMMENT '收盘价',
                volume DECIMAL(20, 2) NOT NULL COMMENT '成交量',
                turnover DECIMAL(25, 4) DEFAULT 0 COMMENT '成交额',
                created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
                updated_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',

                UNIQUE KEY uk_bar (symbol, exchange, `interval`, `datetime`),
                KEY idx_symbol_interval_time (symbol, `interval`, `datetime`),
                KEY idx_exchange_time (exchange, `datetime`),
                KEY idx_datetime (`datetime`),
                KEY idx_covering (symbol, exchange, `interval`, `datetime`, close_price, volume)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            COMMENT='股票K线数据表';
            """

            cursor.execute(sql)
            conn.commit()
            cursor.close()
            # 连接自动归还到池中

            logger.info("K线数据表创建成功: db_bar_data")
            return True

        except (OperationalError, DatabaseError) as e:
            logger.error(f"创建K线数据表失败: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"创建K线数据表异常: {e}", exc_info=True)
            return False

    def create_stock_info_table(self) -> bool:
        """创建股票基本信息表

        Returns:
            是否创建成功
        """
        if not self._ensure_connection():
            return False

        try:
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor()

            sql = """
            CREATE TABLE IF NOT EXISTS db_stock_info (
                id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
                symbol VARCHAR(32) NOT NULL COMMENT '股票代码',
                name VARCHAR(64) NOT NULL COMMENT '股票名称',
                exchange VARCHAR(16) NOT NULL COMMENT '交易所代码',
                industry VARCHAR(64) COMMENT '所属行业',
                area VARCHAR(32) COMMENT '所属地域',
                market VARCHAR(32) COMMENT '市场类型',
                list_date DATE COMMENT '上市日期',
                is_st TINYINT(1) DEFAULT 0 COMMENT '是否ST股票',
                status VARCHAR(16) DEFAULT 'L' COMMENT '上市状态',
                market_cap DECIMAL(20, 4) COMMENT '总市值',
                circulating_cap DECIMAL(20, 4) COMMENT '流通市值',
                created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
                updated_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',

                UNIQUE KEY uk_symbol (symbol),
                KEY idx_exchange_market (exchange, market),
                KEY idx_industry (industry),
                KEY idx_status (status),
                KEY idx_list_date (list_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            COMMENT='股票基本信息表';
            """

            cursor.execute(sql)
            conn.commit()
            cursor.close()
            # 连接自动归还到池中

            logger.info("股票信息表创建成功: db_stock_info")
            return True

        except (OperationalError, DatabaseError) as e:
            logger.error(f"创建股票信息表失败: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"创建股票信息表异常: {e}", exc_info=True)
            return False

    def create_all_tables(self) -> bool:
        """创建所有数据表

        Returns:
            是否全部创建成功
        """
        logger.info("开始创建数据库表...")

        results = {
            "db_bar_data": self.create_bar_data_table(),
            "db_stock_info": self.create_stock_info_table(),
        }

        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)

        logger.info(f"数据库表创建完成: {success_count}/{total_count} 成功")

        for table, success in results.items():
            status = "✓" if success else "✗"
            logger.info(f"  {status} {table}")

        return all(results.values())

    def drop_bar_data_table(self) -> bool:
        """删除K线数据表（谨慎使用）

        Returns:
            是否删除成功
        """
        if not self._ensure_connection():
            return False

        try:
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor()

            sql = "DROP TABLE IF EXISTS db_bar_data"
            cursor.execute(sql)
            conn.commit()
            cursor.close()
            # 连接自动归还到池中

            logger.warning("K线数据表已删除: db_bar_data")
            return True

        except (OperationalError, DatabaseError) as e:
            logger.error(f"删除K线数据表失败: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"删除K线数据表异常: {e}", exc_info=True)
            return False

    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取表信息

        Args:
            table_name: 表名

        Returns:
            表信息字典，包含行数、大小等
        """
        if not self._ensure_connection():
            return None

        try:
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor(DictCursor)

            sql = """
            SELECT
                table_name,
                table_rows,
                ROUND((data_length + index_length) / 1024 / 1024, 2) AS size_mb,
                ROUND((data_length + index_length) / 1024 / 1024 / 1024, 2) AS size_gb,
                ROUND(index_length / 1024 / 1024, 2) AS index_mb,
                engine,
                table_collation
            FROM information_schema.TABLES
            WHERE table_schema = %s AND table_name = %s
            """

            cursor.execute(sql, (self.config["database"], table_name))
            result = cursor.fetchone()
            cursor.close()
            # 连接自动归还到池中

            return result

        except (OperationalError, DatabaseError) as e:
            logger.error(f"获取表信息失败: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"获取表信息异常: {e}", exc_info=True)
            return None

    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息

        Returns:
            数据库统计信息
        """
        if not self._ensure_connection():
            return {}

        try:
            # 从连接池获取连接
            conn = self._pool.connection()
            cursor = conn.cursor()

            # 获取所有表的大小信息
            sql = """
            SELECT
                table_name,
                COALESCE(ROUND((data_length + index_length) / 1024 / 1024, 2), 0) AS size_mb
            FROM information_schema.TABLES
            WHERE table_schema = %s
                AND table_name LIKE 'db_%%'
            ORDER BY (data_length + index_length) DESC
            """

            cursor.execute(sql, (self.config["database"],))
            size_rows = cursor.fetchall()

            # 使用 COUNT(*) 获取精确行数
            tables = []
            for table_name, size_mb in size_rows:
                try:
                    count_sql = f"SELECT COUNT(*) FROM `{table_name}`"
                    cursor.execute(count_sql)
                    row_count = cursor.fetchone()[0]
                except Exception:
                    row_count = 0

                tables.append({
                    "table_name": table_name,
                    "table_rows": row_count,
                    "size_mb": size_mb,
                    "table_comment": None
                })

            cursor.close()
            # 连接自动归还到池中

            # 汇总统计
            total_rows = sum(t["table_rows"] for t in tables)
            total_size_mb = sum(t["size_mb"] for t in tables)

            return {
                "database": self.config["database"],
                "table_count": len(tables),
                "total_rows": total_rows,
                "total_size_mb": round(total_size_mb, 2),
                "total_size_gb": round(total_size_mb / 1024, 2),
                "tables": tables
            }

        except (OperationalError, DatabaseError) as e:
            logger.error(f"获取数据库统计失败：{e}")
            return {}
        except Exception as e:
            logger.error(f"获取数据库统计异常: {e}", exc_info=True)
            return {}
