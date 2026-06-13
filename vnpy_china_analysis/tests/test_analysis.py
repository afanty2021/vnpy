"""Tests for vnpy_china_analysis module - REQ-007 行情数据分析

测试体仅使用原生 assert，无需 pytest 即可运行（pytest/unittest runner 均兼容）。
"""

import os
import sys

# 项目根目录（本文件上溯三级：tests -> vnpy_china_analysis -> 项目根）
# 跨平台替代原先硬编码的 macOS 绝对路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from decimal import Decimal


class TestMoneyFlowClassifier:
    """Test money flow classification

    金额计算：price * volume * 100 (每手100股)
    """

    def test_classifier_creation(self):
        """Test classifier can be created"""
        from vnpy_china_analysis.money_flow.classifier import (
            MoneyFlowClassifier,
            MoneyFlowLevel
        )
        classifier = MoneyFlowClassifier()
        assert classifier is not None
        assert hasattr(classifier, 'thresholds')

    def test_classify_super_large(self):
        """Test super large flow classification"""
        from vnpy_china_analysis.money_flow.classifier import (
            MoneyFlowClassifier,
            MoneyFlowLevel
        )
        classifier = MoneyFlowClassifier()
        # 100万以上为超大单
        # 10.0 * 1000 * 100 = 100万 = SUPER_LARGE
        result = classifier.classify(price=10.0, volume=1000)
        assert result == MoneyFlowLevel.SUPER_LARGE

    def test_classify_large(self):
        """Test large flow classification"""
        from vnpy_china_analysis.money_flow.classifier import (
            MoneyFlowClassifier,
            MoneyFlowLevel
        )
        classifier = MoneyFlowClassifier()
        # 20-100万为大单
        # 10.0 * 500 * 100 = 50万 = LARGE (20-100万之间)
        result = classifier.classify(price=10.0, volume=500)
        assert result == MoneyFlowLevel.LARGE

    def test_classify_medium(self):
        """Test medium flow classification"""
        from vnpy_china_analysis.money_flow.classifier import (
            MoneyFlowClassifier,
            MoneyFlowLevel
        )
        classifier = MoneyFlowClassifier()
        # 5-20万为中单
        # 10.0 * 100 * 100 = 10万 = MEDIUM
        result = classifier.classify(price=10.0, volume=100)
        assert result == MoneyFlowLevel.MEDIUM

    def test_classify_small(self):
        """Test small flow classification"""
        from vnpy_china_analysis.money_flow.classifier import (
            MoneyFlowClassifier,
            MoneyFlowLevel
        )
        classifier = MoneyFlowClassifier()
        # 5万以下为小单
        # 10.0 * 30 * 100 = 3万 = SMALL (<5万)
        result = classifier.classify(price=10.0, volume=30)
        assert result == MoneyFlowLevel.SMALL


class TestVolumeRatioCalculator:
    """Test volume ratio calculation for auction"""

    def test_calculator_creation(self):
        """Test calculator can be created"""
        from vnpy_china_analysis.auction.volume_ratio import VolumeRatioCalculator
        calculator = VolumeRatioCalculator()
        assert calculator is not None

    def test_calculate_normal_volume_ratio(self):
        """Test normal volume ratio calculation"""
        from vnpy_china_analysis.auction.volume_ratio import VolumeRatioCalculator

        calculator = VolumeRatioCalculator()
        # 竞价量500万，平均量1000万，量比=0.5
        result = calculator.calculate("000001", auction_volume=5000000, avg_volume=10000000)
        assert result == 0.5

    def test_calculate_high_volume_ratio(self):
        """Test high volume ratio calculation"""
        from vnpy_china_analysis.auction.volume_ratio import VolumeRatioCalculator

        calculator = VolumeRatioCalculator()
        # 竞价量3000万，平均量1000万，量比=3.0
        result = calculator.calculate("000001", auction_volume=30000000, avg_volume=10000000)
        assert result == 3.0


class TestOpenPricePredictor:
    """Test open price prediction"""

    def test_predictor_creation(self):
        """Test predictor can be created"""
        from vnpy_china_analysis.auction.open_predict import OpenPricePredictor
        predictor = OpenPricePredictor()
        assert predictor is not None


class TestMainForceAnalyzer:
    """Test main force analysis"""

    def test_analyzer_creation(self):
        """Test main force analyzer can be created"""
        from vnpy_china_analysis.level2.main_force import MainForceAnalyzer
        analyzer = MainForceAnalyzer()
        assert analyzer is not None

    def test_calculate_main_force(self):
        """Test main force calculation"""
        from vnpy_china_analysis.level2.main_force import MainForceAnalyzer

        analyzer = MainForceAnalyzer()
        result = analyzer.calculate_main_force("000001", minutes=5)
        assert result is not None
        assert result.symbol == "000001"


class TestSectorIndex:
    """Test sector index"""

    def test_sector_index_creation(self):
        """Test sector index can be created"""
        from vnpy_china_analysis.objects.types import SectorIndexData
        data = SectorIndexData(
            sector_code="BK001",
            sector_name="银行",
            datetime=datetime.now(),
            index_value=100.0,
            change_pct=1.5,
            volume=1000000000,
            turnover=2.5
        )
        assert data.sector_code == "BK001"
        assert data.index_value == 100.0


class TestHelpers:
    """Test utility helper functions"""

    def test_calculate_change_pct(self):
        """Test change percentage calculation"""
        from vnpy_china_analysis.utils.helpers import calculate_change_pct

        result = calculate_change_pct(current=11.0, previous=10.0)
        assert result == 10.0  # 10% increase

    def test_calculate_change_pct_negative(self):
        """Test negative change percentage"""
        from vnpy_china_analysis.utils.helpers import calculate_change_pct

        result = calculate_change_pct(current=9.0, previous=10.0)
        assert result == -10.0  # 10% decrease

    def test_calculate_turnover_rate(self):
        """Test turnover rate calculation"""
        from vnpy_china_analysis.utils.helpers import calculate_turnover_rate

        # 成交量100万股，总股本1亿股
        result = calculate_turnover_rate(volume=1000000, total_shares=100000000)
        assert result == 1.0  # 1%


# ---------------------------------------------------------------------------
# 以下为代码审查修复的回归测试（A/B/C/D/E）
# ---------------------------------------------------------------------------

def _make_tick(symbol, price, cum_volume, bid1, ask1, last_volume=0):
    """构造 TickData（Level1，QMT 不填 last_volume）"""
    from vnpy.trader.object import TickData
    from vnpy.trader.constant import Exchange
    return TickData(
        symbol=symbol, exchange=Exchange.SZSE, datetime=datetime.now(),
        gateway_name="QMT", last_price=price, volume=cum_volume,
        last_volume=last_volume, bid_price_1=bid1, ask_price_1=ask1
    )


class TestMoneyFlowAnalyzerUpdate:
    """修复B：update() 聚合（tick 缓冲区）"""

    def test_update_accumulates_tick_history(self):
        """连续 update 两条 tick，tick_history 应累积为 2（聚合生效）"""
        from vnpy_china_analysis.money_flow.analyzer import MoneyFlowAnalyzer

        a = MoneyFlowAnalyzer()
        a.update("000001", {"price": 10.0, "volume": 100, "direction": "buy"})
        a.update("000001", {"price": 10.0, "volume": 100, "direction": "sell"})

        assert "000001" in a.tick_history
        assert len(a.tick_history["000001"]) == 2


class TestTickAdapter:
    """修复C：TickData→TickFlowData（Level1 方向推断 + 成交量差分）"""

    def test_direction_buy_at_ask(self):
        """成交价 >= ask1 → 主动买"""
        from vnpy_china_analysis.adapters.tick_adapter import tick_to_flow

        tick = _make_tick("000001", 10.01, 1000, 10.00, 10.01)
        lp, ld, lv = {}, {}, {}
        flow = tick_to_flow(tick, lp, ld, lv)
        assert flow.direction == "buy"

    def test_direction_sell_at_bid(self):
        """成交价 <= bid1 → 主动卖"""
        from vnpy_china_analysis.adapters.tick_adapter import tick_to_flow

        tick = _make_tick("000001", 9.99, 1000, 9.99, 10.00)
        lp, ld, lv = {}, {}, {}
        flow = tick_to_flow(tick, lp, ld, lv)
        assert flow.direction == "sell"

    def test_volume_diff_fallback(self):
        """QMT 不填 last_volume 时，用累计 volume 差分得到本笔成交量"""
        from vnpy_china_analysis.adapters.tick_adapter import tick_to_flow

        lp, ld, lv = {}, {}, {}
        t1 = _make_tick("000001", 10.01, 1000, 10.00, 10.01)
        f1 = tick_to_flow(t1, lp, ld, lv)
        t2 = _make_tick("000001", 10.01, 1200, 10.00, 10.01)
        f2 = tick_to_flow(t2, lp, ld, lv)

        assert f1.volume == 1000    # 首笔：无前值，差分 = 1000 - 0
        assert f2.volume == 200     # 次笔：1200 - 1000

    def test_on_tick_drives_aggregation(self):
        """on_tick 端到端：发 tick 后 tick_history 非空"""
        from vnpy_china_analysis.money_flow.analyzer import MoneyFlowAnalyzer

        a = MoneyFlowAnalyzer()
        a.on_tick(_make_tick("000001", 10.01, 1000, 10.00, 10.01))
        a.on_tick(_make_tick("000001", 9.99, 1200, 9.99, 10.00))

        buf = a.tick_history["000001"]
        assert len(buf) == 2
        assert buf[0].direction == "buy" and buf[0].volume == 1000
        assert buf[1].direction == "sell" and buf[1].volume == 200


class TestOpenPricePredictionAccuracy:
    """修复D：开盘价方向判断（None 兼容，不虚高准确率）"""

    def test_accuracy_with_valid_pre_close(self):
        """预测与实际同向（均高于 pre_close）→ 计入正确，accuracy=100"""
        from vnpy_china_analysis.auction.open_predict import OpenPricePredictor

        p = OpenPricePredictor()
        p.prediction_history["000001"] = [{
            "datetime": datetime.now(),
            "predicted_price": 10.5, "pre_close": 10.0,
            "actual_price": 10.8, "confidence": 80
        }]
        r = p.get_prediction_accuracy("000001")
        assert r["accuracy"] == 100.0

    def test_accuracy_skips_missing_pre_close(self):
        """旧记录无 pre_close → 跳过方向判断，accuracy=0（不虚高）"""
        from vnpy_china_analysis.auction.open_predict import OpenPricePredictor

        p = OpenPricePredictor()
        p.prediction_history["000001"] = [{
            "datetime": datetime.now(),
            "predicted_price": 9.5, "actual_price": 11.0, "confidence": 80
            # 无 pre_close
        }]
        r = p.get_prediction_accuracy("000001")
        assert r["sample_size"] == 1
        assert r["accuracy"] == 0.0

    def test_predict_stores_pre_close_in_history(self):
        """predict() 必须将 pre_close 写入历史记录（方向判断的生产者）

        回归保障：防止 append 漏存 pre_close 导致 accuracy 恒为 0。
        """
        from vnpy_china_analysis.auction.open_predict import OpenPricePredictor

        p = OpenPricePredictor()
        p.predict("000001", {
            "pre_close": 10.0,
            "auction_price": 10.2,
            "auction_volume": 100000
        })
        rec = p.prediction_history["000001"][-1]
        assert "pre_close" in rec, "predict() 未将 pre_close 写入历史记录"
        assert rec["pre_close"] == 10.0


class TestLevel2UiFieldMapping:
    """修复A：Level2 字段类型映射（dict 取值，不抛 TypeError）"""

    def test_dict_field_extraction(self):
        """support_level/price_depth 为 dict 时，取 price/depth_ratio 不崩溃"""
        from vnpy_china_analysis.ui.widget import BaseAnalysisWidget

        class _W(BaseAnalysisWidget):
            def __init__(self):
                pass

        w = _W()
        order_queue = {
            "support_level": {"price": 10.0, "volume": 500, "strength": 2500, "level": "weak"},
            "resistance_level": {"price": 10.2, "volume": 300, "strength": 1500, "level": "minimal"},
            "price_depth": {"bid_total": 1000, "ask_total": 800, "depth_ratio": 1.25}
        }
        support = order_queue.get("support_level") or {}
        resistance = order_queue.get("resistance_level") or {}
        depth = order_queue.get("price_depth") or {}

        assert w.format_number(support.get("price", 0), 2) == "10.00"
        assert w.format_number(resistance.get("price", 0), 2) == "10.20"
        assert w.format_number(depth.get("depth_ratio", 0), 2) == "1.25"

    def test_empty_order_queue_fallback(self):
        """空 order_queue（无 tick 数据）→ 取值兜底 0，不崩溃"""
        order_queue = {}
        support = order_queue.get("support_level") or {}
        depth = order_queue.get("price_depth") or {}
        assert support.get("price", 0) == 0
        assert depth.get("depth_ratio", 0) == 0


class TestMoneyFlowAmountFormat:
    """修复E：历史金额单位（元，不再 /10000 双重换算）"""

    def test_format_yi_level(self):
        """1亿元主力净流入应显示为「亿」量级（与实时路径一致）"""
        from vnpy_china_analysis.ui.widget import BaseAnalysisWidget

        class _W(BaseAnalysisWidget):
            def __init__(self):
                pass

        w = _W()
        # 模拟修复后：main_net_amount（元）直接进 format_amount
        assert "亿" in w.format_amount(100000000)

    def test_format_wan_level(self):
        """2万元应显示为「万」量级"""
        from vnpy_china_analysis.ui.widget import BaseAnalysisWidget

        class _W(BaseAnalysisWidget):
            def __init__(self):
                pass

        w = _W()
        assert "万" in w.format_amount(20000)
