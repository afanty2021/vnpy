"""
回撤控制器单元测试
"""

import pytest
from vnpy_china_capital.equity.drawdown import DrawdownController


class TestDrawdownController:
    """回撤控制器测试类"""

    def test_init(self):
        """测试初始化"""
        controller = DrawdownController(
            max_drawdown=0.15,
            warning_level=0.10
        )

        assert controller.max_drawdown == 0.15
        assert controller.warning_level == 0.10
        assert controller.stop_level == 0.15

    def test_init_custom_stop_level(self):
        """测试自定义停止水平"""
        controller = DrawdownController(
            max_drawdown=0.20,
            warning_level=0.10,
            stop_level=0.25
        )

        assert controller.stop_level == 0.25

    def test_position_multiplier_normal(self):
        """测试正常状态下的仓位系数"""
        controller = DrawdownController(
            max_drawdown=0.15,
            warning_level=0.10
        )

        # 回撤小于预警线，返回满仓
        assert controller.get_position_multiplier(0.05) == 1.0
        assert controller.get_position_multiplier(0.09) == 1.0

    def test_position_multiplier_warning(self):
        """测试预警状态下的仓位系数"""
        controller = DrawdownController(
            max_drawdown=0.15,
            warning_level=0.10
        )

        # 回撤在预警线和0.75*max之间，返回7成
        multiplier = controller.get_position_multiplier(0.10)  # 正好是warning
        assert multiplier == 0.7

        multiplier = controller.get_position_multiplier(0.11)
        assert multiplier == 0.7

    def test_position_multiplier_danger(self):
        """测试危险状态下的仓位系数"""
        controller = DrawdownController(
            max_drawdown=0.15,
            warning_level=0.10
        )

        # 回撤在0.75*max和max之间，返回5成
        multiplier = controller.get_position_multiplier(0.12)
        assert multiplier == 0.5

    def test_position_multiplier_stop(self):
        """测试停止状态下的仓位系数"""
        controller = DrawdownController(
            max_drawdown=0.15,
            warning_level=0.10
        )

        # 回撤超过max，返回0
        multiplier = controller.get_position_multiplier(0.15)
        assert multiplier == 0.0

        multiplier = controller.get_position_multiplier(0.20)
        assert multiplier == 0.0

    def test_should_stop_trading(self):
        """测试是否应该停止交易"""
        controller = DrawdownController(
            max_drawdown=0.15,
            warning_level=0.10,
            stop_level=0.15
        )

        assert controller.should_stop_trading(0.10) is False
        assert controller.should_stop_trading(0.14) is False
        assert controller.should_stop_trading(0.15) is True
        assert controller.should_stop_trading(0.20) is True

    def test_should_stop_trading_custom_stop_level(self):
        """测试自定义停止水平的停止判断"""
        controller = DrawdownController(
            max_drawdown=0.15,
            warning_level=0.10,
            stop_level=0.20
        )

        # 在max和stop之间应该还能交易
        assert controller.should_stop_trading(0.15) is False
        assert controller.should_stop_trading(0.19) is False
        assert controller.should_stop_trading(0.20) is True

    def test_should_reduce_position(self):
        """测试是否应该减少仓位"""
        controller = DrawdownController(
            max_drawdown=0.15,
            warning_level=0.10
        )

        assert controller.should_reduce_position(0.05) is False
        assert controller.should_reduce_position(0.10) is True
        assert controller.should_reduce_position(0.15) is True

    def test_get_risk_level(self):
        """测试风险等级判断"""
        controller = DrawdownController(
            max_drawdown=0.15,
            warning_level=0.10
        )

        assert controller.get_risk_level(0.05) == "normal"
        assert controller.get_risk_level(0.10) == "warning"
        assert controller.get_risk_level(0.12) == "danger"
        assert controller.get_risk_level(0.15) == "stop"

    def test_get_risk_status(self):
        """测试风险状态详细信息"""
        controller = DrawdownController(
            max_drawdown=0.15,
            warning_level=0.10
        )

        status = controller.get_risk_status(0.12)

        assert "current_drawdown" in status
        assert "risk_level" in status
        assert "position_multiplier" in status
        assert "should_stop_trading" in status
        assert "should_reduce_position" in status
        assert "max_drawdown" in status
        assert "warning_level" in status
        assert "stop_level" in status

        assert status["current_drawdown"] == 0.12
        assert status["risk_level"] == "danger"
        assert status["position_multiplier"] == 0.5

    def test_calculate_new_position(self):
        """测试计算新仓位"""
        controller = DrawdownController(
            max_drawdown=0.15,
            warning_level=0.10
        )

        # 正常状态
        new_pos = controller.calculate_new_position(100000, 0.05)
        assert new_pos == 100000

        # 预警状态
        new_pos = controller.calculate_new_position(100000, 0.10)
        assert new_pos == 70000

        # 危险状态
        new_pos = controller.calculate_new_position(100000, 0.12)
        assert new_pos == 50000

        # 停止状态
        new_pos = controller.calculate_new_position(100000, 0.15)
        assert new_pos == 0

    def test_zero_drawdown(self):
        """测试零回撤"""
        controller = DrawdownController(
            max_drawdown=0.15,
            warning_level=0.10
        )

        assert controller.get_position_multiplier(0.0) == 1.0
        assert controller.should_stop_trading(0.0) is False
        assert controller.get_risk_level(0.0) == "normal"

    def test_boundary_conditions(self):
        """测试边界条件"""
        controller = DrawdownController(
            max_drawdown=0.15,
            warning_level=0.10
        )

        # 边界值测试
        # 0 < dd < 0.10: 正常
        assert controller.get_position_multiplier(0.0) == 1.0
        # 0.10 <= dd < 0.1125: 预警
        assert controller.get_position_multiplier(0.10) == 0.7
        # 0.1125 <= dd < 0.15: 危险
        assert controller.get_position_multiplier(0.1125) == 0.5
        assert controller.get_position_multiplier(0.15) == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
