"""
模型模块单元测试

测试A股机器学习模型和交易规则适配器的功能。
"""

import unittest
import numpy as np
from datetime import datetime, timedelta

from vnpy_china_ml.model.china_model import ChinaAlphaModel
from vnpy_china_ml.model.adapters import T1RuleAdapter, PriceLimitAdapter, ChinaTradingAdapter
from vnpy_china_ml.utils.types import ModelType


class TestChinaAlphaModel(unittest.TestCase):
    """测试A股机器学习模型"""

    def test_model_initialization(self):
        """测试模型初始化"""
        # 默认初始化
        model = ChinaAlphaModel()
        self.assertEqual(model.model_type, ModelType.RANDOM_FOREST)
        self.assertFalse(model.is_trained)
        self.assertEqual(model.feature_names, [])

        # 指定模型类型
        model_rf = ChinaAlphaModel(ModelType.RANDOM_FOREST)
        self.assertEqual(model_rf.model_type, ModelType.RANDOM_FOREST)

    def test_random_forest_train_and_predict(self):
        """测试随机森林模型训练和预测"""
        model = ChinaAlphaModel(ModelType.RANDOM_FOREST)

        # 生成测试数据
        np.random.seed(42)
        X_train = np.random.randn(100, 5)
        y_train = np.random.randn(100)

        # 训练模型
        result = model.train(X_train, y_train)
        self.assertEqual(result["status"], "success")
        self.assertTrue(model.is_trained)
        self.assertEqual(result["n_samples"], 100)
        self.assertEqual(result["n_features"], 5)

        # 预测
        X_test = np.random.randn(10, 5)
        predictions = model.predict(X_test)
        self.assertEqual(len(predictions), 10)

    def test_lasso_train_and_predict(self):
        """测试Lasso回归模型"""
        model = ChinaAlphaModel(ModelType.LASSO)

        # 生成线性测试数据
        np.random.seed(42)
        X_train = np.random.randn(100, 3)
        y_train = 2 * X_train[:, 0] + 0.5 * X_train[:, 1] - X_train[:, 2] + np.random.randn(100) * 0.1

        # 训练模型
        model.train(X_train, y_train)
        self.assertTrue(model.is_trained)

        # 预测
        X_test = np.random.randn(10, 3)
        predictions = model.predict(X_test)
        self.assertEqual(len(predictions), 10)

    def test_ridge_train_and_predict(self):
        """测试Ridge回归模型"""
        model = ChinaAlphaModel(ModelType.RIDGE)

        np.random.seed(42)
        X_train = np.random.randn(100, 4)
        y_train = np.random.randn(100)

        model.train(X_train, y_train)
        self.assertTrue(model.is_trained)

        predictions = model.predict(X_train)
        self.assertEqual(len(predictions), 100)

    def test_feature_importance(self):
        """测试特征重要性获取"""
        model = ChinaAlphaModel(ModelType.RANDOM_FOREST)

        np.random.seed(42)
        X_train = np.random.randn(100, 5)
        y_train = np.random.randn(100)

        model.train(X_train, y_train, feature_names=["f1", "f2", "f3", "f4", "f5"])

        importance = model.get_feature_importance()
        self.assertEqual(len(importance), 5)

        importance_dict = model.get_feature_importance_dict()
        self.assertEqual(len(importance_dict), 5)
        self.assertIn("f1", importance_dict)

    def test_predict_without_train(self):
        """测试未训练模型预测"""
        model = ChinaAlphaModel(ModelType.RANDOM_FOREST)
        X_test = np.random.randn(10, 5)

        with self.assertRaises(ValueError) as context:
            model.predict(X_test)
        self.assertIn("未训练", str(context.exception))

    def test_train_with_invalid_data(self):
        """测试无效数据训练"""
        model = ChinaAlphaModel(ModelType.RANDOM_FOREST)

        # 空数据
        with self.assertRaises(ValueError):
            model.train(np.array([]), np.array([]))

        # 特征和标签长度不匹配
        with self.assertRaises(ValueError):
            model.train(np.random.randn(100, 5), np.random.randn(50))

    def test_predict_with_signals(self):
        """测试带信号的预测"""
        model = ChinaAlphaModel(ModelType.RANDOM_FOREST)

        np.random.seed(42)
        X_train = np.random.randn(100, 5)
        y_train = np.random.randn(100)

        model.train(X_train, y_train)

        # 测试预测
        X_test = np.random.randn(10, 5)
        symbols = [f"00000{i}.SZ" for i in range(10)]
        dates = [datetime.now()] * 10

        results = model.predict_with_signals(X_test, symbols, dates)
        self.assertEqual(len(results), 10)

        # 检查信号类型
        for result in results:
            self.assertIn(result.signal.value, ["buy", "sell", "hold"])

    def test_model_save_load(self):
        """测试模型保存和加载"""
        import tempfile
        import os

        model = ChinaAlphaModel(ModelType.RANDOM_FOREST)

        np.random.seed(42)
        X_train = np.random.randn(100, 5)
        y_train = np.random.randn(100)

        model.train(X_train, y_train, feature_names=["f1", "f2", "f3", "f4", "f5"])

        # 保存模型
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as f:
            temp_path = f.name

        try:
            self.assertTrue(model.save_model(temp_path))

            # 加载模型
            new_model = ChinaAlphaModel(ModelType.RANDOM_FOREST)
            self.assertTrue(new_model.load_model(temp_path))

            self.assertTrue(new_model.is_trained)
            self.assertEqual(new_model.model_type, ModelType.RANDOM_FOREST)
            self.assertEqual(new_model.feature_names, ["f1", "f2", "f3", "f4", "f5"])

            # 测试加载后的预测
            X_test = np.random.randn(10, 5)
            predictions = new_model.predict(X_test)
            self.assertEqual(len(predictions), 10)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_get_model_info(self):
        """测试获取模型信息"""
        model = ChinaAlphaModel(ModelType.RANDOM_FOREST)

        info = model.get_model_info()
        self.assertEqual(info["model_type"], "random_forest")
        self.assertFalse(info["is_trained"])

        np.random.seed(42)
        X_train = np.random.randn(100, 5)
        y_train = np.random.randn(100)
        model.train(X_train, y_train)

        info = model.get_model_info()
        self.assertTrue(info["is_trained"])
        self.assertIsNotNone(info["training_date"])


class TestT1RuleAdapter(unittest.TestCase):
    """测试T+1规则适配器"""

    def test_initialization(self):
        """测试初始化"""
        adapter = T1RuleAdapter()
        self.assertEqual(len(adapter.holdings), 0)
        self.assertEqual(len(adapter.last_buy_date), 0)

    def test_can_sell_without_buy(self):
        """测试未买入时可以直接卖出"""
        adapter = T1RuleAdapter()
        current_date = datetime.now()

        self.assertTrue(adapter.can_sell("000001.SZ", current_date))

    def test_can_sell_after_buy_same_day(self):
        """测试买入当天不能卖出"""
        adapter = T1RuleAdapter()
        buy_date = datetime(2024, 1, 15, 10, 30)

        adapter.record_buy("000001.SZ", buy_date, 100)

        # 同一天不能卖出
        self.assertFalse(adapter.can_sell("000001.SZ", buy_date))

    def test_can_sell_after_one_day(self):
        """测试买入次日可以卖出"""
        adapter = T1RuleAdapter()
        buy_date = datetime(2024, 1, 15, 10, 30)
        sell_date = datetime(2024, 1, 16, 10, 30)

        adapter.record_buy("000001.SZ", buy_date, 100)

        # 第二天可以卖出
        self.assertTrue(adapter.can_sell("000001.SZ", sell_date))

    def test_record_buy_and_get_holdings(self):
        """测试记录买入和获取持仓"""
        adapter = T1RuleAdapter()

        adapter.record_buy("000001.SZ", datetime.now(), 100)
        adapter.record_buy("000002.SZ", datetime.now(), 200)

        holdings = adapter.get_all_holdings()
        self.assertEqual(holdings["000001.SZ"], 100)
        self.assertEqual(holdings["000002.SZ"], 200)

    def test_record_sell(self):
        """测试记录卖出"""
        adapter = T1RuleAdapter()

        adapter.record_buy("000001.SZ", datetime.now(), 100)

        # 卖出部分
        sold = adapter.record_sell("000001.SZ", 30)
        self.assertEqual(sold, 30)
        self.assertEqual(adapter.holdings["000001.SZ"], 70)

        # 卖出全部
        sold = adapter.record_sell("000001.SZ", 100)
        self.assertEqual(sold, 70)  # 只能卖出剩余的70
        self.assertNotIn("000001.SZ", adapter.holdings)

    def test_get_holdable_volume(self):
        """测试获取可卖出数量"""
        adapter = T1RuleAdapter()

        adapter.record_buy("000001.SZ", datetime.now(), 100)

        # 同一天不可卖出，传入当前日期
        self.assertEqual(adapter.get_holdable_volume("000001.SZ", datetime.now()), 0)

        # 第二天可卖出
        tomorrow = datetime.now() + timedelta(days=1)
        adapter.record_buy("000001.SZ", datetime.now(), 100)
        # 需要满足T+1
        self.assertEqual(adapter.get_holdable_volume("000001.SZ", tomorrow), 200)

    def test_can_sell_volume(self):
        """测试计算可卖出数量"""
        adapter = T1RuleAdapter()

        adapter.record_buy("000001.SZ", datetime.now(), 100)

        # 同一天
        self.assertEqual(adapter.can_sell_volume("000001.SZ", datetime.now(), 50), 0)

        # 第二天
        tomorrow = datetime.now() + timedelta(days=1)
        self.assertEqual(adapter.can_sell_volume("000001.SZ", tomorrow, 50), 50)

    def test_reset(self):
        """测试重置"""
        adapter = T1RuleAdapter()

        adapter.record_buy("000001.SZ", datetime.now(), 100)
        adapter.reset()

        self.assertEqual(len(adapter.holdings), 0)
        self.assertEqual(len(adapter.last_buy_date), 0)


class TestPriceLimitAdapter(unittest.TestCase):
    """测试涨跌停适配器"""

    def test_initialization(self):
        """测试初始化"""
        adapter = PriceLimitAdapter()
        self.assertEqual(adapter.limit_up_ratio, 0.10)
        self.assertEqual(adapter.limit_down_ratio, 0.10)
        self.assertEqual(len(adapter.limit_up_stocks), 0)
        self.assertEqual(len(adapter.limit_down_stocks), 0)

    def test_initialization_custom_ratios(self):
        """测试自定义涨跌停比例"""
        adapter = PriceLimitAdapter(0.20, 0.20)
        self.assertEqual(adapter.limit_up_ratio, 0.20)
        self.assertEqual(adapter.limit_down_ratio, 0.20)

    def test_update_limit_status(self):
        """测试更新涨跌停状态"""
        adapter = PriceLimitAdapter()

        # 设置涨停
        adapter.update_limit_status("000001.SZ", is_limit_up=True)
        self.assertTrue(adapter.is_limit_up("000001.SZ"))
        self.assertFalse(adapter.is_limit_down("000001.SZ"))

        # 设置跌停
        adapter.update_limit_status("000002.SZ", is_limit_up=False, is_limit_down=True)
        self.assertTrue(adapter.is_limit_down("000002.SZ"))
        self.assertFalse(adapter.is_limit_up("000002.SZ"))

    def test_can_buy_when_limit_up(self):
        """测试涨停时不能买入"""
        adapter = PriceLimitAdapter()

        adapter.update_limit_status("000001.SZ", is_limit_up=True)

        # 涨停时不能买入
        self.assertFalse(adapter.can_buy("000001.SZ", 10.0, 10.5))

    def test_can_buy_when_not_limit_up(self):
        """测试非涨停时可以买入"""
        adapter = PriceLimitAdapter()

        # 未涨停时，可以买入
        self.assertTrue(adapter.can_buy("000001.SZ", 10.0, 10.5))

    def test_can_sell_when_limit_down(self):
        """测试跌停时不能卖出"""
        adapter = PriceLimitAdapter()

        adapter.update_limit_status("000001.SZ", is_limit_up=False, is_limit_down=True)

        # 跌停时不能卖出
        self.assertFalse(adapter.can_sell("000001.SZ", 10.0, 9.5))

    def test_can_sell_when_not_limit_down(self):
        """测试非跌停时可以卖出"""
        adapter = PriceLimitAdapter()

        # 未跌停时，可以卖出
        self.assertTrue(adapter.can_sell("000001.SZ", 10.0, 9.5))

    def test_stock_type_normal(self):
        """测试普通股票涨跌停比例"""
        adapter = PriceLimitAdapter()
        adapter.set_stock_type("000001.SZ", adapter.StockType.NORMAL)

        limit_up, limit_down = adapter._get_limit_ratios("000001.SZ")
        self.assertEqual(limit_up, 0.10)
        self.assertEqual(limit_down, 0.10)

    def test_stock_type_st(self):
        """测试ST股票涨跌停比例"""
        adapter = PriceLimitAdapter()
        adapter.set_stock_type("000001.SZ", adapter.StockType.ST)

        limit_up, limit_down = adapter._get_limit_ratios("000001.SZ")
        self.assertEqual(limit_up, 0.05)
        self.assertEqual(limit_down, 0.05)

    def test_stock_type_star_market(self):
        """测试科创板股票涨跌停比例"""
        adapter = PriceLimitAdapter()
        adapter.set_stock_type("688001.SH", adapter.StockType.STAR_MARKET)

        limit_up, limit_down = adapter._get_limit_ratios("688001.SH")
        self.assertEqual(limit_up, 0.20)
        self.assertEqual(limit_down, 0.20)

    def test_get_limit_price(self):
        """测试获取涨跌停价格"""
        adapter = PriceLimitAdapter()

        previous_close = 10.0

        # 涨停价
        limit_up_price = adapter.get_limit_price("000001.SZ", previous_close, is_buy=True)
        self.assertEqual(limit_up_price, 11.0)

        # 跌停价
        limit_down_price = adapter.get_limit_price("000001.SZ", previous_close, is_buy=False)
        self.assertEqual(limit_down_price, 9.0)

    def test_update_limit_status_by_price(self):
        """测试根据价格更新涨跌停状态"""
        adapter = PriceLimitAdapter()

        previous_close = 10.0

        # 涨到涨停价
        changed = adapter.update_limit_status_by_price("000001.SZ", 11.0, previous_close)
        self.assertTrue(changed)
        self.assertTrue(adapter.is_limit_up("000001.SZ"))

        # 跌到跌停价
        changed = adapter.update_limit_status_by_price("000002.SZ", 9.0, previous_close)
        self.assertTrue(changed)
        self.assertTrue(adapter.is_limit_down("000002.SZ"))

    def test_clear(self):
        """测试清除涨跌停记录"""
        adapter = PriceLimitAdapter()

        adapter.update_limit_status("000001.SZ", is_limit_up=True)
        adapter.update_limit_status("000002.SZ", is_limit_up=False, is_limit_down=True)

        adapter.clear()

        self.assertEqual(len(adapter.limit_up_stocks), 0)
        self.assertEqual(len(adapter.limit_down_stocks), 0)


class TestChinaTradingAdapter(unittest.TestCase):
    """测试A股交易综合适配器"""

    def test_initialization(self):
        """测试初始化"""
        adapter = ChinaTradingAdapter()
        self.assertIsInstance(adapter.t1_adapter, T1RuleAdapter)
        self.assertIsInstance(adapter.price_limit_adapter, PriceLimitAdapter)

    def test_can_buy(self):
        """测试是否可以买入"""
        adapter = ChinaTradingAdapter()

        # 正常情况可以买入
        self.assertTrue(adapter.can_buy("000001.SZ", 10.0, 10.5))

        # 涨停时不能买入
        adapter.update_limit_status("000001.SZ", is_limit_up=True)
        self.assertFalse(adapter.can_buy("000001.SZ", 10.0, 10.5))

    def test_can_sell(self):
        """测试是否可以卖出"""
        adapter = ChinaTradingAdapter()

        # 先买入
        buy_date = datetime.now() - timedelta(days=2)
        adapter.record_buy("000001.SZ", buy_date, 100)

        # 满足T+1条件，可以卖出
        current_date = datetime.now()
        self.assertTrue(adapter.can_sell("000001.SZ", current_date, 10.0, 9.5, 50))

    def test_cannot_sell_same_day(self):
        """测试当日买入不能卖出"""
        adapter = ChinaTradingAdapter()

        # 当日买入
        buy_date = datetime.now()
        adapter.record_buy("000001.SZ", buy_date, 100)

        # 同一天不能卖出
        self.assertFalse(adapter.can_sell("000001.SZ", buy_date, 10.0, 9.5, 50))

    def test_record_buy_and_sell(self):
        """测试记录买卖操作"""
        adapter = ChinaTradingAdapter()

        # 买入
        adapter.record_buy("000001.SZ", datetime.now(), 100)

        holdings = adapter.get_holdings()
        self.assertEqual(holdings["000001.SZ"], 100)

        # 卖出
        sold = adapter.record_sell("000001.SZ", 30)
        self.assertEqual(sold, 30)

        holdings = adapter.get_holdings()
        self.assertEqual(holdings["000001.SZ"], 70)

    def test_reset(self):
        """测试重置"""
        adapter = ChinaTradingAdapter()

        adapter.record_buy("000001.SZ", datetime.now(), 100)
        adapter.update_limit_status("000001.SZ", is_limit_up=True)

        adapter.reset()

        self.assertEqual(len(adapter.get_holdings()), 0)


if __name__ == "__main__":
    unittest.main()
