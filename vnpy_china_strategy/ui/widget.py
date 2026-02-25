"""
A股策略UI组件
提供策略管理和监控界面
"""

from typing import Dict, Any, Optional, List
from collections.abc import Callable
from datetime import date, datetime

from vnpy.trader.ui.qt import QtCore, QtGui, QtWidgets
from vnpy.trader.ui.widget import BaseMonitor, BaseCell
from vnpy.trader.object import TickData, BarData, OrderData, TradeData, ContractData
from vnpy.trader.constant import Direction, Status, Exchange
from vnpy.trader.utility import get_icon_path, TRADER_DIR
from vnpy.trader.locale import _


class ChinaStrategyWidget(QtWidgets.QWidget):
    """A股策略主界面"""

    def __init__(self, main_engine: Any, event_engine: Any) -> None:
        """初始化界面"""
        super().__init__()

        self.main_engine = main_engine
        self.event_engine = event_engine

        # 获取GUI引擎
        self.gui_engine: Optional[Any] = None
        try:
            self.gui_engine = main_engine.get_engine("ChinaStrategyApp")
        except Exception:
            pass

        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle(_("A股策略管理"))
        self.setMinimumSize(800, 600)

        # 创建主布局
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 创建标签页
        tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(tab_widget)

        # 策略列表页
        strategy_list_widget = StrategyListWidget(self.main_engine, self.event_engine, self.gui_engine)
        tab_widget.addTab(strategy_list_widget, _("策略列表"))

        # 龙虎榜策略页
        dragon_tiger_widget = DragonTigerStrategyWidget(self.main_engine, self.event_engine, self.gui_engine)
        tab_widget.addTab(dragon_tiger_widget, _("龙虎榜策略"))

        # 北向资金策略页
        northbound_widget = NorthboundStrategyWidget(self.main_engine, self.event_engine, self.gui_engine)
        tab_widget.addTab(northbound_widget, _("北向资金"))

        # 板块轮动策略页
        sector_widget = SectorRotationWidget(self.main_engine, self.event_engine, self.gui_engine)
        tab_widget.addTab(sector_widget, _("板块轮动"))

        # 事件驱动策略页
        event_widget = EventDrivenWidget(self.main_engine, self.event_engine, self.gui_engine)
        tab_widget.addTab(event_widget, _("事件驱动"))

        # 可转债策略页
        convertible_widget = ConvertibleWidget(self.main_engine, self.event_engine, self.gui_engine)
        tab_widget.addTab(convertible_widget, _("可转债"))


class StrategyListWidget(BaseMonitor):
    """策略列表监控组件"""

    event_type: str = ""
    data_key: str = ""
    sorting: bool = True

    def __init__(self, main_engine: Any, event_engine: Any, gui_engine: Optional[Any] = None) -> None:
        """初始化"""
        super().__init__(main_engine, event_engine)

        # 获取GUI引擎
        self.gui_engine = gui_engine

        # 创建按钮
        self.create_buttons()

        # 启动定时刷新
        self.start_timer()

    def init_table(self) -> None:
        """初始化表格"""
        # 定义表格列
        self.headers = [
            _("策略名称"),
            _("合约代码"),
            _("策略类型"),
            _("状态"),
            _("仓位"),
            _("盈亏"),
            _("创建时间"),
        ]

        # 设置列宽
        self.width_ratios = [2, 2, 2, 1, 1, 1, 2]

    def create_buttons(self) -> None:
        """创建控制按钮"""
        # 添加工具栏
        toolbar = QtWidgets.QHBoxLayout()

        refresh_btn = QtWidgets.QPushButton(_("刷新"))
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)

        start_btn = QtWidgets.QPushButton(_("启动策略"))
        start_btn.clicked.connect(self.start_selected_strategy)
        toolbar.addWidget(start_btn)

        stop_btn = QtWidgets.QPushButton(_("停止策略"))
        stop_btn.clicked.connect(self.stop_selected_strategy)
        toolbar.addWidget(stop_btn)

        toolbar.addStretch()

        # 添加到布局
        self.layout().insertLayout(0, toolbar)

    def refresh_data(self) -> None:
        """刷新数据"""
        if not self.gui_engine:
            return

        try:
            # 从GUI引擎获取所有策略
            strategies = self.gui_engine.get_all_strategies()

            # 清空表格
            self.setRowCount(0)

            # 填充数据
            for row, (strategy_name, strategy) in enumerate(strategies.items()):
                self.insertRow(row)
                self.setItem(row, 0, QtWidgets.QTableWidgetItem(strategy_name))

                if hasattr(strategy, "vt_symbol"):
                    self.setItem(row, 1, QtWidgets.QTableWidgetItem(strategy.vt_symbol))

                if hasattr(strategy, "strategy_class"):
                    self.setItem(row, 2, QtWidgets.QTableWidgetItem(strategy.strategy_class.__name__))

                if hasattr(strategy, "active"):
                    status = _("运行中") if strategy.active else _("已停止")
                    item = QtWidgets.QTableWidgetItem(status)
                    # 设置状态颜色
                    if strategy.active:
                        item.setForeground(QtGui.QColor("green"))
                    else:
                        item.setForeground(QtGui.QColor("red"))
                    self.setItem(row, 3, item)

                if hasattr(strategy, "pos"):
                    self.setItem(row, 4, QtWidgets.QTableWidgetItem(str(strategy.pos)))

                if hasattr(strategy, "trading_pnl"):
                    self.setItem(row, 5, QtWidgets.QTableWidgetItem(f"{strategy.trading_pnl:.2f}"))

                if hasattr(strategy, "create_time"):
                    self.setItem(row, 6, QtWidgets.QTableWidgetItem(str(strategy.create_time)))
        except Exception as e:
            self.write_log(f"刷新策略列表失败：{e}")

    def start_selected_strategy(self) -> None:
        """启动选中的策略"""
        current_row = self.currentRow()
        if current_row < 0:
            QtWidgets.QMessageBox.warning(self, _("警告"), _("请先选择一个策略"))
            return

        strategy_name = self.item(current_row, 0).text()
        if not self.gui_engine:
            return

        try:
            result = self.gui_engine.start_strategy(strategy_name)
            if result:
                QtWidgets.QMessageBox.information(self, _("成功"), f"策略 {strategy_name} 启动成功")
                self.refresh_data()
            else:
                QtWidgets.QMessageBox.warning(self, _("失败"), f"策略 {strategy_name} 启动失败")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, _("错误"), f"启动策略失败：{e}")

    def stop_selected_strategy(self) -> None:
        """停止选中的策略"""
        current_row = self.currentRow()
        if current_row < 0:
            QtWidgets.QMessageBox.warning(self, _("警告"), _("请先选择一个策略"))
            return

        strategy_name = self.item(current_row, 0).text()
        if not self.gui_engine:
            return

        try:
            result = self.gui_engine.stop_strategy(strategy_name)
            if result:
                QtWidgets.QMessageBox.information(self, _("成功"), f"策略 {strategy_name} 停止成功")
                self.refresh_data()
            else:
                QtWidgets.QMessageBox.warning(self, _("失败"), f"策略 {strategy_name} 停止失败")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, _("错误"), f"停止策略失败：{e}")

    def start_timer(self) -> None:
        """启动定时刷新"""
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(5000)  # 每5秒刷新一次

    def write_log(self, msg: str) -> None:
        """写日志"""
        print(f"[StrategyList] {msg}")


class DragonTigerStrategyWidget(QtWidgets.QWidget):
    """龙虎榜策略界面"""

    def __init__(self, main_engine: Any, event_engine: Any, gui_engine: Optional[Any] = None) -> None:
        """初始化"""
        super().__init__()
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.gui_engine = gui_engine
        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("龙虎榜策略配置"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 策略说明
        desc = QtWidgets.QLabel(
            _("龙虎榜策略追踪机构席位和游资动向，提供以下策略：\n"
              "• 机构席位追踪：追踪机构席位买卖行为\n"
              "• 游资追踪：追踪游资席位动向\n"
              "• 跟随策略：跟随龙虎榜资金流向")
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 查询控制区
        query_group = QtWidgets.QGroupBox(_("数据查询"))
        query_layout = QtWidgets.QHBoxLayout()
        query_group.setLayout(query_layout)
        layout.addWidget(query_group)

        query_layout.addWidget(QtWidgets.QLabel(_("查询日期：")))
        self.date_edit = QtWidgets.QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QtCore.QDate.currentDate())
        query_layout.addWidget(self.date_edit)

        query_btn = QtWidgets.QPushButton(_("查询"))
        query_btn.clicked.connect(self.query_dragon_tiger)
        query_layout.addWidget(query_btn)

        refresh_btn = QtWidgets.QPushButton(_("刷新"))
        refresh_btn.clicked.connect(self.refresh_data)
        query_layout.addWidget(refresh_btn)

        # 状态标签
        self.status_label = QtWidgets.QLabel(_("就绪"))
        self.status_label.setStyleSheet("padding: 5px; background: #f0f0f0;")
        layout.addWidget(self.status_label)

        # 数据表格
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            _("代码"), _("名称"), _("交易日期"), _("收盘价"),
            _("涨跌幅(%)"), _("换手率(%)"), _("机构净买入"), _("上榜原因")
        ])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def query_dragon_tiger(self) -> None:
        """查询龙虎榜数据"""
        if not self.gui_engine:
            self.show_status(_("错误：GUI引擎未初始化"))
            return

        qdate = self.date_edit.date()
        trade_date = qdate.toPython()

        self.show_status(_("正在查询龙虎榜数据..."))

        try:
            data = self.gui_engine.query_dragon_tiger(trade_date)
            self.update_table(data)

            if data:
                self.show_status(_(f"查询完成，共{len(data)}条记录"))
            else:
                self.show_status(_("未查询到数据"))
        except Exception as e:
            self.show_status(_(f"查询失败：{e}"))

    def refresh_data(self) -> None:
        """刷新数据（使用当前日期）"""
        self.date_edit.setDate(QtCore.QDate.currentDate())
        self.query_dragon_tiger()

    def update_table(self, data: List[Dict[str, Any]]) -> None:
        """更新表格数据"""
        self.table.setRowCount(len(data))

        for row, item in enumerate(data):
            # 代码
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(item.get("symbol", "")))

            # 名称
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(item.get("name", "")))

            # 交易日期
            trade_date = item.get("trade_date")
            if trade_date:
                date_str = trade_date.strftime("%Y-%m-%d") if isinstance(trade_date, date) else str(trade_date)
                self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(date_str))

            # 收盘价
            close_price = item.get("close_price", 0)
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(f"{close_price:.2f}"))

            # 涨跌幅（带颜色）
            change_pct = item.get("change_pct", 0)
            change_item = QtWidgets.QTableWidgetItem(f"{change_pct:+.2f}")
            if change_pct > 0:
                change_item.setForeground(QtGui.QColor("red"))
            elif change_pct < 0:
                change_item.setForeground(QtGui.QColor("green"))
            self.table.setItem(row, 4, change_item)

            # 换手率
            turnover = item.get("turnover_rate", 0)
            self.table.setItem(row, 5, QtWidgets.QTableWidgetItem(f"{turnover:.2f}"))

            # 机构净买入（带颜色）
            inst_buy = item.get("institution_net_buy", 0)
            inst_item = QtWidgets.QTableWidgetItem(f"{inst_buy:.0f}")
            if inst_buy > 0:
                inst_item.setForeground(QtGui.QColor("red"))
            elif inst_buy < 0:
                inst_item.setForeground(QtGui.QColor("green"))
            self.table.setItem(row, 6, inst_item)

            # 上榜原因
            self.table.setItem(row, 7, QtWidgets.QTableWidgetItem(item.get("reason", "")))

        # 调整列宽
        self.table.resizeColumnsToContents()

    def show_status(self, msg: str) -> None:
        """显示状态信息"""
        self.status_label.setText(msg)


class NorthboundStrategyWidget(QtWidgets.QWidget):
    """北向资金策略界面"""

    def __init__(self, main_engine: Any, event_engine: Any, gui_engine: Optional[Any] = None) -> None:
        """初始化"""
        super().__init__()
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.gui_engine = gui_engine
        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("北向资金策略配置"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 策略说明
        desc = QtWidgets.QLabel(
            _("北向资金策略追踪外资动向，提供以下策略：\n"
              "• 资金流向：追踪北向资金净流入流出\n"
              "• 持股变化：追踪北向资金持股变化\n"
              "• 板块偏好：分析北向资金板块偏好"))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 查询控制区
        query_group = QtWidgets.QGroupBox(_("数据查询"))
        query_layout = QtWidgets.QHBoxLayout()
        query_group.setLayout(query_layout)
        layout.addWidget(query_group)

        query_layout.addWidget(QtWidgets.QLabel(_("查询日期：")))
        self.date_edit = QtWidgets.QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QtCore.QDate.currentDate())
        query_layout.addWidget(self.date_edit)

        query_flow_btn = QtWidgets.QPushButton(_("资金流向"))
        query_flow_btn.clicked.connect(self.query_flow)
        query_layout.addWidget(query_flow_btn)

        query_sector_btn = QtWidgets.QPushButton(_("板块偏好"))
        query_sector_btn.clicked.connect(self.query_sector)
        query_layout.addWidget(query_sector_btn)

        refresh_btn = QtWidgets.QPushButton(_("刷新"))
        refresh_btn.clicked.connect(self.refresh_data)
        query_layout.addWidget(refresh_btn)

        # 状态标签
        self.status_label = QtWidgets.QLabel(_("就绪"))
        self.status_label.setStyleSheet("padding: 5px; background: #f0f0f0;")
        layout.addWidget(self.status_label)

        # 数据显示区（使用标签页）
        self.tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(self.tab_widget)

        # 资金流向页
        self.flow_table = QtWidgets.QTableWidget()
        self.flow_table.setColumnCount(5)
        self.flow_table.setHorizontalHeaderLabels([
            _("市场"), _("交易日期"), _("买入金额"), _("卖出金额"), _("净流入")
        ])
        self.flow_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.flow_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tab_widget.addTab(self.flow_table, _("资金流向"))

        # 板块偏好页
        self.sector_table = QtWidgets.QTableWidget()
        self.sector_table.setColumnCount(3)
        self.sector_table.setHorizontalHeaderLabels([
            _("板块"), _("净流入"), _("占比(%)")
        ])
        self.sector_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.sector_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tab_widget.addTab(self.sector_table, _("板块偏好"))

    def query_flow(self) -> None:
        """查询资金流向"""
        if not self.gui_engine:
            self.show_status(_("错误：GUI引擎未初始化"))
            return

        qdate = self.date_edit.date()
        trade_date = qdate.toPython()

        self.show_status(_("正在查询资金流向..."))

        try:
            data = self.gui_engine.query_northbound_flow(trade_date)
            self.update_flow_table(data)

            if data:
                net_inflow = data.get("net_inflow", 0) / 100000000
                self.show_status(_(f"查询完成，净流入：{net_inflow:.2f}亿元"))
            else:
                self.show_status(_("未查询到数据"))
        except Exception as e:
            self.show_status(_(f"查询失败：{e}"))

    def query_sector(self) -> None:
        """查询板块偏好"""
        if not self.gui_engine:
            self.show_status(_("错误：GUI引擎未初始化"))
            return

        qdate = self.date_edit.date()
        trade_date = qdate.toPython()

        self.show_status(_("正在查询板块偏好..."))

        try:
            data = self.gui_engine.query_sector_preference(trade_date)
            self.update_sector_table(data)

            if data:
                self.show_status(_(f"查询完成，共{len(data)}个板块"))
            else:
                self.show_status(_("未查询到数据"))
        except Exception as e:
            self.show_status(_(f"查询失败：{e}"))

    def refresh_data(self) -> None:
        """刷新数据"""
        self.date_edit.setDate(QtCore.QDate.currentDate())
        self.query_flow()

    def update_flow_table(self, data: Optional[Dict[str, Any]]) -> None:
        """更新资金流向表格"""
        if not data:
            self.flow_table.setRowCount(0)
            return

        # 创建三行数据：沪股通、深股通、合计
        rows_data = [
            {
                "market": _("沪股通"),
                "trade_date": data.get("trade_date", ""),
                "buy_volume": data.get("sh_buy_volume", 0) / 100000000,
                "sell_volume": data.get("sh_sell_volume", 0) / 100000000,
                "net_inflow": data.get("sh_net_inflow", 0) / 100000000,
            },
            {
                "market": _("深股通"),
                "trade_date": data.get("trade_date", ""),
                "buy_volume": data.get("sz_buy_volume", 0) / 100000000,
                "sell_volume": data.get("sz_sell_volume", 0) / 100000000,
                "net_inflow": data.get("sz_net_inflow", 0) / 100000000,
            },
            {
                "market": _("合计"),
                "trade_date": data.get("trade_date", ""),
                "buy_volume": (data.get("sh_buy_volume", 0) + data.get("sz_buy_volume", 0)) / 100000000,
                "sell_volume": (data.get("sh_sell_volume", 0) + data.get("sz_sell_volume", 0)) / 100000000,
                "net_inflow": data.get("total_net_inflow", 0) / 100000000,
            },
        ]

        self.flow_table.setRowCount(len(rows_data))

        for row, row_data in enumerate(rows_data):
            # 市场
            self.flow_table.setItem(row, 0, QtWidgets.QTableWidgetItem(row_data["market"]))

            # 交易日期
            trade_date = row_data["trade_date"]
            if trade_date:
                date_str = trade_date.strftime("%Y-%m-%d") if isinstance(trade_date, date) else str(trade_date)
                self.flow_table.setItem(row, 1, QtWidgets.QTableWidgetItem(date_str))

            # 买入金额
            buy = row_data["buy_volume"]
            self.flow_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{buy:.2f}"))

            # 卖出金额
            sell = row_data["sell_volume"]
            self.flow_table.setItem(row, 3, QtWidgets.QTableWidgetItem(f"{sell:.2f}"))

            # 净流入（带颜色）
            net = row_data["net_inflow"]
            net_item = QtWidgets.QTableWidgetItem(f"{net:+.2f}")
            if net > 0:
                net_item.setForeground(QtGui.QColor("red"))
            elif net < 0:
                net_item.setForeground(QtGui.QColor("green"))
            self.flow_table.setItem(row, 4, net_item)

            # 高亮合计行
            if row == 2:
                for col in range(self.flow_table.columnCount()):
                    item = self.flow_table.item(row, col)
                    if item:
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)

        self.flow_table.resizeColumnsToContents()

    def update_sector_table(self, data: List[Dict[str, Any]]) -> None:
        """更新板块偏好表格"""
        self.sector_table.setRowCount(len(data))

        for row, item in enumerate(data):
            # 板块
            self.sector_table.setItem(row, 0, QtWidgets.QTableWidgetItem(item.get("sector", "")))

            # 净流入
            net_inflow = item.get("net_inflow", 0) / 100000000
            net_item = QtWidgets.QTableWidgetItem(f"{net_inflow:+.2f}")
            if net_inflow > 0:
                net_item.setForeground(QtGui.QColor("red"))
            elif net_inflow < 0:
                net_item.setForeground(QtGui.QColor("green"))
            self.sector_table.setItem(row, 1, net_item)

            # 占比
            ratio = item.get("ratio", 0)
            self.sector_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{ratio:.2f}"))

        self.sector_table.resizeColumnsToContents()

    def show_status(self, msg: str) -> None:
        """显示状态信息"""
        self.status_label.setText(msg)


class SectorRotationWidget(QtWidgets.QWidget):
    """板块轮动策略界面"""

    # 主要板块列表
    SECTORS = [
        _("半导体"), _("新能源"), _("医药生物"),
        _("食品饮料"), _("计算机"), _("电子"),
        _("通信"), _("传媒"), _("有色金属")
    ]

    def __init__(self, main_engine: Any, event_engine: Any, gui_engine: Optional[Any] = None) -> None:
        """初始化"""
        super().__init__()
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.gui_engine = gui_engine
        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("板块轮动策略配置"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 策略说明
        desc = QtWidgets.QLabel(
            _("板块轮动策略捕捉板块轮动机会，提供以下策略：\n"
              "• 板块强度：基于动量指标的板块强度排序\n"
              "• 轮动信号：基于资金流向的轮动信号识别"))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 查询控制区
        query_group = QtWidgets.QGroupBox(_("数据查询"))
        query_layout = QtWidgets.QHBoxLayout()
        query_group.setLayout(query_layout)
        layout.addWidget(query_group)

        query_layout.addWidget(QtWidgets.QLabel(_("查询日期：")))
        self.date_edit = QtWidgets.QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QtCore.QDate.currentDate())
        query_layout.addWidget(self.date_edit)

        query_layout.addWidget(QtWidgets.QLabel(_("板块：")))
        self.sector_combo = QtWidgets.QComboBox()
        self.sector_combo.addItems([_("全部")] + self.SECTORS)
        query_layout.addWidget(self.sector_combo)

        query_strength_btn = QtWidgets.QPushButton(_("板块强度"))
        query_strength_btn.clicked.connect(self.query_strength)
        query_layout.addWidget(query_strength_btn)

        query_signal_btn = QtWidgets.QPushButton(_("轮动信号"))
        query_signal_btn.clicked.connect(self.query_signal)
        query_layout.addWidget(query_signal_btn)

        refresh_btn = QtWidgets.QPushButton(_("刷新"))
        refresh_btn.clicked.connect(self.refresh_data)
        query_layout.addWidget(refresh_btn)

        # 状态标签
        self.status_label = QtWidgets.QLabel(_("就绪"))
        self.status_label.setStyleSheet("padding: 5px; background: #f0f0f0;")
        layout.addWidget(self.status_label)

        # 数据显示区（使用标签页）
        self.tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(self.tab_widget)

        # 板块强度页
        self.strength_table = QtWidgets.QTableWidget()
        self.strength_table.setColumnCount(4)
        self.strength_table.setHorizontalHeaderLabels([
            _("板块"), _("涨跌幅(%)"), _("成交量"), _("强度评分")
        ])
        self.strength_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.strength_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tab_widget.addTab(self.strength_table, _("板块强度"))

        # 轮动信号页
        self.signal_table = QtWidgets.QTableWidget()
        self.signal_table.setColumnCount(3)
        self.signal_table.setHorizontalHeaderLabels([
            _("板块"), _("涨跌幅(%)"), _("信号")
        ])
        self.signal_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.signal_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tab_widget.addTab(self.signal_table, _("轮动信号"))

    def query_strength(self) -> None:
        """查询板块强度"""
        if not self.gui_engine:
            self.show_status(_("错误：GUI引擎未初始化"))
            return

        qdate = self.date_edit.date()
        trade_date = qdate.toPython()

        sector = self.sector_combo.currentText()
        if sector == _("全部"):
            sector = ""

        self.show_status(_("正在查询板块强度..."))

        try:
            if sector:
                # 查询单个板块
                data = self.gui_engine.query_sector_strength(sector, trade_date)
                if data:
                    self.update_strength_table([data])
                    self.show_status(_(f"查询完成，板块：{sector}"))
                else:
                    self.show_status(_("未查询到数据"))
            else:
                # 查询所有板块
                data_list = []
                for s in self.SECTORS:
                    data = self.gui_engine.query_sector_strength(s, trade_date)
                    if data:
                        data_list.append(data)
                self.update_strength_table(data_list)
                self.show_status(_(f"查询完成，共{len(data_list)}个板块"))
        except Exception as e:
            self.show_status(_(f"查询失败：{e}"))

    def query_signal(self) -> None:
        """查询轮动信号"""
        if not self.gui_engine:
            self.show_status(_("错误：GUI引擎未初始化"))
            return

        qdate = self.date_edit.date()
        trade_date = qdate.toPython()

        self.show_status(_("正在查询轮动信号..."))

        try:
            data = self.gui_engine.query_rotation_signal(trade_date)
            self.update_signal_table(data)

            if data:
                self.show_status(_(f"查询完成，共{len(data)}个信号"))
            else:
                self.show_status(_("未查询到数据"))
        except Exception as e:
            self.show_status(_(f"查询失败：{e}"))

    def refresh_data(self) -> None:
        """刷新数据"""
        self.date_edit.setDate(QtCore.QDate.currentDate())
        self.query_signal()

    def update_strength_table(self, data: List[Dict[str, Any]]) -> None:
        """更新板块强度表格"""
        # 按涨跌幅排序
        sorted_data = sorted(data, key=lambda x: x.get("change_pct", 0), reverse=True)

        self.strength_table.setRowCount(len(sorted_data))

        for row, item in enumerate(sorted_data):
            # 板块
            self.strength_table.setItem(row, 0, QtWidgets.QTableWidgetItem(item.get("sector", "")))

            # 涨跌幅（带颜色）
            change_pct = item.get("change_pct", 0)
            change_item = QtWidgets.QTableWidgetItem(f"{change_pct:+.2f}")
            if change_pct > 0:
                change_item.setForeground(QtGui.QColor("red"))
            elif change_pct < 0:
                change_item.setForeground(QtGui.QColor("green"))
            self.strength_table.setItem(row, 1, change_item)

            # 成交量
            volume = item.get("volume", 0) / 100000000
            self.strength_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{volume:.2f}"))

            # 强度评分（基于涨跌幅和成交量）
            score = self._calculate_strength_score(item)
            score_item = QtWidgets.QTableWidgetItem(f"{score:.1f}")
            if score >= 80:
                score_item.setBackground(QtGui.QColor("#d4edda"))
            elif score >= 60:
                score_item.setBackground(QtGui.QColor("#fff3cd"))
            else:
                score_item.setBackground(QtGui.QColor("#f8d7da"))
            self.strength_table.setItem(row, 3, score_item)

        self.strength_table.resizeColumnsToContents()

    def update_signal_table(self, data: List[Dict[str, Any]]) -> None:
        """更新轮动信号表格"""
        self.signal_table.setRowCount(len(data))

        for row, item in enumerate(data):
            # 板块
            self.signal_table.setItem(row, 0, QtWidgets.QTableWidgetItem(item.get("sector", "")))

            # 涨跌幅（带颜色）
            change_pct = item.get("change_pct", 0)
            change_item = QtWidgets.QTableWidgetItem(f"{change_pct:+.2f}")
            if change_pct > 0:
                change_item.setForeground(QtGui.QColor("red"))
            elif change_pct < 0:
                change_item.setForeground(QtGui.QColor("green"))
            self.signal_table.setItem(row, 1, change_item)

            # 信号
            signal = item.get("signal", "hold")
            signal_text = {
                "buy": _("买入"),
                "sell": _("卖出"),
                "hold": _("持有")
            }.get(signal, signal)

            signal_item = QtWidgets.QTableWidgetItem(signal_text)
            if signal == "buy":
                signal_item.setForeground(QtGui.QColor("red"))
            elif signal == "sell":
                signal_item.setForeground(QtGui.QColor("green"))
            self.signal_table.setItem(row, 2, signal_item)

        self.signal_table.resizeColumnsToContents()

    def _calculate_strength_score(self, item: Dict[str, Any]) -> float:
        """计算强度评分"""
        change_pct = item.get("change_pct", 0)
        volume = item.get("volume", 0)

        # 简单评分：涨跌幅 * 10 + 成交量因子
        score = abs(change_pct) * 10
        if volume > 0:
            score += min(volume / 1000000000 * 10, 20)

        return min(score, 100)

    def show_status(self, msg: str) -> None:
        """显示状态信息"""
        self.status_label.setText(msg)


class EventDrivenWidget(QtWidgets.QWidget):
    """事件驱动策略界面"""

    def __init__(self, main_engine: Any, event_engine: Any, gui_engine: Optional[Any] = None) -> None:
        """初始化"""
        super().__init__()
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.gui_engine = gui_engine
        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("事件驱动策略配置"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 策略说明
        desc = QtWidgets.QLabel(
            _("事件驱动策略捕捉市场事件机会，提供以下策略：\n"
              "• 业绩预告：基于业绩预告的策略\n"
              "• 政策事件：基于政策事件的策略"))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 查询控制区
        query_group = QtWidgets.QGroupBox(_("数据查询"))
        query_layout = QtWidgets.QHBoxLayout()
        query_group.setLayout(query_layout)
        layout.addWidget(query_group)

        query_layout.addWidget(QtWidgets.QLabel(_("股票代码：")))
        self.symbol_input = QtWidgets.QLineEdit()
        self.symbol_input.setPlaceholderText(_("输入股票代码，如：000001"))
        query_layout.addWidget(self.symbol_input)

        query_earnings_btn = QtWidgets.QPushButton(_("业绩预告"))
        query_earnings_btn.clicked.connect(self.query_earnings)
        query_layout.addWidget(query_earnings_btn)

        query_policy_btn = QtWidgets.QPushButton(_("政策事件"))
        query_policy_btn.clicked.connect(self.query_policy)
        query_layout.addWidget(query_policy_btn)

        refresh_btn = QtWidgets.QPushButton(_("刷新"))
        refresh_btn.clicked.connect(self.refresh_data)
        query_layout.addWidget(refresh_btn)

        # 状态标签
        self.status_label = QtWidgets.QLabel(_("就绪"))
        self.status_label.setStyleSheet("padding: 5px; background: #f0f0f0;")
        layout.addWidget(self.status_label)

        # 数据显示区（使用标签页）
        self.tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(self.tab_widget)

        # 业绩预告页
        self.earnings_table = QtWidgets.QTableWidget()
        self.earnings_table.setColumnCount(5)
        self.earnings_table.setHorizontalHeaderLabels([
            _("公告日期"), _("报告期"), _("预告类型"), _("净利润变动"), _("预告内容")
        ])
        self.earnings_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.earnings_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tab_widget.addTab(self.earnings_table, _("业绩预告"))

        # 政策事件页
        self.policy_table = QtWidgets.QTableWidget()
        self.policy_table.setColumnCount(4)
        self.policy_table.setHorizontalHeaderLabels([
            _("发布日期"), _("政策类型"), _("影响板块"), _("政策内容")
        ])
        self.policy_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.policy_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tab_widget.addTab(self.policy_table, _("政策事件"))

    def query_earnings(self) -> None:
        """查询业绩预告"""
        if not self.gui_engine:
            self.show_status(_("错误：GUI引擎未初始化"))
            return

        symbol = self.symbol_input.text().strip()
        if not symbol:
            QtWidgets.QMessageBox.warning(self, _("警告"), _("请输入股票代码"))
            return

        self.show_status(_("正在查询业绩预告..."))

        try:
            data = self.gui_engine.query_earnings_forecast(symbol, days=30)
            self.update_earnings_table(data)

            if data:
                self.show_status(_(f"查询完成，共{len(data)}条记录"))
            else:
                self.show_status(_("未查询到数据"))
        except Exception as e:
            self.show_status(_(f"查询失败：{e}"))

    def query_policy(self) -> None:
        """查询政策事件"""
        if not self.gui_engine:
            self.show_status(_("错误：GUI引擎未初始化"))
            return

        self.show_status(_("正在查询政策事件..."))

        try:
            data = self.gui_engine.query_policy_events(days=30)
            self.update_policy_table(data)

            if data:
                self.show_status(_(f"查询完成，共{len(data)}条记录"))
            else:
                self.show_status(_("未查询到数据"))
        except Exception as e:
            self.show_status(_(f"查询失败：{e}"))

    def refresh_data(self) -> None:
        """刷新数据"""
        if self.symbol_input.text().strip():
            self.query_earnings()

    def update_earnings_table(self, data: List[Dict[str, Any]]) -> None:
        """更新业绩预告表格"""
        self.earnings_table.setRowCount(len(data))

        for row, item in enumerate(data):
            # 公告日期
            announce_date = item.get("announce_date")
            if announce_date:
                date_str = announce_date.strftime("%Y-%m-%d") if isinstance(announce_date, date) else str(announce_date)
                self.earnings_table.setItem(row, 0, QtWidgets.QTableWidgetItem(date_str))

            # 报告期
            report_period = item.get("report_period")
            if report_period:
                period_str = report_period.strftime("%Y-%m-%d") if isinstance(report_period, date) else str(report_period)
                self.earnings_table.setItem(row, 1, QtWidgets.QTableWidgetItem(period_str))

            # 预告类型
            forecast_type = item.get("forecast_type", "")
            self.earnings_table.setItem(row, 2, QtWidgets.QTableWidgetItem(forecast_type))

            # 净利润变动（带颜色）
            profit_change = item.get("profit_change", 0)
            change_item = QtWidgets.QTableWidgetItem(f"{profit_change:+.2f}%")
            if profit_change > 0:
                change_item.setForeground(QtGui.QColor("red"))
            elif profit_change < 0:
                change_item.setForeground(QtGui.QColor("green"))
            self.earnings_table.setItem(row, 3, change_item)

            # 预告内容
            content = item.get("content", "")
            self.earnings_table.setItem(row, 4, QtWidgets.QTableWidgetItem(content))

        self.earnings_table.resizeColumnsToContents()

    def update_policy_table(self, data: List[Dict[str, Any]]) -> None:
        """更新政策事件表格"""
        self.policy_table.setRowCount(len(data))

        for row, item in enumerate(data):
            # 发布日期
            pub_date = item.get("publish_date")
            if pub_date:
                date_str = pub_date.strftime("%Y-%m-%d") if isinstance(pub_date, date) else str(pub_date)
                self.policy_table.setItem(row, 0, QtWidgets.QTableWidgetItem(date_str))

            # 政策类型
            policy_type = item.get("policy_type", "")
            self.policy_table.setItem(row, 1, QtWidgets.QTableWidgetItem(policy_type))

            # 影响板块
            affected_sectors = item.get("affected_sectors", "")
            self.policy_table.setItem(row, 2, QtWidgets.QTableWidgetItem(affected_sectors))

            # 政策内容
            content = item.get("content", "")
            self.policy_table.setItem(row, 3, QtWidgets.QTableWidgetItem(content))

        self.policy_table.resizeColumnsToContents()

    def show_status(self, msg: str) -> None:
        """显示状态信息"""
        self.status_label.setText(msg)


class ConvertibleWidget(QtWidgets.QWidget):
    """可转债策略界面"""

    def __init__(self, main_engine: Any, event_engine: Any, gui_engine: Optional[Any] = None) -> None:
        """初始化"""
        super().__init__()
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.gui_engine = gui_engine
        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("可转债套利策略配置"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 策略说明
        desc = QtWidgets.QLabel(
            _("可转债套利策略利用可转债与正股之间的价差获利，提供以下策略：\n"
              "• 转股套利：利用转股溢价率进行套利\n"
              "• 定价模型：基于定价模型的套利机会"))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 查询控制区
        query_group = QtWidgets.QGroupBox(_("数据查询"))
        query_layout = QtWidgets.QHBoxLayout()
        query_group.setLayout(query_layout)
        layout.addWidget(query_group)

        query_layout.addWidget(QtWidgets.QLabel(_("溢价率筛选：")))
        self.premium_spinbox = QtWidgets.QDoubleSpinBox()
        self.premium_spinbox.setRange(-50, 50)
        self.premium_spinbox.setValue(5)
        self.premium_spinbox.setSuffix("%")
        query_layout.addWidget(self.premium_spinbox)

        query_btn = QtWidgets.QPushButton(_("查询可转债"))
        query_btn.clicked.connect(self.query_convertible)
        query_layout.addWidget(query_btn)

        refresh_btn = QtWidgets.QPushButton(_("刷新"))
        refresh_btn.clicked.connect(self.refresh_data)
        query_layout.addWidget(refresh_btn)

        # 状态标签
        self.status_label = QtWidgets.QLabel(_("就绪"))
        self.status_label.setStyleSheet("padding: 5px; background: #f0f0f0;")
        layout.addWidget(self.status_label)

        # 数据表格
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            _("转债代码"), _("转债名称"), _("正股代码"), _("正股名称"),
            _("转债价格"), _("转股溢价率(%)"), _("套利空间")
        ])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def query_convertible(self) -> None:
        """查询可转债列表"""
        if not self.gui_engine:
            self.show_status(_("错误：GUI引擎未初始化"))
            return

        premium_threshold = self.premium_spinbox.value()
        self.show_status(_("正在查询可转债列表..."))

        try:
            data = self.gui_engine.query_convertible_bonds()

            # 按溢价率筛选
            filtered_data = [
                item for item in data
                if abs(item.get("premium_ratio", 100)) <= premium_threshold
            ]

            self.update_table(filtered_data)

            if filtered_data:
                self.show_status(_(f"查询完成，共{len(filtered_data)}只可转债（溢价率≤{premium_threshold}%）"))
            else:
                self.show_status(_(f"未找到符合条件的可转债（溢价率≤{premium_threshold}%）"))
        except Exception as e:
            self.show_status(_(f"查询失败：{e}"))

    def refresh_data(self) -> None:
        """刷新数据"""
        self.query_convertible()

    def update_table(self, data: List[Dict[str, Any]]) -> None:
        """更新表格数据"""
        # 按溢价率排序
        sorted_data = sorted(data, key=lambda x: abs(x.get("premium_ratio", 100)))

        self.table.setRowCount(len(sorted_data))

        for row, item in enumerate(sorted_data):
            # 转债代码
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(item.get("cb_code", "")))

            # 转债名称
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(item.get("cb_name", "")))

            # 正股代码
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(item.get("stock_code", "")))

            # 正股名称
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(item.get("stock_name", "")))

            # 转债价格
            cb_price = item.get("cb_price", 0)
            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(f"{cb_price:.2f}"))

            # 转股溢价率（带颜色）
            premium_ratio = item.get("premium_ratio", 0)
            premium_item = QtWidgets.QTableWidgetItem(f"{premium_ratio:+.2f}")
            if premium_ratio > 0:
                premium_item.setForeground(QtGui.QColor("green"))
            elif premium_ratio < 0:
                premium_item.setForeground(QtGui.QColor("red"))
            self.table.setItem(row, 5, premium_item)

            # 套利空间（负溢价率为正套利空间）
            arbitrage = -premium_ratio
            arbitrage_item = QtWidgets.QTableWidgetItem(f"{arbitrage:+.2f}%")
            if arbitrage > 0:
                arbitrage_item.setForeground(QtGui.QColor("red"))
                arbitrage_item.setBackground(QtGui.QColor("#d4edda"))
            elif arbitrage < 0:
                arbitrage_item.setForeground(QtGui.QColor("green"))
            self.table.setItem(row, 6, arbitrage_item)

        self.table.resizeColumnsToContents()

    def show_status(self, msg: str) -> None:
        """显示状态信息"""
        self.status_label.setText(msg)


# 用于向后兼容的别名
StrategyManagerWidget = ChinaStrategyWidget


__all__ = [
    "ChinaStrategyWidget",
    "StrategyManagerWidget",
    "StrategyListWidget",
    "DragonTigerStrategyWidget",
    "NorthboundStrategyWidget",
    "SectorRotationWidget",
    "EventDrivenWidget",
    "ConvertibleWidget",
]
