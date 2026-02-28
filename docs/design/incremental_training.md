# 模型增量训练功能设计方案

> 更新时间：2026-02-28

## Context

**问题背景**：VeighNa 框架的 `vnpy/alpha` 模块目前不支持真正的模型增量训练。虽然 `AlphaDataset` 有 `process_type="append"` 参数，但这只是数据层面的追加，所有模型（LgbModel、MlpModel、LassoModel）在调用 `fit()` 时都会完整重训练。

**目标**：设计并实现完整的模型增量训练功能，包括：
1. 增量训练 API 接口
2. 模型版本管理
3. 增量数据管理
4. AlphaLab 工作流集成

---

## 现有架构

```
vnpy/alpha/
├── lab.py                    # AlphaLab - 投研实验室
├── dataset/
│   └── template.py           # AlphaDataset - 数据集模板
├── model/
│   ├── template.py           # AlphaModel - 模型基类
│   └── models/
│       ├── lgb_model.py      # LightGBM - 支持增量（init_model）
│       ├── mlp_model.py      # PyTorch MLP - 支持 warm_start
│       └── lasso_model.py    # Lasso - 不支持增量
```

**关键发现**：
- LightGBM 原生支持 `init_model` 参数实现增量训练
- PyTorch 可通过加载已有权重实现 warm_start
- 模型使用 pickle 序列化存储，无版本管理

---

## 设计方案

### 1. 新增文件

| 文件 | 职责 |
|------|------|
| `vnpy/alpha/model/version.py` | ModelVersion 数据类 |
| `vnpy/alpha/model/version_manager.py` | ModelVersionManager 版本管理器 |
| `vnpy/alpha/dataset/incremental.py` | IncrementalDatasetManager 数据增量管理 |

### 2. AlphaModel 基类修改

**文件**: `vnpy/alpha/model/template.py`

```python
class AlphaModel(metaclass=ABCMeta):
    # 新增：增量训练能力标识
    supports_incremental: bool = False

    # 新增：增量训练接口
    def partial_fit(self, dataset: AlphaDataset, **kwargs) -> dict:
        """增量训练（可选实现）"""
        if not self.supports_incremental:
            raise NotImplementedError(f"{self.__class__.__name__} 不支持增量训练")
        raise NotImplementedError("子类必须实现 partial_fit()")

    # 新增：训练状态序列化
    def get_training_state(self) -> dict: return {}
    def set_training_state(self, state: dict) -> None: pass
```

### 3. LgbModel 增量训练实现

**文件**: `vnpy/alpha/model/models/lgb_model.py`

```python
class LgbModel(AlphaModel):
    supports_incremental: bool = True
    _last_model: lgb.Booster | None = None  # 保存上次模型

    def partial_fit(self, dataset, num_boost_round=100, reset_model=False) -> dict:
        """使用 init_model 参数实现增量训练"""
        if reset_model:
            self._last_model = None

        self.model = lgb.train(
            self.params,
            ds[0],
            num_boost_round=num_boost_round,
            init_model=self._last_model,  # 关键：从已有模型继续
            callbacks=[...]
        )
        self._last_model = self.model
        return {"status": "success", "method": "incremental"}
```

### 4. ModelVersion 数据结构

**文件**: `vnpy/alpha/model/version.py`

```python
@dataclass
class ModelVersion:
    version_id: str                    # v{timestamp}
    created_at: datetime
    train_period: tuple[str, str]
    valid_period: tuple[str, str]

    # 训练统计
    n_samples: int = 0
    training_duration: float = 0.0
    train_loss: float | None = None
    valid_loss: float | None = None

    # 增量训练信息
    is_incremental: bool = False
    base_version: str | None = None

    # 元数据
    description: str = ""
    tags: list[str] = field(default_factory=list)
```

### 5. AlphaLab 新增方法

**文件**: `vnpy/alpha/lab.py`

```python
class AlphaLab:
    def __init__(self, lab_path: str):
        # 新增
        self.version_manager = ModelVersionManager(self.model_path)

    def train_model_incremental(
        self,
        model_name: str,
        dataset: AlphaDataset
    ) -> tuple[AlphaModel, ModelVersion]:
        """智能增量训练：自动检测是否增量"""

    def save_model_with_version(
        self,
        name: str,
        model: AlphaModel,
        dataset: AlphaDataset
    ) -> ModelVersion:
        """保存模型并创建版本"""

    def load_model_version(
        self,
        name: str,
        version_id: str | None = None
    ) -> tuple[AlphaModel, ModelVersion]:
        """加载指定版本"""

    def rollback_model(self, name: str, version_id: str) -> bool:
        """回滚到指定版本"""
```

### 6. 版本存储格式

**文件**: `lab_path/model/versions.json`

```json
{
  "my_model": {
    "current_version": "v20260228_143022",
    "versions": [
      {
        "version_id": "v20260228_143022",
        "created_at": "2026-02-28T14:30:22",
        "train_period": ["2020-01-01", "2025-12-31"],
        "is_incremental": true,
        "base_version": "v20260215_100000",
        "train_loss": 0.00234,
        "file_path": "my_model/v20260228_143022.pkl"
      }
    ]
  }
}
```

### 7. 目录结构

```
lab_path/
├── model/
│   ├── my_model.pkl              # 当前版本（向后兼容）
│   ├── versions.json             # 版本索引
│   └── my_model/                 # 历史版本
│       ├── v20260215_100000.pkl
│       └── v20260228_143022.pkl
├── dataset/
│   └── my_dataset.pkl
└── ...
```

---

## 实现任务

### Phase 1: 基础架构（P0）

- [ ] 创建 `ModelVersion` 数据类
- [ ] 实现 `ModelVersionManager` 版本管理器
- [ ] 修改 `AlphaModel` 基类添加增量接口

### Phase 2: 模型实现（P0）

- [ ] `LgbModel` 实现 `partial_fit()` 方法
- [ ] `MlpModel` 实现 warm_start 支持
- [ ] `LassoModel` 标记 `supports_incremental=False`

### Phase 3: 工作流集成（P0）

- [ ] `AlphaLab` 添加版本管理器初始化
- [ ] `AlphaLab` 添加 `train_model_incremental()` 方法
- [ ] `AlphaLab` 添加 `save_model_with_version()` 方法
- [ ] `AlphaLab` 添加 `load_model_version()` 方法
- [ ] `AlphaLab` 添加 `rollback_model()` 方法

### Phase 4: 测试验证（P0）

- [ ] 单元测试：版本创建、保存、加载
- [ ] 单元测试：LgbModel 增量训练
- [ ] 集成测试：完整增量训练工作流
- [ ] 性能对比：增量 vs 完整重训练

---

## 验证方案

### 1. 功能测试

```python
# 测试增量训练工作流
lab = AlphaLab("./test_lab")
dataset = AlphaDataset(df, ...)

# 初始训练
model = LgbModel()
model.fit(dataset)
v1 = lab.save_model_with_version("test", model, dataset)

# 模拟新数据
new_df = load_new_data()
dataset.df = pl.concat([dataset.df, new_df])

# 增量训练
model2, v2 = lab.train_model_incremental("test", dataset)
assert v2.is_incremental == True
assert v2.base_version == v1.version_id

# 回滚测试
lab.rollback_model("test", v1.version_id)
```

### 2. 性能验证

```bash
# 运行性能对比测试
python -m pytest tests/test_incremental_performance.py -v
```

---

## 关键文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `vnpy/alpha/model/version.py` | 新增 | ModelVersion 数据类 |
| `vnpy/alpha/model/version_manager.py` | 新增 | 版本管理器 |
| `vnpy/alpha/model/template.py` | 修改 | 添加增量训练接口 |
| `vnpy/alpha/model/models/lgb_model.py` | 修改 | 实现 partial_fit |
| `vnpy/alpha/model/models/mlp_model.py` | 修改 | 实现 warm_start |
| `vnpy/alpha/lab.py` | 修改 | 集成版本管理 |