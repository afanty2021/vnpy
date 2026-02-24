"""
资金分类器单元测试
"""
import pytest
from datetime import datetime
from vnpy_china_analysis.money_flow.classifier import MoneyFlowClassifier
from vnpy_china_analysis.objects.types import MoneyFlowLevel, TickFlowData


class TestMoneyFlowClassifier:
    """资金分类器测试"""

    def setup_method(self):
        """测试前置设置"""
        self.classifier = MoneyFlowClassifier()

    def test_classify_super_large_order(self):
        """测试超大单分类"""
        # 价格10元，10000手 = 10 * 10000 * 100 = 1000万元
        level = self.classifier.classify(price=10.0, volume=10000)

        assert level == MoneyFlowLevel.SUPER_LARGE

    def test_classify_large_order(self):
        """测试大单分类"""
        # 价格10元，500手 = 10 * 500 * 100 = 50万元 (20-100万范围)
        level = self.classifier.classify(price=10.0, volume=500)

        assert level == MoneyFlowLevel.LARGE

    def test_classify_medium_order(self):
        """测试中单分类"""
        # 价格10元，100手 = 10 * 100 * 100 = 10万元 (5-20万范围)
        level = self.classifier.classify(price=10.0, volume=100)

        assert level == MoneyFlowLevel.MEDIUM

    def test_classify_small_order(self):
        """测试小单分类"""
        # 价格10元，30手 = 10 * 30 * 100 = 3万元
        level = self.classifier.classify(price=10.0, volume=30)

        assert level == MoneyFlowLevel.SMALL

    def test_classify_boundary_super_large(self):
        """测试超大单边界"""
        # 刚好100万：价格10元，1000手 = 10 * 1000 * 100 = 100万元
        level = self.classifier.classify(price=10.0, volume=1000)
        assert level == MoneyFlowLevel.SUPER_LARGE

    def test_classify_boundary_large(self):
        """测试大单边界"""
        # 刚好20万：价格10元，200手 = 10 * 200 * 100 = 20万元
        level = self.classifier.classify(price=10.0, volume=200)
        assert level == MoneyFlowLevel.LARGE

    def test_classify_boundary_medium(self):
        """测试中单边界"""
        # 刚好5万：价格10元，50手 = 10 * 50 * 100 = 5万元
        level = self.classifier.classify(price=10.0, volume=50)
        assert level == MoneyFlowLevel.MEDIUM

    def test_custom_thresholds(self):
        """测试自定义阈值"""
        custom_thresholds = {
            MoneyFlowLevel.SUPER_LARGE: 500000,  # 50万
            MoneyFlowLevel.LARGE: 100000,       # 10万
            MoneyFlowLevel.MEDIUM: 20000,       # 2万
        }

        classifier = MoneyFlowClassifier(thresholds=custom_thresholds)

        # 价格10元，600手 = 10 * 600 * 100 = 60万元，应该是超大单
        level = classifier.classify(price=10.0, volume=600)
        assert level == MoneyFlowLevel.SUPER_LARGE

    def test_get_threshold(self):
        """测试获取阈值"""
        threshold = self.classifier.get_threshold(MoneyFlowLevel.SUPER_LARGE)
        assert threshold == 1000000  # 100万

        threshold = self.classifier.get_threshold(MoneyFlowLevel.LARGE)
        assert threshold == 200000  # 20万

    def test_classify_batch(self):
        """测试批量分类"""
        trades = [
            {"price": 10.0, "volume": 500},    # 大单 (50万)
            {"price": 10.0, "volume": 30},     # 小单 (3万)
            {"price": 10.0, "volume": 100},    # 中单 (10万)
        ]

        result = self.classifier.classify_batch(trades)

        assert len(result[MoneyFlowLevel.LARGE]) == 1
        assert len(result[MoneyFlowLevel.SMALL]) == 1
        assert len(result[MoneyFlowLevel.MEDIUM]) == 1

    def test_classify_by_amount(self):
        """测试按金额分类（向后兼容）"""
        # 直接使用金额分类
        level = self.classifier.classify_by_amount(1000000)  # 100万
        assert level == MoneyFlowLevel.SUPER_LARGE

        level = self.classifier.classify_by_amount(500000)  # 50万
        assert level == MoneyFlowLevel.LARGE
