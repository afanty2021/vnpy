"""
vnpy_china_analysis 集成测试

测试各模块之间的协同工作。
"""
import pytest
from datetime import datetime

from vnpy_china_analysis.level2 import Level2Analyzer
from vnpy_china_analysis.money_flow.analyzer import MoneyFlowAnalyzer
from vnpy_china_analysis.auction import AuctionAnalyzer
from vnpy_china_analysis.objects.types import TickFlowData


def test_money_flow_integration():
    """测试资金流向分析集成"""
    money_flow_analyzer = MoneyFlowAnalyzer()

    # 构造TickFlowData列表
    tick_flows = []
    for i in range(10):
        tick = TickFlowData(
            symbol="000001",
            datetime=datetime.now(),
            price=10.0 + i * 0.01,
            volume=1000,
            amount=10000,
            direction="buy" if i % 2 == 0 else "sell",
            function_code=1
        )
        tick_flows.append(tick)

    money_flow = money_flow_analyzer.analyze("000001", tick_flows)
    assert money_flow is not None
    assert money_flow.symbol == "000001"


def test_auction_integration():
    """测试集合竞价分析集成"""
    auction_analyzer = AuctionAnalyzer()

    auction_data = {
        "datetime": datetime.now(),
        "pre_close": 10.0,
        "auction_price": 10.2,
        "auction_volume": 10000,
        "total_buy_volume": 6000,
        "total_sell_volume": 4000,
        "buy_orders": 100,
        "sell_orders": 80,
        "volume_ratio": 1.5,  # 提供量比数据
        "avg_volume": 5000    # 提供平均成交量
    }

    auction = auction_analyzer.analyze("000001", auction_data)
    assert auction is not None
    # volume_ratio会被计算或使用提供的值
    assert auction.auction_price == 10.2


def test_performance_requirement():
    """测试性能要求"""
    import time

    # 构造测试数据
    tick_flows = []
    for i in range(100):
        tick = TickFlowData(
            symbol=f"{i:06d}.SZ",
            datetime=datetime.now(),
            price=10.0,
            volume=500,
            amount=5000,
            direction="buy",
            function_code=1
        )
        tick_flows.append(tick)

    # 测试资金分析性能
    analyzer = MoneyFlowAnalyzer()

    start = time.time()
    for tick in tick_flows:
        analyzer.analyze(tick.symbol, [tick])

    elapsed = time.time() - start

    # 100只股票分析应在1秒内完成
    assert elapsed < 1.0
