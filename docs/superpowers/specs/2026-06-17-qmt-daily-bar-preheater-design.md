# QMT 日线数据预热（Preheater）设计

> 日期：2026-06-17
> 状态：待评审（v2，已整合复审反馈）
> 关联：[[qmt-patch-status]] 补丁3（md.py 行情增强字段，量比依赖近5日日线）

## 1. 背景与动机

`md.py:_get_avg_daily_vol` 计算量比需要「过去 5 日平均日成交量」作为分母，数据来源是
`xtdata.get_local_data(period='1d')`，读取的是 `userdata_mini/datadir/{SH|SZ}/86400/*.DAT`
本地日线文件。

这些 `.DAT` 文件**只在该标的被 `download_history_data2` 下载过时才存在**。当前环境仅手动下载过
8 只标的的日线，导致：

- 已下载标的：量比正常
- 未下载标的：`get_local_data` 返回空 → `_get_avg_daily_vol` 返回 0 → 量比显示 0

实盘时客户端可能随时订阅任意 A 股/ETF，逐个手动下载不可行。需要一个**启动时自动预热**
机制，把全市场（A股+ETF）日线下载到本地，确保量比对任意标的可算。

## 2. 目标与非目标

### 目标
- 服务端启动时，后台异步下载沪深 A 股 + 创业板 + 科创板 + 沪深 ETF 的日线数据
- 不阻塞 RPC 服务启动（启动即可接受客户端连接）
- 增量下载（`download_history_data2` 原生支持，只下缺失部分）
- 进度可见（日志输出），失败容错（单批失败不影响整体）
- 可独立测试（不依赖真实 miniQMT 运行）

### 非目标（YAGNI）
- ❌ 不下载 tick / 分钟线（量比只需日线）
- ❌ 不下载指数 / 港股通（量比是 A 股个股概念，`_trading_minutes` 仅支持 A 股时段）
- ❌ 不做定时刷新调度（日线每日收盘后更新一次，启动时增量下载已足够；定时调度留给后续独立需求）
- ❌ 不修改 `md.py` 的消费逻辑（生产/消费解耦）

## 3. 架构概览

```
run_qmt_server.py 启动
  │
  ├─ main_engine.add_gateway(QmtGateway)   [xtdata 此时已连 miniQMT（import 时建立）]
  ├─ main_engine.add_app(RpcServiceApp)
  │
  ├─ rpc_engine.start()                     [RPC 立即就绪，可接受客户端]
  │
  └─ 起 daemon 线程 ──► QmtDailyBarPreheater(main_engine).preheat()
                          │
                          ├─ 0. 实测留痕：打印各板块成分数量 + 子集关系（见 4.2）
                          ├─ 1. 枚举标的：遍历 SECTORS → get_stock_list_in_sector → set 去重
                          ├─ 2. 分批（每批 100 只）
                          │     └─ xtdata.download_history_data2(stock_list=batch, period='1d',
                          │            start_time=近30日, callback=lambda:None)
                          │        → 落盘 datadir/{SH|SZ}/86400/*.DAT
                          ├─ 3. 进度日志：每批打印 "预热进度 N/M"
                          └─ 4. 汇总日志：成功/失败批数、耗时（格式 8m12s）

  之后任意客户端订阅 → tick 到达 → md._get_avg_daily_vol 读 .DAT → 量比可算
```

**关键时序保证**：预热线程是 daemon，与 RPC 启动并行；RPC 不等待预热。预热未完成期间，已落盘
的标的量比可算，未落盘的暂为 0，随下载推进逐步可用。

## 4. 详细设计

### 4.1 新建模块 `qmt_preheater.py`

位置：`patches/qmt_preheater.py`（源）→ 同步到 `site-packages/vnpy_qmt/qmt_preheater.py`
（与 md.py/td.py 同级，符合现有补丁模式）。模块内 `from xtquant import xtdata`。

```python
from xtquant import xtdata

class QmtDailyBarPreheater:
    """QMT 日线数据预热器：启动时后台下载全市场（A股+ETF）日线，保证量比可算。"""

    # 板块列表：显式列举全部所需板块 + set 去重，不依赖"沪深A股是否含子板块"的假设。
    # 无论沪深A股是否已含创业板/科创板，此列表都正确覆盖（去重后无重复下载副作用）。
    SECTORS: list[str] = ["沪深A股", "创业板", "科创板", "沪深ETF"]
    # 时间范围：近 N 个自然日（量比只需 5 日，多下覆盖停牌/节假日；增量下载不浪费）
    LOOKBACK_DAYS: int = 30
    # 分批大小
    BATCH_SIZE: int = 100
    # 批间等待（秒）：保守默认值，给 download_history_data2 异步落盘留时间。
    # 经验值，可按 miniQMT 实际响应调整（md.py 单只下载后 sleep 2s，批量 100 只需更长）。
    BATCH_SLEEP: float = 3.0

    def __init__(self, main_engine):
        self.main_engine = main_engine

    def preheat(self) -> None:
        """主流程：实测留痕 → 枚举 → 分批下载 → 日志。异常不抛出（不影响交易）。"""
        ...

    def _collect_symbols(self) -> list[str]:
        """从板块枚举标的代码（如 '000001.SZ'），跨板块去重。"""
        ...

    def _download_batch(self, batch: list[str], start_time: str) -> bool:
        """下载一批，返回是否成功（按 download_history_data2 返回值判定）。
        单批异常被捕获并返回 False，不中断整体。"""
        ...

    def _log(self, msg: str) -> None:
        """同时写 main_engine 日志（客户端可见）+ stdout。"""
        ...
```

### 4.2 标的枚举与实测留痕

**枚举**：
- 调用 `xtdata.get_stock_list_in_sector(sector_name=s)` 遍历 `SECTORS`
- 返回的代码格式为 `000001.SZ`（带交易所后缀，与 `download_history_data2` 入参一致）
- 用 `set` 去重（板块间成分股可能重叠，显式列举多板块会导致重复，去重消除）

**实测留痕**（`preheat()` 第一步，解决"沪深A股是否含子板块"的核查空白）：
- 打印每个板块的成分数量
- 计算 `创业板 ⊂ 沪深A股?` 与 `科创板 ⊂ 沪深A股?` 的子集关系
- 输出示例：`板块成分：沪深A股=5200 创业板=1380 科创板=560 沪深ETF=850 | 创业板⊂沪深A股=True 科创板⊂沪深A股=True | 去重后总数=5480`
- **首次运行日志即为权威实测证据**；若发现沪深A股确实已含子板块，后续可精简 SECTORS

> 核查状态：设计阶段 WebSearch 无权威文档（经验性结论倾向"沪深A股含子板块"），miniQMT 未运行
> 无法实测。故采用"显式列举+去重"的稳健兜底，不押注该假设，并在运行时留痕验证。

### 4.3 时间范围

- `start_time` = 今天往前 `LOOKBACK_DAYS` 个自然日，格式 `YYYYMMDD`
- **`end_time` 不传**（让 API 用默认的"今天"），避免传入未来日期导致异常
- `download_history_data2` 原生增量：已存在的 `.DAT` 只补缺失日期，不重复全量下
- 因此"每次启动都跑"成本低（首次慢，之后只增量补昨日）

### 4.4 分批下载

- 按 `BATCH_SIZE` 切片，每批一次 `download_history_data2`
- **显式传 `callback=lambda: None`**（与 md.py 一致，满足 API 签名，避免不同 QMT 版本省略
  callback 时行为差异）
- 批间 `time.sleep(BATCH_SLEEP)`（默认 3.0s，给异步落盘留时间）
- 每批 `try/except`：失败记录日志、计为失败批，**继续下一批**（不中断）
- **失败粒度**：以 `download_history_data2` 的返回值（bool）判定批次成功/失败。
  QMT 不同版本对该批量内单只失败的细粒度反馈能力不一；若 callback 携带单只完成/错误信息则
  利用之，否则按批次粒度统计（诚实标注，不臆测返回结构）
- 全流程外层再包一层 `try/except`，确保任何异常都不影响服务

### 4.5 日志

- 通过 `main_engine.write_log(...)`（走事件引擎，GUI/客户端可见）+ `print`（服务端 stdout）
- 进度：每批结束打印 `"日线预热进度 1200/5500"`
- 汇总：`"日线预热完成：batches_ok=54 batches_fail=1 symbols=5500 elapsed=8m12s"`（区分批次与
  标的，语义清晰：`batches_*` 是 `_download_batch` 返回值的批次统计，`symbols` 是去重后参与
  预热的总标的数；无论 QMT 是否提供标的级细粒度回报，该语义都一致）

### 4.6 错误处理

| 场景 | 处理 |
|---|---|
| miniQMT 未运行 | `get_stock_list_in_sector`/`download_history_data2` 抛异常 → 单批失败 → 整体 try/except 兜底 → 日志告警，服务正常 |
| 某标的代码异常 | 分批粒度容错，该批失败，其余继续 |
| 网络抖动 | 不做自动重试（YAGNI；下次启动自动增量补） |
| 板块返回空 | 日志告警，preheat 提前结束 |

## 5. 集成点：`run_qmt_server.py`

在 `QmtRpcServer.start()` 中，`rpc_engine.start()` 之后追加（约 +10 行）：

```python
import threading
from vnpy_qmt.qmt_preheater import QmtDailyBarPreheater

def _preheat_in_background():
    try:
        QmtDailyBarPreheater(self.main_engine).preheat()
    except Exception as e:
        self.main_engine.write_log(f"日线预热异常（不影响交易）: {e}")

threading.Thread(target=_preheat_in_background, daemon=True, name="qmt-preheater").start()
```

daemon 线程：服务进程退出时自动结束，无需显式 stop。

**线程安全**：预热线程写 `.DAT`，`md._get_avg_daily_vol` 读 `.DAT` 并缓存于 MD 实例内，
两者无共享可变状态，无竞争。`download_history_data2` 的下载与 `get_local_data` 的读取由
xtquant 内部协调，文件级一致性由 miniQMT 保证。

## 6. 测试策略

新建 `test_qmt_preheater.py`（纯逻辑，mock xtdata，不依赖真实 miniQMT）。

**mock 目标**：`vnpy_qmt.qmt_preheater.xtdata`（模块内 `from xtquant import xtdata`，故 mock
该命名空间下的引用，而非 `xtquant.xtdata`）。

用例：
1. **标的枚举与去重**：mock `get_stock_list_in_sector` 返回多个有重叠的列表，验证去重后总数
2. **实测留痕**：mock 数据构造有明确包含关系的板块列表（如让"创业板"是"沪深A股"的真子集），
   验证 `_log` 输出含各板块数量与子集关系判定（True/False 正确）
3. **分批调用**：550 个标的、BATCH_SIZE=100 → 验证 `download_history_data2` 被调 6 次，每次
   stock_list 长度正确，且每次都传 `callback=lambda:None`
4. **失败容错**：mock 第 2 批返回 False/抛异常 → 验证后续批次仍执行，failed 计数正确
5. **start_time 计算**：验证近 30 日日期格式 `YYYYMMDD`，且**不传 end_time**
6. **进度/汇总日志**：验证进度按批输出、汇总含 `batches_ok/batches_fail/symbols/elapsed`
   （批次与标的区分，语义清晰），elapsed 为 `NmNs` 格式

测试不发起真实网络/磁盘 IO，全部 mock。

## 7. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 首次全量下载耗时长（数十分钟） | daemon 后台不阻塞；日志进度可见；增量机制使后续启动快 |
| miniQMT 未启动时预热无意义 | 异常被捕获、日志告警；不阻断服务 |
| 全市场下载占用磁盘 | 仅日线（每只约 KB 级），5500 只约几十 MB，可接受 |
| '沪深A股' 是否含子板块无法预确认 | 显式列举全部板块+去重，不依赖假设；运行时实测留痕可后续精简 |
| BATCH_SLEEP 过短致首启落盘不全 | 默认 3.0s 保守值；增量机制保证最终一致（下次启动补齐） |
| 与交易主流程资源竞争 | 分批 + sleep 节流；下载是 miniQMT 后台行为，对交易影响小 |

## 8. 交付物

- `patches/qmt_preheater.py`（源）
- `site-packages/vnpy_qmt/qmt_preheater.py`（运行时，与源同步）
- `examples/client_server/run_qmt_server.py`（+10 行集成）
- `test_qmt_preheater.py`（测试）
- 更新记忆 `qmt-patch-status.md`（补丁4 记录）

## 9. 变更记录

- 2026-06-17 v1：初版（基于 brainstorming 三项决策：全市场 A股+ETF / 启动异步后台 / 增量下载）
- 2026-06-17 v2（整合复审反馈）：
  - SECTORS 显式补充创业板/科创板 + set 去重，不依赖"沪深A股是否含子板块"（复审点1）
  - preheat 开头加实测留痕日志，作为板块成分的运行时权威证据（回应"沪深A股含子板块"核查）
  - BATCH_SLEEP 默认 1.0→3.0（保守，给异步落盘留时间）（复审点2）
  - 显式传 `callback=lambda:None` 保持 API 一致性（复审点3）
  - 失败粒度诚实标注：按返回值判定批次，细粒度依赖 QMT 版本（复审点3）
  - `end_time` 不传避免未来日期异常；耗时格式改 `8m12s`（复审点7）
  - 测试明确 mock 目标 `vnpy_qmt.qmt_preheater.xtdata`（复审点4）
  - 补充线程安全说明（复审点6）
- 2026-06-17 v3（复审二轮）：
  - 汇总日志区分批次与标的：`batches_ok/batches_fail/symbols/elapsed`（`_download_batch` 改返回 bool 后，原 `success=N` 的标的语义断裂，故区分批次与标的，语义对齐）
  - 测试"实测留痕"用例补充：mock 数据需构造明确包含关系（如创业板⊂沪深A股）以验证子集判定
