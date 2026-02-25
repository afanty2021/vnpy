"""Tests for vnpy_china_analysis module - REQ-007 行情数据分析"""

import sys
sys.path.insert(0, '/Users/berton/Github/vnpy')

import pytest
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
