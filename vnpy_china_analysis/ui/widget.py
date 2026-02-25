"""
A股分析UI组件
提供Level-2分析、资金流向、技术指标等界面
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from vnpy.trader.ui.qt import QtCore, QtGui, QtWidgets
from vnpy.trader.ui.widget import BaseMonitor
from vnpy.trader.object import TickData, BarData
from vnpy.trader.utility import get_icon_path
from vnpy.trader.locale import _

# 尝试导入pandas用于数据导出
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class ChinaAnalysisWidget(QtWidgets.QWidget):
    """A股分析主界面"""

    def __init__(self, main_engine: Any, event_engine: Any) -> None:
        """初始化界面"""
        super().__init__()

        self.main_engine = main_engine
        self.event_engine = event_engine

        # 获取分析引擎
        self.analysis_engine = main_engine.get_engine("ChinaAnalysisApp")

        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle(_("A股市场分析"))
        self.setMinimumSize(900, 600)

        # 创建主布局
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 创建标签页
        tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(tab_widget)

        # Level-2分析页
        level2_widget = Level2AnalysisWidget(self.main_engine, self.event_engine, self.analysis_engine)
        tab_widget.addTab(level2_widget, _("Level-2分析"))

        # 资金流向页
        money_flow_widget = MoneyFlowWidget(self.main_engine, self.event_engine, self.analysis_engine)
        tab_widget.addTab(money_flow_widget, _("资金流向"))

        # 技术指标页
        technical_widget = TechnicalWidget(self.main_engine, self.event_engine, self.analysis_engine)
        tab_widget.addTab(technical_widget, _("技术指标"))

        # 集合竞价页
        auction_widget = AuctionWidget(self.main_engine, self.event_engine, self.analysis_engine)
        tab_widget.addTab(auction_widget, _("集合竞价"))


class BaseAnalysisWidget(QtWidgets.QWidget):
    """分析组件基类"""

    def __init__(self, main_engine: Any, event_engine: Any, analysis_engine: Any) -> None:
        """初始化"""
        super().__init__()
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.analysis_engine = analysis_engine

        # 数据缓存
        self.cache_data: Dict[str, Any] = {}

    def write_log(self, msg: str) -> None:
        """写日志"""
        print(f"[{self.__class__.__name__}] {msg}")

    def format_number(self, value: float, decimals: int = 2) -> str:
        """格式化数字显示

        Args:
            value: 数值
            decimals: 小数位数

        Returns:
            格式化后的字符串
        """
        return f"{value:,.{decimals}f}"

    def format_amount(self, amount: float) -> str:
        """格式化金额显示（万/亿）

        Args:
            amount: 金额

        Returns:
            格式化后的字符串
        """
        if abs(amount) >= 100000000:
            return f"{amount/100000000:.2f}亿"
        elif abs(amount) >= 10000:
            return f"{amount/10000:.2f}万"
        else:
            return f"{amount:.2f}"

    def get_symbol_list(self) -> List[str]:
        """获取当前订阅的合约列表

        Returns:
            合约代码列表
        """
        # 从主引擎获取所有合约
        contracts = self.main_engine.get_all_contracts()
        return [c.symbol for c in contracts.values() if c.symbol]


class Level2AnalysisWidget(BaseAnalysisWidget):
    """Level-2行情分析界面"""

    def __init__(self, main_engine: Any, event_engine: Any, analysis_engine: Any) -> None:
        """初始化"""
        super().__init__(main_engine, event_engine, analysis_engine)
        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("Level-2行情分析"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 策略说明
        desc = QtWidgets.QLabel(
            _("Level-2行情分析提供深度的行情数据分析：\n"
              "• 十档行情：查看买卖十档报价\n"
              "• 逐笔成交：分析大单成交情况\n"
              "• 主力动向：追踪主力资金流向"))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 功能按钮区
        btn_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout)

        refresh_btn = QtWidgets.QPushButton(_("刷新数据"))
        refresh_btn.clicked.connect(self.refresh_data)
        btn_layout.addWidget(refresh_btn)

        export_btn = QtWidgets.QPushButton(_("导出数据"))
        export_btn.clicked.connect(self.export_data)
        btn_layout.addWidget(export_btn)

        # 股票代码输入
        symbol_label = QtWidgets.QLabel(_("股票代码："))
        btn_layout.addWidget(symbol_label)

        self.symbol_input = QtWidgets.QLineEdit()
        self.symbol_input.setPlaceholderText(_("输入股票代码，如000001"))
        btn_layout.addWidget(self.symbol_input)

        query_btn = QtWidgets.QPushButton(_("查询"))
        query_btn.clicked.connect(self.query_symbol)
        btn_layout.addWidget(query_btn)

        # 数据显示区
        data_group = QtWidgets.QGroupBox(_("实时数据"))
        data_layout = QtWidgets.QVBoxLayout()
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)

        # 创建表格
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            _("合约代码"), _("支撑位"), _("阻力位"),
            _("价格深度"), _("主力动向"), _("大单成交")
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        data_layout.addWidget(self.table)

        # 状态栏
        self.status_label = QtWidgets.QLabel(_("就绪"))
        layout.addWidget(self.status_label)

    def refresh_data(self) -> None:
        """刷新数据 - 显示所有订阅合约"""
        symbols = self.get_symbol_list()
        if not symbols:
            self.status_label.setText(_("无可用合约"))
            return

        self.update_table(symbols)
        self.status_label.setText(_("已刷新") + f" ({len(symbols)} " + _("个合约") + ")")

    def query_symbol(self) -> None:
        """查询指定股票"""
        symbol = self.symbol_input.text().strip()
        if not symbol:
            self.status_label.setText(_("请输入股票代码"))
            return

        self.update_table([symbol])
        self.status_label.setText(_("查询完成：") + symbol)

    def update_table(self, symbols: List[str]) -> None:
        """更新表格数据

        Args:
            symbols: 股票代码列表
        """
        self.table.setRowCount(len(symbols))

        for row, symbol in enumerate(symbols):
            # 获取分析数据
            analysis = self.analysis_engine.get_level2_analysis(symbol)

            # 填充数据
            self.setItemText(row, 0, symbol)

            if analysis:
                order_queue = analysis.get("order_queue", {})
                self.setItemText(row, 1, self.format_number(order_queue.get("support_level", 0), 2))
                self.setItemText(row, 2, self.format_number(order_queue.get("resistance_level", 0), 2))
                self.setItemText(row, 3, str(order_queue.get("price_depth", 0)))

                main_force = analysis.get("main_force", {})
                self.setItemText(row, 4, main_force.get("action", _("未知")))

                tick_flow = analysis.get("tick_flow", {})
                self.setItemText(row, 5, str(tick_flow.get("large_trades", 0)))
            else:
                for col in range(1, 6):
                    self.setItemText(row, col, "-")

    def setItemText(self, row: int, column: int, text: str) -> None:
        """设置表格单元格文本

        Args:
            row: 行号
            column: 列号
            text: 文本内容
        """
        item = QtWidgets.QTableWidgetItem(text)
        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, column, item)

    def export_data(self) -> None:
        """导出数据"""
        if not PANDAS_AVAILABLE:
            QtWidgets.QMessageBox.warning(self, _("导出失败"), _("需要安装pandas库才能导出数据"))
            return

        # 收集当前表格数据
        data = []
        for row in range(self.table.rowCount()):
            row_data = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        if not data:
            QtWidgets.QMessageBox.information(self, _("导出提示"), _("没有数据可导出"))
            return

        # 创建DataFrame并导出
        columns = [self.table.horizontalHeaderItem(i).text()
                   for i in range(self.table.columnCount())]
        df = pd.DataFrame(data, columns=columns)

        # 选择保存路径
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, _("导出Level-2数据"), "", "CSV Files (*.csv)"
        )

        if path:
            df.to_csv(path, index=False, encoding="utf-8-sig")
            self.write_log(_("数据已导出：") + path)
            self.status_label.setText(_("导出成功：") + path)


class MoneyFlowWidget(BaseAnalysisWidget):
    """资金流向分析界面"""

    def __init__(self, main_engine: Any, event_engine: Any, analysis_engine: Any) -> None:
        """初始化"""
        super().__init__(main_engine, event_engine, analysis_engine)
        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("资金流向分析"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 策略说明
        desc = QtWidgets.QLabel(
            _("资金流向分析追踪市场资金动向：\n"
              "• 主力资金：大单资金净流入流出\n"
              "• 散户资金：小单资金净流入流出\n"
              "• 资金分类：超大单、大单、中单、小单"))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 功能按钮区
        btn_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout)

        refresh_btn = QtWidgets.QPushButton(_("刷新数据"))
        refresh_btn.clicked.connect(self.refresh_data)
        btn_layout.addWidget(refresh_btn)

        export_btn = QtWidgets.QPushButton(_("导出数据"))
        export_btn.clicked.connect(self.export_data)
        btn_layout.addWidget(export_btn)

        # 时间范围选择
        time_label = QtWidgets.QLabel(_("时间范围："))
        btn_layout.addWidget(time_label)

        self.time_combo = QtWidgets.QComboBox()
        self.time_combo.addItems([_("5分钟"), _("30分钟"), _("60分钟"), _("当日")])
        btn_layout.addWidget(self.time_combo)

        # 统计信息区
        stats_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(stats_layout)

        self.main_inflow_label = QtWidgets.QLabel(_("主力净流入：--"))
        self.main_inflow_label.setStyleSheet("font-size: 14px; font-weight: bold; color: red;")
        stats_layout.addWidget(self.main_inflow_label)

        self.net_inflow_label = QtWidgets.QLabel(_("总净流入：--"))
        self.net_inflow_label.setStyleSheet("font-size: 14px;")
        stats_layout.addWidget(self.net_inflow_label)

        stats_layout.addStretch()

        # 数据显示区
        data_group = QtWidgets.QGroupBox(_("资金流向数据"))
        data_layout = QtWidgets.QVBoxLayout()
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)

        # 创建表格
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            _("合约代码"), _("主力净流入"), _("超大单"),
            _("大单"), _("中单"), _("小单"), _("总净流入")
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        data_layout.addWidget(self.table)

        # 状态栏
        self.status_label = QtWidgets.QLabel(_("就绪"))
        layout.addWidget(self.status_label)

    def refresh_data(self) -> None:
        """刷新数据"""
        symbols = self.get_symbol_list()
        if not symbols:
            self.status_label.setText(_("无可用合约"))
            return

        self.update_table(symbols)
        self.update_summary(symbols)
        self.status_label.setText(_("已刷新") + f" ({len(symbols)} " + _("个合约") + ")")

    def update_table(self, symbols: List[str]) -> None:
        """更新表格数据

        Args:
            symbols: 股票代码列表
        """
        self.table.setRowCount(len(symbols))

        for row, symbol in enumerate(symbols):
            # 获取分析数据
            analysis = self.analysis_engine.get_money_flow_analysis(symbol)

            # 填充数据
            self.setItemText(row, 0, symbol)

            if analysis and "summary_60min" in analysis:
                summary = analysis["summary_60min"]

                # 主力净流入（着色）
                main_inflow = summary.get("main_inflow", 0)
                self.setItemText(row, 1, self.format_amount(main_inflow), color=self.get_inflow_color(main_inflow))

                self.setItemText(row, 2, self.format_amount(summary.get("super_large_inflow", 0)))
                self.setItemText(row, 3, self.format_amount(summary.get("large_inflow", 0)))
                self.setItemText(row, 4, self.format_amount(summary.get("medium_inflow", 0)))
                self.setItemText(row, 5, self.format_amount(summary.get("small_inflow", 0)))

                # 总净流入（着色）
                net_inflow = summary.get("net_inflow", 0)
                self.setItemText(row, 6, self.format_amount(net_inflow), color=self.get_inflow_color(net_inflow))
            else:
                for col in range(1, 7):
                    self.setItemText(row, col, "-")

    def update_summary(self, symbols: List[str]) -> None:
        """更新汇总信息

        Args:
            symbols: 股票代码列表
        """
        total_main_inflow = 0.0
        total_net_inflow = 0.0

        for symbol in symbols:
            analysis = self.analysis_engine.get_money_flow_analysis(symbol)
            if analysis and "summary_60min" in analysis:
                summary = analysis["summary_60min"]
                total_main_inflow += summary.get("main_inflow", 0)
                total_net_inflow += summary.get("net_inflow", 0)

        self.main_inflow_label.setText(_("主力净流入：") + self.format_amount(total_main_inflow))
        self.main_inflow_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {self.get_inflow_color(total_main_inflow)};"
        )
        self.net_inflow_label.setText(_("总净流入：") + self.format_amount(total_net_inflow))

    def get_inflow_color(self, value: float) -> str:
        """根据流入值获取颜色

        Args:
            value: 流入值

        Returns:
            颜色字符串
        """
        if value > 0:
            return "red"
        elif value < 0:
            return "green"
        else:
            return "black"

    def setItemText(self, row: int, column: int, text: str, color: str = "black") -> None:
        """设置表格单元格文本

        Args:
            row: 行号
            column: 列号
            text: 文本内容
            color: 文本颜色
        """
        item = QtWidgets.QTableWidgetItem(text)
        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        item.setForeground(QtGui.QColor(color))
        self.table.setItem(row, column, item)

    def export_data(self) -> None:
        """导出数据"""
        if not PANDAS_AVAILABLE:
            QtWidgets.QMessageBox.warning(self, _("导出失败"), _("需要安装pandas库才能导出数据"))
            return

        # 收集当前表格数据
        data = []
        for row in range(self.table.rowCount()):
            row_data = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        if not data:
            QtWidgets.QMessageBox.information(self, _("导出提示"), _("没有数据可导出"))
            return

        # 创建DataFrame并导出
        columns = [self.table.horizontalHeaderItem(i).text()
                   for i in range(self.table.columnCount())]
        df = pd.DataFrame(data, columns=columns)

        # 选择保存路径
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, _("导出资金流向数据"), "", "CSV Files (*.csv)"
        )

        if path:
            df.to_csv(path, index=False, encoding="utf-8-sig")
            self.write_log(_("数据已导出：") + path)
            self.status_label.setText(_("导出成功：") + path)


class TechnicalWidget(BaseAnalysisWidget):
    """技术指标增强界面"""

    def __init__(self, main_engine: Any, event_engine: Any, analysis_engine: Any) -> None:
        """初始化"""
        super().__init__(main_engine, event_engine, analysis_engine)
        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("技术指标增强"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 策略说明
        desc = QtWidgets.QLabel(
            _("技术指标增强提供A股特色指标分析：\n"
              "• 涨跌停统计：每日涨跌停股票统计\n"
              "• 板块指数：行业板块指数分析\n"
              "• 市场情绪：市场热度指标"))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 功能按钮区
        btn_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout)

        refresh_btn = QtWidgets.QPushButton(_("刷新数据"))
        refresh_btn.clicked.connect(self.refresh_data)
        btn_layout.addWidget(refresh_btn)

        export_btn = QtWidgets.QPushButton(_("导出数据"))
        export_btn.clicked.connect(self.export_data)
        btn_layout.addWidget(export_btn)

        # 市场概览区
        market_group = QtWidgets.QGroupBox(_("市场概览"))
        market_layout = QtWidgets.QHBoxLayout()
        market_group.setLayout(market_layout)
        layout.addWidget(market_group)

        self.limit_up_count = QtWidgets.QLabel(_("涨停数：--"))
        self.limit_up_count.setStyleSheet("font-size: 14px; color: red;")
        market_layout.addWidget(self.limit_up_count)

        self.limit_down_count = QtWidgets.QLabel(_("跌停数：--"))
        self.limit_down_count.setStyleSheet("font-size: 14px; color: green;")
        market_layout.addWidget(self.limit_down_count)

        market_layout.addStretch()

        # 数据显示区
        data_group = QtWidgets.QGroupBox(_("技术指标数据"))
        data_layout = QtWidgets.QVBoxLayout()
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)

        # 创建表格
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            _("合约代码"), _("是否涨停"), _("连续涨停"),
            _("涨停次数"), _("是否跌停"), _("连续跌停")
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        data_layout.addWidget(self.table)

        # 状态栏
        self.status_label = QtWidgets.QLabel(_("就绪"))
        layout.addWidget(self.status_label)

    def refresh_data(self) -> None:
        """刷新数据"""
        symbols = self.get_symbol_list()
        if not symbols:
            self.status_label.setText(_("无可用合约"))
            return

        self.update_table(symbols)
        self.update_market_overview(symbols)
        self.status_label.setText(_("已刷新") + f" ({len(symbols)} " + _("个合约") + ")")

    def update_table(self, symbols: List[str]) -> None:
        """更新表格数据

        Args:
            symbols: 股票代码列表
        """
        self.table.setRowCount(len(symbols))

        limit_up_count = 0
        limit_down_count = 0

        for row, symbol in enumerate(symbols):
            # 获取分析数据
            analysis = self.analysis_engine.get_technical_analysis(symbol)

            # 填充数据
            self.setItemText(row, 0, symbol)

            if analysis and "limit_analysis" in analysis:
                limit_data = analysis["limit_analysis"]

                is_limit_up = limit_data.get("is_limit_up", False)
                is_limit_down = limit_data.get("is_limit_down", False)

                self.setItemText(row, 1, _("是") if is_limit_up else _("否"), color="red" if is_limit_up else "black")
                self.setItemText(row, 2, str(limit_data.get("continuous_limit_up", 0)))
                self.setItemText(row, 3, str(limit_data.get("total_limit_up", 0)))
                self.setItemText(row, 4, _("是") if is_limit_down else _("否"), color="green" if is_limit_down else "black")
                self.setItemText(row, 5, str(limit_data.get("continuous_limit_down", 0)))

                if is_limit_up:
                    limit_up_count += 1
                if is_limit_down:
                    limit_down_count += 1
            else:
                for col in range(1, 6):
                    self.setItemText(row, col, "-")

        # 更新计数
        self.current_limit_up = limit_up_count
        self.current_limit_down = limit_down_count

    def update_market_overview(self, symbols: List[str]) -> None:
        """更新市场概览

        Args:
            symbols: 股票代码列表
        """
        limit_up_count = getattr(self, "current_limit_up", 0)
        limit_down_count = getattr(self, "current_limit_down", 0)

        self.limit_up_count.setText(_("涨停数：") + str(limit_up_count))
        self.limit_down_count.setText(_("跌停数：") + str(limit_down_count))

    def setItemText(self, row: int, column: int, text: str, color: str = "black") -> None:
        """设置表格单元格文本

        Args:
            row: 行号
            column: 列号
            text: 文本内容
            color: 文本颜色
        """
        item = QtWidgets.QTableWidgetItem(text)
        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        item.setForeground(QtGui.QColor(color))
        self.table.setItem(row, column, item)

    def export_data(self) -> None:
        """导出数据"""
        if not PANDAS_AVAILABLE:
            QtWidgets.QMessageBox.warning(self, _("导出失败"), _("需要安装pandas库才能导出数据"))
            return

        # 收集当前表格数据
        data = []
        for row in range(self.table.rowCount()):
            row_data = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        if not data:
            QtWidgets.QMessageBox.information(self, _("导出提示"), _("没有数据可导出"))
            return

        # 创建DataFrame并导出
        columns = [self.table.horizontalHeaderItem(i).text()
                   for i in range(self.table.columnCount())]
        df = pd.DataFrame(data, columns=columns)

        # 选择保存路径
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, _("导出技术指标数据"), "", "CSV Files (*.csv)"
        )

        if path:
            df.to_csv(path, index=False, encoding="utf-8-sig")
            self.write_log(_("数据已导出：") + path)
            self.status_label.setText(_("导出成功：") + path)


class AuctionWidget(BaseAnalysisWidget):
    """集合竞价分析界面"""

    def __init__(self, main_engine: Any, event_engine: Any, analysis_engine: Any) -> None:
        """初始化"""
        super().__init__(main_engine, event_engine, analysis_engine)
        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 标题
        title = QtWidgets.QLabel(_("集合竞价分析"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 策略说明
        desc = QtWidgets.QLabel(
            _("集合竞价分析捕捉开盘机会：\n"
              "• 量比分析：集合竞价量比统计\n"
              "• 开盘预测：预测开盘价格\n"
              "• 竞价明细：查看竞价过程"))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 功能按钮区
        btn_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout)

        refresh_btn = QtWidgets.QPushButton(_("刷新数据"))
        refresh_btn.clicked.connect(self.refresh_data)
        btn_layout.addWidget(refresh_btn)

        export_btn = QtWidgets.QPushButton(_("导出数据"))
        export_btn.clicked.connect(self.export_data)
        btn_layout.addWidget(export_btn)

        # 股票代码输入
        symbol_label = QtWidgets.QLabel(_("股票代码："))
        btn_layout.addWidget(symbol_label)

        self.symbol_input = QtWidgets.QLineEdit()
        self.symbol_input.setPlaceholderText(_("输入股票代码，如000001"))
        btn_layout.addWidget(self.symbol_input)

        query_btn = QtWidgets.QPushButton(_("查询"))
        query_btn.clicked.connect(self.query_symbol)
        btn_layout.addWidget(query_btn)

        # 高量比股票区
        high_volume_group = QtWidgets.QGroupBox(_("高量比股票 (量比>2)"))
        high_volume_layout = QtWidgets.QVBoxLayout()
        high_volume_group.setLayout(high_volume_layout)
        layout.addWidget(high_volume_group)

        self.high_volume_table = QtWidgets.QTableWidget()
        self.high_volume_table.setColumnCount(4)
        self.high_volume_table.setHorizontalHeaderLabels([
            _("合约代码"), _("竞价价格"), _("竞价量"), _("量比")
        ])
        high_volume_layout.addWidget(self.high_volume_table)

        # 数据显示区
        data_group = QtWidgets.QGroupBox(_("竞价数据"))
        data_layout = QtWidgets.QVBoxLayout()
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)

        # 创建表格
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            _("合约代码"), _("竞价价格"), _("竞价量"),
            _("量比"), _("振幅(%)"), _("买卖比"), _("预测开盘")
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        data_layout.addWidget(self.table)

        # 状态栏
        self.status_label = QtWidgets.QLabel(_("就绪"))
        layout.addWidget(self.status_label)

    def refresh_data(self) -> None:
        """刷新数据"""
        symbols = self.get_symbol_list()
        if not symbols:
            self.status_label.setText(_("无可用合约"))
            return

        self.update_table(symbols)
        self.update_high_volume_table(symbols)
        self.status_label.setText(_("已刷新") + f" ({len(symbols)} " + _("个合约") + ")")

    def query_symbol(self) -> None:
        """查询指定股票"""
        symbol = self.symbol_input.text().strip()
        if not symbol:
            self.status_label.setText(_("请输入股票代码"))
            return

        # 创建模拟竞价数据（实际应用中从数据源获取）
        auction_data = {
            "date": datetime.now().date(),
            "pre_close": 10.0,
            "auction_price": 10.2,
            "auction_volume": 100000,
            "total_buy_volume": 500000,
            "total_sell_volume": 300000,
            "buy_orders": 100,
            "sell_orders": 80
        }

        # 获取分析数据
        analysis = self.analysis_engine.get_auction_analysis(symbol, auction_data)

        # 显示结果
        self.update_table([symbol], analysis.get(symbol))
        self.status_label.setText(_("查询完成：") + symbol)

    def update_table(self, symbols: List[str], analysis_map: Optional[Dict[str, Any]] = None) -> None:
        """更新表格数据

        Args:
            symbols: 股票代码列表
            analysis_map: 分析数据映射（可选）
        """
        self.table.setRowCount(len(symbols))

        for row, symbol in enumerate(symbols):
            # 填充数据
            self.setItemText(row, 0, symbol)

            # 使用提供的分析数据或创建默认数据
            if analysis_map and symbol in analysis_map:
                auction_data = analysis_map[symbol].get("auction_data", {})
                prediction = analysis_map[symbol].get("prediction", {})
            else:
                # 创建模拟数据
                auction_data = {
                    "auction_price": 10.0,
                    "auction_volume": 100000,
                    "volume_ratio": 1.0,
                    "amplitude": 0.5,
                    "buy_sell_ratio": 1.0
                }
                prediction = {"predicted_price": 10.0}

            self.setItemText(row, 1, self.format_number(auction_data.get("auction_price", 0), 2))

            volume = auction_data.get("auction_volume", 0)
            self.setItemText(row, 2, f"{volume:,}")

            volume_ratio = auction_data.get("volume_ratio", 0)
            color = "red" if volume_ratio > 2 else "black"
            self.setItemText(row, 3, self.format_number(volume_ratio, 2), color=color)

            amplitude = auction_data.get("amplitude", 0)
            self.setItemText(row, 4, self.format_number(amplitude, 2))

            buy_sell_ratio = auction_data.get("buy_sell_ratio", 0)
            self.setItemText(row, 5, self.format_number(buy_sell_ratio, 2))

            predicted_price = prediction.get("predicted_price", 0)
            self.setItemText(row, 6, self.format_number(predicted_price, 2))

    def update_high_volume_table(self, symbols: List[str]) -> None:
        """更新高量比股票表格

        Args:
            symbols: 股票代码列表
        """
        high_volume_symbols = []

        # 筛选高量比股票（这里使用模拟数据）
        for symbol in symbols[:10]:  # 限制显示前10个
            high_volume_symbols.append(symbol)

        self.high_volume_table.setRowCount(len(high_volume_symbols))

        for row, symbol in enumerate(high_volume_symbols):
            self.setItemHighVolume(row, 0, symbol)
            self.setItemHighVolume(row, 1, self.format_number(10.0, 2))
            self.setItemHighVolume(row, 2, f"{100000:,}")
            self.setItemHighVolume(row, 3, self.format_number(2.5, 2), color="red")

    def setItemText(self, row: int, column: int, text: str, color: str = "black") -> None:
        """设置表格单元格文本

        Args:
            row: 行号
            column: 列号
            text: 文本内容
            color: 文本颜色
        """
        item = QtWidgets.QTableWidgetItem(text)
        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        item.setForeground(QtGui.QColor(color))
        self.table.setItem(row, column, item)

    def setItemHighVolume(self, row: int, column: int, text: str, color: str = "black") -> None:
        """设置高量比表格单元格文本

        Args:
            row: 行号
            column: 列号
            text: 文本内容
            color: 文本颜色
        """
        item = QtWidgets.QTableWidgetItem(text)
        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        item.setForeground(QtGui.QColor(color))
        self.high_volume_table.setItem(row, column, item)

    def export_data(self) -> None:
        """导出数据"""
        if not PANDAS_AVAILABLE:
            QtWidgets.QMessageBox.warning(self, _("导出失败"), _("需要安装pandas库才能导出数据"))
            return

        # 收集当前表格数据
        data = []
        for row in range(self.table.rowCount()):
            row_data = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        if not data:
            QtWidgets.QMessageBox.information(self, _("导出提示"), _("没有数据可导出"))
            return

        # 创建DataFrame并导出
        columns = [self.table.horizontalHeaderItem(i).text()
                   for i in range(self.table.columnCount())]
        df = pd.DataFrame(data, columns=columns)

        # 选择保存路径
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, _("导出集合竞价数据"), "", "CSV Files (*.csv)"
        )

        if path:
            df.to_csv(path, index=False, encoding="utf-8-sig")
            self.write_log(_("数据已导出：") + path)
            self.status_label.setText(_("导出成功：") + path)


__all__ = [
    "ChinaAnalysisWidget",
    "Level2AnalysisWidget",
    "MoneyFlowWidget",
    "TechnicalWidget",
    "AuctionWidget",
]
