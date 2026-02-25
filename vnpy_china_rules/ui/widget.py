"""
A股交易规则UI组件
提供T+1规则、涨跌停规则、交易时间等界面
"""

from typing import Dict, Any, Optional
from datetime import datetime
from vnpy.trader.ui.qt import QtCore, QtGui, QtWidgets
from vnpy.trader.ui.widget import BaseMonitor
from vnpy.trader.object import OrderData, TradeData
from vnpy.trader.utility import get_icon_path
from vnpy.trader.locale import _


class ChinaRulesWidget(QtWidgets.QWidget):
    """A股交易规则主界面"""

    def __init__(self, main_engine: Any, event_engine: Any) -> None:
        """初始化界面"""
        super().__init__()

        self.main_engine = main_engine
        self.event_engine = event_engine

        # 获取规则GUI引擎
        self.gui_engine = main_engine.get_engine("ChinaRulesApp")

        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle(_("A股交易规则管理"))
        self.setMinimumSize(800, 600)

        # 创建主布局
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 创建标签页
        tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(tab_widget)

        # T+1规则页
        t1_widget = T1RulesWidget(self.main_engine, self.event_engine, self.gui_engine)
        tab_widget.addTab(t1_widget, _("T+1规则"))

        # 涨跌停规则页
        price_limit_widget = PriceLimitWidget(self.main_engine, self.event_engine, self.gui_engine)
        tab_widget.addTab(price_limit_widget, _("涨跌停"))

        # 交易时间规则页
        time_widget = TimeRulesWidget(self.main_engine, self.event_engine, self.gui_engine)
        tab_widget.addTab(time_widget, _("交易时间"))

        # 规则检查历史页
        history_widget = RulesHistoryWidget(self.main_engine, self.event_engine, self.gui_engine)
        tab_widget.addTab(history_widget, _("检查历史"))


class T1RulesWidget(QtWidgets.QWidget):
    """T+1交易规则界面"""

    def __init__(self, main_engine: Any, event_engine: Any, gui_engine: Any) -> None:
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
        title = QtWidgets.QLabel(_("T+1交易规则"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 规则说明
        desc = QtWidgets.QLabel(
            _("T+1交易规则说明：\n"
              "• 当日买入的股票只能在下一个交易日卖出\n"
              "• 系统自动维护持仓流水记录\n"
              "• 计算可卖数量时使用FIFO原则"))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 持仓查询区
        query_group = QtWidgets.QGroupBox(_("持仓查询"))
        query_layout = QtWidgets.QHBoxLayout()
        query_group.setLayout(query_layout)
        layout.addWidget(query_group)

        symbol_input = QtWidgets.QLineEdit()
        symbol_input.setPlaceholderText(_("输入股票代码，如：000001"))
        query_layout.addWidget(symbol_input)

        query_btn = QtWidgets.QPushButton(_("查询可卖数量"))
        query_btn.clicked.connect(lambda: self.query_sellable(symbol_input.text()))
        query_layout.addWidget(query_btn)

        # 结果显示区
        result_group = QtWidgets.QGroupBox(_("查询结果"))
        result_layout = QtWidgets.QVBoxLayout()
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        self.result_label = QtWidgets.QLabel(_("请输入股票代码查询"))
        self.result_label.setStyleSheet("padding: 10px; background: #f5f5f5;")
        result_layout.addWidget(self.result_label)

    def query_sellable(self, symbol: str) -> None:
        """查询可卖数量"""
        if not symbol:
            self.result_label.setText(_("请输入股票代码"))
            return

        # 从规则引擎获取可卖数量
        sellable = self.gui_engine.get_sellable_volume(symbol)

        result_text = _("""股票代码：{symbol}
可卖数量：{volume} 股
查询时间：{time}""").format(
            symbol=symbol,
            volume=sellable,
            time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        self.result_label.setText(result_text)


class PriceLimitWidget(QtWidgets.QWidget):
    """涨跌停规则界面"""

    def __init__(self, main_engine: Any, event_engine: Any, gui_engine: Any) -> None:
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
        title = QtWidgets.QLabel(_("涨跌停规则"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 规则说明
        desc = QtWidgets.QLabel(
            _("涨跌停规则说明：\n"
              "• 主板股票涨跌停比例：10%\n"
              "• 创业板/科创板涨跌停比例：20%\n"
              "• 北交所涨跌停比例：30%\n"
              "• ST股票涨跌停比例：5%"))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 价格查询区
        query_group = QtWidgets.QGroupBox(_("涨跌停价格计算"))
        query_layout = QtWidgets.QHBoxLayout()
        query_group.setLayout(query_layout)
        layout.addWidget(query_group)

        symbol_input = QtWidgets.QLineEdit()
        symbol_input.setPlaceholderText(_("股票代码"))
        query_layout.addWidget(symbol_input)

        price_input = QtWidgets.QLineEdit()
        price_input.setPlaceholderText(_("昨收价（可选，不填则自动获取）"))
        query_layout.addWidget(price_input)

        calc_btn = QtWidgets.QPushButton(_("计算"))
        calc_btn.clicked.connect(
            lambda: self.calculate_limit(symbol_input.text(), price_input.text())
        )
        query_layout.addWidget(calc_btn)

        # 结果显示区
        result_group = QtWidgets.QGroupBox(_("计算结果"))
        result_layout = QtWidgets.QVBoxLayout()
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        self.result_label = QtWidgets.QLabel(_("请输入股票代码计算涨跌停价格"))
        self.result_label.setStyleSheet("padding: 10px; background: #f5f5f5;")
        result_layout.addWidget(self.result_label)

    def calculate_limit(self, symbol: str, prev_close: str) -> None:
        """计算涨跌停价格"""
        if not symbol:
            self.result_label.setText(_("请输入股票代码"))
            return

        # 获取昨收价
        pre_close = None
        if prev_close:
            try:
                pre_close = float(prev_close)
            except ValueError:
                self.result_label.setText(_("昨收价格式错误"))
                return
        else:
            # 尝试从缓存获取
            pre_close = self.gui_engine.get_pre_close(symbol)
            if pre_close is None:
                self.result_label.setText(_("无法获取昨收价，请手动输入"))
                return

        # 计算涨跌停价格
        result = self.gui_engine.calculate_limit_price(symbol, pre_close)

        if result:
            limit_up, limit_down = result
            result_text = _("""股票代码：{symbol}
昨收价：{pre_close:.2f}
涨停价：{limit_up:.2f} (+{up_pct:.1f}%)
跌停价：{limit_down:.2f} ({down_pct:.1f}%)
查询时间：{time}""").format(
                symbol=symbol,
                pre_close=pre_close,
                limit_up=limit_up,
                limit_down=limit_down,
                up_pct=(limit_up / pre_close - 1) * 100,
                down_pct=(limit_down / pre_close - 1) * 100,
                time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            self.result_label.setText(result_text)
        else:
            self.result_label.setText(_("涨跌停价格计算失败"))


class TimeRulesWidget(QtWidgets.QWidget):
    """交易时间规则界面"""

    def __init__(self, main_engine: Any, event_engine: Any, gui_engine: Any) -> None:
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
        title = QtWidgets.QLabel(_("交易时间规则"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 规则说明
        desc = QtWidgets.QLabel(
            _("交易时间说明：\n"
              "• 集合竞价：9:15-9:25\n"
              "• 上午交易：9:30-11:30\n"
              "• 下午交易：13:00-15:00\n"
              "• 大宗交易：15:00-15:30"))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 当前状态
        status_group = QtWidgets.QGroupBox(_("当前状态"))
        status_layout = QtWidgets.QVBoxLayout()
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        refresh_btn = QtWidgets.QPushButton(_("刷新状态"))
        refresh_btn.clicked.connect(self.refresh_status)
        status_layout.addWidget(refresh_btn)

        self.status_label = QtWidgets.QLabel(_("点击刷新获取当前状态"))
        self.status_label.setStyleSheet("padding: 10px; background: #f5f5f5;")
        status_layout.addWidget(self.status_label)

        # 添加定时刷新
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(60000)  # 每分钟刷新一次

        # 初始刷新
        self.refresh_status()

    def refresh_status(self) -> None:
        """刷新状态"""
        status_info = self.gui_engine.get_trading_status()

        # 根据状态设置颜色
        if status_info["is_trading"]:
            color = "#d4edda"  # 绿色背景
            status_text = _("""当前时间：{current_time}
交易时段：{phase}
交易状态：✓ 在交易时间""").format(
                current_time=status_info["current_time"],
                phase=status_info["trading_phase"]
            )
        else:
            color = "#f8d7da"  # 红色背景
            status_text = _("""当前时间：{current_time}
交易时段：{phase}
交易状态：✗ 非交易时间""").format(
                current_time=status_info["current_time"],
                phase=status_info["trading_phase"]
            )

        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(f"padding: 10px; background: {color};")


class RulesHistoryWidget(QtWidgets.QWidget):
    """规则检查历史界面"""

    def __init__(self, main_engine: Any, event_engine: Any, gui_engine: Any) -> None:
        """初始化"""
        super().__init__()
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.gui_engine = gui_engine
        self.init_ui()

        # 初始加载数据
        self.refresh_data()

    def init_ui(self) -> None:
        """初始化UI"""
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("规则检查历史"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 工具栏
        toolbar = QtWidgets.QHBoxLayout()
        layout.addLayout(toolbar)

        refresh_btn = QtWidgets.QPushButton(_("刷新"))
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)

        clear_btn = QtWidgets.QPushButton(_("清空历史"))
        clear_btn.clicked.connect(self.clear_data)
        toolbar.addWidget(clear_btn)

        toolbar.addStretch()

        # 数据表格
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            _("时间"), _("股票"), _("规则"), _("结果"), _("消息")
        ])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        # 添加定时刷新
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(5000)  # 每5秒刷新一次

    def refresh_data(self) -> None:
        """刷新数据"""
        # 从规则引擎获取检查历史
        history = self.gui_engine.get_check_history(limit=200)

        self.table.setRowCount(len(history))

        for row, item in enumerate(history):
            # 时间
            time_item = QtWidgets.QTableWidgetItem(
                item["time"].strftime("%H:%M:%S")
            )
            self.table.setItem(row, 0, time_item)

            # 股票
            symbol_item = QtWidgets.QTableWidgetItem(item["symbol"])
            self.table.setItem(row, 1, symbol_item)

            # 规则
            rules = []
            for result in item["rule_results"]:
                rules.append(result.rule_name)
            rules_item = QtWidgets.QTableWidgetItem(", ".join(rules))
            self.table.setItem(row, 2, rules_item)

            # 结果
            all_passed = all(r.passed for r in item["rule_results"])
            result_text = _("通过") if all_passed else _("失败")
            result_item = QtWidgets.QTableWidgetItem(result_text)
            if all_passed:
                result_item.setForeground(QtGui.QColor("green"))
            else:
                result_item.setForeground(QtGui.QColor("red"))
            self.table.setItem(row, 3, result_item)

            # 消息
            messages = []
            for result in item["rule_results"]:
                if not result.passed:
                    messages.append(f"{result.rule_name}: {result.message}")
            msg_text = "; ".join(messages) if messages else "-"
            msg_item = QtWidgets.QTableWidgetItem(msg_text)
            self.table.setItem(row, 4, msg_item)

        # 调整列宽
        self.table.resizeColumnsToContents()

    def clear_data(self) -> None:
        """清空历史"""
        self.gui_engine.clear_check_history()
        self.table.setRowCount(0)

    def write_log(self, msg: str) -> None:
        """写日志"""
        print(f"[RulesHistory] {msg}")


__all__ = [
    "ChinaRulesWidget",
    "T1RulesWidget",
    "PriceLimitWidget",
    "TimeRulesWidget",
]
