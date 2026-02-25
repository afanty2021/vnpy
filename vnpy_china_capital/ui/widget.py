"""A股资金管理UI组件"""
from vnpy.trader.ui.qt import QtWidgets
from vnpy.trader.locale import _


class ChinaCapitalWidget(QtWidgets.QWidget):
    """A股资金管理主界面"""
    def __init__(self, main_engine, event_engine):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(_("A股资金管理"))
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(QtWidgets.QLabel(_("资金管理功能")))


__all__ = ["ChinaCapitalWidget"]
