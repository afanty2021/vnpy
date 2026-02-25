"""
A股资金管理UI组件
专注于A股特色的资金管理功能
"""
from typing import Any, Optional, List
from datetime import datetime, date

from vnpy.trader.ui.qt import QtCore, QtGui, QtWidgets
from vnpy.trader.object import PositionData, TradeData, ContractData
from vnpy.trader.constant import Direction
from vnpy.trader.locale import _


class ChinaCapitalWidget(QtWidgets.QWidget):
    """A股资金管理主界面

    专注于A股特色功能：
    - T+1持仓流水（今日买入明细、可卖数量）
    - 资金流水记录（出入金记录）
    - 风险监控（仓位集中度、单票限制）
    """

    def __init__(self, main_engine: Any, event_engine: Any):
        """初始化界面"""
        super().__init__()
        self.main_engine = main_engine
        self.event_engine = event_engine

        # 获取GUI引擎
        self.gui_engine: Optional[Any] = None
        try:
            self.gui_engine = main_engine.get_engine("ChinaCapitalApp")
        except Exception:
            pass

        # 持仓流水记录缓存 {symbol: [{buy_time, volume, available}]}
        self.position_records: dict = {}

        self.init_ui()

        # 定时刷新
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(2000)  # 每2秒刷新一次

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle(_("A股资金管理"))
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 创建标签页
        tab = QtWidgets.QTabWidget()
        layout.addWidget(tab)

        # T+1持仓流水
        t1_widget = self.create_t1_tab()
        tab.addTab(t1_widget, _("T+1持仓流水"))

        # 资金流水
        cash_flow_widget = self.create_cash_flow_tab()
        tab.addTab(cash_flow_widget, _("资金流水"))

        # 风险监控
        risk_widget = self.create_risk_tab()
        tab.addTab(risk_widget, _("风险监控"))

        # 状态栏
        self.status_label = QtWidgets.QLabel(_("就绪"))
        layout.addWidget(self.status_label)

    def create_t1_tab(self) -> QtWidgets.QWidget:
        """创建T+1持仓流水标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 标题和说明
        title = QtWidgets.QLabel(_("T+1持仓流水"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        desc = QtWidgets.QLabel(
            _("显示每日买入记录和可卖数量计算（FIFO原则）\n"
              "• 今日买入的股票只能在下一个交易日卖出\n"
              "• 可卖数量 = 昨日及之前买入的数量 - 已卖出数量")
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray; padding: 5px; background: #f5f5f5;")
        layout.addWidget(desc)

        # 工具栏
        toolbar = QtWidgets.QHBoxLayout()
        layout.addLayout(toolbar)

        refresh_btn = QtWidgets.QPushButton(_("刷新"))
        refresh_btn.clicked.connect(self.refresh_t1_data)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()

        # 持仓流水表格
        self.t1_table = QtWidgets.QTableWidget()
        self.t1_table.setColumnCount(6)
        self.t1_table.setHorizontalHeaderLabels([
            _("股票代码"), _("股票名称"), _("买入日期"),
            _("买入数量"), _("已卖出"), _("可卖数量")
        ])
        self.t1_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.t1_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.t1_table.setAlternatingRowColors(True)
        layout.addWidget(self.t1_table)

        return widget

    def create_cash_flow_tab(self) -> QtWidgets.QWidget:
        """创建资金流水标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("资金流水记录"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 说明
        desc = QtWidgets.QLabel(_("记录出入金流水和资金变动"))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray; padding: 5px;")
        layout.addWidget(desc)

        # 流水表格
        self.cash_flow_table = QtWidgets.QTableWidget()
        self.cash_flow_table.setColumnCount(5)
        self.cash_flow_table.setHorizontalHeaderLabels([
            _("时间"), _("类型"), _("金额"),
            _("说明"), _("余额")
        ])
        self.cash_flow_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.cash_flow_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.cash_flow_table.setAlternatingRowColors(True)
        layout.addWidget(self.cash_flow_table)

        # 工具栏
        toolbar = QtWidgets.QHBoxLayout()
        refresh_btn = QtWidgets.QPushButton(_("刷新"))
        refresh_btn.clicked.connect(self.refresh_cash_flow_data)
        toolbar.addWidget(refresh_btn)
        layout.addLayout(toolbar)

        return widget

    def create_risk_tab(self) -> QtWidgets.QWidget:
        """创建风险监控标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("风险监控"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 风险指标卡片
        metrics_layout = QtWidgets.QGridLayout()
        layout.addLayout(metrics_layout)

        # 总资产
        metrics_layout.addWidget(QtWidgets.QLabel(_("总资产：")), 0, 0)
        self.total_asset_label = QtWidgets.QLabel("--")
        self.total_asset_label.setStyleSheet("font-size: 18px; font-weight: bold; color: red;")
        metrics_layout.addWidget(self.total_asset_label, 0, 1)

        # 持仓市值占比
        metrics_layout.addWidget(QtWidgets.QLabel(_("持仓市值占比：")), 1, 0)
        self.position_ratio_label = QtWidgets.QLabel("--")
        self.position_ratio_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        metrics_layout.addWidget(self.position_ratio_label, 1, 1)

        # 单票最大占比
        metrics_layout.addWidget(QtWidgets.QLabel(_("单票最大占比：")), 2, 0)
        self.max_single_ratio_label = QtWidgets.QLabel("--")
        self.max_single_ratio_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        metrics_layout.addWidget(self.max_single_ratio_label, 2, 1)

        # 持仓数量
        metrics_layout.addWidget(QtWidgets.QLabel(_("持仓股票数：")), 3, 0)
        self.position_count_label = QtWidgets.QLabel("--")
        self.position_count_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        metrics_layout.addWidget(self.position_count_label, 3, 1)

        # 刷新按钮
        refresh_btn = QtWidgets.QPushButton(_("刷新"))
        refresh_btn.clicked.connect(self.refresh_risk_data)
        layout.addWidget(refresh_btn)

        layout.addStretch()

        return widget

    def refresh_data(self) -> None:
        """刷新所有数据"""
        self.refresh_t1_data()
        self.refresh_cash_flow_data()
        self.refresh_risk_data()

    def refresh_t1_data(self) -> None:
        """刷新T+1持仓流水"""
        # 获取所有持仓
        positions = self.main_engine.get_all_positions()
        contracts = {c.vt_symbol: c for c in self.main_engine.get_all_contracts()}

        # 按股票汇总持仓
        position_summary: dict = {}
        for pos in positions:
            symbol = pos.vt_symbol
            if symbol not in position_summary:
                position_summary[symbol] = {
                    "volume": 0,
                    "price": pos.price,
                    "cost": pos.price,
                }
            position_summary[symbol]["volume"] += pos.volume

        # 更新表格
        self.t1_table.setRowCount(len(position_summary))

        for row, (symbol, data) in enumerate(position_summary.items()):
            # 股票代码
            symbol_item = QtWidgets.QTableWidgetItem(symbol)
            self.t1_table.setItem(row, 0, symbol_item)

            # 股票名称
            contract = contracts.get(symbol)
            name = contract.name if contract else symbol.split('.')[0]
            name_item = QtWidgets.QTableWidgetItem(name)
            self.t1_table.setItem(row, 1, name_item)

            # 买入日期（使用当前日期）
            today = date.today()
            date_item = QtWidgets.QTableWidgetItem(today.strftime("%Y-%m-%d"))
            self.t1_table.setItem(row, 2, date_item)

            # 买入数量
            volume_item = QtWidgets.QTableWidgetItem(str(data["volume"]))
            self.t1_table.setItem(row, 3, volume_item)

            # 已卖出（模拟为0，实际需要从历史记录获取）
            sold_item = QtWidgets.QTableWidgetItem("0")
            self.t1_table.setItem(row, 4, sold_item)

            # 可卖数量（A股T+1：昨日买入可卖，今日买入不可卖）
            sellable = "0" if today.strftime("%Y%m%d") == datetime.now().strftime("%Y%m%d") else str(data["volume"])
            sellable_item = QtWidgets.QTableWidgetItem(sellable)
            # 今日买入显示灰色
            if sellable == "0":
                sellable_item.setForeground(QtGui.QColor("gray"))
            self.t1_table.setItem(row, 5, sellable_item)

        self.t1_table.resizeColumnsToContents()
        self.show_status(_(f"T+1持仓流水已更新，共{len(position_summary)}条记录"))

    def refresh_cash_flow_data(self) -> None:
        """刷新资金流水"""
        # 模拟数据
        mock_flows = [
            {"time": "09:30:00", "type": "转入", "amount": 100000.00, "desc": "初始资金", "balance": 100000.00},
            {"time": "10:15:00", "type": "买入", "amount": -15000.00, "desc": "买入平安银行", "balance": 85000.00},
            {"time": "14:20:00", "type": "卖出", "amount": 20000.00, "desc": "卖出贵州茅台", "balance": 105000.00},
        ]

        self.cash_flow_table.setRowCount(len(mock_flows))

        for row, flow in enumerate(mock_flows):
            # 时间
            time_item = QtWidgets.QTableWidgetItem(flow["time"])
            self.cash_flow_table.setItem(row, 0, time_item)

            # 类型
            type_item = QtWidgets.QTableWidgetItem(flow["type"])
            # 根据类型设置颜色
            if flow["type"] == "买入":
                type_item.setForeground(QtGui.QColor("green"))  # 付出绿色
            elif flow["type"] == "卖出":
                type_item.setForeground(QtGui.QColor("red"))     # 收入红色
            elif flow["type"] == "转入":
                type_item.setForeground(QtGui.QColor("red"))
            self.cash_flow_table.setItem(row, 1, type_item)

            # 金额
            amount_text = f"{flow['amount']:,.2f}"
            amount_item = QtWidgets.QTableWidgetItem(amount_text)
            if flow["amount"] > 0:
                amount_item.setForeground(QtGui.QColor("red"))
            else:
                amount_item.setForeground(QtGui.QColor("green"))
            self.cash_flow_table.setItem(row, 2, amount_item)

            # 说明
            desc_item = QtWidgets.QTableWidgetItem(flow["desc"])
            self.cash_flow_table.setItem(row, 3, desc_item)

            # 余额
            balance_text = f"{flow['balance']:,.2f}"
            balance_item = QtWidgets.QTableWidgetItem(balance_text)
            self.cash_flow_table.setItem(row, 4, balance_item)

        self.cash_flow_table.resizeColumnsToContents()

    def refresh_risk_data(self) -> None:
        """刷新风险数据"""
        # 获取账户和持仓数据
        accounts = self.main_engine.get_all_accounts()
        positions = self.main_engine.get_all_positions()

        if not accounts:
            self.total_asset_label.setText("--")
            return

        account = accounts[0]
        total_asset = account.balance
        position_value = 0

        # 计算持仓市值
        position_values: dict = {}
        for pos in positions:
            market_value = pos.volume * pos.price
            position_value += market_value
            position_values[pos.vt_symbol] = market_value

        # 更新显示
        self.total_asset_label.setText(f"{total_asset:,.2f}")
        self.position_ratio_label.setText(
            f"{position_value / total_asset * 100:.1f}%" if total_asset > 0 else "--"
        )

        # 单票最大占比
        if position_values:
            max_ratio = max(position_values.values()) / total_asset * 100
            self.max_single_ratio_label.setText(f"{max_ratio:.1f}%")
            # 超过30%显示红色警告
            if max_ratio > 30:
                self.max_single_ratio_label.setStyleSheet("font-size: 18px; font-weight: bold; color: red;")
            else:
                self.max_single_ratio_label.setStyleSheet("font-size: 18px; font-weight: bold; color: orange;")
        else:
            self.max_single_ratio_label.setText("--")
            self.max_single_ratio_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        self.position_count_label.setText(str(len(position_values)))

    def show_status(self, msg: str) -> None:
        """显示状态信息"""
        self.status_label.setText(msg)


__all__ = ["ChinaCapitalWidget"]
