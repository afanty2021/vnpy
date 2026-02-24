"""
单元测试：核心数据类型验证

测试 vnpy_china_ml.utils.types 模块中定义的所有数据模型
"""

import pytest
from datetime import datetime, date
from vnpy_china_ml.utils.types import (
    FactorType,
    ModelType,
    SignalType,
    FactorData,
    PredictionResult,
    TrainingConfig,
    BacktestResult,
)


class TestFactorType:
    """测试因子类型枚举"""

    def test_factor_type_values(self):
        """测试因子类型枚举值"""
        assert FactorType.TECHNICAL.value == "technical"
        assert FactorType.FUNDAMENTAL.value == "fundamental"
        assert FactorType.DRAGON_TIGER.value == "dragon_tiger"
        assert FactorType.NORTHBOUND.value == "northbound"
        assert FactorType.SECTOR_ROTATION.value == "sector_rotation"
        assert FactorType.LIMIT_STATS.value == "limit_stats"

    def test_factor_type_count(self):
        """测试因子类型数量"""
        assert len(FactorType) == 6


class TestModelType:
    """测试模型类型枚举"""

    def test_model_type_values(self):
        """测试模型类型枚举值"""
        assert ModelType.LIGHTGBM.value == "lightgbm"
        assert ModelType.XGBOOST.value == "xgboost"
        assert ModelType.RANDOM_FOREST.value == "random_forest"
        assert ModelType.LASSO.value == "lasso"
        assert ModelType.RIDGE.value == "ridge"
        assert ModelType.LSTM.value == "lstm"

    def test_model_type_count(self):
        """测试模型类型数量"""
        assert len(ModelType) == 6


class TestSignalType:
    """测试信号类型枚举"""

    def test_signal_type_values(self):
        """测试信号类型枚举值"""
        assert SignalType.BUY.value == "buy"
        assert SignalType.SELL.value == "sell"
        assert SignalType.HOLD.value == "hold"
        assert SignalType.CLOSE.value == "close"

    def test_signal_type_count(self):
        """测试信号类型数量"""
        assert len(SignalType) == 4


class TestFactorData:
    """测试因子数据结构"""

    def test_factor_data_creation(self):
        """测试因子数据创建"""
        factor = FactorData(
            symbol="000001.SZ",
            datetime=datetime(2025, 1, 1),
            factor_name="macd",
            factor_type=FactorType.TECHNICAL,
            value=0.5,
            importance=0.8,
        )
        assert factor.symbol == "000001.SZ"
        assert factor.factor_name == "macd"
        assert factor.value == 0.5
        assert factor.importance == 0.8

    def test_factor_data_default_importance(self):
        """测试默认值"""
        factor = FactorData(
            symbol="000001.SZ",
            datetime=datetime(2025, 1, 1),
            factor_name="macd",
            factor_type=FactorType.TECHNICAL,
            value=0.5,
        )
        assert factor.importance == 0.0

    def test_factor_data_empty_symbol_validation(self):
        """测试空symbol验证"""
        with pytest.raises(ValueError, match="symbol不能为空"):
            FactorData(
                symbol="",
                datetime=datetime(2025, 1, 1),
                factor_name="macd",
                factor_type=FactorType.TECHNICAL,
                value=0.5,
            )

    def test_factor_data_importance_range_validation(self):
        """测试importance范围验证"""
        with pytest.raises(ValueError, match="importance必须在0.0-1.0之间"):
            FactorData(
                symbol="000001.SZ",
                datetime=datetime(2025, 1, 1),
                factor_name="macd",
                factor_type=FactorType.TECHNICAL,
                value=0.5,
                importance=1.5,
            )


class TestPredictionResult:
    """测试预测结果结构"""

    def test_prediction_result_creation(self):
        """测试预测结果创建"""
        result = PredictionResult(
            symbol="000001.SZ",
            datetime=datetime(2025, 1, 1),
            predicted_return=0.05,
            confidence=0.8,
            signal=SignalType.BUY,
            model_name="lightgbm",
        )
        assert result.symbol == "000001.SZ"
        assert result.predicted_return == 0.05
        assert result.confidence == 0.8
        assert result.signal == SignalType.BUY
        assert result.model_name == "lightgbm"

    def test_prediction_result_confidence_range_validation(self):
        """测试置信度范围验证"""
        with pytest.raises(ValueError, match="confidence必须在0.0-1.0之间"):
            PredictionResult(
                symbol="000001.SZ",
                datetime=datetime(2025, 1, 1),
                predicted_return=0.05,
                confidence=1.5,
                signal=SignalType.BUY,
                model_name="lightgbm",
            )

    def test_prediction_result_empty_symbol_validation(self):
        """测试空symbol验证"""
        with pytest.raises(ValueError, match="symbol不能为空"):
            PredictionResult(
                symbol="",
                datetime=datetime(2025, 1, 1),
                predicted_return=0.05,
                confidence=0.8,
                signal=SignalType.BUY,
                model_name="lightgbm",
            )

    def test_prediction_result_signal_type_validation(self):
        """测试信号类型验证"""
        with pytest.raises(ValueError, match="signal必须是SignalType枚举类型"):
            PredictionResult(
                symbol="000001.SZ",
                datetime=datetime(2025, 1, 1),
                predicted_return=0.05,
                confidence=0.8,
                signal="buy",  # 传入字符串而非枚举
                model_name="lightgbm",
            )


class TestTrainingConfig:
    """测试训练配置结构"""

    def test_training_config_creation(self):
        """测试训练配置创建"""
        config = TrainingConfig(
            model_type=ModelType.LIGHTGBM,
            train_start=date(2023, 1, 1),
            train_end=date(2024, 1, 1),
            test_start=date(2024, 1, 1),
            test_end=date(2024, 12, 31),
            lookback_days=60,
            forward_days=5,
            min_samples=1000,
        )
        assert config.model_type == ModelType.LIGHTGBM
        assert config.train_start == date(2023, 1, 1)
        assert config.lookback_days == 60

    def test_training_config_default_values(self):
        """测试默认值"""
        config = TrainingConfig(
            model_type=ModelType.LIGHTGBM,
            train_start=date(2023, 1, 1),
            train_end=date(2024, 1, 1),
            test_start=date(2024, 1, 1),
            test_end=date(2024, 12, 31),
        )
        assert config.lookback_days == 60
        assert config.forward_days == 5
        assert config.min_samples == 1000

    def test_training_config_train_dates_validation(self):
        """测试训练集日期验证"""
        with pytest.raises(ValueError, match="train_start必须早于train_end"):
            TrainingConfig(
                model_type=ModelType.LIGHTGBM,
                train_start=date(2024, 1, 1),
                train_end=date(2023, 1, 1),
                test_start=date(2024, 1, 1),
                test_end=date(2024, 12, 31),
            )

    def test_training_config_test_dates_validation(self):
        """测试测试集日期验证"""
        with pytest.raises(ValueError, match="test_start必须早于test_end"):
            TrainingConfig(
                model_type=ModelType.LIGHTGBM,
                train_start=date(2023, 1, 1),
                train_end=date(2024, 1, 1),
                test_start=date(2024, 12, 31),
                test_end=date(2024, 1, 1),
            )

    def test_training_config_period_overlap_validation(self):
        """测试训练集和测试集不能重叠"""
        with pytest.raises(ValueError, match="训练集结束日期必须早于或等于测试集开始日期"):
            TrainingConfig(
                model_type=ModelType.LIGHTGBM,
                train_start=date(2023, 1, 1),
                train_end=date(2024, 6, 1),
                test_start=date(2024, 5, 1),
                test_end=date(2024, 12, 31),
            )

    def test_training_config_lookback_days_validation(self):
        """测试lookback_days验证"""
        with pytest.raises(ValueError, match="lookback_days必须大于0"):
            TrainingConfig(
                model_type=ModelType.LIGHTGBM,
                train_start=date(2023, 1, 1),
                train_end=date(2024, 1, 1),
                test_start=date(2024, 1, 1),
                test_end=date(2024, 12, 31),
                lookback_days=0,
            )

    def test_training_config_properties(self):
        """测试属性方法"""
        config = TrainingConfig(
            model_type=ModelType.LIGHTGBM,
            train_start=date(2023, 1, 1),
            train_end=date(2024, 1, 1),
            test_start=date(2024, 1, 1),
            test_end=date(2024, 12, 31),
        )
        assert config.train_period_days == 365  # 2023-01-01 到 2024-01-01 是365天
        assert config.test_period_days == 365


class TestBacktestResult:
    """测试回测结果结构"""

    def test_backtest_result_creation(self):
        """测试回测结果创建"""
        result = BacktestResult(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            total_return=0.25,
            annual_return=0.25,
            sharpe_ratio=1.5,
            max_drawdown=0.1,
            win_rate=0.6,
            total_trades=100,
        )
        assert result.start_date == date(2024, 1, 1)
        assert result.total_return == 0.25
        assert result.total_trades == 100

    def test_backtest_result_to_dict(self):
        """测试转换为字典"""
        result = BacktestResult(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            total_return=0.25,
            annual_return=0.25,
            sharpe_ratio=1.5,
            max_drawdown=0.1,
            win_rate=0.6,
            total_trades=100,
        )
        result_dict = result.to_dict()
        assert result_dict["total_return"] == 0.25
        assert result_dict["total_trades"] == 100
        assert result_dict["start_date"] == "2024-01-01"

    def test_backtest_result_properties(self):
        """测试属性方法"""
        result = BacktestResult(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            total_return=0.25,
            annual_return=0.25,
            sharpe_ratio=1.5,
            max_drawdown=0.1,
            win_rate=0.6,
            total_trades=100,
        )
        assert result.backtest_period_days == 365

    def test_backtest_result_win_rate_validation(self):
        """测试胜率范围验证"""
        with pytest.raises(ValueError, match="win_rate必须在0.0-1.0之间"):
            BacktestResult(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                total_return=0.25,
                annual_return=0.25,
                sharpe_ratio=1.5,
                max_drawdown=0.1,
                win_rate=1.5,
                total_trades=100,
            )

    def test_backtest_result_negative_trades_validation(self):
        """测试负数交易次数验证"""
        with pytest.raises(ValueError, match="total_trades不能为负数"):
            BacktestResult(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                total_return=0.25,
                annual_return=0.25,
                sharpe_ratio=1.5,
                max_drawdown=0.1,
                win_rate=0.6,
                total_trades=-10,
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
