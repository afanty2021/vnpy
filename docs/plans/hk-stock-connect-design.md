# 港股通支持扩展设计方案

> 版本：1.0.0
> 创建日期：2026-02-26
> 状态：设计评审中

---

## 一、项目概述

### 1.1 背景与目标

**背景**：
- VeighNa 框架已定义港股通交易所枚举（SHHK/SZHK/SEHK）
- QMT (迅投量化交易平台) 作为券商提供的接口，已支持港股通市场数据
- 当前 `vnpy_china_data` 模块主要针对 A 股市场，港股通支持尚未实现

**目标**：
- 扩展 `vnpy_china_data` 模块，完整支持港股通市场数据获取
- 实现港股通实时行情订阅、历史数据下载、标的股票管理等功能
- 与现有 A 股功能保持一致的 API 设计和用户体验

---

## 二、需求分析

### 2.1 功能性需求

| 需求编号 | 需求描述 | 优先级 | 依赖 |
|---------|---------|--------|------|
| HK-001 | 支持获取沪港通标的股票列表 | P0 | QMT_API |
| HK-002 | 支持获取深港通标的股票列表 | P0 | QMT_API |
| HK-003 | 支持沪港通实时行情订阅 | P0 | QMT_API |
| HK-004 | 支持深港通实时行情订阅 | P0 | QMT_API |
| HK-005 | 支持港股通历史K线数据下载 | P0 | QMT_API |
| HK-006 | 支持港股通交易日历（两地交集） | P1 | QMT_API |
| HK-007 | 支持香港本地市场 (SEHK) 数据 | P2 | QMT_API |
| HK-008 | 港股通标的定期更新机制 | P1 | 调度任务 |

### 2.2 非功能性需求

| 需求类型 | 具体要求 | 验证标准 |
|---------|---------|---------|
| **性能** | 港股通数据获取响应时间 < 500ms | 性能测试 |
| **可靠性** | API 调用失败自动重试 3 次 | 集成测试 |
| **兼容性** | 与现有 A 股 API 保持一致 | 单元测试 |
| **可扩展性** | 易于添加其他港股相关市场 | 代码审查 |
| **可维护性** | 清晰的代码注释和文档 | 代码审查 |

---

## 三、架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        vnpy_china_data                       │
│                            Service                           │
│                      (ChinaDataService)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
       ▼               ▼               ▼
┌────────────┐  ┌────────────┐  ┌────────────┐
│ Tushare    │  │   QMT      │  │   RPC QMT  │
│ Adapter    │  │ Adapter    │  │ Adapter    │
│            │  │            │  │            │
│ • A股数据   │  │ • A股数据   │  │ • A股数据   │
│ • 港股数据   │  │ • 港股数据   │  │ • 港股数据   │
└────────────┘  └────────────┘  └────────────┘
                      │
                      ▼
              ┌──────────────┐
              │ QMT API      │
              │ (xtquant)    │
              └──────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
   Market_SH   Market_SZ   Market_HK
   (沪市)      (深市)      (港股通)
```

### 3.2 核心组件设计

#### 3.2.1 Exchange 映射

| VeighNa Exchange | QMT Market | 说明 |
|------------------|------------|------|
| Exchange.SSE | `SH` | 上海市场 |
| Exchange.SZSE | `SZ` | 深圳市场 |
| Exchange.BSE | `BJ` | 北京市场 |
| Exchange.SHHK | `HK_SHTC` | 沪港通 |
| Exchange.SZHK | `HK_SZTC` | 深港通 |
| Exchange.SEHK | `HK` | 香港本地市场 |

#### 3.2.2 股票代码格式

| 格式类型 | 示例 | 说明 |
|---------|------|------|
| **VeighNa 标准格式** | `0700.SHHK` | {symbol}.{exchange.value} |
| **QMT 格式** | `0700.HK_SHTC` | {code}.{market} |
| **Tushare 格式** | `0700.HK` | {code}.{HK} |

#### 3.2.3 数据流设计

```
用户请求
    │
    ▼
ChinaDataService
    │
    ├─→ _convert_to_ts_code() (转换 VeighNa → Tushare/QMT)
    │   ├─ A股: 000001 → 000001.SZ
    │   ├─ 沪港通: 0700.SHHK → 0700.HK_SHTC
    │   └─ 深港通: 0941.SZHK → 0941.HK_SZTC
    │
    ├─→ _fetch_bars_from_api()
    │   ├─ 优先使用 QMT (港股通)
    │   └─ Fallback 到 Tushare
    │
    └─→ 返回 BarData[]
```

---

## 四、详细设计

### 4.1 模块扩展方案

#### 4.1.1 QMTDataAdapter 扩展

**文件：`vnpy_china_data/adapter/qmt_adapter.py`**

新增方法：

```python
def get_hk_sh_symbols(self, date: str = None) -> List[str]:
    """获取沪港通标的股票列表"""

def get_hk_sz_symbols(self, date: str = None) -> List[str]:
    """获取深港通标的股票列表"""

def subscribe_hk_sh_quotes(self, symbols: List[str]) -> bool:
    """订阅沪港通实时行情"""

def subscribe_hk_sz_quotes(self, symbols: List[str]) -> bool:
    """订阅深港通实时行情"""

def _exchange_to_market(self, exchange: Exchange) -> str:
    """转换 VeighNa Exchange 到 QMT Market 参数"""
```

#### 4.1.2 ChinaDataService 扩展

**文件：`vnpy_china_data/service.py`**

修改现有方法：

```python
def _convert_to_ts_code(self, symbol: str, exchange: Exchange) -> str:
    """扩展支持港股通 Exchange 映射"""
    suffix_map = {
        Exchange.SSE: "SH",
        Exchange.SZSE: "SZ",
        Exchange.BSE: "BJ",
        Exchange.SHHK: "HK",  # Tushare 格式
        Exchange.SZHK: "HK",
        Exchange.SEHK: "HK",
    }
    return f"{symbol}.{suffix}"
```

新增方法：

```python
def get_hk_sh_symbols(self, date: str = None) -> List[str]:
    """获取沪港通标的股票列表"""

def get_hk_sz_symbols(self, date: str = None) -> List[str]:
    """获取深港通标的股票列表"""

def is_hk_sh_trading_day(self, date: str) -> bool:
    """判断是否为沪港通交易日（两地交易日历交集）"""

def is_hk_sz_trading_day(self, date: str) -> bool:
    """判断是否为深港通交易日（两地交易日历交集）"""
```

#### 4.1.3 GUI 组件扩展

**文件：`vnpy_china_data/ui/widget.py`**

修改：

```python
# 在股票范围选择下拉框中添加港股通选项
self.scope_combo.addItem(_("沪港通"), "HK_SH")
self.scope_combo.addItem(_("深港通"), "HK_SZ")
self.scope_combo.addItem(_("港股通全部"), "HK_ALL")
```

```python
def get_hk_sh_symbols(self) -> List[str]:
    """获取沪港通股票列表"""

def get_hk_sz_symbols(self) -> List[str]:
    """获取深港通股票列表"""
```

---

### 4.2 数据库设计

#### 4.2.1 港股通标的表

```sql
CREATE TABLE hk_stock_connect_targets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    symbol VARCHAR(20) NOT NULL COMMENT '股票代码',
    exchange VARCHAR(10) NOT NULL COMMENT '交易所 (SHHK/SZHK)',
    name VARCHAR(100) COMMENT '股票名称',
    company_name VARCHAR(200) COMMENT '公司名称',
    list_date DATE COMMENT '纳入日期',
    weight DECIMAL(10,4) COMMENT '权重',
    is_active TINYINT DEFAULT 1 COMMENT '是否有效',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol_exchange (symbol, exchange),
    INDEX idx_exchange_active (exchange, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='港股通标的股票表';
```

#### 4.2.2 港股通交易日历表

```sql
CREATE TABLE hk_trading_calendar (
    id INT PRIMARY KEY AUTO_INCREMENT,
    trade_date DATE NOT NULL COMMENT '交易日期',
    exchange VARCHAR(10) NOT NULL COMMENT '交易所 (SHHK/SZHK)',
    cn_trading TINYINT COMMENT '内地是否交易日',
    hk_trading TINYINT COMMENT '香港是否交易日',
    is_hk_connect TINYINT COMMENT '是否为港股通交易日',
    UNIQUE KEY uk_date_exchange (trade_date, exchange),
    INDEX idx_trade_date (trade_date),
    INDEX idx_exchange (exchange)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='港股通交易日历表';
```

---

### 4.3 API 接口设计

#### 4.3.1 新增 API 端点

```python
# 获取沪港通标的列表
GET /api/hk_stock_connect/sh_targets?date=20240101

# 获取深港通标的列表
GET /api/hk_stock_connect/sz_targets?date=20240101

# 查询港股通交易日历
GET /api/hk_stock_connect/calendar?start=20240101&end=20241231&exchange=SHHK

# 订阅港股通行情
POST /api/hk_stock_connect/subscribe
{
    "symbols": ["0700.SHHK", "0941.SZHK"],
    "exchange": "SHHK"
}
```

---

### 4.4 异常处理

| 异常类型 | 处理策略 | 用户提示 |
|---------|---------|---------|
| QMT 未连接 | 返回空列表 + 日志 | "QMT未连接，请先连接券商接口" |
| 港股通额度不足 | 记录日志 + 等待 | "港股通额度不足，请稍后再试" |
| 标的更新失败 | 记录日志 + 保持旧数据 | "港股通标的更新失败，使用缓存数据" |
| 交易日历不同步 | 记录日志 + 计算 | "交易日历同步异常，已自动计算" |

---

## 五、测试设计

### 5.1 单元测试

**文件：`tests/china_data/test_hk_stock_connect.py`**

| 测试用例 | 测试目标 | 预期结果 |
|---------|---------|---------|
| test_exchange_to_market() | Exchange → Market 映射 | SHHK → HK_SHTC |
| test_market_to_exchange() | Market → Exchange 映射 | HK_SHTC → SHHK |
| test_xtq_to_vt_symbol() | QMT → VeighNa 转换 | 0700.HK_SHTC → 0700.SHHK |
| test_vt_to_xtq_symbol() | VeighNa → QMT 转换 | 0700.SHHK → 0700.HK_SHTC |
| test_get_hk_sh_symbols() | 沪港通标的列表 | 返回非空列表 |
| test_get_hk_sz_symbols() | 深港通标的列表 | 返回非空列表 |
| test_is_hk_sh_trading_day() | 交易日历交集 | 正确判断 |

### 5.2 集成测试

| 测试场景 | 测试步骤 | 验证点 |
|---------|---------|--------|
| 港股通实时行情订阅 | 1. 连接 QMT<br>2. 订阅沪港通股票<br>3. 验证 Tick 数据 | 收到实时 Tick 数据 |
| 港股通历史数据下载 | 1. 请求历史K线<br>2. 验证数据完整性<br>3. 验证数据准确性 | 数据完整、准确 |
| 港股通标的更新 | 1. 调用更新接口<br>2. 验证数据库更新<br>3. 验证缓存更新 | 数据同步更新 |

### 5.3 性能测试

| 测试指标 | 目标值 | 测试方法 |
|---------|--------|---------|
| 标的列表查询 | < 100ms | 压力测试 |
| 实时行情订阅 | < 50ms | 单次调用测试 |
| 历史数据下载 | 1000条/秒 | 批量下载测试 |

---

## 六、实施计划

### 6.1 阶段划分

| 阶段 | 任务 | 预计工作量 | 交付物 |
|-----|------|-----------|--------|
| **阶段一** | 扩展 QMT 适配器 | 2人天 | QMTDataAdapter 港股通支持 |
| **阶段二** | 扩展数据服务 | 2人天 | ChinaDataService 港股通方法 |
| **阶段三** | UI 组件更新 | 1人天 | 港股通选项和功能 |
| **阶段四** | 数据库和存储 | 1人天 | 表结构和存储逻辑 |
| **阶段五** | 测试和验证 | 2人天 | 单元测试、集成测试 |
| **总计** | | **8人天** | |

### 6.2 里程碑

| 里程碑 | 完成标准 | 预计日期 |
|-------|---------|---------|
| M1: QMT 适配器扩展 | 单元测试通过 | D+2 |
| M2: 数据服务扩展 | 集成测试通过 | D+4 |
| M3: UI 功能完成 | 功能验证通过 | D+5 |
| M4: 全部测试通过 | 质量验收通过 | D+7 |

---

## 七、风险评估与应对

| 风险 | 可能性 | 影响 | 应对措施 |
|-----|--------|------|---------|
| QMT API 港股通接口不稳定 | 中 | 高 | 添加重试机制和降级方案 |
| 港股通交易日历计算复杂 | 中 | 中 | 提前实现并充分测试 |
| 标的更新频率不明确 | 低 | 中 | 提供手动和自动两种更新方式 |
| 性能不满足要求 | 低 | 低 | 优化查询逻辑和缓存策略 |

---

## 八、附录

### 8.1 参考资料

- VeighNa 文档：https://vnpy.com
- QMT API 文档：券商提供的技术文档
- 港股通规则：上交所/深交所官方规则

### 8.2 术语表

| 术语 | 定义 |
|-----|------|
| SHHK | Shanghai-HK Stock Connect，沪港通 |
| SZHK | Shenzhen-HK Stock Connect，深港通 |
| SEHK | Stock Exchange of Hong Kong，香港联合交易所 |
| QMT | 迅投量化交易平台 |
| xtquant | QMT 的量化交易 SDK |

---

**文档变更记录**

| 版本 | 日期 | 作者 | 变更说明 |
|-----|------|------|---------|
| 1.0.0 | 2026-02-26 | AI Assistant | 初始版本创建 |