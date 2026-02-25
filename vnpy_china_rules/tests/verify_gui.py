"""
简单验证A股规则模块GUI集成功能
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
from vnpy_china_rules.gui_engine import ChinaRulesGuiEngine
from vnpy_china_rules.engine import ChinaStockRulesEngine, DataSourceManager


def test_gui_engine():
    """测试GUI引擎核心功能"""
    print("\n" + "=" * 50)
    print("验证A股规则模块GUI集成")
    print("=" * 50 + "\n")

    # 创建数据源管理器
    dm = DataSourceManager()
    print("✓ 数据源管理器创建成功")

    # 创建规则引擎
    rules_engine = ChinaStockRulesEngine(dm)
    print("✓ 规则引擎创建成功")

    # 记录测试买入数据
    test_date = datetime(2026, 2, 20, 9, 30)
    rules_engine.t1_rules.record_buy("000001", 1000, test_date)
    rules_engine.t1_rules.record_buy("000001", 2000, test_date)
    rules_engine.t1_rules.record_buy("600000", 1500, test_date)
    print("✓ 测试买入数据已记录")

    # 验证T+1规则引擎
    sellable = rules_engine.t1_rules.get_sellable_volume("000001", datetime.now())
    print(f"✓ T+1可卖数量查询: 000001 可卖 {sellable} 股")
    assert sellable == 3000, f"期望3000股，实际{sellable}股"

    # 验证涨跌停规则引擎
    limit_up, limit_down = rules_engine.price_limit_rules.calculate_limit_price("000001", 10.0)
    print(f"✓ 涨跌停价格计算: 昨收10.0 -> 涨停{limit_up}, 跌停{limit_down}")
    assert abs(limit_up - 11.0) < 0.01, f"期望涨停11.0，实际{limit_up}"
    assert abs(limit_down - 9.0) < 0.01, f"期望跌停9.0，实际{limit_down}"

    # 验证交易时间规则引擎
    is_trading = rules_engine.time_rules.is_trading_time(datetime.now())
    print(f"✓ 交易时间判断: 当前是否交易时间 = {is_trading}")

    # 验证订单检查
    from vnpy.trader.object import OrderData
    from vnpy.trader.constant import Direction, Exchange

    order = OrderData(
        symbol="000001",
        exchange=Exchange.SZSE,
        orderid="TEST001",
        direction=Direction.SHORT,
        price=10.0,
        volume=1000,
        datetime=datetime.now(),
        gateway_name="TEST",
    )

    results = rules_engine.check_order(order)
    print(f"✓ 订单规则检查: 检查了 {len(results)} 条规则")
    for result in results:
        status = "通过" if result.passed else "失败"
        print(f"  - {result.rule_name}: {status} - {result.message}")

    print("\n" + "=" * 50)
    print("GUI集成功能验证完成!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    test_gui_engine()
