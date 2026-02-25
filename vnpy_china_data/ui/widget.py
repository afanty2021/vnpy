"""A股数据UI组件"""
from datetime import date
from typing import Any, Optional

from vnpy.trader.ui.qt import QtWidgets, QtCore, QtGui
from vnpy.trader.ui.widget import BaseCell
from vnpy.trader.locale import _
from .table import DragonTigerTable, NorthboundTable


class ChinaDataWidget(QtWidgets.QWidget):
    """A股数据服务主界面"""

    def __init__(self, main_engine: Any, event_engine: Any):
        super().__init__()
        self.main_engine = main_engine
        self.event_engine = event_engine

        # 获取GUI引擎
        self.gui_engine: Optional[Any] = None
        try:
            self.gui_engine = main_engine.get_engine("ChinaDataApp")
        except Exception:
            pass

        self.init_ui()

    def init_ui(self) -> None:
        """初始化界面"""
        self.setWindowTitle(_("A股数据服务"))
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 创建标签页
        tab = QtWidgets.QTabWidget()
        layout.addWidget(tab)

        # 龙虎榜数据标签页
        dt_widget = self.create_dragon_tiger_tab()
        tab.addTab(dt_widget, _("龙虎榜"))

        # 北向资金标签页
        nb_widget = self.create_northbound_tab()
        tab.addTab(nb_widget, _("北向资金"))

        # 状态栏
        self.status_label = QtWidgets.QLabel(_("就绪"))
        layout.addWidget(self.status_label)

    def create_dragon_tiger_tab(self) -> QtWidgets.QWidget:
        """创建龙虎榜标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 控制面板
        control_panel = QtWidgets.QWidget()
        control_layout = QtWidgets.QHBoxLayout()
        control_panel.setLayout(control_layout)

        # 日期选择
        control_layout.addWidget(QtWidgets.QLabel(_("查询日期：")))
        self.dt_date_edit = QtWidgets.QDateEdit()
        self.dt_date_edit.setCalendarPopup(True)
        self.dt_date_edit.setDate(QtCore.QDate.currentDate())
        control_layout.addWidget(self.dt_date_edit)

        # 查询按钮
        self.dt_query_btn = QtWidgets.QPushButton(_("查询"))
        self.dt_query_btn.clicked.connect(self.query_dragon_tiger)
        control_layout.addWidget(self.dt_query_btn)

        # 刷新按钮
        self.dt_refresh_btn = QtWidgets.QPushButton(_("刷新"))
        self.dt_refresh_btn.clicked.connect(self.refresh_dragon_tiger)
        control_layout.addWidget(self.dt_refresh_btn)

        control_layout.addStretch()
        layout.addWidget(control_panel)

        # 数据表格
        self.dt_table = DragonTigerTable()
        layout.addWidget(self.dt_table)

        return widget

    def create_northbound_tab(self) -> QtWidgets.QWidget:
        """创建北向资金标签页"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        # 控制面板
        control_panel = QtWidgets.QWidget()
        control_layout = QtWidgets.QHBoxLayout()
        control_panel.setLayout(control_layout)

        # 日期选择
        control_layout.addWidget(QtWidgets.QLabel(_("查询日期：")))
        self.nb_date_edit = QtWidgets.QDateEdit()
        self.nb_date_edit.setCalendarPopup(True)
        self.nb_date_edit.setDate(QtCore.QDate.currentDate())
        control_layout.addWidget(self.nb_date_edit)

        # 查询按钮
        self.nb_query_btn = QtWidgets.QPushButton(_("查询"))
        self.nb_query_btn.clicked.connect(self.query_northbound)
        control_layout.addWidget(self.nb_query_btn)

        # 刷新按钮
        self.nb_refresh_btn = QtWidgets.QPushButton(_("刷新"))
        self.nb_refresh_btn.clicked.connect(self.refresh_northbound)
        control_layout.addWidget(self.nb_refresh_btn)

        control_layout.addStretch()
        layout.addWidget(control_panel)

        # 数据表格
        self.nb_table = NorthboundTable()
        layout.addWidget(self.nb_table)

        return widget

    def query_dragon_tiger(self) -> None:
        """查询龙虎榜数据"""
        if not self.gui_engine:
            self.show_status(_("错误：GUI引擎未初始化"))
            return

        qdate = self.dt_date_edit.date()
        trade_date = qdate.toPython()

        self.show_status(_("正在查询龙虎榜数据..."))
        data = self.gui_engine.query_dragon_tiger(trade_date)

        self.dt_table.update_data(data)

        if data:
            self.show_status(_(f"查询完成，共{len(data)}条记录"))
        else:
            self.show_status(_("未查询到数据"))

    def refresh_dragon_tiger(self) -> None:
        """刷新龙虎榜数据（使用当前日期）"""
        self.dt_date_edit.setDate(QtCore.QDate.currentDate())
        self.query_dragon_tiger()

    def query_northbound(self) -> None:
        """查询北向资金数据"""
        if not self.gui_engine:
            self.show_status(_("错误：GUI引擎未初始化"))
            return

        qdate = self.nb_date_edit.date()
        trade_date = qdate.toPython()

        self.show_status(_("正在查询北向资金数据..."))
        data = self.gui_engine.query_northbound_flow(trade_date)

        self.nb_table.update_data(data)

        if data:
            self.show_status(_(f"查询完成，净流入：{data.total_net_inflow:.2f}亿元"))
        else:
            self.show_status(_("未查询到数据"))

    def refresh_northbound(self) -> None:
        """刷新北向资金数据（使用当前日期）"""
        self.nb_date_edit.setDate(QtCore.QDate.currentDate())
        self.query_northbound()

    def show_status(self, msg: str) -> None:
        """显示状态信息"""
        self.status_label.setText(msg)


__all__ = ["ChinaDataWidget"]
