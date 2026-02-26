# A股增强模块 Mock 数据使用分析报告

> 报告日期：2026-02-26
> 分析范围：vnpy_china_* 系列模块生产代码
> 排除范围：测试文件、示例代码、文档

---

## 概述

本报告分析了A股增强各模块中使用的mock（模拟）数据，区分**测试用途的Mock**和**生产环境中的Fallback Mock**，重点标记需要替换为真实数据的位置。

---

## 1. vnpy_china_ml - A股机器学习模块

### 1.1 Mock 数据位置

| 文件 | 行号 | 方法/函数 | 用途 | 状态 |
|------|------|-----------|------|------|
| `gui_engine.py` | 273 | `_prepare_training_data()` | 训练数据准备失败时的fallback | ⚠️ **需改进** |
| `gui_engine.py` | 304 | `_prepare_training_data()` | 数据加载异常时的fallback | ⚠️ **需改进** |
| `gui_engine.py` | 306-332 | `_generate_mock_data()` | 生成随机训练数据（备用方案） | ⚠️ **需改进** |
| `gui_engine.py` | 475 | `_prepare_prediction_data()` | 预测数据准备失败时的fallback | ⚠️ **需改进** |
| `gui_engine.py` | 488 | `_prepare_prediction_data()` | 加载真实数据失败时的fallback | ⚠️ **需改进** |
| `gui_engine.py` | 497 | `_prepare_prediction_data()` | 数据为空时的fallback | ⚠️ **需改进** |
| `gui_engine.py` | 511 | `_prepare_prediction_data()` | 特征计算失败时的fallback | ⚠️ **需改进** |
| `gui_engine.py` | 513-530 | `_generate_mock_prediction_data()` | 生成随机预测数据（备用方案） | ⚠️ **需改进** |

### 1.2 详细分析

#### 训练数据 Mock (`_generate_mock_data`)

```python
# vnpy_china_ml/gui_engine.py:306
def _generate_mock_data(self, n_samples: int, n_features: int) -> tuple:
    X = np.random.randn(n_samples, n_features)
    y = np.random.randn(n_samples) * 0.02  # 2%的波动率
    feature_names = ["Return_5d", "Return_10d", ...]
    return X, y, feature_names
```

**触发条件：**
1. 数据集模块不可用（ImportError）
2. 数据加载失败（Exception）

**影响：** 用户在没有配置数据源时仍可"训练"模型，但模型完全无效。

---

#### 预测数据 Mock (`_generate_mock_prediction_data`)

```python
# vnpy_china_ml/gui_engine.py:513
def _generate_mock_prediction_data(self, symbols, symbol_names) -> tuple:
    # 生成随机数据
    X = np.random.randn(n_samples, n_features)
    return X, valid_symbols, valid_names
```

**触发条件：**
1. 未能加载真实数据
2. 数据为空
3. 特征计算失败

**影响：** 用户看到"预测成功"，但结果完全随机，具有误导性。

### 1.3 改进建议

1. **明确错误提示**：当真实数据不可用时，应明确提示用户配置数据源，而非静默使用mock
2. **添加配置选项**：允许用户选择是否启用fallback模式
3. **标记Mock数据**：在使用mock数据时，UI应明显标识（如"演示模式"标签）

---

## 2. vnpy_china_capital - A股资金管理模块

### 2.1 Mock 数据位置

| 文件 | 行号 | 方法/函数 | 用途 | 状态 |
|------|------|-----------|------|------|
| `ui/widget.py` | 285 | `refresh_cash_flow_data()` | GUI引擎不可用时的fallback | ⚠️ **需改进** |
| `ui/widget.py` | 333-339 | `_get_mock_flows()` | 生成演示资金流水数据 | ⚠️ **需改进** |

### 2.2 详细分析

#### 资金流水 Mock (`_get_mock_flows`)

```python
# vnpy_china_capital/ui/widget.py:333
def _get_mock_flows(self) -> List[dict]:
    return [
        {"trade_time": "09:30:00", "flow_type": "转入", "amount": 100000.00, ...},
        {"trade_time": "10:15:00", "flow_type": "买入", "amount": -15000.00, ...},
        {"trade_time": "14:20:00", "flow_type": "卖出", "amount": 20000.00, ...},
    ]
```

**触发条件：**
- `self.gui_engine` 为 `None`

**影响：** 在未连接GUI引擎时显示固定的演示数据。

### 2.3 改进建议

1. **添加空状态处理**：当没有数据时，显示"暂无数据"而非假数据
2. **引导用户配置**：提示用户导入资金流水或连接交易账户

---

## 3. vnpy_china_data - A股数据服务模块

### 3.1 Mock 数据位置

| 文件 | 行号 | 方法/函数 | 用途 | 状态 |
|------|------|-----------|------|------|
| `gui_engine.py` | 67 | `query_dragon_tiger_data()` | 数据服务未初始化时的fallback | ⚠️ **可接受** |
| `gui_engine.py` | 78 | `query_dragon_tiger_data()` | 查询无结果时的fallback | ⚠️ **可接受** |
| `gui_engine.py` | 84 | `query_dragon_tiger_data()` | 查询失败时的fallback | ⚠️ **可接受** |
| `gui_engine.py` | 134-160 | `_get_mock_dragon_tiger_data()` | 生成演示龙虎榜数据 | ⚠️ **可接受** |
| `gui_engine.py` | 98 | `query_northbound_flow()` | 数据服务未初始化时的fallback | ⚠️ **可接受** |
| `gui_engine.py` | 110 | `query_northbound_flow()` | 查询无结果时的fallback | ⚠️ **可接受** |
| `gui_engine.py` | 114 | `query_northbound_flow()` | 查询失败时的fallback | ⚠️ **可接受** |
| `gui_engine.py` | 162-180 | `_get_mock_northbound_flow()` | 生成演示北向资金数据 | ⚠️ **可接受** |

### 3.2 详细分析

#### 龙虎榜 Mock (`_get_mock_dragon_tiger_data`)

```python
# vnpy_china_data/gui_engine.py:134
def _get_mock_dragon_tigger_data(self, trade_date: date) -> List[Any]:
    return [
        DragonTigerRecord("000001", "平安银行", trade_date, 15.50, 5.23, ...),
        DragonTigerRecord("600519", "贵州茅台", trade_date, 1850.00, 2.15, ...),
        DragonTigerRecord("300750", "宁德时代", trade_date, 220.50, -3.12, ...),
    ]
```

**触发条件：**
1. 数据服务未初始化
2. Tushare token未配置
3. 网络问题导致查询失败
4. 非交易日（无真实数据）

**特点：** 已有明确的警告日志，提示用户配置Tushare token。

#### 北向资金 Mock (`_get_mock_northbound_flow`)

```python
# vnpy_china_data/gui_engine.py:162
def _get_mock_northbound_flow(self, trade_date: date) -> Any:
    return NorthboundFlowData(
        trade_date=trade_date,
        sh_net_inflow=10.0,  # 10亿
        sz_net_inflow=5.0,   # 5亿
        ...
    )
```

**触发条件：** 同上

### 3.3 评估

**状态：可接受**

理由：
1. 已有明确的警告日志
2. 主要用于数据展示模块的演示功能
3. 不影响交易决策（仅提供市场数据查看）

---

## 4. vnpy_china_analysis - A股分析模块

**状态：✅ 无生产代码Mock数据**

该模块未发现生产环境中的mock数据使用。

---

## 5. vnpy_china_strategy - A股策略模块

**状态：✅ 无生产代码Mock数据**

该模块未发现生产环境中的mock数据使用。

---

## 统计汇总

### 按模块统计

| 模块 | Mock位置数量 | 严重程度 | 主要问题 |
|------|-------------|---------|---------|
| **vnpy_china_ml** | 8 | 🔴 **高** | 训练/预测使用随机数据，误导性强 |
| **vnpy_china_capital** | 2 | 🟡 **中** | 资金流水演示数据 |
| **vnpy_china_data** | 8 | 🟢 **低** | 已有警告日志的演示数据 |
| **vnpy_china_analysis** | 0 | ✅ | 无问题 |
| **vnpy_china_strategy** | 0 | ✅ | 无问题 |

### 按类型统计

| 类型 | 数量 | 说明 |
|------|------|------|
| **训练数据Mock** | 2 | 随机生成的特征和标签 |
| **预测数据Mock** | 4 | 随机生成的预测输入 |
| **展示数据Mock** | 10 | 用于UI演示的固定数据 |

---

## 改进建议优先级

### P0 - 高优先级（需立即改进）

**vnpy_china_ml 模块的训练/预测Mock**

```python
# 当前代码（问题）
def _prepare_training_data(self, ...):
    try:
        from ..dataset import create_alpha_dataset
        # ... 真实数据加载
    except Exception as e:
        self._log(f"数据加载失败: {e}，使用模拟数据")
        return self._generate_mock_data(1000, 20)  # ❌ 静默使用随机数据
```

**建议改进：**

```python
# 改进方案
def _prepare_training_data(self, ...):
    try:
        from ..dataset import create_alpha_dataset
        # ... 真实数据加载
    except Exception as e:
        self._log(f"数据加载失败: {e}")
        self._log("错误：无法加载训练数据，请确保：")
        self._log("  1. vnpy数据库中有所需历史数据")
        self._log("  2. 数据库连接配置正确")
        raise DataNotAvailableError("训练数据不可用")  # ✅ 明确抛出错误
```

### P1 - 中优先级（建议改进）

**vnpy_china_capital 模块的资金流水Mock**

```python
# 建议改为显示空状态提示
def refresh_cash_flow_data(self) -> None:
    flows = []
    if self.gui_engine:
        flows = self.gui_engine.get_capital_flows()
    else:
        # 显示空状态而非mock数据
        self._show_empty_state("请连接GUI引擎或导入资金流水")
        return
```

### P2 - 低优先级（可选改进）

**vnpy_china_data 模块的演示Mock**

当前实现已经较为合理（有警告日志），可选改进：
- 添加"演示模式"标签
- 支持禁用演示数据的配置选项

---

## 结论

1. **vnpy_china_ml** 是Mock数据使用最多的模块，且影响最严重，应优先改进
2. **vnpy_china_data** 的Mock数据使用较为规范，有明确警告，可接受度较高
3. **vnpy_china_capital** 应移除Mock数据，改用空状态提示
4. 建议统一Mock数据的处理策略，制定明确的开发规范

---

## 附录：文件清单

### 需要修改的文件

1. `vnpy_china_ml/gui_engine.py` - 移除/改进训练和预测的Mock fallback
2. `vnpy_china_capital/ui/widget.py` - 移除资金流水的Mock数据

### 无需修改的文件

1. `vnpy_china_data/gui_engine.py` - 已有完善的警告机制
2. 测试文件中的Mock是正常的，不属于本报告范围

---

*报告生成者：Claude AI*
*分析方法：静态代码分析 + Grep搜索*
