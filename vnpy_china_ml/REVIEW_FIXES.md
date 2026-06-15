# vnpy_china_ml 审查修复变更总结

> 修复批次日期：2026-06-15
> 触发：4 模块架构审查 → P0/P1/P2 优先级修复 + 2 个独立问题
> 测试状态：226 tests 全绿（0 failure，0 error）

## 改动概览

```
13 files modified + 1 file created | +1115 insertions, -297 deletions
```

| 类别 | 文件数 | 净增行 |
|------|--------|--------|
| 安全修复（P0） | 2 | +298 |
| 用户体验（P1） | 3 | +20 |
| 架构优化（P2） | 5 | +483 |
| 独立问题（data_manager API 漂移） | 1 | +531（含重写） |
| 测试新增 | 1 新建 + 1 修改 | +184 / +18 |

---

## P0 — 安全 + 文档修复

### `model/manager.py`（+116 行）
**pickle → JSON 反序列化安全修复**（消除 `pickle.load` 任意代码执行风险）
- `_save_metadata`：改写 JSON（`metadata.json`，UTF-8/indent=2/ensure_ascii=False），利用 `ModelMetadata.to_dict()`
- `_load_metadata`：优先读 JSON；类型还原 `model_type`（枚举）、`training_date`（datetime）；**向后兼容**——旧 `metadata.pkl` 加载后转存 JSON 并删除
- 新增 `ModelMetadata.from_dict` classmethod（与 `to_dict` 对称）+ `_DATE_FORMAT` 类常量（消除格式串重复）
- `create_preset_models`：docstring + 3 个 description 强化（`[预置·仅供演示]`，标注"不可用于实盘"）

### `model/china_model.py`（+1/-1 行）
- L42 docstring `默认为LIGHTGBM` → `默认为RANDOM_FOREST`（与实际 `__init__` 默认值一致）

### `tests/test_model.py`（+184 行）
- 新增 `TestModelManagerMetadata`（7 测试）：JSON 持久化、类型还原、None 边界、旧 pkl 迁移、缺失字段补全、空目录、损坏 JSON

---

## P1 — 用户体验

### `requirements.txt`（+7 行）
- 拆分"机器学习（核心）"+ 注释式可选依赖（`# lightgbm`/`# xgboost`/`# torch`，标注对应 ModelType）——pip 不强制安装，避免 ImportError 困惑

### `gui_engine.py`（含 P1 部分）
- `init` 方法：预置模型创建后补充两条告警日志（纯中文无 emoji）

---

## P2 — 架构优化

### `dataset/loader.py`（+284 行）
- 新增 3 个模块级函数，承接 gui_engine 数据准备逻辑：
  - `prepare_training_data(start, end, lookback, forward)` → `(X, y, feature_names)`
  - `prepare_prediction_data(symbols, predict_date)` → `(X, valid_symbols, valid_names)`
  - `calculate_alpha158_features(symbols, start, end, infer_factor_type=None)` → `pl.DataFrame`
- `infer_factor_type` 参数注入（None 回退"其他"），避免反向耦合 gui_engine

### `dataset/__init__.py`（+11 行）
- 导出 3 个新函数

### `gui_engine.py`（-190 行净减，**1137→980，-14%**）
- `_prepare_training_data`/`_prepare_prediction_data`/`calculate_features` 改为薄包装委托
- 5 条 RuntimeError 关键文本逐字符保持（向后兼容）
- `_infer_factor_type`/`_calculate_accuracy`/`predict`/`train_model` 外部行为不变
- P2 Minor #2：删除 `_prepare_prediction_data` 冗余 ndim guard

### `tests/test_gui_engine.py`（**新建**，18 测试）
- `_infer_factor_type`（8）、`_calculate_accuracy`（6）、`_prepare_*` 错误契约（2）、`predict` 错误传播（2）
- characterization test，锁定重构安全网；用 `assertIn` 关键文本（重构调整措辞不破坏测试）

### `factors/`（5 文件各 +6 行）
- `base.py`/`dragon_tiger.py`/`northbound.py`/`sector_rotation.py`/`loader.py`：docstring 内追加跨库格式说明（pandas ↔ polars 转换指引）

---

## 独立问题 — data_manager API 漂移（生产 bug）

### `data/data_manager.py`（+588 行，**完全重写**）
**根因**：实现是过期版本，`gui_engine.py`（生产代码）和 `test_data_manager.py` 都期望新版 API，导致 gui_engine 数据管理功能运行时 `AttributeError` 崩溃。

- **PreloadConfig**：`enable_bar`→`enable_bar_data`、`symbols` 默认 None、`start_date` 3年、新增 `concurrent`/`batch_size`/`interval`
- **UpdateConfig**：`update_time` 默认 15:30、新增 `update_weekdays`/`lookback_days`/`bar_symbols`/`bar_interval`
- **DataPreloader**：`preload(config, callback)`→stats dict、`is_preloading()`、`get_preload_progress()`→三层 dict；`threading.Lock` 保护共享状态
- **DataUpdateScheduler**：`is_running()`方法、`trigger_update_now()`、`update_config()`、`get_stats()`、`_should_update_today()`、构造默认 config
- **create_data_manager**：返回 `(preloader, scheduler)` 元组 + 模块级 `CHINA_DATA_AVAILABLE`
- **C1 修复（Critical）**：`_preload_bars` 真实签名匹配 `get_bar_data(symbol, exchange, interval, start, end)` + 新增 `_resolve_exchange`（11 样例验证）——**消除 bar 数据静默加载失败的生产 bug**（Mock 测试曾掩盖）
- **I1/I2 修复**：trigger_update_now 增 bar 分支、PRELOAD_COMPLETE 事件携带 success 标志

---

## 测试成果

```
新增测试：25 个（TestModelManagerMetadata 7 + TestGuiEngine 18）
全量回归：226 tests OK，0 failure，0 error（装齐 scikit-learn 1.9.0 + lightgbm 4.6.0 后）
```

## 审查流程（subagent-driven）

每个改动经：implementer → spec 符合性审查 → code quality 审查 →（修复）→ 复审。全程 controller 独立验证，两次抓出 subagent 报告未体现的问题：
1. P2-2 注释放置在 docstring 外（SyntaxError，5 文件）
2. data_manager `_preload_bars` 真实签名不匹配（C1，生产 bug）

## 环境依赖变更

本次修复验证过程补装了两个可选依赖（注释式声明于 requirements.txt）：
- `scikit-learn` 1.9.0（核心，RANDOM_FOREST/LASSO/RIDGE 模型）
- `lightgbm` 4.6.0（可选，LIGHTGBM 模型）

未装 `xgboost`/`torch`（XGBOOST/LSTM 模型按需安装）。
