"""Tests for vnpy_china_backtest module - REQ-006 增强回测系统"""

import os
import sys
# 项目根目录（本文件上溯三级：tests -> vnpy_china_backtest -> 项目根）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from datetime import datetime


class TestAStockCost:
    """Test A股交易成本"""

    def test_creation(self):
        """Test cost creation"""
        from vnpy_china_backtest.cost import AStockCost
        cost = AStockCost()
        assert cost is not None


class TestTradingCost:
    """Test trading cost"""

    def test_creation(self):
        """Test trading cost creation"""
        from vnpy_china_backtest.cost import TradingCost
        tc = TradingCost(
            commission=100.0,
            stamp_duty=50.0,
            transfer_fee=10.0,
            handling_fee=5.0,
            total=165.0,
            cost_rate=0.001
        )
        assert tc is not None


class TestCostConfig:
    """Test cost configuration"""

    def test_creation(self):
        """Test config creation"""
        from vnpy_china_backtest.cost import CostConfig
        config = CostConfig()
        assert config is not None


class TestCostCalculator:
    """Test cost calculator"""

    def test_creation(self):
        """Test calculator creation"""
        from vnpy_china_backtest.cost import CostCalculator
        calc = CostCalculator()
        assert calc is not None


class TestSlippageConfig:
    """Test slippage configuration"""

    def test_creation(self):
        """Test slippage config creation"""
        from vnpy_china_backtest.slippage import SlippageConfig
        config = SlippageConfig()
        assert config is not None


class TestSlippageModels:
    """Test slippage models"""

    def test_fixed_slippage_creation(self):
        """Test fixed slippage creation"""
        from vnpy_china_backtest.slippage import FixedSlippage
        model = FixedSlippage()
        assert model is not None

    def test_percent_slippage_creation(self):
        """Test percent slippage creation"""
        from vnpy_china_backtest.slippage import PercentSlippage
        model = PercentSlippage()
        assert model is not None

    def test_impact_cost_slippage_creation(self):
        """Test impact cost slippage creation"""
        from vnpy_china_backtest.slippage import ImpactCostSlippage
        model = ImpactCostSlippage()
        assert model is not None


class TestPriceLimitEngine:
    """Test price limit engine"""

    def test_creation(self):
        """Test engine creation"""
        from vnpy_china_backtest.rules.price_limit import PriceLimitEngine
        engine = PriceLimitEngine()
        assert engine is not None


class TestT1Simulator:
    """Test T+1 simulator"""

    def test_creation(self):
        """Test simulator creation"""
        from vnpy_china_backtest.rules.t1_simulator import T1Simulator
        sim = T1Simulator()
        assert sim is not None

    def test_position_record_creation(self):
        """Test position record creation"""
        from vnpy_china_backtest.rules.t1_simulator import PositionRecord

        record = PositionRecord(
            symbol="000001",
            volume=1000,
            available=0,
            frozen=1000,
            avg_price=10.0
        )
        assert record.symbol == "000001"
        assert record.volume == 1000


class TestEnhancedMetrics:
    """Test enhanced metrics"""

    def test_creation(self):
        """Test metrics creation"""
        from vnpy_china_backtest.report.metrics import EnhancedMetrics
        metrics = EnhancedMetrics()
        assert metrics is not None


class TestBacktestConfig:
    """Test backtest configuration"""

    def test_creation(self):
        """Test config creation"""
        from vnpy_china_backtest.config import BacktestConfig
        config = BacktestConfig()
        assert config is not None

    def test_default_values(self):
        """Test default config values"""
        from vnpy_china_backtest.config import BacktestConfig
        config = BacktestConfig()
        # 检查默认值
        assert config.commission_rate > 0
        assert config.initial_capital > 0


# ---------------------------------------------------------------------------
# 代码审查修复回归测试（F1-F11）
# ---------------------------------------------------------------------------

def _mk_trade(symbol, direction, price, volume, dt):
    """构造 TradeData（测试辅助）"""
    from vnpy.trader.object import TradeData
    from vnpy.trader.constant import Exchange, Offset
    return TradeData(
        symbol=symbol, exchange=Exchange.SZSE, orderid="o", tradeid=f"{dt}{direction}",
        direction=direction, offset=Offset.NONE, price=price, volume=volume,
        datetime=dt, gateway_name="T"
    )


class TestPnLFIFOMatching:
    """F1: 部分平仓 PnL（FIFO 匹配）"""

    def test_partial_close_pnl(self):
        from datetime import datetime
        from vnpy.trader.constant import Direction
        from vnpy_china_backtest.report.metrics import MetricsCalculator
        d = datetime(2024, 1, 1)
        trades = [
            _mk_trade("000001", Direction.LONG, 10.0, 200, d),
            _mk_trade("000001", Direction.SHORT, 15.0, 100, d.replace(day=2)),
            _mk_trade("000001", Direction.SHORT, 12.0, 100, d.replace(day=3)),
        ]
        mc = MetricsCalculator()
        # 100*(15-10) + 100*(12-10) = 700（原算法会得 -500）
        assert abs(mc._calculate_stock_pnl(trades) - 700) < 0.001

    def test_win_rate_profit_stock(self):
        from datetime import datetime
        from vnpy.trader.constant import Direction
        from vnpy_china_backtest.report.metrics import MetricsCalculator
        d = datetime(2024, 1, 1)
        trades = [
            _mk_trade("A", Direction.LONG, 10.0, 100, d),
            _mk_trade("A", Direction.SHORT, 12.0, 100, d.replace(day=2)),
        ]
        mc = MetricsCalculator()
        m = mc.calculate(trades=trades, equity_curve=[100000, 100200],
                         trading_days=1, initial_capital=100000, final_capital=100200)
        assert m.win_rate == 1.0   # 盈利标的计为胜


class TestConsecutiveWinsTimeOrdered:
    """F2: 连续盈亏按时间序（非 symbol 序）"""

    def test_alternating_by_time(self):
        from datetime import datetime
        from vnpy.trader.constant import Direction
        from vnpy_china_backtest.report.metrics import MetricsCalculator
        base = datetime(2024, 1, 1)
        trades = [
            _mk_trade("A", Direction.LONG, 10.0, 100, base.replace(hour=9)),
            _mk_trade("A", Direction.SHORT, 12.0, 100, base.replace(hour=10)),   # +200
            _mk_trade("B", Direction.LONG, 10.0, 100, base.replace(hour=11)),
            _mk_trade("B", Direction.SHORT, 9.0, 100, base.replace(hour=12)),    # -100
            _mk_trade("A", Direction.LONG, 10.0, 100, base.replace(hour=13)),
            _mk_trade("A", Direction.SHORT, 12.0, 100, base.replace(hour=14)),   # +200
        ]
        mc = MetricsCalculator()
        m = mc.calculate(trades=trades, equity_curve=[100000, 100300],
                         trading_days=1, initial_capital=100000, final_capital=100300)
        # 事件序 +200,-100,+200 → 连续赢1 连续亏1
        assert m.max_consecutive_wins == 1
        assert m.max_consecutive_losses == 1


class TestPreClosesCleanup:
    """F3: load_data 清理 pre_closes"""

    def test_no_residual(self):
        from datetime import datetime
        from vnpy.trader.object import BarData
        from vnpy.trader.constant import Exchange
        from vnpy_china_backtest.engine import EnhancedBacktestEngine
        e = EnhancedBacktestEngine()
        e.pre_closes["OLD.SZSE"] = 99.9
        b = BarData(symbol="000001", exchange=Exchange.SZSE,
                    datetime=datetime(2024, 1, 1), close_price=10.0, gateway_name="T")
        e.load_data([b])
        assert "OLD.SZSE" not in e.pre_closes


class TestSortinoRatio:
    """F4: sortino 计算"""

    def test_sortino_positive_with_downside(self):
        from vnpy_china_backtest.report.metrics import MetricsCalculator
        mc = MetricsCalculator()
        eq = [100000, 101000, 100500, 100200, 100800]   # 含负收益
        m = mc.calculate(trades=[], equity_curve=eq, trading_days=4,
                         initial_capital=100000, final_capital=100800)
        assert m.sortino_ratio > 0


class TestRealizedPnl:
    """F5: get_realized_pnl（FIFO 累加）"""

    def test_realized_on_full_close(self):
        from datetime import date
        from vnpy_china_backtest.rules.t1_simulator import T1Simulator
        sim = T1Simulator()
        sim.record_buy("000001", 100, 10.0, date(2024, 1, 1))
        sim.record_sell("000001", 100, 12.0, date(2024, 1, 2))
        assert abs(sim.get_realized_pnl("000001") - 200) < 0.001

    def test_realized_on_partial_close(self):
        from datetime import date
        from vnpy_china_backtest.rules.t1_simulator import T1Simulator
        sim = T1Simulator()
        sim.record_buy("000001", 200, 10.0, date(2024, 1, 1))
        sim.record_sell("000001", 100, 12.0, date(2024, 1, 2))
        # 100*(12-10)=200，剩 100 未平不计
        assert abs(sim.get_realized_pnl("000001") - 200) < 0.001


class TestImpactCostSlippage:
    """F6: ImpactCost 走冲击公式"""

    def test_market_volume_branch(self):
        from vnpy.trader.constant import Direction
        from vnpy_china_backtest.slippage import ImpactCostSlippage
        s = ImpactCostSlippage(impact_factor=0.1)
        # market_volume=0 → 固定 price*0.0005
        assert abs(s.apply(10.0, 100, Direction.LONG, market_volume=0) - 10.005) < 0.0001
        # market_volume=1000 → volume_ratio=0.1, slip=10*0.1*0.1*0.1=0.01
        assert abs(s.apply(10.0, 100, Direction.LONG, market_volume=1000) - 10.01) < 0.0001

    def test_engine_propagates_volume(self):
        from datetime import datetime
        from vnpy.trader.object import BarData
        from vnpy.trader.constant import Exchange
        from vnpy_china_backtest.engine import EnhancedBacktestEngine
        e = EnhancedBacktestEngine()
        e.capital = 1000000
        e.cash = 1000000
        e.enable_cost = False
        e.enable_price_limit = False
        e.enable_t1 = False
        e.set_slippage("impact", impact_factor=0.1)
        b = BarData(symbol="000001", exchange=Exchange.SZSE, datetime=datetime(2024, 1, 2),
                    gateway_name="T", open_price=10.0, high_price=10.0, low_price=10.0,
                    close_price=10.0, volume=1000)
        e.process_bar(b)
        assert e.current_bar_volume == 1000
        ok, _ = e.buy("000001.SZSE", 10.0, 100)
        assert ok and abs(e.avg_prices["000001.SZSE"] - 10.01) < 0.001


class TestTransferFeeNoMin:
    """F7: 过户费无最低值"""

    def test_small_turnover_not_floored(self):
        from vnpy.trader.constant import Direction, Exchange
        from vnpy_china_backtest.cost import CostCalculator
        c = CostCalculator().calculate(price=1.0, volume=100, direction=Direction.LONG, exchange=Exchange.SZSE)
        # turnover=100, transfer=100*0.00001=0.001（不被 max(0.1) 抬高）
        assert abs(c.transfer_fee - 0.001) < 0.0001


class TestAnnualDaysPropagation:
    """F8: annual_days 贯通 engine→calculator"""

    def test_set_parameters_propagates(self):
        from datetime import datetime
        from vnpy.trader.constant import Interval
        from vnpy_china_backtest.engine import EnhancedBacktestEngine
        e = EnhancedBacktestEngine()
        e.set_parameters(["000001.SZSE"], Interval.DAILY,
                         datetime(2024, 1, 1), datetime(2024, 12, 31), annual_days=365)
        assert e.metrics_calculator.annual_days == 365


class TestMonthlyReturns:
    """F9: monthly_returns"""

    def test_cross_two_months(self):
        from datetime import datetime
        from vnpy_china_backtest.report.metrics import MetricsCalculator
        mc = MetricsCalculator()
        dts = [datetime(2024, 1, 30), datetime(2024, 1, 31),
               datetime(2024, 2, 1), datetime(2024, 2, 2)]
        eq = [100000, 101000, 101500, 102000, 103000]
        m = mc.calculate(trades=[], equity_curve=eq, trading_days=4,
                         initial_capital=100000, final_capital=103000, bar_datetimes=dts)
        assert "2024-01" in m.monthly_returns and "2024-02" in m.monthly_returns

    def test_length_mismatch_returns_empty(self):
        from datetime import datetime
        from vnpy_china_backtest.report.metrics import MetricsCalculator
        mc = MetricsCalculator()
        dts = [datetime(2024, 1, 30), datetime(2024, 1, 31)]
        eq = [100000, 101000, 101500, 102000, 103000]
        m = mc.calculate(trades=[], equity_curve=eq, trading_days=4,
                         initial_capital=100000, final_capital=103000, bar_datetimes=dts)
        assert m.monthly_returns == {}


class TestBacktestWorker:
    """F11: UI 回测线程化"""

    def test_worker_normal_and_cancel(self):
        import os
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from datetime import datetime, timedelta
        from vnpy.trader.object import BarData
        from vnpy.trader.constant import Exchange
        from vnpy.trader.ui.qt import QtWidgets
        from vnpy_china_backtest.ui.widget import BacktestWorker

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        bars = [BarData(
            symbol="000001", exchange=Exchange.SZSE,
            datetime=datetime(2024, 1, 1) + timedelta(days=i),
            gateway_name="T", open_price=10.0, high_price=10.5, low_price=9.5,
            close_price=10.0 + i * 0.05, volume=10000) for i in range(300)]
        cfg = {"enable_cost": False, "enable_slippage": False,
               "enable_price_limit": False, "enable_t1": False}

        # 正常路径：应收到 finished_ok
        w = BacktestWorker("000001.SZSE", bars, 100000, "buy_hold", cfg)
        got = []
        w.finished_ok.connect(lambda r, t, e, l: got.append(r))
        w.start(); w.wait(); app.processEvents()
        assert len(got) == 1 and got[0]["bar_count"] == 300

        # cancel 路径：不应发 finished_ok
        w2 = BacktestWorker("000001.SZSE", bars, 100000, "buy_hold", cfg)
        got2 = []
        w2.finished_ok.connect(lambda r, t, e, l: got2.append(r))
        w2.start(); w2.cancel(); w2.wait(); app.processEvents()
        assert len(got2) == 0
