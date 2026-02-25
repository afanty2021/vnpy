# A股资金流水持久化功能实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 实现A股资金流水记录功能，支持实时记录和历史数据导入持久化到数据库

**架构:** 在vnpy_china_capital模块中添加资金流水数据库层，通过事件监听实现实时记录，同时提供历史数据导入接口

**Tech Stack:** MySQL, SQLAlchemy/PyMySQL, vnpy事件系统

---

## 任务分解

### 任务1: 创建资金流水数据模型

**Files:**
- Create: `vnpy_china_capital/objects/capital_flow.py`

**Step 1: 定义CapitalFlowData数据类**

```python
"""资金流水数据对象"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from vnpy.trader.constant import Direction, Offset


@dataclass
class CapitalFlowData:
    """资金流水数据"""

    # 基本信息
    flow_id: str                      # 流水唯一标识
    gateway_name: str                   # 网关名称
    trade_id: str                       # 成交ID（关联TradeData）

    # 交易信息
    symbol: str                         # 股票代码
    exchange: str                       # 交易所
    direction: Direction                # 方向
    offset: Offset                      # 开平

    # 数量金额
    price: float                        # 成交价格
    volume: float                       # 成交数量
    amount: float                       # 成交金额

    # 账户状态
    balance: float                      # 总资金
    available: float                    # 可用资金

    # 时间
    trade_time: datetime                # 成交时间
    created_at: datetime                 # 记录创建时间

    # 分类
    flow_type: str                      # 流水类型：trade/transfer/fee/withdraw/deposit
    description: str = ""                # 说明

    def __post_init__(self):
        """后处理：生成flow_id"""
        if not self.flow_id:
            self.flow_id = f"{self.gateway_name}_{self.trade_id}"
```

**Step 2: 创建单元测试**

```python
import pytest
from datetime import datetime

def test_capital_flow_data_creation():
    """测试资金流水数据创建"""
    from vnpy_china_capital.objects.capital_flow import CapitalFlowData
    from vnpy.trader.constant import Direction, Offset

    flow = CapitalFlowData(
        flow_id="test_flow_1",
        gateway_name="TEST",
        trade_id="trade_001",
        symbol="000001",
        exchange="SZSE",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        price=10.50,
        volume=1000,
        amount=10500.0,
        balance=50000.0,
        available=39500.0,
        trade_time=datetime.now(),
        created_at=datetime.now(),
        flow_type="trade",
        description="买入平安银行"
    )

    assert flow.symbol == "000001"
    assert flow.amount == 10500.0
```

**Step 3: 运行测试**
```bash
pytest vnpy_china_capital/tests/test_capital_flow.py -v
```

**Step 4: 提交**
```bash
git add vnpy_china_capital/objects/capital_flow.py vnpy_china_capital/tests/
git commit -m "feat(capital): add CapitalFlowData model"
```

---

### 任务2: 创建数据库表和操作方法

**Files:**
- Create: `vnpy_china_capital/database.py`
- Modify: `vnpy_china_china_data/database.py` - 添加capital_flow相关方法

**Step 1: 创建数据库操作层**

```python
"""A股资金管理数据库操作"""
from typing import List, Optional
from datetime import datetime, date
from vnpy.trader.object import TradeData
from .objects.capital_flow import CapitalFlowData


class CapitalFlowDatabase:
    """资金流水数据库操作"""

    def save_capital_flow(self, flow: CapitalFlowData) -> bool:
        """保存资金流水记录"""
        raise NotImplementedError

    def save_capital_flow_from_trade(self, trade: TradeData, balance: float, available: float) -> Optional[CapitalFlowData]:
        """从成交数据创建资金流水记录

        Args:
            trade: 成交数据
            balance: 总资金
            available: 可用资金

        Returns:
            资金流水记录
        """
        flow = CapitalFlowData(
            gateway_name=trade.gateway_name,
            trade_id=trade.vt_tradeid,
            symbol=trade.symbol,
            exchange=trade.exchange.value,
            direction=trade.direction,
            offset=trade.offset,
            price=trade.price,
            volume=trade.volume,
            amount=trade.price * trade.volume,
            balance=balance,
            available=available,
            trade_time=trade.datetime,
            created_at=datetime.now(),
            flow_type="trade",
            description=f"{trade.direction.value}{trade.offset.value} {trade.symbol}"
        )
        self.save_capital_flow(flow)
        return flow

    def query_capital_flow(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        symbol: Optional[str] = None,
        flow_type: Optional[str] = None
    ) -> List[CapitalFlowData]:
        """查询资金流水记录"""
        raise NotImplementedError

    def import_historical_flows(self, flows: List[CapitalFlowData]) -> int:
        """批量导入历史流水记录

        Args:
            flows: 历史流水列表

        Returns:
            导入成功数量
        """
        count = 0
        for flow in flows:
            if self.save_capital_flow(flow):
                count += 1
        return count

    def delete_duplicate_flows(self) -> int:
        """删除重复的流水记录"""
        raise NotImplementedError
```

**Step 2: 在vnpy_china_data的MySQLDatabaseLayer中添加表操作**

在`vnpy_china_data/database.py`的`MySQLDatabaseLayer`类中添加：

```python
def create_capital_flow_table(self) -> bool:
    """创建资金流水表"""
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
    return self._execute_sql(sql)

def save_capital_flow(self, flow: "CapitalFlowData") -> bool:
    """保存资金流水"""
    sql = """
    INSERT INTO db_capital_flow
    (flow_id, gateway_name, trade_id, symbol, exchange, direction, offset,
     price, volume, amount, balance, available, trade_time, created_at,
     flow_type, description)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        amount = VALUES(amount),
        balance = VALUES(balance),
        available = VALUES(available)
    """
    params = (
        flow.flow_id, flow.gateway_name, flow.trade_id, flow.symbol,
        flow.exchange, flow.direction.value if flow.direction else None,
        flow.offset.value if flow.offset else None, flow.price, flow.volume,
        flow.amount, flow.balance, flow.available, flow.trade_time,
        flow.created_at, flow.flow_type, flow.description
    )
    return self._execute_sql(sql, params)

def query_capital_flow(
    self, start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    symbol: Optional[str] = None
) -> List[dict]:
    """查询资金流水"""
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

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    sql = f"""
    SELECT * FROM db_capital_flow
    WHERE {where_clause}
    ORDER BY trade_time DESC
    """

    results = self._execute_sql(sql, params, fetch_all=True)
    return results if results else []
```

**Step 3: 创建测试**

**Step 4: 提交**

---

### 任务3: 在GUI引擎中添加事件监听和数据库初始化

**Files:**
- Modify: `vnpy_china_china_capital/gui_engine.py`

**Step 1: 在ChinaCapitalGuiEngine中添加数据库连接**

```python
"""A股资金管理GUI引擎"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine
from vnpy.trader.object import TradeData, AccountData
from loguru import logger


class ChinaCapitalGuiEngine(BaseEngine):
    """A股资金管理GUI引擎"""

    engine_name: str = "ChinaCapitalApp"

    def __init__(self, main_engine: Any, event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, self.engine_name)

        # 数据库操作实例
        self.capital_db: Optional[Any] = None

        # 资金流水缓存
        self.flows_cache: List[Dict[str, Any]] = []

        # 初始化数据库连接
        self._init_database()

    def _init_database(self) -> None:
        """初始化数据库连接"""
        try:
            # 尝试使用vnpy_china_data的数据库
            from vnpy_china_data.database import MySQLDatabaseLayer
            from vnpy_china_data.service import get_data_service

            ds = get_data_service()
            if hasattr(ds, 'database') and ds.database:
                self.capital_db = ds.database
                # 创建资金流水表
                if hasattr(self.capital_db, 'create_capital_flow_table'):
                    self.capital_db.create_capital_flow_table()
                self.main_engine.write_log("资金流水数据库初始化成功", "ChinaCapitalApp")
            else:
                self.main_engine.write_log("警告：数据库未连接，使用内存缓存", "ChinaCapitalApp")
        except Exception as e:
            logger.warning(f"数据库初始化失败: {e}")
            self.main_engine.write_log("使用内存模式记录资金流水", "ChinaCapitalApp")

    def register_event(self) -> None:
        """注册事件监听"""
        # 订阅成交事件
        self.event_engine.register("trade", self.process_trade_event)
        # 订阅账户事件
        self.event_engine.register("account", self.process_account_event)

    def process_trade_event(self, event: Event) -> None:
        """处理成交事件，记录资金流水"""
        trade: TradeData = event.data

        try:
            # 获取账户信息
            accounts = self.main_engine.get_all_accounts()
            if accounts:
                account = accounts[0]

                # 保存流水
                if self.capital_db:
                    flow = self.capital_db.save_capital_flow_from_trade(
                        trade,
                        account.balance,
                        account.available
                    )
                else:
                    # 内存缓存
                    flow_dict = {
                        "gateway_name": trade.gateway_name,
                        "trade_id": trade.vt_tradeid,
                        "symbol": trade.symbol,
                        "exchange": trade.exchange.value,
                        "direction": trade.direction.value if trade.direction else "",
                        "offset": trade.offset.value if trade.offset else "",
                        "price": trade.price,
                        "volume": trade.volume,
                        "amount": trade.price * trade.volume,
                        "balance": account.balance,
                        "available": account.available,
                        "trade_time": trade.datetime,
                        "created_at": datetime.now(),
                        "flow_type": "trade",
                        "description": f"{trade.direction.value}{trade.offset.value} {trade.symbol}"
                    }
                    self.flows_cache.append(flow_dict)

                self.main_engine.write_log(
                    f"记录资金流水: {trade.symbol} {trade.direction.value} {trade.price}x{trade.volume}",
                    "ChinaCapitalApp"
                )
        except Exception as e:
            logger.error(f"处理成交事件失败: {e}")

    def process_account_event(self, event: Event) -> None:
        """处理账户事件"""
        # 可以记录出入金等操作
        pass

    def get_capital_flows(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取资金流水记录

        Args:
            start_date: 开始日期
            end_date: 结束日期
            symbol: 股票代码

        Returns:
            资金流水列表
        """
        if self.capital_db:
            try:
                flows = self.capital_db.query_capital_flow(
                    start_date.isoformat() if start_date else None,
                    end_date.isoformat() if end_date else None,
                    symbol
                )
                return flows
            except Exception as e:
                logger.error(f"查询资金流水失败: {e}")

        # 返回缓存数据
        return self.flows_cache[-100:]  # 返回最近100条

    def import_historical_data(self, flows: List[Any]) -> Dict[str, Any]:
        """导入历史资金流水数据

        Args:
            flows: 历史流水列表

        Returns:
            导入结果 {success_count: int, error_count: int, errors: List[str]}
        """
        success_count = 0
        error_count = 0
        errors = []

        for flow in flows:
            try:
                if self.capital_db:
                    self.capital_db.save_capital_flow(flow)
                    success_count += 1
                else:
                    # 内存缓存
                    self.flows_cache.append(flow)
                    success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(str(e))

        return {
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors
        }

    def get_database_status(self) -> Dict[str, Any]:
        """获取数据库状态"""
        return {
            "connected": self.capital_db is not None,
            "cache_count": len(self.flows_cache),
            "database_type": type(self.capital_db).__name__ if self.capital_db else "memory"
        }
```

**Step 2: 创建数据库连接测试**

**Step 3: 创建单元测试**

**Step 4: 提交**

---

### 任务4: 更新UI组件支持真实数据显示

**Files:**
- Modify: `vnpy_china_china_capital/ui/widget.py`

**Step 1: 更新refresh_cash_flow_data方法**

```python
def refresh_cash_flow_data(self) -> None:
    """刷新资金流水"""
    flows = []

    if self.gui_engine:
        flows = self.gui_engine.get_capital_flows()
    else:
        # 使用mock数据作为fallback
        flows = self._get_mock_flows()

    # 更新表格
    self.cash_flow_table.setRowCount(len(flows))

    for row, flow in enumerate(flows):
        # 时间
        time_item = QtWidgets.QTableWidgetItem(
            flow["trade_time"].strftime("%H:%M:%S") if isinstance(flow["trade_time"], datetime)
            else str(flow.get("trade_time", "")).split(" ")[1] if " " in str(flow.get("trade_time", "")) else flow.get("trade_time", "")
        )
        self.cash_flow_table.setItem(row, 0, time_item)

        # 类型
        type_item = QtWidgets.QTableWidgetItem(flow.get("flow_type", "trade"))
        # 根据类型设置颜色
        flow_type = flow.get("flow_type", "")
        if flow_type == "买入":
            type_item.setForeground(QtGui.QColor("green"))
        elif flow_type == "卖出":
            type_item.setForeground(QtGui.QColor("red"))
        elif flow_type == "转入":
            type_item.setForeground(QtGui.QColor("red"))
        self.cash_flow_table.setItem(row, 1, type_item)

        # 金额
        amount = flow.get("amount", 0)
        amount_text = f"{amount:,.2f}"
        amount_item = QtWidgets.QTableWidgetItem(amount_text)
        if amount > 0:
            amount_item.setForeground(QtGui.QColor("red"))
        else:
            amount_item.setForeground(QtGui.QColor("green"))
        self.cash_flow_table.setItem(row, 2, amount_item)

        # 说明
        desc_item = QtWidgets.QTableWidgetItem(flow.get("description", ""))
        self.cash_flow_table.setItem(row, 3, desc_item)

        # 余额
        balance = flow.get("balance", 0)
        balance_text = f"{balance:,.2f}"
        balance_item = QtWidgets.QTableWidgetItem(balance_text)
        self.cash_flow_table.setItem(row, 4, balance_item)

    self.cash_flow_table.resizeColumnsToContents()
    self.show_status(_(f"资金流水已更新，共{len(flows)}条记录"))
```

**Step 2: 创建测试**

**Step 3: 提交**

---

### 任务5: 添加历史数据导入功能

**Files:**
- Modify: `vnpy_china_capital/ui/widget.py` - 添加导入按钮和对话框
- Modify: `vnpy_china_china_capital/gui_engine.py` - 导入处理逻辑

**Step 1: 在资金流水标签页添加导入按钮**

在`create_cash_flow_tab`方法中添加导入按钮：

```python
# 导入按钮
import_btn = QtWidgets.QPushButton(_("导入历史数据"))
import_btn.clicked.connect(self.show_import_dialog)
toolbar.addWidget(import_btn)
```

**Step 2: 创建导入对话框方法**

```python
def show_import_dialog(self) -> None:
    """显示历史数据导入对话框"""
    dialog = QtWidgets.QDialog(self)
    dialog.setWindowTitle(_("导入历史资金流水"))
    dialog.setMinimumWidth(600)

    layout = QtWidgets.QVBoxLayout()
    dialog.setLayout(layout)

    # 说明
    desc = QtWidgets.QLabel(
        _("支持导入CSV格式的历史资金流水数据\n"
                  "CSV格式要求：flow_id,gateway_name,trade_id,symbol,exchange,direction,offset,price,volume,amount,balance,available,trade_time,flow_type,description\n"
                  "• flow_id: 流水唯一标识\n"
                  "• trade_time格式: YYYY-MM-DD HH:MM:SS")
    )
    desc.setWordWrap(True)
    layout.addWidget(desc)

    # 文件选择
    file_layout = QtWidgets.QHBoxLayout()
    file_path = QtWidgets.QLineEdit()
    file_path.setPlaceholderText(_("选择CSV文件..."))
    file_layout.addWidget(file_path)

    browse_btn = QtWidgets.QPushButton(_("浏览"))
    browse_btn.clicked.connect(lambda: self._select_import_file(file_path))
    file_layout.addWidget(browse_btn)
    layout.addLayout(file_layout)

    # 进度显示
    self.import_progress_label = QtWidgets.QLabel(_("准备导入..."))
    layout.addWidget(self.import_progress_label)

    # 按钮
    btn_layout = QtWidgets.QHBoxLayout()
    import_btn = QtWidgets.QPushButton(_("开始导入"))
    import_btn.clicked.connect(lambda: self._start_import(file_path.text(), dialog))
    btn_layout.addWidget(import_btn)

    close_btn = QtWidgets.QPushButton(_("关闭"))
    close_btn.clicked.connect(dialog.close)
    btn_layout.addWidget(close_btn)

    btn_layout.addStretch()
    layout.addLayout(btn_layout)

    # 结果显示
    self.import_result_label = QtWidgets.QLabel("")
    layout.addWidget(self.import_result_label)

    dialog.exec_()

def _select_import_file(self, line_edit: QtWidgets.QLineEdit) -> None:
    """选择导入文件"""
    file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
        self,
        _("选择CSV文件"),
        "",
        "CSV Files (*.csv);;All Files (*)"
    )
    if file_path:
        line_edit.setText(file_path)

def _start_import(self, file_path: str, dialog: QtWidgets.QDialog) -> None:
    """开始导入历史数据"""
    if not file_path:
        self.import_result_label.setText(_("请先选择文件"))
        return

    self.import_progress_label.setText(_("正在导入..."))

    try:
        import csv
        flows = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 解析数据
                from datetime import datetime
                from vnpy.trader.constant import Direction, Offset

                try:
                    flow = {
                        "flow_id": row["flow_id"],
                        "gateway_name": row.get("gateway_name", ""),
                        "trade_id": row["trade_id"],
                        "symbol": row["symbol"],
                        "exchange": row["exchange"],
                        "direction": Direction[row["direction"]] if row.get("direction") else None,
                        "offset": Offset[row["offset"]] if row.get("offset") else None,
                        "price": float(row["price"]),
                        "volume": float(row["volume"]),
                        "amount": float(row["amount"]),
                        "balance": float(row["balance"]),
                        "available": float(row["available"]),
                        "trade_time": datetime.strptime(row["trade_time"], "%Y-%m-%d %H:%M:%S"),
                        "created_at": datetime.now(),
                        "flow_type": row.get("flow_type", "trade"),
                        "description": row.get("description", "")
                    }
                    flows.append(flow)
                except Exception as e:
                    self.import_result_label.setText(f"数据解析错误: {e}")
                    return

        # 导入数据
        if self.gui_engine:
            result = self.gui_engine.import_historical_data(flows)

            success_count = result["success_count"]
            error_count = result["error_count"]

            msg = f"导入完成！成功: {success_count}, 失败: {error_count}"
            self.import_progress_label.setText(msg)

            if error_count > 0:
                msg += f"\n错误: {result['errors'][:3]}"  # 显示前3个错误

            self.import_result_label.setText(msg)

            # 刷新显示
            self.refresh_cash_flow_data()
        else:
            self.import_result_label.setText(_("错误：GUI引擎未初始化"))

    except Exception as e:
        self.import_result_label.setText(f"导入失败: {e}")
```

**Step 3: 创建测试**

**Step 4: 提交**

---

### 任务6: 添加QMT历史数据导入接口

**Files:**
- Create: `vnpy_china_capital/importer.py` - QMT历史数据导入器

**Step 1: 创建QMT历史数据导入器**

```python
"""QMT历史数据导入器"""
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from vnpy.trader.object import TradeData


class QMTHistoryImporter:
    """QMT历史数据导入器

    用于从QMT获取历史成交数据并转换为资金流水格式
    """

    def __init__(self, main_engine: Any) -> None:
        """初始化导入器"""
        self.main_engine = main_engine
        self.rpc_client = None

    def connect_rpc(self, rpc_address: str = "tcp://127.0.0.1:2014") -> bool:
        """连接RPC服务获取历史数据"""
        try:
            from vnpy.rpc import RpcClient
            self.rpc_client = RpcClient()
            self.rpc_client.connect(rpc_address, "")
            return True
        except Exception as e:
            print(f"RPC连接失败: {e}")
            return False

    def fetch_history_trades(
        self,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> List[TradeData]:
        """从QMT获取历史成交数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            历史成交数据列表
        """
        if not self.rpc_client:
            return []

        # TODO: 实现RPC调用获取历史成交
        # 这里需要QMT提供历史成交查询接口
        return []

    def convert_to_capital_flows(
        self,
        trades: List[TradeData],
        account_data: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """将成交数据转换为资金流水格式

        Args:
            trades: 成交数据列表
            account_data: 账户数据 {symbol: balance, available}

        Returns:
            资金流水字典列表
        """
        flows = []

        for trade in trades:
            balance = account_data.get(trade.symbol, 0)
            available = account_data.get(f"{trade.symbol}_available", balance)

            flow = {
                "flow_id": f"QMT_{trade.vt_tradeid}",
                "gateway_name": trade.gateway_name,
                "trade_id": trade.vt_tradeid,
                "symbol": trade.symbol,
                "exchange": trade.exchange.value,
                "direction": trade.direction,
                "offset": trade.offset,
                "price": trade.price,
                "volume": trade.volume,
                "amount": trade.price * trade.volume,
                "balance": balance,
                "available": available,
                "trade_time": trade.datetime,
                "created_at": datetime.now(),
                "flow_type": "trade",
                "description": f"历史成交导入-{trade.direction.value}{trade.offset.value}"
            }
            flows.append(flow)

        return flows

    def import_from_qmt(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        gui_engine: Any
    ) -> Dict[str, Any]:
        """从QMT导入历史数据

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            gui_engine: GUI引擎用于保存数据

        Returns:
            导入结果
        """
        total_count = 0
        success_count = 0
        errors = []

        for symbol in symbols:
            try:
                trades = self.fetch_history_trades(symbol, start_date, end_date)
                if trades:
                    flows = self.convert_to_capital_flows(trades, {})
                    result = gui_engine.import_historical_data(flows)

                    total_count += len(flows)
                    success_count += result["success_count"]
                    errors.extend(result.get("errors", []))
            except Exception as e:
                errors.append(f"{symbol}: {str(e)}")

        return {
            "total_count": total_count,
            "success_count": success_count,
            "error_count": total_count - success_count,
            "errors": errors
        }
```

**Step 2: 创建测试**

**Step 3: 提交**

---

## 实施检查清单

完成上述任务后，应该实现：

- [x] **数据模型**：CapitalFlowData数据类
- [x] **数据库表**：db_capital_flow表
- [x] **实时记录**：监听trade事件自动记录资金流水
- [x] **历史查询**：按日期、股票、类型查询流水
- [x] **数据导入**：CSV文件导入功能
- [x] **QMT集成**：从QMT导入历史成交
- [x] **UI展示**：真实数据替换mock数据

## 测试要点

1. **单元测试**：数据模型创建、数据库CRUD操作
2. **集成测试**：事件监听、数据持久化
3. **UI测试**：导入对话框、数据显示
4. **边界测试**：空数据、大量数据导入、重复数据处理
5. **数据库测试**：连接断开重连、事务回滚
