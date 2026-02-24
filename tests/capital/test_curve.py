"""
资金曲线管理器单元测试
"""

import pytest
from datetime import datetime, timedelta
from vnpy_china_capital.equity.curve import EquityCurveManager


class TestEquityCurveManager:
    """资金曲线管理器测试类"""

    def test_init(self):
        """测试初始化"""
        manager = EquityCurveManager(initial_capital=100000.0)

        assert manager.initial_capital == 100000.0
        assert manager.current_equity == 100000.0
        assert manager.peak_equity == 100000.0
        assert len(manager.equity_curve) == 0

    def test_init_zero_capital(self):
        """测试零初始资金"""
        manager = EquityCurveManager(initial_capital=0.0)

        assert manager.initial_capital == 0.0
        assert manager.current_equity == 0.0
        assert manager.peak_equity == 0.0

    def test_update_basic(self):
        """测试基本更新"""
        manager = EquityCurveManager(initial_capital=100000.0)
        point = manager.update(equity=105000.0)

        assert len(manager.equity_curve) == 1
        assert point.equity == 105000.0
        assert point.cumulative_return == 0.05  # 5%
        assert manager.current_equity == 105000.0

    def test_update_with_datetime(self):
        """测试指定时间更新"""
        manager = EquityCurveManager(initial_capital=100000.0)
        dt = datetime(2025, 1, 15, 10, 30, 0)
        point = manager.update(equity=105000.0, dt=dt)

        assert point.datetime == dt

    def test_peak_equity_update(self):
        """测试峰值资金更新"""
        manager = EquityCurveManager(initial_capital=100000.0)

        manager.update(equity=105000.0)  # 新高
        manager.update(equity=103000.0)  # 回落
        manager.update(equity=108000.0)  # 再次新高

        assert manager.peak_equity == 108000.0

    def test_drawdown_calculation(self):
        """测试回撤计算"""
        manager = EquityCurveManager(initial_capital=100000.0)

        manager.update(equity=100000.0)  # 初始
        manager.update(equity=110000.0)  # 上涨到11万，峰值11万
        manager.update(equity=100000.0)  # 回到10万，回撤约9.09%

        # 当前回撤 = (110000 - 100000) / 110000 = 0.0909...
        current_dd = manager.get_current_drawdown()
        assert abs(current_dd - 0.0909) < 0.001

        # 最大回撤也是这个值
        max_dd = manager.get_max_drawdown()
        assert abs(max_dd - 0.0909) < 0.001

    def test_max_drawdown_tracking(self):
        """测试最大回撤跟踪"""
        manager = EquityCurveManager(initial_capital=100000.0)

        manager.update(equity=100000.0)
        manager.update(equity=120000.0)  # peak = 120000
        manager.update(equity=110000.0)  # dd = (120000-110000)/120000 = 8.33%
        manager.update(equity=100000.0)  # dd = (120000-100000)/120000 = 16.67%
        manager.update(equity=115000.0)  # peak更新为120000, dd = 4.17%

        assert manager.get_max_drawdown() > 0.15  # 最大回撤约16.67%

    def test_daily_return(self):
        """测试日收益率计算"""
        manager = EquityCurveManager(initial_capital=100000.0)

        manager.update(equity=100000.0)  # 第一个点，没有日收益（相对于初始资金）
        point2 = manager.update(equity=105000.0)  # 日收益 = 5%
        point3 = manager.update(equity=110000.0)  # 日收益 = (110000-105000)/105000 = 4.76%

        # 第一个点（初始资金点）日收益为0
        assert len(manager.equity_curve) == 3

        # 第二个点日收益 = (105000-100000)/100000 = 5%
        assert abs(point2.daily_return - 0.05) < 0.0001

        # 第三个点日收益 = (110000-105000)/105000 = 4.76%
        assert abs(point3.daily_return - 0.047619) < 0.001

    def test_get_returns(self):
        """测试获取收益率序列"""
        manager = EquityCurveManager(initial_capital=100000.0)

        manager.update(equity=100000.0)
        manager.update(equity=105000.0)
        manager.update(equity=103000.0)
        manager.update(equity=108000.0)

        returns = manager.get_returns()
        assert len(returns) == 4

    def test_sharpe_ratio_basic(self):
        """测试夏普比率基本计算"""
        manager = EquityCurveManager(initial_capital=100000.0)

        # 添加一些收益率数据
        manager.update(equity=100000.0)
        manager.update(equity=101000.0)  # 1%
        manager.update(equity=102000.0)  # 0.99%
        manager.update(equity=103000.0)  # 0.98%
        manager.update(equity=104000.0)  # 0.97%

        sharpe = manager.calculate_sharpe_ratio(risk_free_rate=0.03)
        assert isinstance(sharpe, float)

    def test_sharpe_ratio_insufficient_data(self):
        """测试数据不足时的夏普比率"""
        manager = EquityCurveManager(initial_capital=100000.0)

        # 少于2个数据点
        manager.update(equity=100000.0)
        sharpe = manager.calculate_sharpe_ratio()

        assert sharpe == 0.0

    def test_sortino_ratio(self):
        """测试索提诺比率"""
        manager = EquityCurveManager(initial_capital=100000.0)

        manager.update(equity=100000.0)
        manager.update(equity=105000.0)  # +5%
        manager.update(equity=103000.0)  # -1.9%
        manager.update(equity=107000.0)  # +3.88%

        sortino = manager.calculate_sortino_ratio()
        assert isinstance(sortino, float)

    def test_calmar_ratio(self):
        """测试卡玛比率"""
        manager = EquityCurveManager(initial_capital=100000.0)

        manager.update(equity=100000.0)
        manager.update(equity=120000.0)
        manager.update(equity=100000.0)

        calmar = manager.calculate_calmar_ratio()
        # 年化收益约100%，最大回撤约16.67%
        assert isinstance(calmar, float)

    def test_annual_return(self):
        """测试年化收益率"""
        manager = EquityCurveManager(initial_capital=100000.0)

        dt1 = datetime(2025, 1, 1)
        dt2 = datetime(2026, 1, 1)

        manager.update(equity=100000.0, dt=dt1)
        manager.update(equity=120000.0, dt=dt2)

        annual_return = manager.get_annual_return()
        assert abs(annual_return - 0.20) < 0.01  # 约20%

    def test_volatility(self):
        """测试波动率"""
        manager = EquityCurveManager(initial_capital=100000.0)

        manager.update(equity=100000.0)
        manager.update(equity=105000.0)
        manager.update(equity=103000.0)
        manager.update(equity=108000.0)

        vol = manager.get_volatility()
        assert isinstance(vol, float)
        assert vol >= 0

    def test_get_summary(self):
        """测试摘要信息"""
        manager = EquityCurveManager(initial_capital=100000.0)

        manager.update(equity=100000.0)
        manager.update(equity=105000.0)

        summary = manager.get_summary()

        assert "initial_capital" in summary
        assert "current_equity" in summary
        assert "peak_equity" in summary
        assert "max_drawdown" in summary
        assert "sharpe_ratio" in summary
        assert "num_points" in summary

    def test_reset(self):
        """测试重置功能"""
        manager = EquityCurveManager(initial_capital=100000.0)

        manager.update(equity=105000.0)
        manager.update(equity=110000.0)

        manager.reset()

        assert len(manager.equity_curve) == 0
        assert manager.peak_equity == 100000.0
        assert manager.current_equity == 100000.0

    def test_empty_curve_max_drawdown(self):
        """测试空曲线的最大回撤"""
        manager = EquityCurveManager(initial_capital=100000.0)

        assert manager.get_max_drawdown() == 0.0

    def test_zero_equity_drawdown(self):
        """测试零资金时的回撤"""
        manager = EquityCurveManager(initial_capital=0.0)

        manager.update(equity=0.0)
        manager.update(equity=100.0)

        assert manager.get_current_drawdown() == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
