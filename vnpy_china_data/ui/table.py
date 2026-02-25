"""A股数据表格组件"""
from typing import Any, Optional, List
from datetime import date

from vnpy.trader.ui.qt import QtWidgets, QtCore, QtGui
from vnpy.trader.ui.widget import BaseCell
from vnpy.trader.locale import _


class PnlCell(BaseCell):
    """用于显示带颜色数字的单元格（正数为红，负数为绿）"""

    def __init__(self, content: Any, data: Any) -> None:
        super().__init__(content, data)

    def set_content(self, content: Any, data: Any) -> None:
        """设置内容并根据数值设置颜色"""
        if content is None:
            content = 0.0

        value = float(content)
        text = f"{value:+.2f}"

        if value > 0:
            self.setForeground(QtGui.QColor("red"))
        elif value < 0:
            self.setForeground(QtGui.QColor("green"))
        else:
            self.setForeground(QtGui.QColor("black"))

        self.setText(text)
        self._data = data


class DateCell(BaseCell):
    """用于显示日期的单元格"""

    def __init__(self, content: Any, data: Any) -> None:
        super().__init__(content, data)

    def set_content(self, content: Any, data: Any) -> None:
        """设置日期显示"""
        if content is None:
            self.setText("-")
            return

        if isinstance(content, date):
            self.setText(content.strftime("%Y-%m-%d"))
        else:
            self.setText(str(content))
        self._data = data


class DragonTigerTable(QtWidgets.QTableWidget):
    """龙虎榜数据表格"""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        # 表格配置
        self.headers: dict = {
            "symbol": {"display": "代码", "cell": BaseCell, "update": False},
            "name": {"display": "名称", "cell": BaseCell, "update": False},
            "trade_date": {"display": "交易日期", "cell": DateCell, "update": False},
            "close_price": {"display": "收盘价", "cell": BaseCell, "update": False},
            "change_pct": {"display": "涨跌幅(%)", "cell": PnlCell, "update": False},
            "turnover_rate": {"display": "换手率(%)", "cell": BaseCell, "update": False},
            "institution_net_buy": {"display": "机构净买入", "cell": PnlCell, "update": False},
            "broker_net_buy": {"display": "营业部净买入", "cell": PnlCell, "update": False},
            "total_net_buy": {"display": "总净买入", "cell": PnlCell, "update": False},
            "reason": {"display": "上榜原因", "cell": BaseCell, "update": False},
        }

        self.init_ui()

    def init_ui(self) -> None:
        """初始化界面"""
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels([h["display"] for h in self.headers.values()])

        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSortingEnabled(True)

        # 右键菜单
        self.menu = QtWidgets.QMenu(self)

        resize_action = QtGui.QAction(_("调整列宽"), self)
        resize_action.triggered.connect(self.resize_columns)
        self.menu.addAction(resize_action)

    def update_data(self, data_list: List[Any]) -> None:
        """更新表格数据"""
        # 清空现有数据
        self.setRowCount(0)

        if not data_list:
            return

        # 插入新数据
        self.setRowCount(len(data_list))
        for row, data in enumerate(data_list):
            for col, (field, setting) in enumerate(self.headers.items()):
                try:
                    content = getattr(data, field, None)
                    cell = setting["cell"](content, data)
                    self.setItem(row, col, cell)
                except Exception:
                    pass

        # 自动调整列宽
        self.resize_columns()

    def resize_columns(self) -> None:
        """调整列宽"""
        self.horizontalHeader().resizeSections(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        """显示右键菜单"""
        self.menu.popup(QtGui.QCursor.pos())


class NorthboundTable(QtWidgets.QTableWidget):
    """北向资金数据表格"""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self.headers: dict = {
            "market": {"display": "市场", "cell": BaseCell, "update": False},
            "trade_date": {"display": "交易日期", "cell": DateCell, "update": False},
            "buy_volume": {"display": "买入金额", "cell": BaseCell, "update": False},
            "sell_volume": {"display": "卖出金额", "cell": BaseCell, "update": False},
            "net_inflow": {"display": "净流入", "cell": PnlCell, "update": False},
        }

        self.init_ui()

    def init_ui(self) -> None:
        """初始化界面"""
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels([h["display"] for h in self.headers.values()])

        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSortingEnabled(False)

        # 右键菜单
        self.menu = QtWidgets.QMenu(self)

        resize_action = QtGui.QAction(_("调整列宽"), self)
        resize_action.triggered.connect(self.resize_columns)
        self.menu.addAction(resize_action)

    def update_data(self, data: Any) -> None:
        """更新表格数据

        Args:
            data: NorthboundFlowData对象
        """
        self.setRowCount(0)

        if not data:
            return

        # 创建三行数据：沪股通、深股通、合计
        rows_data = [
            {
                "market": "沪股通",
                "trade_date": data.trade_date,
                "buy_volume": data.sh_buy_volume,
                "sell_volume": data.sh_sell_volume,
                "net_inflow": data.sh_net_inflow,
            },
            {
                "market": "深股通",
                "trade_date": data.trade_date,
                "buy_volume": data.sz_buy_volume,
                "sell_volume": data.sz_sell_volume,
                "net_inflow": data.sz_net_inflow,
            },
            {
                "market": "合计",
                "trade_date": data.trade_date,
                "buy_volume": data.sh_buy_volume + data.sz_buy_volume,
                "sell_volume": data.sh_sell_volume + data.sz_sell_volume,
                "net_inflow": data.total_net_inflow,
            },
        ]

        self.setRowCount(len(rows_data))
        for row, row_data in enumerate(rows_data):
            # 创建数据对象（简单对象用于访问属性）
            class DataObj:
                def __init__(self, **kwargs):
                    for k, v in kwargs.items():
                        setattr(self, k, v)

            obj = DataObj(**row_data)

            for col, (field, setting) in enumerate(self.headers.items()):
                try:
                    content = getattr(obj, field, None)
                    cell = setting["cell"](content, obj)
                    self.setItem(row, col, cell)
                except Exception:
                    pass

        # 高亮合计行
        if self.rowCount() >= 3:
            for col in range(self.columnCount()):
                item = self.item(2, col)
                if item:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)

        self.resize_columns()

    def resize_columns(self) -> None:
        """调整列宽"""
        self.horizontalHeader().resizeSections(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        """显示右键菜单"""
        self.menu.popup(QtGui.QCursor.pos())


__all__ = ["DragonTigerTable", "NorthboundTable", "PnlCell", "DateCell"]
