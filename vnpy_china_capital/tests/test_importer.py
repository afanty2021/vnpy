"""Tests for QMTHistoryImporter - C3 类型一致性回归"""

import os
import sys
# 项目根目录（本文件上溯三级：tests -> vnpy_china_capital -> 项目根）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime

from vnpy.trader.object import TradeData
from vnpy.trader.constant import Exchange, Direction, Offset
from vnpy_china_capital.importer import QMTHistoryImporter


class TestImporterDirectionValue:
    """C3: importer 存 .value 字符串（非枚举对象），与 gui_engine/DB 路径一致"""

    def test_convert_direction_is_value_string(self):
        """convert_to_capital_flows 产出的 direction/offset 应为 .value 字符串"""
        imp = QMTHistoryImporter(main_engine=None)
        trade = TradeData(
            gateway_name="QMT",
            symbol="000001",
            exchange=Exchange.SZSE,
            orderid="o",
            tradeid="t",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=10.0,
            volume=100,
            datetime=datetime(2024, 1, 1),
        )
        flow = imp.convert_to_capital_flows([trade], {"000001": 100000})[0]

        # 关键：direction/offset 是字符串（.value），非枚举对象
        assert isinstance(flow["direction"], str), "direction 应为 .value 字符串，非枚举对象"
        assert isinstance(flow["offset"], str)
        assert flow["direction"] == Direction.LONG.value
        assert flow["offset"] == Offset.OPEN.value

    def test_convert_none_direction_safe(self):
        """direction 为 None 时安全兜底为空串"""
        imp = QMTHistoryImporter(main_engine=None)
        trade = TradeData(
            gateway_name="QMT",
            symbol="000001",
            exchange=Exchange.SZSE,
            orderid="o",
            tradeid="t",
            direction=None,
            offset=Offset.OPEN,
            price=10.0,
            volume=100,
            datetime=datetime(2024, 1, 1),
        )
        flow = imp.convert_to_capital_flows([trade], {})[0]
        assert flow["direction"] == ""
