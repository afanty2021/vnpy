"""回测可信度修复验证测试

对应代码审查报告修复点：
- #1  get_equity() 按市价计算持仓市值
- #2  回测日期取自 bar.datetime（T+1 当日买入次日可卖出）
- #3+ calculate_metrics 接入完整权益曲线（夏普比率非0、回测天数真实）
- #10 CostCalculatorFactory('ETF') 不再因拼写错误崩溃
- #5  策略可脱离 UI 运行

可直接运行：python vnpy_china_backtest/tests/test_fixes_verification.py
"""
import os
import sys
from datetime import datetime, date, timedelta

# 确保项目根在 sys.path（支持从任意目录运行）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from vnpy.trader.constant import Exchange, Interval, Direction
from vnpy.trader.object import BarData

from vnpy_china_backtest import create_engine, get_strategy
from vnpy_china_backtest.cost import CostCalculatorFactory


def make_bar(vt_symbol: str, dt: datetime, close: float) -> BarData:
    """构造测试用 BarData"""
    symbol, exchange = vt_symbol.split(".")
    return BarData(
        symbol=symbol,
        exchange=Exchange(exchange),
        interval=Interval.DAILY,
        datetime=dt,
        open_price=close,
        high_price=close,
        low_price=close,
        close_price=close,
        volume=100000,
        turnover=close * 100000,
        gateway_name="TEST",
    )


def make_bars(vt_symbol: str, prices: list) -> list:
    """prices -> 每日收盘价序列，起始 2024-01-01 逐日递增"""
    base = date(2024, 1, 1)
    bars = []
    for i, close in enumerate(prices):
        dt = datetime.combine(base + timedelta(days=i), datetime.min.time())
        bars.append(make_bar(vt_symbol, dt, close))
    return bars


def test_get_equity_uses_market_price():
    """#1: get_equity 应按当前市价而非买入均价计算持仓市值"""
    engine = create_engine(
        capital=100000, enable_cost=False, enable_slippage=False,
        enable_price_limit=False, enable_t1=False,
    )
    vt_symbol = "600519.SSE"
    bars = make_bars(vt_symbol, [100.0, 110.0])
    engine.load_data(bars)

    engine.process_bar(bars[0])
    engine.buy(vt_symbol, 100.0, 100)   # 100股@100，无成本
    engine.process_bar(bars[1])         # 价格涨到110

    position_value = engine.get_equity() - engine.cash
    assert abs(position_value - 100 * 110.0) < 1e-6, \
        f"持仓应按市价110计算，实际市值={position_value}"
    print("[PASS] #1 get_equity 按市价计算持仓市值")


def test_t1_next_day_sellable():
    """#2: 开启T+1时，当日买入次日才能卖出（修复前 datetime.now 会全部阻止）"""
    engine = create_engine(
        capital=100000, enable_cost=False, enable_slippage=False,
        enable_price_limit=False, enable_t1=True,
    )
    vt_symbol = "600519.SSE"
    bars = make_bars(vt_symbol, [100.0, 100.0, 100.0])
    engine.load_data(bars)

    engine.process_bar(bars[0])
    ok, _ = engine.buy(vt_symbol, 100.0, 100)
    assert ok, "首日买入应成功"

    # 当日卖出应被 T+1 阻止
    ok, reason = engine.sell(vt_symbol, 100.0, 100)
    assert not ok, f"当日卖出应被T+1阻止，实际返回: ok={ok}, reason={reason}"

    # 次日卖出应成功
    engine.process_bar(bars[1])
    ok, reason = engine.sell(vt_symbol, 100.0, 100)
    assert ok, f"次日卖出应成功，实际: {reason}"
    print("[PASS] #2 T+1 规则：当日买入次日可卖出")


def test_sharpe_nonzero_and_real_trading_days():
    """#3+: 波动权益曲线下夏普比率应非0、回测天数应等于实际bar数"""
    engine = create_engine(
        capital=100000, enable_cost=False, enable_slippage=False,
        enable_price_limit=False, enable_t1=False,
    )
    vt_symbol = "600519.SSE"
    prices = [100, 105, 98, 108, 95, 110, 92, 115]
    bars = make_bars(vt_symbol, prices)
    engine.load_data(bars)

    # 首日买入持有，使权益随价格波动（否则无持仓权益曲线为常数，std=0）
    engine.process_bar(bars[0])
    engine.buy(vt_symbol, 100.0, 100)
    for bar in bars[1:]:
        engine.process_bar(bar)

    metrics = engine.calculate_metrics()
    assert metrics.sharpe_ratio != 0, \
        f"波动权益曲线下夏普比率不应为0（两点曲线缺陷），实际={metrics.sharpe_ratio}"
    assert metrics.trading_days == len(bars), \
        f"回测天数应={len(bars)}，实际={metrics.trading_days}"
    print(f"[PASS] #3 夏普比率非0: {metrics.sharpe_ratio:.4f}, "
          f"trading_days={metrics.trading_days}")


def test_cost_factory_etf():
    """#10: CostCalculatorFactory('ETF') 不应因 min_commmission 拼写错误崩溃"""
    CostCalculatorFactory._calculators.pop("ETF", None)  # 清缓存走 _create_config
    calc = CostCalculatorFactory.get_calculator("ETF")
    assert calc is not None, "ETF 计算器应成功创建"

    cost = calc.calculate(price=10.0, volume=1000, direction=Direction.SHORT)
    assert cost.stamp_duty == 0, "ETF 应无印花税"
    print(f"[PASS] #10 CostCalculatorFactory('ETF') 正常，无 TypeError，"
          f"卖出总成本={cost.total}")


def test_strategy_decoupled_from_ui():
    """#5: 策略可脱离 UI 独立运行"""
    strategy = get_strategy("buy_hold")
    engine = create_engine(
        capital=100000, enable_cost=False, enable_slippage=False,
        enable_price_limit=False, enable_t1=False,
    )
    vt_symbol = "600519.SSE"
    bars = make_bars(vt_symbol, [100.0, 105.0, 110.0])
    engine.load_data(bars)

    logs = strategy.run(engine, bars, vt_symbol)  # 无 UI 依赖
    assert len(engine.trades) > 0, "买入持有应产生交易"
    print(f"[PASS] #5 策略脱离 UI 运行：日志{len(logs)}条，交易{len(engine.trades)}笔")


def main():
    tests = [
        test_get_equity_uses_market_price,
        test_t1_next_day_sellable,
        test_sharpe_nonzero_and_real_trading_days,
        test_cost_factory_etf,
        test_strategy_decoupled_from_ui,
    ]
    passed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}: {e}")
            return 1
        except Exception as e:  # noqa: BLE001
            print(f"[ERROR] {test.__name__}: {type(e).__name__}: {e}")
            return 1
    print(f"\n全部通过: {passed}/{len(tests)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
