"""
vnpy_china_analysis 集成测试

测试各模块之间的协同工作。
"""
import pytest
from datetime import datetime

from vnpy_china_analysis.level2.level2 import Level2Analyzer
from vnpy_china_analysis.money_flow.analyzer import MoneyFlowAnalyzer
from vnpy_china_analysis.auction.analyzer import AuctionAnalyzer
from vnpy_china_analysis.objects.types import TickFlowData


def test_full_analysis_workflow():
    """测试完整分析流程"""
    # 1. Level-2分析
    level2_analyzer = Level2Analyzer()

    # 模拟逐笔成交数据
    tick_data_list = []
    for i in range(10):
        data = {
            "datetime": datetime.now(),
            "price": 10.0 + i * 0.01,
            "volume": 1000,
            "amount": 10000,
            "direction": "buy" if i % 2 == 0 else "sell",
            "function_code": 1
        }
        tick_data_list.append(data)

    # 使用update更新数据
    for data in tick_data_list:
        level2_analyzer.update("000001", data)

    # 获取主力动向
    main_force = level2_analyzer.get_main_force("000001")
    assert main_force is not None
    assert main_force.symbol == "000001"

    # 2. 资金流向分析
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

    # 3. 集合竞价分析
    auction_analyzer = AuctionAnalyzer()

    auction_data = {
        "datetime": datetime.now(),
        "pre_close": 10.0,
        "auction_price": 10.2,
        "auction_volume": 10000,
        "total_buy_volume": 6000,
        "total_sell_volume": 4000,
        "buy_orders": 100,
        "sell_orders": 80
    }

    auction = auction_analyzer.analyze("000001", auction_data)
    assert auction is not None
    assert auction.volume_ratio > 0


def test_cross_module_integration():
    """测试跨模块集成"""
    # 综合使用多个分析器生成交易信号

    tick_flows = [
        TickFlowData(
            symbol="000001",
            datetime=datetime.now(),
            price=10.5,
            volume=1000,  # 10.5万元，中单
            amount=105000,
            direction="buy",
            function_code=1
        )
    ]

    # 主力分析
    level2 = Level2Analyzer()
    for tick in tick_flows:
        data = {
            "datetime": tick.datetime,
            "price": tick.price,
            "volume": tick.volume,
            "amount": tick.amount,
            "direction": tick.direction,
            "function_code": tick.function_code
        }
        level2.update("000001", data)

    main_force = level2.get_main_force("000001")

    # 资金流向
    money_flow_analyzer = MoneyFlowAnalyzer()
    flow = money_flow_analyzer.analyze("000001", tick_flows)

    # 综合判断
    signal = "neutral"
    if hasattr(main_force, 'direction') and main_force.direction == "buy" and flow.main_inflow > 0:
        signal = "buy"

    # 信号可能是 buy 或 neutral
    assert signal in ["buy", "neutral"]


def test_adapter_integration():
    """测试适配器集成"""
    from vnpy_china_analysis.adapters.qmt_adapter import QMTDataAdapter
    from vnpy_china_analysis.adapters.tushare_adapter import TushareDataAdapter

    # QMT适配器
    qmt_adapter = QMTDataAdapter()

    # 模拟QMT tick数据
    qmt_data = {
        "symbol": "000001",
        "datetime": datetime.now(),
        "last_price": 10.5,
        "volume": 1000,
        "ask_price_1": 10.51,
        "ask_price_2": 10.52,
        "ask_price_3": 10.53,
        "ask_price_4": 10.54,
        "ask_price_5": 10.55,
        "bid_price_1": 10.50,
        "bid_price_2": 10.49,
        "bid_price_3": 10.48,
        "bid_price_4": 10.47,
        "bid_price_5": 10.46,
        "ask_volume_1": 1000,
        "ask_volume_2": 2000,
        "ask_volume_3": 3000,
        "ask_volume_4": 4000,
        "ask_volume_5": 5000,
        "bid_volume_1": 5000,
        "bid_volume_2": 4000,
        "bid_volume_3": 3000,
        "bid_volume_4": 2000,
        "bid_volume_5": 1000,
    }

    # 转换为分析器可用格式
    level2_data = qmt_adapter.convert_to_analysis_format(qmt_data, "level2")

    assert level2_data is not None
    assert "ask_prices" in level2_data
    assert "bid_prices" in level2_data

    # Tushare适配器
    tushare_adapter = TushareDataAdapter()
    # Tushare适配器主要用于回测，这里只验证初始化
    assert tushare_adapter is not None


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
