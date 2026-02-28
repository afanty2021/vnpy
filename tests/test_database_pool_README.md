# 数据库连接池测试使用指南

## 测试文件说明

### 1. `tests/test_database_pool.py` (完整版)

**用途**: 完整的单元测试套件，用于验证数据库连接池的所有功能

**依赖**:
- vnpy.trader.object (BarData)
- vnpy.trader.constant (Exchange, Interval)

**特点**:
- 使用 unittest 框架
- 包含 Mock 对象模拟数据库连接
- 完整的测试覆盖（并发、复用、超时、集成）

**运行方式**:
```bash
# 方式1: 直接运行
python tests/test_database_pool.py

# 方式2: 使用 unittest
python -m unittest tests.test_database_pool -v

# 方式3: 使用 pytest
pytest tests/test_database_pool.py -v --tb=short
```

### 2. `tests/test_database_pool_simple.py` (简化版)

**用途**: 快速验证测试逻辑，不依赖 vnpy 模块

**依赖**: 仅 Python 标准库

**特点**:
- 无需 vnpy 环境
- 快速运行
- 适合 CI/CD 流水线

**运行方式**:
```bash
python tests/test_database_pool_simple.py
```

## 测试用例列表

### TestConcurrentWrites - 并发写入测试
| 测试用例 | 描述 | 测试规模 |
|---------|------|---------|
| test_concurrent_writes_basic | 基础并发写入 | 10线程 x 10次 |
| test_concurrent_writes_high_load | 高并发写入 | 20线程 x 20次 |
| test_concurrent_writes_no_deadlock | 无死锁检测 | 10线程 x 10次 |

### TestConnectionReuse - 连接复用测试
| 测试用例 | 描述 | 测试规模 |
|---------|------|---------|
| test_connection_reuse_basic | 基础连接复用 | 100次查询 |
| test_connection_reuse_concurrent | 并发连接复用 | 5线程 x 50次 |
| test_pool_status | 连接池状态 | - |
| test_pool_status_after_operations | 操作后状态 | - |

### TestConnectionTimeout - 连接超时测试
| 测试用例 | 描述 | 测试规模 |
|---------|------|---------|
| test_connection_timeout_recovery | 超时恢复 | - |
| test_auto_reconnect | 自动重连 | - |
| test_concurrent_with_timeout_simulation | 并发超时模拟 | 10线程 x 10次 |

### TestPoolIntegration - 集成测试
| 测试用例 | 描述 | 测试规模 |
|---------|------|---------|
| test_mixed_operations | 读写混合操作 | 5线程 x 20次 |
| test_stress_test | 压力测试 | 20线程 x 50次 |
| test_connection_lifecycle | 连接生命周期 | - |

## 在 CI/CD 中使用

### GitHub Actions 示例

```yaml
name: Database Pool Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -e .

    - name: Run database pool tests
      run: |
        python tests/test_database_pool.py
```

## 调试测试失败

### 启用详细输出

```bash
# unittest
python -m unittest tests.test_database_pool -v

# pytest
pytest tests/test_database_pool.py -vv -s
```

### 运行特定测试

```bash
# unittest
python -m unittest tests.test_database_pool.TestConcurrentWrites.test_concurrent_writes_basic -v

# pytest
pytest tests/test_database_pool.py::TestConcurrentWrites::test_concurrent_writes_basic -v
```

## 性能基准

在参考硬件上的性能数据：

| 场景 | 操作数 | 预期耗时 | 预期吞吐 |
|-----|-------|---------|---------|
| 并发写入 | 100 | < 1s | > 100 ops/sec |
| 连接复用 | 100 | < 1s | > 100 ops/sec |
| 高负载 | 400 | < 5s | > 80 ops/sec |
| 压力测试 | 1000 | < 10s | > 100 ops/sec |

## 已知问题

### Windows 编码问题

在 Windows 系统上运行时可能遇到编码问题。解决方法：

```bash
# 设置环境变量
set PYTHONIOENCODING=utf-8
python tests/test_database_pool.py
```

### 模块导入错误

如果遇到 `ModuleNotFoundError: No module named 'vnpy'`：

1. 确保在项目根目录运行
2. 安装 vnpy: `pip install -e .`
3. 或使用简化版: `python tests/test_database_pool_simple.py`

## 扩展测试

### 添加新测试

```python
class TestNewFeature(unittest.TestCase):
    def setUp(self):
        self.db = MockMySQLDatabaseLayer(...)
        self.assertTrue(self.db.connect())

    def tearDown(self):
        self.db.close()

    def test_new_feature(self):
        """测试新功能"""
        # 实现测试逻辑
        pass
```

### 测试真实数据库

要使用真实 MySQL 数据库测试，修改 `tests/test_database_pool.py`:

```python
# 替换 MockMySQLDatabaseLayer 为真实的 MySQLDatabaseLayer
from vnpy_china_data.database import MySQLDatabaseLayer

def setUp(self):
    self.db = MySQLDatabaseLayer(
        host="localhost",
        port=3306,
        user="test_user",
        password="test_pass",
        database="test_db"
    )
    self.assertTrue(self.db.connect())
```

## 联系方式

如有问题，请查看：
- 项目文档: `CLAUDE.md`
- 修复方案: `docs/fixes/P0_P1_数据库连接池修复方案.md`
- 测试报告: `tests/test_database_pool_REPORT.md`
