"""ChinaMlGuiEngine 回归测试（Characterization Test）

目的：在 P2-1b 委托重构（提取数据准备逻辑到 dataset/loader.py 新增函数）之前，
锁定 ChinaMlGuiEngine 关键方法的"当前行为契约"，作为重构的安全网。

重构后这些测试必须仍然通过——它们记录的是行为契约（异常类型/异常消息关键文本/
返回值），而不是验证设计的正确性。

覆盖方法：
    - _infer_factor_type            纯字符串→因子类型映射
    - _calculate_accuracy           方向准确率数值逻辑（输入 mock model）
    - _prepare_prediction_data      数据为空时抛 RuntimeError
    - _prepare_training_data        数据为空时抛 RuntimeError
    - predict                       模型不存在时抛 RuntimeError

测试原则：
    - 不依赖真实数据库 / 不依赖 sklearn（环境未安装）
    - 不依赖真实数据加载器（统一用 unittest.mock.patch 替换）
    - 不污染工作目录（ModelManager 指向临时目录）
    - 不触发真实 MySQL 连接（patch 掉 _init_data_service）
"""

import os
import shutil
import tempfile
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

import numpy as np
import polars as pl

from vnpy.event import EventEngine

from vnpy_china_ml.gui_engine import ChinaMlGuiEngine


class GuiEngineTestCase(unittest.TestCase):
    """ChinaMlGuiEngine 测试基类

    提供可复用的 setUp/tearDown：
        - 构造轻量 ChinaMlGuiEngine（patch 掉 _init_data_service 避免真实数据库连接）
        - ModelManager 指向临时目录，避免在工作目录创建 models/
    """

    def setUp(self):
        """构造干净的 gui_engine 实例"""
        # 临时目录：供 ModelManager 使用，避免污染工作目录
        self.tmp_dir = tempfile.mkdtemp(prefix="gui_engine_test_")

        # patch 目标清单（全部以补丁上下文管理器形式启动）
        # 1) _init_data_service 内部会真实连 MySQL（环境无 MySQL），patch 成 no-op
        self._data_service_patcher = patch.object(
            ChinaMlGuiEngine, "_init_data_service", return_value=None
        )
        self._data_service_patcher.start()
        self.addCleanup(self._data_service_patcher.stop)

        # 2) ChinaMlGuiEngine.__init__ 硬编码调用 ModelManager() / ModelVersionManager()
        #    （两者默认在 ./models 写文件），patch 它们让默认 model_dir 指向临时目录，
        #    避免在工作目录创建 models/
        from vnpy_china_ml.model.manager import ModelManager as _OrigModelManager
        from vnpy_china_ml.model.version_manager import (
            ModelVersionManager as _OrigVersionManager,
        )

        def _make_isolated_model_manager(model_dir: str = "models", *args, **kwargs):
            return _OrigModelManager(model_dir=self.tmp_dir)

        def _make_isolated_version_manager(
            model_manager, model_dir: str = "models", *args, **kwargs
        ):
            return _OrigVersionManager(
                model_manager=model_manager, model_dir=self.tmp_dir
            )

        self._mm_patcher = patch(
            "vnpy_china_ml.gui_engine.ModelManager",
            side_effect=_make_isolated_model_manager,
        )
        self._vm_patcher = patch(
            "vnpy_china_ml.gui_engine.ModelVersionManager",
            side_effect=_make_isolated_version_manager,
        )
        self._mm_patcher.start()
        self._vm_patcher.start()
        self.addCleanup(self._mm_patcher.stop)
        self.addCleanup(self._vm_patcher.stop)

        fake_main_engine = MagicMock()
        fake_main_engine.write_log = MagicMock()

        self.event_engine = EventEngine()
        self.engine = ChinaMlGuiEngine(fake_main_engine, self.event_engine)

    def tearDown(self):
        """清理临时目录"""
        if self.tmp_dir and os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir, ignore_errors=True)


class TestInferFactorType(GuiEngineTestCase):
    """_infer_factor_type 的字符串映射契约"""

    def test_return_and_roc_map_to_momentum(self):
        """含 'return' 或 'roc' → '动量'"""
        # 精确匹配
        self.assertEqual(self.engine._infer_factor_type("return_5d"), "动量")
        self.assertEqual(self.engine._infer_factor_type("ROC_10"), "动量")
        # 大小写混合
        self.assertEqual(self.engine._infer_factor_type("DailyReturn"), "动量")
        # 词中嵌入
        self.assertEqual(self.engine._infer_factor_type("momentum_return_ratio"), "动量")

    def test_volume_maps_to_volume_type(self):
        """含 'volume' → '成交量'（不是 '资金流'）"""
        self.assertEqual(self.engine._infer_factor_type("volume_5d"), "成交量")
        self.assertEqual(self.engine._infer_factor_type("VolumeRatio"), "成交量")

    def test_obv_and_mfi_map_to_capital_flow(self):
        """含 'obv' 或 'mfi'（但不含 'volume'）→ '资金流'

        代码契约：分支条件是 'volume' OR 'obv' OR 'mfi'，
        返回时再判断 'volume' in name 决定返回 "成交量" / "资金流"。
        因此 obv/mfi（无 volume）走 "资金流"。
        """
        self.assertEqual(self.engine._infer_factor_type("obv_20"), "资金流")
        self.assertEqual(self.engine._infer_factor_type("MFI_14"), "资金流")

    def test_technical_indicators(self):
        """含 macd/rsi/stoch/cci/williams → '技术指标'"""
        self.assertEqual(self.engine._infer_factor_type("macd_12_26"), "技术指标")
        self.assertEqual(self.engine._infer_factor_type("RSI_14"), "技术指标")
        self.assertEqual(self.engine._infer_factor_type("stoch_k"), "技术指标")
        self.assertEqual(self.engine._infer_factor_type("CCI_20"), "技术指标")
        self.assertEqual(self.engine._infer_factor_type("williams_r"), "技术指标")

    def test_volatility_indicators(self):
        """含 bollinger/atr/volatility → '波动率'"""
        self.assertEqual(self.engine._infer_factor_type("bollinger_upper"), "波动率")
        self.assertEqual(self.engine._infer_factor_type("ATR_14"), "波动率")
        self.assertEqual(self.engine._infer_factor_type("volatility_20d"), "波动率")

    def test_trend_indicators(self):
        """含 adx/di/trix → '趋势'

        注意：'di' 是子串匹配，因此像 'media' / 'median' 这类词也会命中。
        这里只验证契约本身（子串匹配），不评判正确性。
        """
        self.assertEqual(self.engine._infer_factor_type("ADX_14"), "趋势")
        self.assertEqual(self.engine._infer_factor_type("+DI_14"), "趋势")
        self.assertEqual(self.engine._infer_factor_type("TRIX_12"), "趋势")

    def test_default_category(self):
        """不匹配任何关键词 → '其他'"""
        self.assertEqual(self.engine._infer_factor_type("unknown_factor"), "其他")
        self.assertEqual(self.engine._infer_factor_type("pe_ratio"), "其他")
        self.assertEqual(self.engine._infer_factor_type("market_cap"), "其他")

    def test_empty_string(self):
        """空字符串 → '其他'（不匹配任何关键词）"""
        self.assertEqual(self.engine._infer_factor_type(""), "其他")


class TestCalculateAccuracy(GuiEngineTestCase):
    """_calculate_accuracy 的方向准确率契约

    契约：accuracy = ((y > 0) == (predictions > 0)).mean()
    任意异常返回 0.0
    """

    def _make_model(self, pred_array):
        """构造 mock model，predict 返回固定数组"""
        model = MagicMock()
        model.predict = MagicMock(return_value=np.array(pred_array))
        return model

    def test_all_positive_perfect_match(self):
        """y 全正、预测全正 → accuracy = 1.0"""
        model = self._make_model([1.0, 2.0, 0.5])
        y = np.array([1.0, 2.0, 0.5])

        acc = self.engine._calculate_accuracy(model, MagicMock(), y)
        self.assertEqual(acc, 1.0)

    def test_all_positive_all_wrong(self):
        """y 全正、预测全负 → accuracy = 0.0"""
        model = self._make_model([-1.0, -2.0, -0.5])
        y = np.array([1.0, 2.0, 0.5])

        acc = self.engine._calculate_accuracy(model, MagicMock(), y)
        self.assertEqual(acc, 0.0)

    def test_mixed_direction_accuracy(self):
        """混合情况：方向准确率 = 命中数 / 总数"""
        # y 方向:        [+0.5, -0.3, +0.2, -0.1]   方向=[1,0,1,0]
        # pred 方向:     [+0.6, +0.4, -0.5, -0.2]   方向=[1,1,0,0]
        # 命中:           ✓     ✗     ✗     ✓     = 2/4 = 0.5
        model = self._make_model([0.6, 0.4, -0.5, -0.2])
        y = np.array([0.5, -0.3, 0.2, -0.1])

        acc = self.engine._calculate_accuracy(model, MagicMock(), y)
        self.assertAlmostEqual(acc, 0.5)

    def test_all_zero_predictions(self):
        """预测值全为 0：方向被当作 0（>0 不成立），统计上视为 '负' 方向"""
        # y 方向=[1,0]  pred 方向=[0,0]   命中=[F,T]   = 1/2 = 0.5
        model = self._make_model([0.0, 0.0])
        y = np.array([0.5, -0.5])

        acc = self.engine._calculate_accuracy(model, MagicMock(), y)
        self.assertAlmostEqual(acc, 0.5)

    def test_returns_python_float(self):
        """返回值必须是 Python float（不是 numpy 类型）"""
        model = self._make_model([1.0, -1.0])
        y = np.array([1.0, -1.0])

        acc = self.engine._calculate_accuracy(model, MagicMock(), y)
        # 锁定 float 类型契约：register_model 会在 f"{accuracy:.2%}" 中使用
        self.assertIsInstance(acc, float)

    def test_model_raises_returns_zero(self):
        """model.predict 抛异常 → 返回 0.0（不向上抛出）"""
        model = MagicMock()
        model.predict = MagicMock(side_effect=RuntimeError("boom"))
        y = np.array([1.0, -1.0])

        # 不应抛异常
        acc = self.engine._calculate_accuracy(model, MagicMock(), y)
        self.assertEqual(acc, 0.0)


class TestPreparePredictionDataEmpty(GuiEngineTestCase):
    """_prepare_prediction_data 在数据为空时抛 RuntimeError 的契约"""

    def test_empty_bars_raises_runtime_error(self):
        """ChinaDataLoader.load_bars 返回空 DataFrame → RuntimeError 含关键文本"""
        # patch 方法内部的 from ... import（在 gui_engine 中是延迟 import）
        # 因为 _prepare_prediction_data 在函数体里执行
        # `from vnpy_china_ml.dataset import ChinaDataLoader, Alpha158Calculator`
        # 所以 patch 源模块即可
        with patch("vnpy_china_ml.dataset.ChinaDataLoader") as MockLoader, \
             patch("vnpy_china_ml.dataset.Alpha158Calculator"):
            # load_bars 返回空 DataFrame（具备 columns 让 len() 工作）
            MockLoader.return_value.load_bars.return_value = pl.DataFrame({
                "datetime": [],
                "vt_symbol": [],
                "open_price": [],
                "close_price": [],
            })

            with self.assertRaises(RuntimeError) as ctx:
                self.engine._prepare_prediction_data(
                    symbols=["000001.SZ"],
                    predict_date=date(2026, 6, 15)
                )

            msg = str(ctx.exception)
            # 关键文本：用于在重构后保持向后兼容
            self.assertIn("本地数据库中没有股票数据", msg)


class TestPrepareTrainingDataEmpty(GuiEngineTestCase):
    """_prepare_training_data 在数据为空时抛 RuntimeError 的契约"""

    def test_empty_dataset_raises_runtime_error(self):
        """create_alpha_dataset().get_all_data() 返回空 X → RuntimeError 含关键文本"""
        # 构造 mock dataset：get_all_data 返回 (空X, 空y)
        mock_dataset = MagicMock()
        empty_X = np.array([]).reshape(0, 0)  # 0 行
        empty_y = np.array([])
        mock_dataset.get_all_data.return_value = (empty_X, empty_y)
        mock_dataset.get_feature_names.return_value = []

        with patch("vnpy_china_ml.dataset.create_alpha_dataset", return_value=mock_dataset):
            with self.assertRaises(RuntimeError) as ctx:
                self.engine._prepare_training_data(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 6, 1),
                    lookback_days=60,
                    forward_days=5
                )

            msg = str(ctx.exception)
            self.assertIn("本地数据库中没有训练数据", msg)


class TestPredictModelNotFound(GuiEngineTestCase):
    """predict 在模型不存在时抛 RuntimeError 的契约"""

    def test_missing_model_id_raises_runtime_error(self):
        """传入不存在的 model_id → RuntimeError 消息含 '模型未找到'"""
        # ModelManager 在临时目录中，load_model 必然返回 None
        with self.assertRaises(RuntimeError) as ctx:
            self.engine.predict(
                model_id="non_existent_model_xyz",
                symbols=["000001.SZ"],
                predict_date=date(2026, 6, 15)
            )

        msg = str(ctx.exception)
        # 关键文本契约
        self.assertIn("模型未找到", msg)
        # 应当包含出错的 model_id，便于排错
        self.assertIn("non_existent_model_xyz", msg)

    def test_missing_model_error_message_contains_hint(self):
        """异常消息应包含 '请先训练模型' 的用户提示"""
        with self.assertRaises(RuntimeError) as ctx:
            self.engine.predict(
                model_id="another_missing",
                symbols=["600000.SH"],
                predict_date=date(2026, 6, 15)
            )
        self.assertIn("请先训练模型", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
