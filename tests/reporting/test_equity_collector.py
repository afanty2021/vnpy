"""EquitySnapshotCollector 单元测试

验证 A股 QMT 场景下采集器从 account.extra 读取真实可用现金/持仓市值，
而非 vnpy 原生 available（A股下≈总资产，不可用作可用现金）。
"""
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

from vnpy_china_reporting.data_source.equity_collector import EquitySnapshotCollector


def _make_acc(balance: float, frozen: float, extra) -> SimpleNamespace:
    """构造一个模拟的 vnpy AccountData（含 extra 字段）"""
    return SimpleNamespace(
        balance=balance,
        frozen=frozen,
        available=balance - frozen,  # vnpy 原生语义：available = balance - frozen
        extra=extra,
        accountid="RPC.40218291",
    )


def test_collect_reads_extra_cash_and_market_value():
    """有 extra['cash']/['market_value'] 时应优先使用，而非原生 available"""
    main_engine = MagicMock()
    main_engine.get_all_accounts.return_value = [
        _make_acc(1_000_000.0, 0.0, {"cash": 300_000.0, "market_value": 700_000.0})
    ]
    collector = EquitySnapshotCollector(db=MagicMock(), main_engine=main_engine)
    collector.store = MagicMock()

    count = collector.collect(snapshot_date=date(2026, 6, 18))

    assert count == 1
    collector.store.save_snapshot.assert_called_once()
    kwargs = collector.store.save_snapshot.call_args.kwargs
    assert kwargs["total_equity"] == 1_000_000.0
    assert kwargs["available_cash"] == 300_000.0   # 来自 extra["cash"]
    assert kwargs["market_value"] == 700_000.0     # 来自 extra["market_value"]
    # 关键不变式：有持仓时可用现金必须小于总权益
    assert kwargs["available_cash"] < kwargs["total_equity"]


def test_collect_falls_back_when_extra_missing():
    """extra 缺失时回退到原生 available，并告警（不抛错）"""
    main_engine = MagicMock()
    main_engine.get_all_accounts.return_value = [
        _make_acc(1_000_000.0, 0.0, None)
    ]
    collector = EquitySnapshotCollector(db=MagicMock(), main_engine=main_engine)
    collector.store = MagicMock()

    collector.collect(snapshot_date=date(2026, 6, 18))

    kwargs = collector.store.save_snapshot.call_args.kwargs
    assert kwargs["available_cash"] == 1_000_000.0  # 回退 available=balance-frozen
    assert kwargs["market_value"] == 0.0


def test_collect_no_accounts_returns_zero():
    """无账户数据时返回 0，不写库"""
    main_engine = MagicMock()
    main_engine.get_all_accounts.return_value = []
    collector = EquitySnapshotCollector(db=MagicMock(), main_engine=main_engine)
    collector.store = MagicMock()

    assert collector.collect(snapshot_date=date(2026, 6, 18)) == 0
    collector.store.save_snapshot.assert_not_called()


def test_collect_multiple_accounts():
    """多账户全部落库"""
    main_engine = MagicMock()
    main_engine.get_all_accounts.return_value = [
        _make_acc(1_000_000.0, 0.0, {"cash": 300_000.0, "market_value": 700_000.0}),
        _make_acc(500_000.0, 0.0, {"cash": 500_000.0, "market_value": 0.0}),
    ]
    collector = EquitySnapshotCollector(db=MagicMock(), main_engine=main_engine)
    collector.store = MagicMock()

    assert collector.collect(snapshot_date=date(2026, 6, 18)) == 2
    assert collector.store.save_snapshot.call_count == 2
