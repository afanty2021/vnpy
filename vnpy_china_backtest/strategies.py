"""
A股回测策略

策略与 UI 解耦：策略只负责交易逻辑，进度通过回调上报，日志通过返回值收集。
新增策略只需继承 BaseStrategy 并在 STRATEGIES 注册，无需修改 Widget。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Callable, TYPE_CHECKING

from vnpy.trader.object import BarData

if TYPE_CHECKING:
    from vnpy_china_backtest.engine import EnhancedBacktestEngine


# 进度回调：参数为策略内部相对进度（0-100）
ProgressCallback = Callable[[int], None]


class BaseStrategy(ABC):
    """回测策略基类

    策略不持有任何 UI 引用：仅通过 engine 接口下单、通过 on_progress 上报进度、
    通过返回值收集交易日志。
    """

    name: str = ""

    @abstractmethod
    def run(
        self,
        engine: "EnhancedBacktestEngine",
        bars: List[BarData],
        vt_symbol: str,
        on_progress: Optional[ProgressCallback] = None,
    ) -> List[str]:
        """执行策略

        Args:
            engine: 回测引擎
            bars: K线数据
            vt_symbol: 合约代码
            on_progress: 进度回调（参数为 0-100 的相对进度）

        Returns:
            每日交易日志列表
        """
        raise NotImplementedError

    @staticmethod
    def _emit_progress(
        on_progress: Optional[ProgressCallback],
        index: int,
        total: int
    ) -> None:
        """上报相对进度（0-100）"""
        if on_progress and total > 0:
            on_progress(int(100 * (index + 1) / total))


class MaCrossStrategy(BaseStrategy):
    """均线策略：MA5/MA20 金叉买入，死叉卖出"""

    name = "均线策略（MA5/MA20 金叉死叉）"

    def run(
        self,
        engine: "EnhancedBacktestEngine",
        bars: List[BarData],
        vt_symbol: str,
        on_progress: Optional[ProgressCallback] = None,
    ) -> List[str]:
        logs: List[str] = []
        close_prices = [bar.close_price for bar in bars]
        total = len(bars)
        holding = False

        for i, bar in enumerate(bars):
            engine.pre_closes[vt_symbol] = bar.close_price

            # 需要至少20根K线才能计算MA20
            if i < 20:
                engine.process_bar(bar)
                self._emit_progress(on_progress, i, total)
                continue

            # 计算均线
            ma5 = sum(close_prices[i - 5: i]) / 5
            ma20 = sum(close_prices[i - 20: i]) / 20
            prev_ma5 = sum(close_prices[i - 6: i - 1]) / 5
            prev_ma20 = sum(close_prices[i - 21: i - 1]) / 20

            price = bar.close_price

            # 金叉：MA5 上穿 MA20 → 买入
            if not holding and prev_ma5 <= prev_ma20 and ma5 > ma20:
                # 计算可买股数（100股整数倍）
                max_volume = int(engine.cash / (price * 100)) * 100
                if max_volume >= 100:
                    ok, _ = engine.buy(vt_symbol, price, max_volume)
                    if ok:
                        holding = True
                        logs.append(
                            f"{bar.datetime.date()} 买入 {vt_symbol} "
                            f"价格:{price:.2f} 数量:{max_volume}"
                        )

            # 死叉：MA5 下穿 MA20 → 卖出
            elif holding and prev_ma5 >= prev_ma20 and ma5 < ma20:
                pos = engine.get_position(vt_symbol)
                if pos > 0:
                    ok, _ = engine.sell(vt_symbol, price, pos)
                    if ok:
                        holding = False
                        logs.append(
                            f"{bar.datetime.date()} 卖出 {vt_symbol} "
                            f"价格:{price:.2f} 数量:{pos}"
                        )

            engine.process_bar(bar)
            self._emit_progress(on_progress, i, total)

        return logs


class BuyHoldStrategy(BaseStrategy):
    """买入持有策略：首日全仓买入，持有到期末"""

    name = "买入持有（基准对比）"

    def run(
        self,
        engine: "EnhancedBacktestEngine",
        bars: List[BarData],
        vt_symbol: str,
        on_progress: Optional[ProgressCallback] = None,
    ) -> List[str]:
        logs: List[str] = []
        if not bars:
            return logs

        total = len(bars)

        # 首日买入
        first_bar = bars[0]
        engine.pre_closes[vt_symbol] = first_bar.close_price
        price = first_bar.close_price
        max_volume = int(engine.cash / (price * 100)) * 100
        if max_volume >= 100:
            engine.buy(vt_symbol, price, max_volume)
            logs.append(
                f"{first_bar.datetime.date()} 买入 {vt_symbol} "
                f"价格:{price:.2f} 数量:{max_volume} (买入持有)"
            )

        # 逐日更新
        for i, bar in enumerate(bars):
            engine.pre_closes[vt_symbol] = bar.close_price
            engine.process_bar(bar)
            self._emit_progress(on_progress, i, total)

        return logs


# 策略注册表：key 与 UI 下拉项数据对应
STRATEGIES = {
    "ma_cross": MaCrossStrategy,
    "buy_hold": BuyHoldStrategy,
}


def get_strategy(key: str) -> BaseStrategy:
    """按 key 获取策略实例

    Args:
        key: 策略标识（与 UI 下拉项 currentData 对应）

    Returns:
        BaseStrategy: 策略实例
    """
    strategy_cls = STRATEGIES.get(key)
    if strategy_cls is None:
        raise ValueError(f"未知策略: {key}，可选: {list(STRATEGIES.keys())}")
    return strategy_cls()
