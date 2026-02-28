"""测试 AlphaModel 基类的增量训练接口"""

import pytest
from unittest.mock import MagicMock, patch

from vnpy.alpha.model.template import AlphaModel


# 创建一个具体的实现类用于测试
class ConcreteAlphaModel(AlphaModel):
    """AlphaModel 的具体实现类，用于测试"""

    def fit(self, dataset):
        """实现抽象方法"""
        pass

    def predict(self, dataset, segment):
        """实现抽象方法"""
        import numpy as np
        return np.array([0.0])


class TestAlphaModelIncremental:
    """测试 AlphaModel 增量训练接口"""

    def test_supports_incremental_default_false(self):
        """测试 supports_incremental 属性默认值为 False"""
        model = ConcreteAlphaModel()
        assert model.supports_incremental is False

    def test_partial_fit_raises_when_not_supported(self):
        """测试当不支持增量训练时，partial_fit 抛出 NotImplementedError"""
        model = ConcreteAlphaModel()

        with pytest.raises(NotImplementedError) as exc_info:
            model.partial_fit(None)

        assert "不支持增量训练" in str(exc_info.value)

    def test_get_training_state_returns_empty_dict(self):
        """测试 get_training_state 返回空字典"""
        model = ConcreteAlphaModel()
        state = model.get_training_state()
        assert state == {}

    def test_set_training_state_accepts_dict(self):
        """测试 set_training_state 接受字典参数"""
        model = ConcreteAlphaModel()
        # 不应该抛出异常
        model.set_training_state({"epoch": 10, "loss": 0.5})
        model.set_training_state({})


class TestAlphaModelWithIncrementalSupport:
    """测试支持增量训练的模型子类"""

    def test_subclass_with_incremental_support(self):
        """测试子类启用增量训练支持"""
        class IncrementalModel(AlphaModel):
            supports_incremental = True

            def fit(self, dataset):
                pass

            def predict(self, dataset, segment):
                import numpy as np
                return np.array([0.0])

            def partial_fit(self, dataset, **kwargs):
                return {"status": "success", "epochs": kwargs.get("epochs", 1)}

        model = IncrementalModel()
        assert model.supports_incremental is True

        # partial_fit 不会被拒绝
        result = model.partial_fit(None, epochs=5)
        assert result["status"] == "success"
        assert result["epochs"] == 5


class TestLassoModelIncremental:
    """测试 LassoModel 增量训练支持"""

    def test_lasso_supports_incremental_is_false(self):
        """测试 LassoModel 不支持增量训练"""
        from vnpy.alpha.model.models.lasso_model import LassoModel

        model = LassoModel()
        assert model.supports_incremental is False

    def test_lasso_partial_fit_raises_not_implemented(self):
        """测试 LassoModel 的 partial_fit 方法抛出 NotImplementedError"""
        from vnpy.alpha.model.models.lasso_model import LassoModel

        model = LassoModel()

        with pytest.raises(NotImplementedError) as exc_info:
            model.partial_fit(None)

        assert "不支持增量训练" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
