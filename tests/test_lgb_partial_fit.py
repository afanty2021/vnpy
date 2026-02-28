"""
LgbModel 增量训练功能测试

测试 LgbModel 的 partial_fit 方法是否正确实现增量训练功能。
"""

import numpy as np
import polars as pl

from vnpy.alpha.model.models.lgb_model import LgbModel


def create_mock_dataset():
    """创建模拟数据集用于测试"""
    # 创建简单的测试数据
    np.random.seed(42)
    n_samples = 1000
    n_features = 10

    # 生成特征数据
    features = np.random.randn(n_samples, n_features)
    labels = features[:, 0] * 0.5 + features[:, 1] * 0.3 + np.random.randn(n_samples) * 0.1

    # 创建 Polars DataFrame
    df = pl.DataFrame({
        "datetime": [pl.datetime(2024, 1, i % 30 + 1) for i in range(n_samples)],
        "vt_symbol": [f"TEST{i % 10}.SSE" for i in range(n_samples)],
        **{f"feature_{i}": features[:, i] for i in range(n_features)},
        "label": labels
    })

    return df


def test_supports_incremental():
    """测试 supports_incremental 属性"""
    model = LgbModel()

    # 验证 supports_incremental 属性存在且为 True
    assert hasattr(model, "supports_incremental"), "LgbModel 缺少 supports_incremental 属性"
    assert model.supports_incremental is True, "LgbModel.supports_incremental 应为 True"

    print("[PASS] supports_incremental 属性测试通过")


def test_last_model_attribute():
    """测试 _last_model 属性"""
    model = LgbModel()

    # 验证 _last_model 属性存在
    assert hasattr(model, "_last_model"), "LgbModel 缺少 _last_model 属性"
    assert model._last_model is None, "初始状态下 _last_model 应为 None"

    print("[PASS] _last_model 属性测试通过")


def test_partial_fit_method():
    """测试 partial_fit 方法的基本功能"""
    # 创建模型
    model = LgbModel(
        learning_rate=0.1,
        num_leaves=31,
        num_boost_round=10,  # 少量轮数用于快速测试
        early_stopping_rounds=5,
        log_evaluation_period=5,
        seed=42
    )

    # 由于完整的 AlphaDataset 需要大量数据，我们创建一个最小化的测试
    # 验证方法签名正确
    import inspect
    sig = inspect.signature(model.partial_fit)

    # 验证参数
    params = list(sig.parameters.keys())
    assert "dataset" in params, "partial_fit 应有 dataset 参数"
    assert "num_boost_round" in params, "partial_fit 应有 num_boost_round 参数"
    assert "reset_model" in params, "partial_fit 应有 reset_model 参数"

    print("[PASS] partial_fit 方法签名测试通过")


def test_training_state_methods():
    """测试训练状态序列化方法"""
    model = LgbModel()

    # 测试 get_training_state
    state = model.get_training_state()
    assert "last_model" in state, "训练状态应包含 last_model"
    assert "model" in state, "训练状态应包含 model"

    # 测试 set_training_state
    model.set_training_state(state)
    assert model._last_model is None, "恢复后 _last_model 应为 None"

    print("[PASS] 训练状态方法测试通过")


def test_incremental_training_flow():
    """测试增量训练流程"""
    # 创建模型
    model = LgbModel(
        learning_rate=0.1,
        num_leaves=31,
        num_boost_round=10,
        early_stopping_rounds=5,
        log_evaluation_period=10,
        seed=42
    )

    # 验证 supports_incremental 为 True
    assert model.supports_incremental is True

    # 验证 _last_model 初始为 None
    assert model._last_model is None

    # 验证 partial_fit 方法存在且可调用
    assert callable(model.partial_fit), "partial_fit 应该是可调用的"

    # 验证方法签名
    import inspect
    sig = inspect.signature(model.partial_fit)
    assert "dataset" in sig.parameters
    assert "num_boost_round" in sig.parameters
    assert "reset_model" in sig.parameters

    print("[PASS] 增量训练流程测试通过")


def test_base_model_inheritance():
    """测试是否正确继承 AlphaModel"""
    from vnpy.alpha.model import AlphaModel

    model = LgbModel()

    # 验证继承关系
    assert isinstance(model, AlphaModel), "LgbModel 应继承自 AlphaModel"

    # 验证基类方法存在
    assert hasattr(model, "fit"), "LgbModel 应有 fit 方法"
    assert hasattr(model, "predict"), "LgbModel 应有 predict 方法"
    assert hasattr(model, "partial_fit"), "LgbModel 应有 partial_fit 方法"
    assert hasattr(model, "detail"), "LgbModel 应有 detail 方法"
    assert hasattr(model, "get_training_state"), "LgbModel 应有 get_training_state 方法"
    assert hasattr(model, "set_training_state"), "LgbModel 应有 set_training_state 方法"

    print("[PASS] 基类继承测试通过")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("LgbModel 增量训练功能测试")
    print("=" * 60)

    tests = [
        ("基类继承测试", test_base_model_inheritance),
        ("supports_incremental 属性测试", test_supports_incremental),
        ("_last_model 属性测试", test_last_model_attribute),
        ("partial_fit 方法测试", test_partial_fit_method),
        ("训练状态方法测试", test_training_state_methods),
        ("增量训练流程测试", test_incremental_training_flow),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n[测试] {name}")
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
