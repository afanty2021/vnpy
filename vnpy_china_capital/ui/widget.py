"""A股资金管理UI组件"""
from typing import Any, Optional
from datetime import datetime

from vnpy.trader.ui.qt import QtCore, QtGui, QtWidgets
from vnpy.trader.ui.widget import BaseCell, PnlCell
from vnpy.trader.object import PositionData, OrderData, AccountData
from vnpy.trader.constant import Direction, OrderType, Status
from vnpy.trader.locale import _


class ChinaCapitalWidget(QtWidgets.QWidget):
    """A股资金管理主界面"""

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

        # 账户信息标签页
        account_widget = self.create_account_tab()
        tab.addTab(account_widget, _("账户信息"))

        # 持仓列表标签页
        position_widget = self.create_position_tab()
        tab.addTab(position_widget, _("持仓列表"))

        # 委托历史标签页
        order_widget = self.create_order_tab()
        tab.addTab(order_widget, _("委托历史"))

        # 状态栏
        self.status_label = QtWidgets.QLabel(_("就绪"))
        layout.addWidget(self.status_label)

    def create_account_tab(self) -> QtWidgets.QWidget:
        """创建账户信息标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("账户信息"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 账户信息显示区
        account_group = QtWidgets.QGroupBox(_("资金概况"))
        account_layout = QtWidgets.QGridLayout()
        account_group.setLayout(account_layout)
        layout.addWidget(account_group)

        # 可用资金
        account_layout.addWidget(QtWidgets.QLabel(_("可用资金：")), 0, 0)
        self.available_label = QtWidgets.QLabel(_("0.00"))
        self.available_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold;")
        account_layout.addWidget(self.available_label, 0, 1)

        # 持仓市值
        account_layout.addWidget(QtWidgets.QLabel(_("持仓市值：")), 1, 0)
        self.position_value_label = QtWidgets.QLabel(_("0.00"))
        self.position_value_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold;")
        account_layout.addWidget(self.position_value_label, 1, 1)

        # 总资产
        account_layout.addWidget(QtWidgets.QLabel(_("总资产：")), 2, 0)
        self.balance_label = QtWidgets.QLabel(_("0.00"))
        self.balance_label.setStyleSheet("color: red; font-size: 16px; font-weight: bold;")
        account_layout.addWidget(self.balance_label, 2, 1)

        # 浮动盈亏
        account_layout.addWidget(QtWidgets.QLabel(_("浮动盈亏：")), 3, 0)
        self.unrealized_pnl_label = QtWidgets.QLabel(_("0.00"))
        account_layout.addWidget(self.unrealized_pnl_label, 3, 1)

        # 风险度
        account_layout.addWidget(QtWidgets.QLabel(_("风险度：")), 4, 0)
        self.risk_label = QtWidgets.QLabel(_("0.00%"))
        account_layout.addWidget(self.risk_label, 4, 1)

        layout.addStretch()

        # 刷新按钮
        refresh_btn = QtWidgets.QPushButton(_("刷新"))
        refresh_btn.clicked.connect(self.refresh_account_data)
        layout.addWidget(refresh_btn)

        return widget

    def create_position_tab(self) -> QtWidgets.QWidget:
        """创建持仓列表标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("持仓列表"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 工具栏
        toolbar = QtWidgets.QHBoxLayout()
        layout.addLayout(toolbar)

        refresh_btn = QtWidgets.QPushButton(_("刷新"))
        refresh_btn.clicked.connect(self.refresh_position_data)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()

        # 持仓表格
        self.position_table = QtWidgets.QTableWidget()
        self.position_table.setColumnCount(9)
        self.position_table.setHorizontalHeaderLabels([
            _("股票代码"), _("股票名称"), _("方向"),
            _("持仓"), _("可用"), _("价格"),
            _("成本"), _("盈亏"), _("盈亏%")
        ])
        self.position_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.position_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.position_table.resizeColumnsToContents()
        layout.addWidget(self.position_table)

        return widget

    def create_order_tab(self) -> QtWidgets.QWidget:
        """创建委托历史标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("委托历史"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 工具栏
        toolbar = QtWidgets.QHBoxLayout()
        layout.addLayout(toolbar)

        refresh_btn = QtWidgets.QPushButton(_("刷新"))
        refresh_btn.clicked.connect(self.refresh_order_data)
        toolbar.addWidget(refresh_btn)

        clear_btn = QtWidgets.QPushButton(_("清空"))
        clear_btn.clicked.connect(self.clear_order_data)
        toolbar.addWidget(clear_btn)

        toolbar.addStretch()

        # 委托表格
        self.order_table = QtWidgets.QTableWidget()
        self.order_table.setColumnCount(8)
        self.order_table.setHorizontalHeaderLabels([
            _("委托时间"), _("股票代码"), _("方向"),
            _("类型"), _("价格"), _("数量"),
            _("成交"), _("状态")
        ])
        self.order_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.order_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.order_table.resizeColumnsToContents()
        layout.addWidget(self.order_table)

        return widget

    def refresh_data(self) -> None:
        """刷新所有数据"""
        self.refresh_account_data()
        self.refresh_position_data()
        self.refresh_order_data()

    def refresh_account_data(self) -> None:
        """刷新账户数据"""
        # 获取账户数据（Mock数据用于演示）
        accounts = self.main_engine.get_all_accounts()

        if not accounts:
            # 使用Mock数据演示
            self._update_mock_account_data()
            return

        # 更新账户信息（使用第一个账户）
        account = accounts[0]
        self.available_label.setText(f"{account.available:,.2f}")
        self.position_value_label.setText(f"{account.position_value:,.2f}" if hasattr(account, 'position_value') else "0.00")
        self.balance_label.setText(f"{account.balance:,.2f}")

        # 计算浮动盈亏
        unrealized_pnl = getattr(account, 'unrealized_pnl', 0)
        self._update_pnl_label(self.unrealized_pnl_label, unrealized_pnl)

        # 计算风险度
        risk = (unrealized_pnl / account.balance * 100) if account.balance > 0 else 0
        self.risk_label.setText(f"{risk:.2f}%")

        self.show_status(_("账户信息已更新"))

    def _update_mock_account_data(self) -> None:
        """更新Mock账户数据"""
        mock_available = 50000.00
        mock_position_value = 150000.00
        mock_balance = mock_available + mock_position_value
        mock_pnl = 12500.00

        self.available_label.setText(f"{mock_available:,.2f}")
        self.position_value_label.setText(f"{mock_position_value:,.2f}")
        self.balance_label.setText(f"{mock_balance:,.2f}")
        self._update_pnl_label(self.unrealized_pnl_label, mock_pnl)

        risk = (mock_pnl / mock_balance * 100)
        self.risk_label.setText(f"{risk:.2f}%")

    def refresh_position_data(self) -> None:
        """刷新持仓数据"""
        positions = self.main_engine.get_all_positions()

        # 更新表格
        self.position_table.setRowCount(len(positions))

        for row, pos in enumerate(positions):
            # 股票代码
            symbol_item = QtWidgets.QTableWidgetItem(pos.vt_symbol)
            self.position_table.setItem(row, 0, symbol_item)

            # 股票名称（从网关获取）
            name = getattr(pos, 'symbol', pos.vt_symbol.split('.')[0])
            name_item = QtWidgets.QTableWidgetItem(name)
            self.position_table.setItem(row, 1, name_item)

            # 方向
            direction = pos.direction
            direction_item = QtWidgets.QTableWidgetItem(direction.value)
            if direction == Direction.SHORT:
                direction_item.setForeground(QtGui.QColor("green"))
            else:
                direction_item.setForeground(QtGui.QColor("red"))
            self.position_table.setItem(row, 2, direction_item)

            # 持仓数量
            volume_item = QtWidgets.QTableWidgetItem(str(pos.volume))
            self.position_table.setItem(row, 3, volume_item)

            # 可用数量
            available_item = QtWidgets.QTableWidgetItem(str(pos.volume - pos.frozen))
            self.position_table.setItem(row, 4, available_item)

            # 当前价格
            price_item = QtWidgets.QTableWidgetItem(f"{pos.price:.2f}")
            self.position_table.setItem(row, 5, price_item)

            # 成本价
            cost_item = QtWidgets.QTableWidgetItem(f"{pos.price:.2f}")
            self.position_table.setItem(row, 6, cost_item)

            # 盈亏
            pnl = (pos.price - pos.price) * pos.volume
            pnl_item = PnlCell(f"{pnl:.2f}", pnl)
            self.position_table.setItem(row, 7, pnl_item)

            # 盈亏百分比
            pnl_pct = ((pos.price - pos.price) / pos.price * 100) if pos.price > 0 else 0
            pnl_pct_item = PnlCell(f"{pnl_pct:.2f}%", pnl_pct)
            self.position_table.setItem(row, 8, pnl_pct_item)

        self.position_table.resizeColumnsToContents()
        self.show_status(_(f"持仓列表已更新，共{len(positions)}条记录"))

    def refresh_order_data(self) -> None:
        """刷新委托数据"""
        orders = self.main_engine.get_all_orders()

        # 过滤活跃订单
        active_orders = [o for o in orders if o.status in [Status.SUBMITTING, Status.NOTTRADED, Status.PARTTRADED]]

        # 更新表格
        self.order_table.setRowCount(len(active_orders))

        for row, order in enumerate(active_orders):
            # 委托时间
            time_item = QtWidgets.QTableWidgetItem(order.time.strftime("%H:%M:%S"))
            self.order_table.setItem(row, 0, time_item)

            # 股票代码
            symbol_item = QtWidgets.QTableWidgetItem(order.vt_symbol)
            self.order_table.setItem(row, 1, symbol_item)

            # 方向
            direction = order.direction
            direction_item = QtWidgets.QTableWidgetItem(direction.value)
            if direction == Direction.SHORT:
                direction_item.setForeground(QtGui.QColor("green"))
            else:
                direction_item.setForeground(QtGui.QColor("red"))
            self.order_table.setItem(row, 2, direction_item)

            # 类型
            type_item = QtWidgets.QTableWidgetItem(order.type.value)
            self.order_table.setItem(row, 3, type_item)

            # 价格
            price_item = QtWidgets.QTableWidgetItem(f"{order.price:.2f}")
            self.order_table.setItem(row, 4, price_item)

            # 数量
            volume_item = QtWidgets.QTableWidgetItem(str(order.volume))
            self.order_table.setItem(row, 5, volume_item)

            # 成交数量
            traded_item = QtWidgets.QTableWidgetItem(str(order.traded))
            self.order_table.setItem(row, 6, traded_item)

            # 状态
            status = order.status
            status_item = QtWidgets.QTableWidgetItem(status.value)
            self.order_table.setItem(row, 7, status_item)

        self.order_table.resizeColumnsToContents()
        self.show_status(_(f"委托列表已更新，共{len(active_orders)}条记录"))

    def clear_order_data(self) -> None:
        """清空委托列表"""
        self.order_table.setRowCount(0)
        self.show_status(_("委托列表已清空"))

    def _update_pnl_label(self, label: QtWidgets.QLabel, pnl: float) -> None:
        """更新盈亏标签颜色"""
        label.setText(f"{pnl:+,.2f}")
        if pnl > 0:
            label.setStyleSheet("color: red; font-size: 14px; font-weight: bold;")
        elif pnl < 0:
            label.setStyleSheet("color: green; font-size: 14px; font-weight: bold;")
        else:
            label.setStyleSheet("color: black; font-size: 14px; font-weight: bold;")

    def show_status(self, msg: str) -> None:
        """显示状态信息"""
        self.status_label.setText(msg)


__all__ = ["ChinaCapitalWidget"]
