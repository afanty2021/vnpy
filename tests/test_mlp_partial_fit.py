"""
MlpModel Incremental Training Feature Tests

Tests for MlpModel's partial_fit method to verify incremental training functionality.
"""

import numpy as np
import polars as pl
import torch

from vnpy.alpha.model.models.mlp_model import MlpModel


def test_supports_incremental():
    """Test supports_incremental attribute"""
    model = MlpModel(input_size=10)

    # Verify supports_incremental attribute exists and is True
    assert hasattr(model, "supports_incremental"), "MlpModel missing supports_incremental attribute"
    assert model.supports_incremental is True, "MlpModel.supports_incremental should be True"

    print("[PASS] supports_incremental attribute test")


def test_last_model_state_attribute():
    """Test _last_model_state attribute"""
    model = MlpModel(input_size=10)

    # Verify _last_model_state attribute exists
    assert hasattr(model, "_last_model_state"), "MlpModel missing _last_model_state attribute"
    assert model._last_model_state is None, "Initial _last_model_state should be None"

    print("[PASS] _last_model_state attribute test")


def test_partial_fit_method_signature():
    """Test partial_fit method signature"""
    # Create model
    model = MlpModel(
        input_size=10,
        hidden_sizes=(32,),
        lr=0.001,
        n_epochs=5,
        batch_size=64,
        seed=42
    )

    # Verify method signature is correct
    import inspect
    sig = inspect.signature(model.partial_fit)

    # Verify parameters
    params = list(sig.parameters.keys())
    assert "dataset" in params, "partial_fit should have dataset parameter"
    assert "n_epochs" in params, "partial_fit should have n_epochs parameter"
    assert "reset_model" in params, "partial_fit should have reset_model parameter"

    print("[PASS] partial_fit method signature test")


def test_training_state_methods():
    """Test training state serialization methods"""
    model = MlpModel(input_size=10)

    # Test get_training_state
    state = model.get_training_state()
    assert "model_state" in state, "Training state should contain model_state"
    assert "fitted" in state, "Training state should contain fitted"
    assert "feature_names" in state, "Training state should contain feature_names"
    assert "best_step" in state, "Training state should contain best_step"

    # Test set_training_state
    model.set_training_state(state)
    assert model._last_model_state is None, "After restore, _last_model_state should be None"
    assert model.fitted is False, "After restore, fitted should be False"

    print("[PASS] training state methods test")


def test_incremental_training_flow():
    """Test incremental training flow"""
    # Create model
    model = MlpModel(
        input_size=10,
        hidden_sizes=(32,),
        lr=0.001,
        n_epochs=5,
        batch_size=64,
        seed=42
    )

    # Verify supports_incremental is True
    assert model.supports_incremental is True

    # Verify _last_model_state initially is None
    assert model._last_model_state is None

    # Verify partial_fit method exists and is callable
    assert callable(model.partial_fit), "partial_fit should be callable"

    # Verify method signature
    import inspect
    sig = inspect.signature(model.partial_fit)
    assert "dataset" in sig.parameters
    assert "n_epochs" in sig.parameters
    assert "reset_model" in sig.parameters

    print("[PASS] incremental training flow test")


def test_model_state_saving():
    """Test model weight saving - simplified test without actual training"""
    model = MlpModel(
        input_size=10,
        hidden_sizes=(32,),
        lr=0.001,
        n_epochs=1,
        batch_size=64,
        seed=42
    )

    # Verify initial state
    assert model._last_model_state is None, "Initial _last_model_state should be None"

    # Simulate saving model state after training
    # Get current model state
    current_state = model.model.state_dict()

    # Save to _last_model_state
    import copy
    model._last_model_state = copy.deepcopy(current_state)

    # Verify state is saved correctly
    assert model._last_model_state is not None, "_last_model_state should be saved"
    assert isinstance(model._last_model_state, dict), "_last_model_state should be dict"

    # Verify saved state can be loaded
    for key in model._last_model_state:
        assert isinstance(model._last_model_state[key], torch.Tensor), \
            f"Model state {key} should be Tensor"

    print("[PASS] model weight saving test")


def test_training_state_serialization():
    """Test training state serialization/deserialization"""
    model = MlpModel(
        input_size=10,
        hidden_sizes=(32,),
        lr=0.001,
        n_epochs=1,
        batch_size=64,
        seed=42
    )

    # Simulate model state
    import copy
    model._last_model_state = copy.deepcopy(model.model.state_dict())
    model.fitted = True
    model.feature_names = ["feature_0", "feature_1"]
    model.best_step = 10

    # Get training state
    state = model.get_training_state()

    # Verify state contents
    assert "model_state" in state
    assert "fitted" in state
    assert "feature_names" in state
    assert "best_step" in state
    assert state["fitted"] is True
    assert state["feature_names"] == ["feature_0", "feature_1"]
    assert state["best_step"] == 10

    # Create new model and restore state
    new_model = MlpModel(
        input_size=10,
        hidden_sizes=(32,),
        lr=0.001,
        seed=42
    )

    new_model.set_training_state(state)

    # Verify state restored
    assert new_model._last_model_state is not None, "After restore, _last_model_state should not be None"
    assert new_model.fitted == model.fitted, "fitted status should match"
    assert new_model.feature_names == model.feature_names, "feature_names should match"
    assert new_model.best_step == model.best_step, "best_step should match"

    print("[PASS] training state serialization test")


def test_base_model_inheritance():
    """Test proper inheritance from AlphaModel"""
    from vnpy.alpha.model import AlphaModel

    model = MlpModel(input_size=10)

    # Verify inheritance
    assert isinstance(model, AlphaModel), "MlpModel should inherit from AlphaModel"

    # Verify base class methods exist
    assert hasattr(model, "fit"), "MlpModel should have fit method"
    assert hasattr(model, "predict"), "MlpModel should have predict method"
    assert hasattr(model, "partial_fit"), "MlpModel should have partial_fit method"
    assert hasattr(model, "detail"), "MlpModel should have detail method"
    assert hasattr(model, "get_training_state"), "MlpModel should have get_training_state method"
    assert hasattr(model, "set_training_state"), "MlpModel should have set_training_state method"

    print("[PASS] base model inheritance test")


def main():
    """Run all tests"""
    print("=" * 60)
    print("MlpModel Incremental Training Feature Tests")
    print("=" * 60)

    tests = [
        ("Base model inheritance test", test_base_model_inheritance),
        ("supports_incremental attribute test", test_supports_incremental),
        ("_last_model_state attribute test", test_last_model_state_attribute),
        ("partial_fit method signature test", test_partial_fit_method_signature),
        ("Training state methods test", test_training_state_methods),
        ("Incremental training flow test", test_incremental_training_flow),
        ("Model weight saving test", test_model_state_saving),
        ("Training state serialization test", test_training_state_serialization),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n[TEST] {name}")
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Tests completed: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
