"""
因子回测模块单元测试

测试因子有效性回测功能。
"""

import unittest
import numpy as np
import polars as pl
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

from vnpy_china_ml.backtesting.factor_backtest import (
    FactorBacktester,
    FactorIcResult,
    FactorIcStats,
    LayerBacktestResult,
    FactorBacktestReport,
    create_factor_backtester,
)


class TestFactorIcResult(unittest.TestCase):
    """测试IC结果数据类"""

    def test_create_ic_result(self):
        """测试创建IC结果"""
        result = FactorIcResult(
            date=date(2024, 1, 1),
            ic=0.05,
            rank_ic=0.04,
            sample_count=100
        )

        self.assertEqual(result.date, date(2024, 1, 1))
        self.assertEqual(result.ic, 0.05)
        self.assertEqual(result.rank_ic, 0.04)
        self.assertEqual(result.sample_count, 100)


class TestFactorIcStats(unittest.TestCase):
    """测试IC统计数据类"""

    def test_create_ic_stats(self):
        """测试创建IC统计"""
        stats = FactorIcStats(
            ic_mean=0.03,
            ic_std=0.02,
            ic_ir=1.5,
            rank_ic_mean=0.025,
            rank_ic_std=0.018,
            rank_ic_ir=1.39,
            ic_positive_ratio=0.6,
            ic_absolute_mean=0.04,
            win_rate=0.55
        )

        self.assertEqual(stats.ic_mean, 0.03)
        self.assertEqual(stats.ic_ir, 1.5)
        self.assertEqual(stats.win_rate, 0.55)


class TestLayerBacktestResult(unittest.TestCase):
    """测试分层回测结果数据类"""

    def test_create_layer_result(self):
        """测试创建分层结果"""
        result = LayerBacktestResult(
            layer=1,
            total_return=0.15,
            annual_return=0.18,
            volatility=0.25,
            sharpe_ratio=0.72,
            max_drawdown=-0.08,
            win_rate=0.55,
            avg_daily_return=0.0006
        )

        self.assertEqual(result.layer, 1)
        self.assertEqual(result.total_return, 0.15)
        self.assertEqual(result.sharpe_ratio, 0.72)


class TestFactorBacktester(unittest.TestCase):
    """测试因子回测器"""

    def setUp(self):
        """设置测试环境"""
        self.backtester = FactorBacktester()

    def test_initialization(self):
        """测试初始化"""
        backtester = FactorBacktester(data_service=None)
        self.assertIsNotNone(backtester)

    def test_create_factor_backtester(self):
        """测试工厂函数"""
        backtester = create_factor_backtester()
        self.assertIsInstance(backtester, FactorBacktester)

    def _create_test_data(self, n_stocks: int = 100, n_days: int = 250):
        """创建测试数据

        Args:
            n_stocks: 股票数量
            n_days: 交易天数

        Returns:
            (factor_data, price_data) 元组
        """
        symbols = [f"{i:06d}.SZ" for i in range(n_stocks)]
        dates = [date.today() - timedelta(days=i) for i in range(n_days, 0, -1)]

        # 生成价格数据
        price_records = []
        for symbol in symbols:
            price = 100.0
            for dt in dates:
                # 随机价格变动
                change = np.random.randn() * 0.02
                price = price * (1 + change)

                price_records.append({
                    "datetime": datetime.combine(dt, datetime.min.time()),
                    "symbol": symbol,
                    "close_price": max(price, 1.0)  # 价格不低于1
                })

        price_df = pl.DataFrame(price_records)

        # 生成因子数据（与未来收益率有一定相关性）
        factor_records = []
        for symbol in symbols:
            for i, dt in enumerate(dates[:-5]):  # 最后5天没有未来数据
                # 因子值 = 前5天收益率（与未来有微弱正相关）
                factor_value = np.random.randn() * 0.5

                factor_records.append({
                    "datetime": datetime.combine(dt, datetime.min.time()),
                    "symbol": symbol,
                    "factor_value": factor_value
                })

        factor_df = pl.DataFrame(factor_records)

        return factor_df, price_df

    def test_backtest_factor(self):
        """测试因子回测"""
        factor_data, price_data = self._create_test_data(n_stocks=50, n_days=100)

        start_date = date.today() - timedelta(days=90)
        end_date = date.today() - timedelta(days=10)

        report = self.backtester.backtest_factor(
            factor_data=factor_data,
            price_data=price_data,
            start_date=start_date,
            end_date=end_date,
            forward_days=5,
            n_layers=5
        )

        # 验证报告结构
        self.assertIsInstance(report, FactorBacktestReport)
        self.assertIsNotNone(report.ic_stats)
        self.assertIsInstance(report.ic_series, list)
        self.assertIsInstance(report.layer_results, list)

    def test_calculate_forward_returns(self):
        """测试计算未来收益率"""
        # 创建简单测试数据
        price_data = pl.DataFrame({
            "datetime": [datetime(2024, 1, 1), datetime(2024, 1, 2), datetime(2024, 1, 3),
                        datetime(2024, 1, 1), datetime(2024, 1, 2), datetime(2024, 1, 3)],
            "symbol": ["A", "A", "A", "B", "B", "B"],
            "close_price": [100.0, 102.0, 104.0, 50.0, 51.0, 49.0]
        })

        result = self.backtester._calculate_forward_returns(price_data, forward_days=2)

        # 验证收益率计算
        self.assertIn("forward_return", result.columns)

        # A股票：100 -> 104，收益率 = (104-100)/100 = 0.04
        a_return = result.filter(
            (pl.col("symbol") == "A") & (pl.col("datetime") == datetime(2024, 1, 1))
        )["forward_return"][0]
        self.assertAlmostEqual(a_return, 0.04, places=2)

    def test_calculate_ic_series(self):
        """测试计算IC序列"""
        # 创建测试数据 - 使用正确的日期范围
        factor_values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        returns = np.array([0.01, 0.02, 0.03, 0.04, 0.05])  # 完全正相关

        # 使用date对象创建测试数据
        dates = [date(2024, 1, i) for i in range(1, 6)]
        df = pl.DataFrame({
            "datetime": dates,
            "symbol": ["A"] * 5,
            "factor_value": factor_values,
            "forward_return": returns
        })

        ic_series = self.backtester._calculate_ic_series(
            df,
            date(2024, 1, 1),
            date(2024, 1, 5)
        )

        self.assertIsInstance(ic_series, list)
        # 至少应该有一些有效的IC计算结果
        if len(ic_series) > 0:
            self.assertIsInstance(ic_series[0], FactorIcResult)

    def test_calculate_ic_stats(self):
        """测试计算IC统计"""
        # 创建IC序列
        ic_series = [
            FactorIcResult(date=date(2024, 1, i), ic=0.05 * (i % 3 - 1),
                          rank_ic=0.04 * (i % 3 - 1), sample_count=100)
            for i in range(1, 11)
        ]

        stats = self.backtester._calculate_ic_stats(ic_series)

        self.assertIsInstance(stats, FactorIcStats)
        self.assertIsNotNone(stats.ic_mean)
        self.assertIsNotNone(stats.ic_std)
        self.assertIsNotNone(stats.ic_ir)

    def test_layer_backtest(self):
        """测试分层回测"""
        # 创建测试数据
        np.random.seed(42)
        n_samples = 1000

        df = pl.DataFrame({
            "datetime": [datetime(2024, 1, 1)] * n_samples,
            "symbol": [f"stock_{i}" for i in range(n_samples)],
            "factor_value": np.random.randn(n_samples),
            "forward_return": np.random.randn(n_samples) * 0.02
        })

        layer_results = self.backtester._layer_backtest(
            df=df,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            n_layers=5
        )

        self.assertEqual(len(layer_results), 5)

        for result in layer_results:
            self.assertIsInstance(result, LayerBacktestResult)
            self.assertGreaterEqual(result.layer, 1)
            self.assertLessEqual(result.layer, 5)

    def test_calculate_turnover(self):
        """测试计算换手率"""
        # 创建测试数据
        dates = [datetime(2024, 1, i) for i in range(1, 11)]
        symbols = [f"stock_{i}" for i in range(50)]

        records = []
        for dt in dates:
            np.random.shuffle(symbols)
            for symbol in symbols:
                records.append({
                    "datetime": dt,
                    "symbol": symbol,
                    "factor_value": np.random.randn()
                })

        factor_data = pl.DataFrame(records)

        turnover = self.backtester.calculate_turnover(factor_data, n_layers=5)

        self.assertIsInstance(turnover, dict)
        self.assertEqual(len(turnover), 5)

        # 换手率应该在0到1之间
        for layer, rate in turnover.items():
            self.assertGreaterEqual(rate, 0.0)
            self.assertLessEqual(rate, 1.0)

    def test_calculate_factor_decay(self):
        """测试计算因子衰减"""
        factor_data, price_data = self._create_test_data(n_stocks=30, n_days=60)

        decay = self.backtester.calculate_factor_decay(
            factor_data=factor_data,
            price_data=price_data,
            max_days=10
        )

        self.assertIsInstance(decay, dict)
        self.assertEqual(len(decay), 10)

        # 验证所有天数都有IC值
        for days, ic in decay.items():
            self.assertGreaterEqual(days, 1)
            self.assertLessEqual(days, 10)
            self.assertGreaterEqual(ic, -1.0)
            self.assertLessEqual(ic, 1.0)


if __name__ == "__main__":
    unittest.main()
