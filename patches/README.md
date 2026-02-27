# Patches - 外部依赖包修复补丁

> 用于跟踪项目依赖的外部包修复，确保环境重建时能正确应用修复。

## 补丁列表

### 1. vnpy_qmt 历史数据下载修复

**包名**: `vnpy_qmt`
**版本**: 最新
**修复日期**: 2026-02-27
**修复文件**: `md.py`

#### 问题描述

1. **RPC 参数缺失**: `query_history` 调用缺少 `gateway_name` 参数
2. **Interval 枚举错误**: 引用了不存在的 `MINUTE_5`, `MINUTE_15`, `MINUTE_30`
3. **缺少下载步骤**: 未调用 `download_history_data2` 先下载数据
4. **API 选择不当**: 使用 `get_market_data_ex` 而非更稳定的 `get_local_data`
5. **DataFrame 处理问题**: 数据类型转换不正确

#### 修复内容

- 添加 `download_history_data2` 下载步骤
- 使用 `get_local_data` 读取数据
- 修复 `period_map` 只使用有效的 Interval 枚举
- 正确处理 pandas DataFrame 数据格式
- 添加字符串映射支持更多周期（'5m', '15m', '30m'）

#### 应用方式

```bash
# 方式1：自动部署脚本（推荐）
python patches/deploy_vnpy_qmt_fix.py

# 方式2：手动复制
# 将 patches/vnpy_qmt/md.py 复制到：
# D:/scoop/apps/miniconda/current/envs/Quant-3.11/Lib/site-packages/vnpy_qmt/md.py
```

#### 验证修复

```bash
cd examples/client_server
python test_qmt_simple.py
```

#### 相关文档

- [miniQMT历史数据下载问题调研报告](../reports/miniQMT历史数据下载问题调研报告.md)

---

## 使用建议

1. **环境初始化**: 在新环境部署后，首先运行所有补丁脚本
2. **版本升级**: 升级外部包后，检查补丁是否仍需应用
3. **补丁维护**: 记录每次修复的原因、内容和测试方法

---

**维护者**: AI Assistant
**最后更新**: 2026-02-27
