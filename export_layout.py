# -*- coding: utf-8 -*-
"""导出 vnpy 窗口布局到项目文件，便于 git 提交 + 跨平台复用。

用法（两步）：
  1. 启动 run_qmt_client.py，确认布局正确（dock 被设了固定英文 objectName，
     restore_submitted_layout 会在启动时设），然后关闭客户端。
  2. python export_layout.py

原理：
  - save_window_setting("custom") → QSettings 存注册表（Windows）
  - 本脚本从注册表读 state/geometry → QByteArray.toBase64 → JSON 文件
  - run_qmt_client.py 启动时读文件 → QByteArray.fromBase64 → restoreState
  - 所有 dock 设了固定英文 objectName（position_monitor/tick_monitor/...），
    saveState/restoreState 用 objectName 匹配，保证 Windows ↔ macOS 兼容。
"""
import sys
import json
from pathlib import Path

import vnpy
from vnpy.trader.utility import TRADER_DIR
from PySide6 import QtCore

WINDOW_TITLE = f"VeighNa Trader 社区版 - {vnpy.__version__}   [{TRADER_DIR}]"
OUT_DIR = Path(__file__).parent / "examples" / "client_server" / "layout"
OUT = OUT_DIR / "custom_layout.json"

app = QtCore.QCoreApplication(sys.argv)
settings = QtCore.QSettings(WINDOW_TITLE, "custom")


def qba_to_b64(obj):
    """QByteArray → base64 字符串（Qt toBase64 编码，与 fromBase64 配对）。"""
    if isinstance(obj, QtCore.QByteArray):
        return bytes(obj.toBase64()).decode()
    return ""


layout = {
    "state": qba_to_b64(settings.value("state")),
    "geometry": qba_to_b64(settings.value("geometry")),
}
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(layout, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"布局已导出到 {OUT}")
print(f"  state 长度: {len(layout['state'])} B64, geometry 长度: {len(layout['geometry'])} B64")
