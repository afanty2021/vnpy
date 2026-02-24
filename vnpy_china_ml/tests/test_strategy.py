"""
策略模块单元测试

测试A股机器学习策略基类和信号生成器的功能。
"""

import unittest
import numpy as np
from datetime import datetime, timedelta

from vnpy_china_ml.strategy.china_ml_strategy import ChinaMLStrategy
from vnpy_china_ml.strategy.signal_generator import (
    SignalGenerator,
    AdaptiveSignalGenerator,
    MultiSignalGenerator
)
from vnpy_china_ml.utils.types import ModelType, SignalType, PredictionResult


class TestChinaMLStrategy(unittest.TestCase):
    """测试A股机器学习策略基类"""

    def test_strategy_initialization(self):
        """测试策略初始化"""
        strategy = ChinaMLStrategy()
        self.assertEqual(strategy.model.model_type, ModelType.LIGHTGBM)
        self.assertFalse(strategy.is_initialized)
        self.assertEqual(len(strategy.factors), 0)

    def test_strategy_initialization_custom_model(self):
        """测试自定义模型类型初始化"""
        strategy = ChinaMLStrategy(model_type=ModelType.RANDOM_FOREST)
        self.assertEqual(strategy.model.model_type, ModelType.RANDOM_FOREST)

    def test_strategy_with_retrain_interval(self):
        """测试自定义重训练间隔"""
        strategy = ChinaMLStrategy(retrain_interval_days=60)
        self.assertEqual(strategy.retrain_interval_days, 60)

    def test_initialize(self):
        """测试初始化方法"""
        strategy = ChinaMLStrategy()
        result = strategy.initialize()
        self.assertTrue(result)
        self.assertTrue(strategy.is_initialized)

    def test_add_factor(self):
        """测试添加因子"""
        from vnpy_china_ml.factors.base import BaseFactor
        from vnpy_china_ml.utils.types import FactorType

        class DummyFactor(BaseFactor):
            def calculate(self, data):
                return data

        factor = DummyFactor("test_factor", FactorType.TECHNICAL)
        strategy = ChinaMLStrategy()

        strategy.add_factor(factor)
        self.assertEqual(len(strategy.factors), 1)

        # 添加重复因子应该无效
        strategy.add_factor(factor)
        self.assertEqual(len(strategy.factors), 1)

    def test_remove_factor(self):
        """测试移除因子"""
        from vnpy_china_ml.factors.base import BaseFactor
        from vnpy_china_ml.utils.types import FactorType

        class DummyFactor(BaseFactor):
            def calculate(self, data):
                return data

        factor = DummyFactor("test_factor", FactorType.TECHNICAL)
        strategy = ChinaMLStrategy()

        strategy.add_factor(factor)
        self.assertEqual(len(strategy.factors), 1)

        strategy.remove_factor(factor)
        self.assertEqual(len(strategy.factors), 0)

    def test_get_factors(self):
        """测试获取因子列表"""
        from vnpy_china_ml.factors.base import BaseFactor
        from vnpy_china_ml.utils.types import FactorType

        class DummyFactor(BaseFactor):
            def calculate(self, data):
                return data

        factor1 = DummyFactor("factor1", FactorType.TECHNICAL)
        factor2 = DummyFactor("factor2", FactorType.TECHNICAL)
        strategy = ChinaMLStrategy()

        strategy.add_factor(factor1)
        strategy.add_factor(factor2)

        factors = strategy.get_factors()
        self.assertEqual(len(factors), 2)

    def test_on_bar_not_initialized(self):
        """测试未初始化时on_bar返回None"""
        strategy = ChinaMLStrategy()
        bar = {"symbol": "000001.SZ", "close": 10.5}

        signal = strategy.on_bar(bar)
        self.assertIsNone(signal)

    def test_on_bar_initialized(self):
        """测试初始化后on_bar"""
        strategy = ChinaMLStrategy()
        strategy.initialize()

        bar = {
            "symbol": "000001.SZ",
            "datetime": datetime.now(),
            "open": 10.0,
            "high": 10.5,
            "low": 9.8,
            "close": 10.2,
            "volume": 1000000
        }

        signal = strategy.on_bar(bar)
        self.assertIsInstance(signal, SignalType)

    def test_prepare_features_empty(self):
        """测试无因子时特征准备"""
        strategy = ChinaMLStrategy()
        strategy.initialize()

        bar = {"symbol": "000001.SZ", "close": 10.5}
        features = strategy.prepare_features(bar)

        self.assertEqual(len(features), 0)

    def test_predict_signal_empty_features(self):
        """测试空特征时信号预测"""
        strategy = ChinaMLStrategy()
        strategy.initialize()

        signal = strategy.predict_signal(np.array([]))
        self.assertEqual(signal, SignalType.HOLD)

    def test_predict_signal_not_trained(self):
        """测试模型未训练时信号预测"""
        strategy = ChinaMLStrategy()
        strategy.initialize()

        features = np.array([1.0, 2.0, 3.0])
        signal = strategy.predict_signal(features)
        self.assertEqual(signal, SignalType.HOLD)

    def test_predict_signal_trained(self):
        """测试模型训练后信号预测"""
        strategy = ChinaMLStrategy()
        strategy.initialize()

        # 训练模型
        np.random.seed(42)
        X_train = np.random.randn(100, 5)
        y_train = np.random.randn(100)

        strategy.retrain_model(X_train, y_train)

        # 预测
        X_test = np.array([[1.0, 2.0, 3.0, 4.0, 5.0]])
        signal = strategy.predict_signal(X_test[0])

        self.assertIsInstance(signal, SignalType)

    def test_should_retrain_not_trained(self):
        """测试未训练时应该重训练"""
        strategy = ChinaMLStrategy()
        self.assertTrue(strategy.should_retrain())

    def test_should_retrain_no_last_train_date(self):
        """测试没有训练日期时应该重训练"""
        strategy = ChinaMLStrategy()
        strategy.model.is_trained = True
        self.assertTrue(strategy.should_retrain())

    def test_should_retrain_interval_passed(self):
        """测试超过重训练间隔"""
        strategy = ChinaMLStrategy(retrain_interval_days=1)
        strategy.model.is_trained = True
        strategy.last_retrain_date = datetime.now() - timedelta(days=2)

        self.assertTrue(strategy.should_retrain())

    def test_should_retrain_interval_not_passed(self):
        """测试未超过重训练间隔"""
        strategy = ChinaMLStrategy(retrain_interval_days=30)
        strategy.model.is_trained = True
        strategy.last_retrain_date = datetime.now() - timedelta(days=1)

        self.assertFalse(strategy.should_retrain())

    def test_retrain_model(self):
        """测试模型重训练"""
        strategy = ChinaMLStrategy()

        np.random.seed(42)
        X_train = np.random.randn(100, 5)
        y_train = np.random.randn(100)

        result = strategy.retrain_model(X_train, y_train)
        self.assertTrue(result)
        self.assertTrue(strategy.model.is_trained)
        self.assertIsNotNone(strategy.last_retrain_date)

    def test_retrain_model_no_data(self):
        """测试无数据时重训练失败"""
        strategy = ChinaMLStrategy()

        result = strategy.retrain_model()
        self.assertFalse(result)

    def test_get_model_info(self):
        """测试获取模型信息"""
        strategy = ChinaMLStrategy()
        strategy.initialize()

        info = strategy.get_model_info()

        self.assertIn("model_type", info)
        self.assertIn("is_initialized", info)
        self.assertIn("n_factors", info)
        self.assertEqual(info["n_factors"], 0)
        self.assertTrue(info["is_initialized"])

    def test_get_position(self):
        """测试获取持仓"""
        strategy = ChinaMLStrategy()

        position = strategy.get_position("000001.SZ")
        self.assertEqual(position, 0)

        # 记录买入
        strategy.record_buy("000001.SZ", 100)
        position = strategy.get_position("000001.SZ")
        self.assertEqual(position, 100)

    def test_can_buy(self):
        """测试是否可以买入"""
        strategy = ChinaMLStrategy()

        # 可以买入
        self.assertTrue(strategy.can_buy("000001.SZ", 10.0, 10.5))

        # 涨停时不能买入
        strategy.update_limit_status("000001.SZ", is_limit_up=True)
        self.assertFalse(strategy.can_buy("000001.SZ", 10.0, 10.5))

    def test_can_sell(self):
        """测试是否可以卖出"""
        strategy = ChinaMLStrategy()

        # 先买入（两天前买入，满足T+1条件）
        # 直接使用 trading_adapter 记录买入日期
        buy_date = datetime.now() - timedelta(days=2)
        strategy.trading_adapter.record_buy("000001.SZ", buy_date, 100)

        # 满足T+1条件，可以卖出
        self.assertTrue(strategy.can_sell("000001.SZ", 10.0, 9.5, 50))

    def test_record_buy_and_sell(self):
        """测试记录买卖"""
        strategy = ChinaMLStrategy()

        strategy.record_buy("000001.SZ", 100)
        self.assertEqual(strategy.get_position("000001.SZ"), 100)

        sold = strategy.record_sell("000001.SZ", 30)
        self.assertEqual(sold, 30)
        self.assertEqual(strategy.get_position("000001.SZ"), 70)

    def test_reset(self):
        """测试重置"""
        strategy = ChinaMLStrategy()

        strategy.record_buy("000001.SZ", 100)
        strategy.update_limit_status("000001.SZ", is_limit_up=True)

        strategy.reset()

        self.assertEqual(strategy.get_position("000001.SZ"), 0)
        holdings = strategy.trading_adapter.get_holdings()
        self.assertEqual(len(holdings), 0)

    def test_str_repr(self):
        """测试字符串表示"""
        strategy = ChinaMLStrategy()
        strategy.initialize()

        repr_str = repr(strategy)
        self.assertIn("ChinaMLStrategy", repr_str)
        self.assertIn("initialized", repr_str)


class TestSignalGenerator(unittest.TestCase):
    """测试信号生成器"""

    def test_initialization(self):
        """测试初始化"""
        generator = SignalGenerator()
        self.assertEqual(generator.threshold_buy, 0.6)
        self.assertEqual(generator.threshold_sell, -0.6)
        self.assertEqual(generator.min_confidence, 0.5)

    def test_initialization_custom(self):
        """测试自定义阈值初始化"""
        generator = SignalGenerator(threshold_buy=0.8, threshold_sell=-0.8, min_confidence=0.6)
        self.assertEqual(generator.threshold_buy, 0.8)
        self.assertEqual(generator.threshold_sell, -0.8)
        self.assertEqual(generator.min_confidence, 0.6)

    def test_generate_signal_buy(self):
        """测试买入信号生成"""
        generator = SignalGenerator()

        # 高收益率高置信度 -> 买入
        signal = generator.generate_signal(0.8, 0.7)
        self.assertEqual(signal, SignalType.BUY)

    def test_generate_signal_sell(self):
        """测试卖出信号生成"""
        generator = SignalGenerator()

        # 低收益率高置信度 -> 卖出
        signal = generator.generate_signal(-0.8, 0.7)
        self.assertEqual(signal, SignalType.SELL)

    def test_generate_signal_hold_low_confidence(self):
        """测试低置信度时持有"""
        generator = SignalGenerator()

        # 低置信度 -> 持有
        signal = generator.generate_signal(0.8, 0.3)
        self.assertEqual(signal, SignalType.HOLD)

    def test_generate_signal_hold_between_thresholds(self):
        """测试阈值之间时持有"""
        generator = SignalGenerator()

        # 收益率在阈值之间 -> 持有
        signal = generator.generate_signal(0.3, 0.7)
        self.assertEqual(signal, SignalType.HOLD)

    def test_generate_signal_boundary(self):
        """测试边界值"""
        generator = SignalGenerator(threshold_buy=0.6, threshold_sell=-0.6)

        # 正好等于阈值时，由于使用严格大于/小于，返回HOLD
        signal = generator.generate_signal(0.6, 0.7)
        self.assertEqual(signal, SignalType.HOLD)

        signal = generator.generate_signal(-0.6, 0.7)
        self.assertEqual(signal, SignalType.HOLD)

        # 稍微超过阈值才产生信号
        signal = generator.generate_signal(0.61, 0.7)
        self.assertEqual(signal, SignalType.BUY)

        signal = generator.generate_signal(-0.61, 0.7)
        self.assertEqual(signal, SignalType.SELL)

    def test_generate_signal_from_prediction(self):
        """测试从PredictionResult生成信号"""
        generator = SignalGenerator()

        prediction = PredictionResult(
            symbol="000001.SZ",
            datetime=datetime.now(),
            predicted_return=0.8,
            confidence=0.7,
            signal=SignalType.HOLD,
            model_name="test"
        )

        signal = generator.generate_signal_from_prediction(prediction)
        self.assertEqual(signal, SignalType.BUY)

    def test_filter_signal_buy_with_position(self):
        """测试有持仓时过滤买入信号"""
        generator = SignalGenerator()

        # 有持仓时买入信号被过滤
        signal = generator.filter_signal(SignalType.BUY, position=100, can_buy=True, can_sell=True)
        self.assertEqual(signal, SignalType.HOLD)

    def test_filter_signal_buy_no_position(self):
        """测试无持仓时可以买入"""
        generator = SignalGenerator()

        signal = generator.filter_signal(SignalType.BUY, position=0, can_buy=True, can_sell=True)
        self.assertEqual(signal, SignalType.BUY)

    def test_filter_signal_cannot_buy(self):
        """测试不能买入时过滤"""
        generator = SignalGenerator()

        signal = generator.filter_signal(SignalType.BUY, position=0, can_buy=False, can_sell=True)
        self.assertEqual(signal, SignalType.HOLD)

    def test_filter_signal_sell_no_position(self):
        """测试无持仓时卖出信号被过滤"""
        generator = SignalGenerator()

        signal = generator.filter_signal(SignalType.SELL, position=0, can_buy=True, can_sell=True)
        self.assertEqual(signal, SignalType.HOLD)

    def test_filter_signal_sell_with_position(self):
        """测试有持仓时可以卖出"""
        generator = SignalGenerator()

        signal = generator.filter_signal(SignalType.SELL, position=100, can_buy=True, can_sell=True)
        self.assertEqual(signal, SignalType.SELL)

    def test_filter_signal_with_price_limit_up(self):
        """测试涨停时过滤买入信号"""
        generator = SignalGenerator()

        signal = generator.filter_signal_with_price_limit(
            SignalType.BUY, is_limit_up=True, is_limit_down=False
        )
        self.assertEqual(signal, SignalType.HOLD)

    def test_filter_signal_with_price_limit_down(self):
        """测试跌停时过滤卖出信号"""
        generator = SignalGenerator()

        signal = generator.filter_signal_with_price_limit(
            SignalType.SELL, is_limit_up=False, is_limit_down=True
        )
        self.assertEqual(signal, SignalType.HOLD)

    def test_combine_signals_empty(self):
        """测试空信号列表"""
        generator = SignalGenerator()

        signal = generator.combine_signals([])
        self.assertEqual(signal, SignalType.HOLD)

    def test_combine_signals_buy_priority(self):
        """测试买入信号优先"""
        generator = SignalGenerator()

        signals = [SignalType.SELL, SignalType.HOLD, SignalType.BUY]
        signal = generator.combine_signals(signals)
        self.assertEqual(signal, SignalType.BUY)

    def test_combine_signals_sell_priority(self):
        """测试卖出信号次优先"""
        generator = SignalGenerator()

        signals = [SignalType.CLOSE, SignalType.SELL, SignalType.HOLD]
        signal = generator.combine_signals(signals)
        self.assertEqual(signal, SignalType.SELL)

    def test_combine_signals_all_hold(self):
        """测试全是持有信号"""
        generator = SignalGenerator()

        signals = [SignalType.HOLD, SignalType.HOLD, SignalType.HOLD]
        signal = generator.combine_signals(signals)
        self.assertEqual(signal, SignalType.HOLD)

    def test_combine_signals_with_weight(self):
        """测试加权合并"""
        generator = SignalGenerator()

        signals = [SignalType.BUY, SignalType.SELL, SignalType.BUY]
        weights = [0.3, 0.4, 0.5]

        signal = generator.combine_signals_with_weight(signals, weights)
        # BUY权重0.3+0.5=0.8，SELL权重0.4
        self.assertEqual(signal, SignalType.BUY)

    def test_get_signal_info(self):
        """测试获取配置信息"""
        generator = SignalGenerator()

        info = generator.get_signal_info()
        self.assertEqual(info["threshold_buy"], 0.6)
        self.assertEqual(info["threshold_sell"], -0.6)
        self.assertEqual(info["min_confidence"], 0.5)

    def test_set_thresholds(self):
        """测试设置阈值"""
        generator = SignalGenerator()

        generator.set_thresholds(0.7, -0.7)
        self.assertEqual(generator.threshold_buy, 0.7)
        self.assertEqual(generator.threshold_sell, -0.7)

    def test_set_thresholds_invalid(self):
        """测试无效阈值"""
        generator = SignalGenerator()

        # 买入阈值小于等于卖出阈值时抛出异常
        # 0.4 <= 0.6 -> 抛出异常
        with self.assertRaises(ValueError):
            generator.set_thresholds(0.4, 0.6)

        # -0.5 <= -0.3 -> 抛出异常
        with self.assertRaises(ValueError):
            generator.set_thresholds(-0.5, -0.3)

        # 相等时也抛出异常
        with self.assertRaises(ValueError):
            generator.set_thresholds(0.5, 0.5)


class TestAdaptiveSignalGenerator(unittest.TestCase):
    """测试自适应信号生成器"""

    def test_initialization(self):
        """测试初始化"""
        generator = AdaptiveSignalGenerator()
        self.assertTrue(generator.volatility_adjust)
        self.assertEqual(generator.volatility, 0.0)

    def test_update_volatility(self):
        """测试更新波动率"""
        generator = AdaptiveSignalGenerator()

        returns = np.array([0.01, -0.02, 0.015, -0.01, 0.005])
        generator.update_volatility(returns)

        self.assertGreater(generator.volatility, 0)

    def test_generate_signal_with_volatility(self):
        """测试带波动率调整的信号生成"""
        generator = AdaptiveSignalGenerator(volatility_adjust=True)

        # 更新波动率
        returns = np.array([0.05, -0.06, 0.07, -0.08, 0.09])
        generator.update_volatility(returns)

        # 高波动率环境下，阈值会被提高
        signal = generator.generate_signal(0.7, 0.7)
        # 由于波动率高，可能不会产生信号
        self.assertIsInstance(signal, SignalType)

    def test_generate_signal_without_volatility_adjust(self):
        """测试不使用波动率调整"""
        generator = AdaptiveSignalGenerator(volatility_adjust=False)

        signal = generator.generate_signal(0.8, 0.7)
        self.assertEqual(signal, SignalType.BUY)


class TestMultiSignalGenerator(unittest.TestCase):
    """测试多信号生成器"""

    def test_initialization(self):
        """测试初始化"""
        multi_gen = MultiSignalGenerator()
        self.assertEqual(len(multi_gen), 0)

    def test_add_generator(self):
        """测试添加生成器"""
        multi_gen = MultiSignalGenerator()
        gen = SignalGenerator()

        multi_gen.add_generator(gen)
        self.assertEqual(len(multi_gen), 1)

    def test_remove_generator(self):
        """测试移除生成器"""
        multi_gen = MultiSignalGenerator()
        gen = SignalGenerator()

        multi_gen.add_generator(gen)
        multi_gen.remove_generator(gen)
        self.assertEqual(len(multi_gen), 0)

    def test_generate_signals(self):
        """测试生成多个信号"""
        multi_gen = MultiSignalGenerator()
        gen1 = SignalGenerator(threshold_buy=0.6)
        gen2 = SignalGenerator(threshold_buy=0.7)

        multi_gen.add_generator(gen1)
        multi_gen.add_generator(gen2)

        signals = multi_gen.generate_signals(0.8, 0.7)
        self.assertEqual(len(signals), 2)

    def test_generate_combined_signal(self):
        """测试生成组合信号"""
        multi_gen = MultiSignalGenerator()
        gen1 = SignalGenerator(threshold_buy=0.6)
        gen2 = SignalGenerator(threshold_buy=0.7)

        multi_gen.add_generator(gen1)
        multi_gen.add_generator(gen2)

        signal = multi_gen.generate_combined_signal(0.8, 0.7)
        self.assertEqual(signal, SignalType.BUY)

    def test_len(self):
        """测试长度方法"""
        multi_gen = MultiSignalGenerator()

        self.assertEqual(len(multi_gen), 0)

        multi_gen.add_generator(SignalGenerator())
        multi_gen.add_generator(SignalGenerator())

        self.assertEqual(len(multi_gen), 2)


if __name__ == "__main__":
    unittest.main()
