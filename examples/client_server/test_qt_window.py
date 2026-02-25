#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""简单的Qt窗口测试"""

import sys
from pathlib import Path

# 设置Qt平台
import os
os.environ['QT_QPA_PLATFORM'] = 'cocoa'

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VeighNa RPC 测试窗口")
        self.setGeometry(100, 100, 400, 300)

        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建布局
        layout = QVBoxLayout()

        # 添加标签
        label = QLabel("这是一个测试窗口")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        # 添加按钮
        button = QPushButton("点击测试")
        button.clicked.connect(self.on_click)
        layout.addWidget(button)

        central_widget.setLayout(layout)

    def on_click(self):
        print("按钮被点击了！")

def main():
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    print("窗口已显示")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
