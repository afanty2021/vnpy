"""A股机器学习UI组件"""
from vnpy.trader.ui.qt import QtWidgets
from vnpy.trader.locale import _


class ChinaMlWidget(QtWidgets.QWidget):
    """A股机器学习主界面"""
    def __init__(self, main_engine, event_engine):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(_("A股机器学习"))
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(QtWidgets.QLabel(_("机器学习功能")))


__all__ = ["ChinaMlWidget"]
