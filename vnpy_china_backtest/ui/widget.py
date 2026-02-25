"""A股回测UI组件"""
from vnpy.trader.ui.qt import QtWidgets
from vnpy.trader.locale import _


class ChinaBacktestWidget(QtWidgets.QWidget):
    """A股回测主界面"""

    def __init__(self, main_engine, event_engine):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(_("A股策略回测"))
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(QtWidgets.QLabel(_("A股回测功能")))


__all__ = ["ChinaBacktestWidget"]
