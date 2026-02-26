"""
A股机器学习模型模块

本模块提供了针对A股市场的机器学习模型实现，支持多种模型类型：
- LightGBM
- XGBoost
- RandomForest
- Lasso
- Ridge
- LSTM

主要功能包括：
- 模型训练与预测
- 特征重要性分析
- 模型持久化（保存/加载）
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from datetime import datetime

from ..utils.types import ModelType, TrainingConfig, PredictionResult, SignalType


class ChinaAlphaModel:
    """A股机器学习模型

    用于A股市场的机器学习预测模型，支持多种算法。

    Attributes:
        model_type: 模型类型
        model: 底层机器学习模型实例
        is_trained: 是否已完成训练
        feature_names: 特征名称列表
        training_date: 最后训练日期
    """

    def __init__(self, model_type: ModelType = ModelType.RANDOM_FOREST):
        """初始化模型

        Args:
            model_type: 模型类型，默认为LIGHTGBM
        """
        # 处理 model_type 可能是字符串的情况
        if isinstance(model_type, str):
            try:
                model_type = ModelType(model_type)
            except ValueError:
                raise ValueError(f"无效的模型类型: {model_type}")

        self.model_type: ModelType = model_type
        self.model: Optional[Any] = None
        self.is_trained: bool = False
        self.feature_names: List[str] = []
        self.training_date: Optional[datetime] = None

        # 初始化底层模型
        self._init_model()

    def _init_model(self) -> None:
        """根据模型类型初始化对应的机器学习模型"""
        if self.model_type == ModelType.LIGHTGBM:
            self._init_lightgbm()
        elif self.model_type == ModelType.XGBOOST:
            self._init_xgboost()
        elif self.model_type == ModelType.RANDOM_FOREST:
            self._init_random_forest()
        elif self.model_type == ModelType.LASSO:
            self._init_lasso()
        elif self.model_type == ModelType.RIDGE:
            self._init_ridge()
        elif self.model_type == ModelType.LSTM:
            self._init_lstm()
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")

    def _init_lightgbm(self) -> None:
        """初始化LightGBM模型"""
        try:
            import lightgbm as lgb
            self.model = lgb.LGBMRegressor(
                n_estimators=100,
                learning_rate=0.05,
                max_depth=6,
                num_leaves=31,
                random_state=42,
                verbose=-1
            )
        except ImportError:
            raise ImportError("请安装lightgbm: pip install lightgbm")

    def _init_xgboost(self) -> None:
        """初始化XGBoost模型"""
        try:
            import xgboost as xgb
            self.model = xgb.XGBRegressor(
                n_estimators=100,
                learning_rate=0.05,
                max_depth=6,
                random_state=42,
                verbosity=0
            )
        except ImportError:
            raise ImportError("请安装xgboost: pip install xgboost")

    def _init_random_forest(self) -> None:
        """初始化随机森林模型"""
        from sklearn.ensemble import RandomForestRegressor
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=6,
            random_state=42,
            n_jobs=-1
        )

    def _init_lasso(self) -> None:
        """初始化Lasso回归模型"""
        from sklearn.linear_model import Lasso
        self.model = Lasso(alpha=1.0, random_state=42)

    def _init_ridge(self) -> None:
        """初始化Ridge回归模型"""
        from sklearn.linear_model import Ridge
        self.model = Ridge(alpha=1.0, random_state=42)

    def _init_lstm(self) -> None:
        """初始化LSTM模型（基于PyTorch）"""
        try:
            import torch
            import torch.nn as nn

            class SimpleLSTM(nn.Module):
                def __init__(self, input_size: int, hidden_size: int = 64, num_layers: int = 2):
                    super().__init__()
                    self.hidden_size = hidden_size
                    self.num_layers = num_layers
                    self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
                    self.fc = nn.Linear(hidden_size, 1)

                def forward(self, x):
                    # x shape: (batch, seq_len, input_size)
                    lstm_out, _ = self.lstm(x)
                    out = self.fc(lstm_out[:, -1, :])
                    return out

            self.model = SimpleLSTM
            self._lstm_input_size: int = 0
        except ImportError:
            raise ImportError("请安装PyTorch: pip install torch")

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weight: Optional[np.ndarray] = None,
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """训练模型

        Args:
            X: 特征矩阵，形状为 (n_samples, n_features)
            y: 目标变量，形状为 (n_samples,)
            sample_weight: 样本权重，可选
            feature_names: 特征名称列表，可选

        Returns:
            训练结果字典，包含训练状态等信息

        Raises:
            ValueError: 如果数据形状不匹配
        """
        # 验证输入数据
        if len(X) == 0:
            raise ValueError("训练数据不能为空")
        if len(X) != len(y):
            raise ValueError(f"特征矩阵和目标变量长度不匹配: {len(X)} vs {len(y)}")
        if sample_weight is not None and len(sample_weight) != len(X):
            raise ValueError(f"样本权重长度不匹配: {len(sample_weight)} vs {len(X)}")

        # 保存特征名称
        if feature_names is not None:
            self.feature_names = feature_names
        elif len(X.shape) > 1:
            self.feature_names = [f"feature_{i}" for i in range(X.shape[1])]

        # 训练模型
        if self.model_type == ModelType.LSTM:
            # LSTM需要特殊处理
            self._train_lstm(X, y, sample_weight)
        else:
            # 其他模型使用sklearn风格
            if sample_weight is not None:
                self.model.fit(X, y, sample_weight=sample_weight)
            else:
                self.model.fit(X, y)

        self.is_trained = True
        self.training_date = datetime.now()

        return {
            "status": "success",
            "model_type": self.model_type.value,
            "n_samples": len(X),
            "n_features": X.shape[1] if len(X.shape) > 1 else 1,
            "training_date": self.training_date.isoformat()
        }

    def _train_lstm(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weight: Optional[np.ndarray] = None
    ) -> None:
        """训练LSTM模型

        Args:
            X: 特征矩阵
            y: 目标变量
            sample_weight: 样本权重
        """
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset

        # 保存输入维度
        self._lstm_input_size = X.shape[1] if len(X.shape) > 1 else 1

        # 将数据转换为LSTM输入格式 (samples, timesteps, features)
        # 假设timesteps=1
        X_lstm = X.reshape((X.shape[0], 1, self._lstm_input_size))

        # 转换为PyTorch张量
        X_tensor = torch.FloatTensor(X_lstm)
        y_tensor = torch.FloatTensor(y)

        # 创建数据加载器
        dataset = TensorDataset(X_tensor, y_tensor)
        dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

        # 初始化模型
        self._lstm_model = self.model(input_size=self._lstm_input_size)
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self._lstm_model.parameters(), lr=0.001)

        # 训练
        self._lstm_model.train()
        for epoch in range(10):
            for batch_X, batch_y in dataloader:
                optimizer.zero_grad()
                outputs = self._lstm_model(batch_X)
                loss = criterion(outputs.squeeze(), batch_y)
                loss.backward()
                optimizer.step()

    def predict(self, X: np.ndarray) -> np.ndarray:
        """使用模型进行预测

        Args:
            X: 特征矩阵，形状为 (n_samples, n_features)

        Returns:
            预测值数组，形状为 (n_samples,)

        Raises:
            ValueError: 如果模型未训练或输入数据无效
        """
        if not self.is_trained:
            raise ValueError("模型未训练，请先调用train方法")

        if len(X) == 0:
            raise ValueError("预测数据不能为空")

        if self.model_type == ModelType.LSTM:
            return self._predict_lstm(X)
        else:
            return self.model.predict(X)

    def _predict_lstm(self, X: np.ndarray) -> np.ndarray:
        """LSTM模型预测

        Args:
            X: 特征矩阵

        Returns:
            预测值数组
        """
        import torch

        # 转换数据格式
        X_lstm = X.reshape((X.shape[0], 1, self._lstm_input_size))
        X_tensor = torch.FloatTensor(X_lstm)

        self._lstm_model.eval()
        with torch.no_grad():
            predictions = self._lstm_model(X_tensor).squeeze().numpy()

        return predictions

    def predict_with_signals(
        self,
        X: np.ndarray,
        symbols: List[str],
        dates: List[datetime],
        confidence_threshold: float = 0.5,
        return_threshold: float = 0.02
    ) -> List[PredictionResult]:
        """带交易信号的预测

        Args:
            X: 特征矩阵
            symbols: 股票代码列表
            dates: 日期列表
            confidence_threshold: 置信度阈值
            return_threshold: 收益率阈值，用于生成信号

        Returns:
            预测结果列表

        Raises:
            ValueError: 如果输入数据不匹配
        """
        if len(X) != len(symbols) or len(X) != len(dates):
            raise ValueError("特征矩阵、股票代码和日期列表长度必须一致")

        # 进行预测
        predictions = self.predict(X)

        results: List[PredictionResult] = []
        for i in range(len(predictions)):
            pred_return = predictions[i]
            confidence = min(abs(pred_return) / return_threshold, 1.0) if pred_return != 0 else 0.0

            # 生成交易信号
            if pred_return > return_threshold and confidence >= confidence_threshold:
                signal = SignalType.BUY
            elif pred_return < -return_threshold and confidence >= confidence_threshold:
                signal = SignalType.SELL
            else:
                signal = SignalType.HOLD

            result = PredictionResult(
                symbol=symbols[i],
                datetime=dates[i],
                predicted_return=pred_return,
                confidence=confidence,
                signal=signal,
                model_name=f"china_alpha_{self.model_type.value}"
            )
            results.append(result)

        return results

    def get_feature_importance(self) -> np.ndarray:
        """获取特征重要性

        Returns:
            特征重要性数组

        Raises:
            ValueError: 如果模型未训练或不支持特征重要性
        """
        if not self.is_trained:
            raise ValueError("模型未训练，请先调用train方法")

        if self.model_type == ModelType.LSTM:
            # LSTM使用其他方法获取重要性
            return np.zeros(len(self.feature_names)) if self.feature_names else np.array([])

        # LightGBM和XGBoost支持feature_importances_
        if hasattr(self.model, 'feature_importances_'):
            return self.model.feature_importances_

        # 随机森林支持feature_importances_
        if hasattr(self.model, 'feature_importances_'):
            return self.model.feature_importances_

        return np.array([])

    def get_feature_importance_dict(self) -> Dict[str, float]:
        """获取特征重要性字典

        Returns:
            特征名称到重要性的映射字典
        """
        importance = self.get_feature_importance()
        if len(importance) == 0:
            return {}

        result: Dict[str, float] = {}
        for i, name in enumerate(self.feature_names):
            result[name] = float(importance[i])

        return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))

    def save_model(self, path: str) -> bool:
        """保存模型到文件

        Args:
            path: 保存路径

        Returns:
            是否保存成功
        """
        import pickle

        try:
            # 保存模型
            model_data = {
                "model_type": self.model_type,
                "model": self.model,
                "is_trained": self.is_trained,
                "feature_names": self.feature_names,
                "training_date": self.training_date
            }

            # 特殊处理LSTM模型
            if self.model_type == ModelType.LSTM and hasattr(self, '_lstm_model'):
                model_data["lstm_model"] = self._lstm_model
                model_data["lstm_input_size"] = self._lstm_input_size

            with open(path, 'wb') as f:
                pickle.dump(model_data, f)

            return True
        except Exception as e:
            print(f"保存模型失败: {e}")
            return False

    def load_model(self, path: str) -> bool:
        """从文件加载模型

        Args:
            path: 模型文件路径

        Returns:
            是否加载成功
        """
        import pickle

        try:
            with open(path, 'rb') as f:
                model_data = pickle.load(f)

            self.model_type = model_data["model_type"]
            self.model = model_data["model"]
            self.is_trained = model_data["is_trained"]
            self.feature_names = model_data["feature_names"]
            self.training_date = model_data.get("training_date")

            # 特殊处理LSTM模型
            if self.model_type == ModelType.LSTM:
                self._lstm_model = model_data.get("lstm_model")
                self._lstm_input_size = model_data.get("lstm_input_size", 0)

            return True
        except Exception as e:
            print(f"加载模型失败: {e}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息

        Returns:
            包含模型信息的字典
        """
        return {
            "model_type": self.model_type.value,
            "is_trained": self.is_trained,
            "n_features": len(self.feature_names),
            "feature_names": self.feature_names,
            "training_date": self.training_date.isoformat() if self.training_date else None
        }

    def __repr__(self) -> str:
        """模型字符串表示"""
        return f"ChinaAlphaModel(model_type={self.model_type.value}, is_trained={self.is_trained})"
