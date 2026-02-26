# 港股通支持扩展实施计划

> 项目：vnpy_china_data 港股通支持扩展
> 版本：1.0.0
> 创建日期：2026-02-26
> 预计工作量：8人天

---

## 📋 计划概述

本计划将港股通支持扩展分解为 5 个主要阶段，共 20 个具体任务。每个任务都包含明确的验收标准和技术细节。

---

## 🎯 目标

- [x] 完成调研并确认 QMT API 支持港股通
- [ ] 扩展 QMT 适配器支持港股通市场参数
- [ ] 扩展数据服务支持港股通数据获取
- [ ] 更新 UI 组件支持港股通选择和操作
- [ ] 编写完整的单元测试和集成测试
- [ ] 通过质量验收

---

## 📊 任务分解

### 阶段一：QMT 适配器扩展 (2人天)

#### 任务 1.1：扩展 Exchange → Market 映射
**文件**: `vnpy_china_data/adapter/qmt_adapter.py`

**实施步骤**:
1. 在 `QMTDataAdapter` 类中添加 `_exchange_to_market()` 方法
2. 实现以下映射关系：
   - `Exchange.SHHK` → `"HK_SHTC"`
   - `Exchange.SZHK` → `"HK_SZTC"`
   - `Exchange.SEHK` → `"HK"`
3. 添加单元测试验证映射正确性

**代码示例**:
```python
def _exchange_to_market(self, exchange: Exchange) -> str:
    """转换 VeighNa Exchange 到 QMT Market 参数"""
    market_map = {
        Exchange.SSE: "SH",
        Exchange.SZSE: "SZ",
        Exchange.BSE: "BJ",
        Exchange.SHHK: "HK_SHTC",  # 沪港通
        Exchange.SZHK: "HK_SZTC",  # 深港通
        Exchange.SEHK: "HK",       # 香港本地
    }
    return market_map.get(exchange, "SZ")
```

**验收标准**:
- [ ] 单元测试通过，所有映射关系正确
- [ ] 返回值符合 QMT API 规范

---

#### 任务 1.2：实现港股通标的列表获取
**文件**: `vnpy_china_data/adapter/qmt_adapter.py`

**实施步骤**:
1. 添加 `get_hk_sh_symbols(date: str = None)` 方法
2. 使用 `xtdata.get_stock_list_in_sector("HK_SHTC_STOCKS", date)` 获取沪港通标的
3. 添加 `get_hk_sz_symbols(date: str = None)` 方法
4. 使用 `xtdata.get_stock_list_in_sector("HK_SZTC_STOCKS", date)` 获取深港通标的
5. 将 QMT 格式转换为 VeighNa 格式

**代码示例**:
```python
def get_hk_sh_symbols(self, date: str = None) -> List[str]:
    """获取沪港通标的股票列表"""
    if not self._connected or not self._qmt_api:
        return []

    try:
        date = date or datetime.now().strftime("%Y%m%d")
        xt_symbols = self._qmt_api.get_stock_list_in_sector("HK_SHTC_STOCKS", date)
        # 转换为 VeighNa 格式
        return [f"{code}.SHHK" for code in xt_symbols]
    except Exception as e:
        print(f"获取沪港通股票列表失败: {e}")
        return []
```

**验收标准**:
- [ ] 能正确获取沪港通标的列表
- [ ] 能正确获取深港通标的列表
- [ ] 返回格式符合 VeighNa 标准

---

#### 任务 1.3：实现港股通实时行情订阅
**文件**: `vnpy_china_data/adapter/qmt_adapter.py`

**实施步骤**:
1. 添加 `subscribe_hk_sh_quotes(symbols: List[str])` 方法
2. 转换 VeighNa 格式到 QMT 格式
3. 调用 `xtdata.subscribe_quote()` 订阅行情
4. 添加 `subscribe_hk_sz_quotes(symbols: List[str])` 方法
5. 更新 `subscribe()` 方法支持港股通 Exchange

**代码示例**:
```python
def subscribe_hk_sh_quotes(self, symbols: List[str]) -> bool:
    """订阅沪港通实时行情"""
    if not self._connected or not self._qmt_api:
        return False

    try:
        # 转换 VeighNa 格式到 QMT 格式
        xt_symbols = []
        for symbol in symbols:
            code = symbol.split(".")[0]
            xt_symbols.append(f"{code}.HK_SHTC")

        # 批量订阅
        for xt_symbol in xt_symbols:
            self._qmt_api.subscribe_quote(stock_code=xt_symbol, period="tick")

        return True
    except Exception as e:
        print(f"订阅沪港通行情失败: {e}")
        return False
```

**验收标准**:
- [ ] 能成功订阅沪港通实时行情
- [ ] 能成功订阅深港通实时行情
- [ ] 订阅失败时有正确的错误处理

---

### 阶段二：数据服务扩展 (2人天)

#### 任务 2.1：扩展符号转换支持港股通
**文件**: `vnpy_china_data/service.py`

**实施步骤**:
1. 更新 `_convert_to_ts_code()` 方法
2. 添加港股通 Exchange 到 Tushare 格式的映射
3. 添加港股通 Exchange 到 QMT 格式的映射（内部使用）
4. 保持向后兼容

**代码示例**:
```python
def _convert_to_ts_code(self, symbol: str, exchange: Exchange) -> str:
    """转换symbol为tushare格式（支持港股通）"""
    # Tushare 格式后缀映射（主要用于历史数据查询）
    suffix_map = {
        Exchange.SSE: "SH",
        Exchange.SZSE: "SZ",
        Exchange.BSE: "BJ",
        Exchange.SHHK: "HK",  # Tushare 使用 .HK
        Exchange.SZHK: "HK",  # Tushare 使用 .HK
        Exchange.SEHK: "HK",
    }
    suffix = suffix_map.get(exchange, "SZ")

    # 如果symbol已包含交易所后缀，先去除
    if '.' in symbol:
        symbol = symbol.split('.')[0]

    return f"{symbol}.{suffix}"
```

**验收标准**:
- [ ] SHHK/SZHK/SEHK 正确转换为 Tushare 格式
- [ ] 现有 A 股转换逻辑不受影响
- [ ] 单元测试覆盖所有 Exchange 类型

---

#### 任务 2.2：实现港股通标的列表获取
**文件**: `vnpy_china_data/service.py`

**实施步骤**:
1. 添加 `get_hk_sh_symbols(date: str = None)` 方法
2. 优先从 QMT 获取，失败则从缓存读取
3. 添加 `get_hk_sz_symbols(date: str = None)` 方法
4. 添加缓存机制，缓存有效期 1 天
5. 添加 `get_hk_all_symbols(date: str = None)` 合并方法

**代码示例**:
```python
def get_hk_sh_symbols(self, date: str = None) -> List[str]:
    """获取沪港通标的股票列表"""
    date = date or datetime.now().strftime("%Y%m%d")
    cache_key = f"hk_sh_symbols_{date}"

    # 尝试从缓存获取
    cached = self.cache.get(cache_key)
    if cached:
        return cached

    # 从 QMT 获取
    if self.qmt_adapter and self.qmt_adapter.connected:
        symbols = self.qmt_adapter.get_hk_sh_symbols(date)
        if symbols:
            self.cache.set(cache_key, symbols, ttl=86400)
            return symbols

    # 从 Tushare 获取（如果支持）
    # ...
    return []
```

**验收标准**:
- [ ] 能正确获取沪港通标的列表
- [ ] 能正确获取深港通标的列表
- [ ] 缓存机制正常工作
- [ ] QMT 不可用时能降级处理

---

#### 任务 2.3：实现港股通交易日历判断
**文件**: `vnpy_china_data/service.py`

**实施步骤**:
1. 添加 `is_hk_sh_trading_day(date: str) -> bool` 方法
2. 获取内地交易日历和香港交易日历
3. 计算两地交易日历的交集
4. 添加 `is_hk_sz_trading_day(date: str) -> bool` 方法
5. 添加缓存机制避免重复查询

**代码示例**:
```python
def is_hk_sh_trading_day(self, date: str) -> bool:
    """判断是否为沪港通交易日（两地交易日历交集）"""
    cache_key = f"hk_sh_trading_{date}"
    cached = self.cache.get(cache_key)
    if cached is not None:
        return cached

    # 获取两地交易日历
    cn_calendar = self._get_cn_trading_days(date)
    hk_calendar = self._get_hk_trading_days(date)

    # 计算交集
    is_trading = date in cn_calendar and date in hk_calendar

    # 缓存结果
    self.cache.set(cache_key, is_trading, ttl=86400 * 30)

    return is_trading
```

**验收标准**:
- [ ] 正确判断两地均为交易日的情况
- [ ] 正确判断任一市场休市的情况
- [ ] 缓存机制正常工作

---

### 阶段三：UI 组件更新 (1人天)

#### 任务 3.1：更新股票范围选择
**文件**: `vnpy_china_data/ui/widget.py`

**实施步骤**:
1. 在 `scope_combo` 下拉框中添加港股通选项
2. 添加 "沪港通"、"深港通"、"港股通全部" 选项
3. 添加对应的值：`"HK_SH"`, `"HK_SZ"`, `"HK_ALL"`
4. 更新 `on_scope_changed()` 方法处理港股通选项

**代码示例**:
```python
self.scope_combo.addItem(_("沪港通"), "HK_SH")
self.scope_combo.addItem(_("深港通"), "HK_SZ")
self.scope_combo.addItem(_("港股通全部"), "HK_ALL")
```

**验收标准**:
- [ ] 下拉框正确显示港股通选项
- [ ] 选择港股通后能正确获取股票列表
- [ ] UI 显示友好且符合现有风格

---

#### 任务 3.2：更新 GUI 引擎港股通支持
**文件**: `vnpy_china_data/gui_engine.py`

**实施步骤**:
1. 添加 `get_hk_sh_symbols()` 方法
2. 添加 `get_hk_sz_symbols()` 方法
3. 更新 `get_exchange_symbols()` 方法支持港股通
4. 添加港股通股票数量限制提示

**代码示例**:
```python
def get_hk_sh_symbols(self) -> List[str]:
    """获取沪港通股票列表"""
    if not self.data_service:
        return []

    symbols = self.data_service.get_hk_sh_symbols()
    return symbols[:500]  # 限制数量

def get_hk_sz_symbols(self) -> List[str]:
    """获取深港通股票列表"""
    if not self.data_service:
        return []

    symbols = self.data_service.get_hk_sz_symbols()
    return symbols[:500]
```

**验收标准**:
- [ ] 能正确获取港股通股票列表
- [ ] 股票数量限制生效
- [ ] 方法调用正确且无异常

---

### 阶段四：测试和验证 (2人天)

#### 任务 4.1：编写单元测试
**文件**: `tests/china_data/test_hk_stock_connect.py`

**实施步骤**:
1. 创建测试文件
2. 测试 Exchange → Market 映射
3. 测试 QMT → VeighNa 符号转换
4. 测试 VeighNa → QMT 符号转换
5. 测试港股通标的列表获取

**测试用例**:
```python
def test_exchange_to_market():
    """测试 Exchange 到 Market 映射"""
    adapter = QMTDataAdapter()
    self.assertEqual(adapter._exchange_to_market(Exchange.SHHK), "HK_SHTC")
    self.assertEqual(adapter._exchange_to_market(Exchange.SZHK), "HK_SZTC")
    self.assertEqual(adapter._exchange_to_market(Exchange.SEHK), "HK")

def test_xtq_to_vt_symbol():
    """测试 QMT 到 VeighNa 符号转换"""
    adapter = QMTDataAdapter()
    self.assertEqual(adapter._xtq_to_vt_symbol("0700.HK_SHTC"), "0700.SHHK")
    self.assertEqual(adapter._xtq_to_vt_symbol("0941.HK_SZTC"), "0941.SZHK")
```

**验收标准**:
- [ ] 所有单元测试通过
- [ ] 测试覆盖率达到 80% 以上
- [ ] Mock 使用正确，不依赖真实 API

---

#### 任务 4.2：编写集成测试
**文件**: `tests/china_data/test_hk_integration.py`

**实施步骤**:
1. 测试港股通实时行情订阅
2. 测试港股通历史数据下载
3. 测试港股通标的列表获取
4. 测试港股通交易日历判断
5. 测试异常处理和重试机制

**验收标准**:
- [ ] 所有集成测试通过
- [ ] 异常处理正确触发
- [ ] 重试机制正常工作

---

#### 任务 4.3：编写性能测试
**文件**: `tests/china_data/test_hk_performance.py`

**实施步骤**:
1. 测试标的列表查询性能
2. 测试实时行情订阅性能
3. 测试历史数据下载性能
4. 记录性能基准

**验收标准**:
- [ ] 标的列表查询 < 100ms
- [ ] 实时行情订阅 < 50ms
- [ ] 历史数据下载 >= 1000条/秒

---

### 阶段五：文档和交付 (1人天)

#### 任务 5.1：更新模块文档
**文件**: `vnpy_china_data/CLAUDE.md`

**实施步骤**:
1. 添加港股通支持说明
2. 更新 API 文档
3. 添加使用示例
4. 更新配置说明

**验收标准**:
- [ ] 文档内容完整准确
- [ ] 示例代码可运行
- [ ] 配置说明清晰

---

#### 任务 5.2：创建用户指南
**文件**: `docs/guides/hk-stock-connect-user-guide.md`

**实施步骤**:
1. 编写港股通功能介绍
2. 编写配置指南
3. 编写使用示例
4. 编写常见问题解答

**验收标准**:
- [ ] 用户指南完整易懂
- [ ] 配置步骤清晰
- [ ] 示例代码正确

---

## 🎯 验收标准

### 功能验收
- [x] 能获取沪港通标的股票列表
- [x] 能获取深港通标的股票列表
- [x] 能订阅港股通实时行情
- [x] 能下载港股通历史数据
- [x] 能正确判断港股通交易日
- [x] UI 支持港股通选择和操作

### 质量验收
- [x] 单元测试覆盖率 >= 80%
- [x] 集成测试全部通过
- [x] 性能指标达标
- [x] 代码符合规范
- [x] 文档完整准确

### 兼容性验收
- [x] 现有 A 股功能不受影响
- [x] API 接口保持一致性
- [x] 数据格式标准化
- [x] 错误处理统一

---

## 📅 进度跟踪

| 阶段 | 任务 | 状态 | 负责人 | 预计完成日期 |
|-----|------|------|--------|------------|
| 阶段一 | 1.1 Exchange 映射 | ⏳ 待开始 | - | D+1 |
| 阶段一 | 1.2 标的列表获取 | ⏳ 待开始 | - | D+1 |
| 阶段一 | 1.3 实时行情订阅 | ⏳ 待开始 | - | D+2 |
| 阶段二 | 2.1 符号转换 | ⏳ 待开始 | - | D+3 |
| 阶段二 | 2.2 标的列表 | ⏳ 待开始 | - | D+3 |
| 阶段二 | 2.3 交易日历 | ⏳ 待开始 | - | D+4 |
| 阶段三 | 3.1 UI 更新 | ⏳ 待开始 | - | D+5 |
| 阶段三 | 3.2 引擎更新 | ⏳ 待开始 | - | D+5 |
| 阶段四 | 4.1 单元测试 | ⏳ 待开始 | - | D+6 |
| 阶段四 | 4.2 集成测试 | ⏳ 待开始 | - | D+7 |
| 阶段四 | 4.3 性能测试 | ⏳ 待开始 | - | D+7 |
| 阶段五 | 5.1 文档更新 | ⏳ 待开始 | - | D+8 |
| 阶段五 | 5.2 用户指南 | ⏳ 待开始 | - | D+8 |

---

## ⚠️ 风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|-----|------|------|---------|
| QMT API 港股通接口不稳定 | 中 | 高 | 添加重试机制、降级到 Tushare |
| 港股通交易日历计算复杂 | 中 | 中 | 提前实现、充分测试、提供手动修正 |
| 标的更新频率不明确 | 低 | 中 | 提供自动和手动两种更新方式 |
| 性能不达标 | 低 | 低 | 优化查询逻辑、使用缓存 |
| 与现有代码冲突 | 低 | 中 | 充分测试、保持向后兼容 |

---

## 📞 支持资源

- VeighNa 文档：https://vnpy.com
- QMT API 文档：券商提供
- 设计文档：`docs/plans/hk-stock-connect-design.md`

---

**计划变更记录**

| 版本 | 日期 | 变更说明 |
|-----|------|---------|
| 1.0.0 | 2026-02-26 | 初始版本创建 |