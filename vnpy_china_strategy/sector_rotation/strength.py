"""
板块强度轮动策略

基于板块相对强度进行轮动。
"""

from typing import Dict, List, Optional
from datetime import datetime, date, timedelta

from vnpy.trader.object import BarData

from vnpy_china_strategy.template import ChinaStrategyTemplate
from vnpy_china_strategy.base import RiskControlMixin, PositionManager
from vnpy_china_strategy.sector_rotation.models import SectorStrength
from vnpy_china_strategy.config import SectorRotationConfig


class SectorStrengthStrategy(ChinaStrategyTemplate, RiskControlMixin):
    """板块强度轮动策略

    策略逻辑：
    1. 计算各板块相对强度 (板块涨幅/大盘涨幅)
    2. 选取强度最高的 N 个板块
    3. 每月轮动一次

    参数：
    - rotation_period: 轮动周期(交易日)
    - top_n: 选取板块数
    - momentum_days: 动量计算天数
    - min_strength: 最小强度阈值
    """

    parameters = [
        "rotation_period",
        "top_n",
        "momentum_days",
        "min_strength",
        "position_ratio",
    ]

    variables = [
        "current_sectors",
        "rotation_day",
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 策略参数
        self.rotation_period = setting.get("rotation_period", 20)  # 20交易日
        self.top_n = setting.get("top_n", 3)
        self.momentum_days = setting.get("momentum_days", 60)
        self.min_strength = setting.get("min_strength", 1.0)
        self.position_ratio = setting.get("position_ratio", 0.2)

        # 策略变量
        self.current_sectors: List[str] = []
        self.rotation_day = 0
        self.positions: Dict[str, int] = {}

        # 持仓管理
        self.position_manager = PositionManager()

        # 配置
        self.config = SectorRotationConfig()

    def on_init(self):
        """策略初始化"""
        self.write_log("板块强度轮动策略初始化")

    def on_start(self):
        """策略启动"""
        self.write_log("板块强度轮动策略启动")

    def on_bar(self, bar: BarData):
        """K线推送"""
        # 轮动周期判断
        if self.rotation_day >= self.rotation_period:
            self._rotate_sectors()
            self.rotation_day = 0
        else:
            self.rotation_day += 1

    def _calculate_all_sector_strength(self) -> List[SectorStrength]:
        """计算所有板块强度"""
        # 获取板块列表
        sector_list = self._get_sector_list()

        strengths = []
        for sector in sector_list:
            # 计算相对强度
            strength = self._calculate_sector_strength(sector)
            if strength:
                strengths.append(strength)

        return strengths

    def _calculate_sector_strength(self, sector: str) -> Optional[SectorStrength]:
        """计算单个板块强度

        Args:
            sector: 板块名称

        Returns:
            板块强度
        """
        # 获取板块指数数据
        bars = self._get_sector_bars(sector, self.momentum_days)
        if len(bars) < 5:
            return None

        # 计算动量
        momentum_5d = self._calculate_momentum(bars, 5)
        momentum_20d = self._calculate_momentum(bars, 20)
        momentum_60d = self._calculate_momentum(bars, 60)

        # 计算相对强度
        market_momentum = self._calculate_market_momentum(self.momentum_days)
        if market_momentum == 0:
            strength = 1.0
        else:
            strength = momentum_60d / market_momentum

        return SectorStrength(
            sector=sector,
            strength=strength,
            momentum_5d=momentum_5d,
            momentum_20d=momentum_20d,
            momentum_60d=momentum_60d,
        )

    def _calculate_momentum(self, bars: List[BarData], days: int) -> float:
        """计算动量

        Args:
            bars: K线数据
            days: 天数

        Returns:
            动量值
        """
        if len(bars) < days:
            return 0.0

        start_price = bars[-days].open_price
        end_price = bars[-1].close_price

        if start_price <= 0:
            return 0.0

        return (end_price - start_price) / start_price * 100

    def _calculate_market_momentum(self, days: int) -> float:
        """计算市场动量

        Args:
            days: 天数

        Returns:
            市场动量
        """
        # 使用沪深300指数作为市场基准
        bars = self._get_sector_bars("000300.SH", days)
        return self._calculate_momentum(bars, days)

    def _get_sector_list(self) -> List[str]:
        """获取板块列表"""
        # 简化实现
        return [
            "银行", "房地产", "医药生物", "电子", "计算机",
            "有色金属", "化工", "机械设备", "汽车", "电力设备"
        ]

    def _get_sector_bars(self, sector: str, days: int) -> List[BarData]:
        """获取板块K线数据"""
        if not self.data_service:
            return []

        # 简化实现
        return []

    def _rotate_sectors(self):
        """轮动板块"""
        # 计算各板块强度
        strengths = self._calculate_all_sector_strength()

        if not strengths:
            return

        # 排序选取top N
        sorted_sectors = sorted(
            strengths,
            key=lambda x: x.strength,
            reverse=True
        )

        # 过滤弱板块
        strong_sectors = [
            s for s in sorted_sectors
            if s.strength >= self.min_strength
        ][:self.top_n]

        # 记录新板块
        new_sectors = [s.sector for s in strong_sectors]

        # 轮出弱板块
        for sector in self.current_sectors:
            if sector not in new_sectors:
                self._close_sector_positions(sector)

        # 轮入强板块
        for sector in new_sectors:
            if sector not in self.current_sectors:
                self._open_sector_positions(sector)

        self.current_sectors = new_sectors

        self.write_log(f"板块轮动: {self.current_sectors}")

    def _open_sector_positions(self, sector: str):
        """开仓板块"""
        # 获取板块内股票
        stocks = self._get_sector_stocks(sector)
        if not stocks:
            return

        # 分配仓位
        position_per_stock = self.position_ratio / min(len(stocks), self.top_n)

        for symbol in stocks[:5]:  # 每个板块最多5只
            if symbol in self.positions:
                continue

            if not self.is_tradeable(symbol):
                continue

            price = self.get_current_price(symbol)
            if not price:
                continue

            # 计算仓位
            account = self.cta_engine.get_account() if self.cta_engine else None
            if account:
                risk_amount = account.available * position_per_stock
                size = self.calculate_position_size(price, risk_amount)
            else:
                size = 100

            if size <= 0:
                continue

            # 执行买入
            exchange = self._get_exchange_from_symbol(symbol)
            vt_symbol = f"{symbol}.{exchange.value}"

            if hasattr(self, "buy"):
                self.buy(price, size, vt_symbol)

            self.positions[symbol] = 0
            self.position_manager.add_position(
                symbol, size, price, datetime.now()
            )

    def _close_sector_positions(self, sector: str):
        """平仓板块"""
        # 获取板块内股票
        stocks = self._get_sector_stocks(sector)

        for symbol in stocks:
            if symbol in self.positions:
                self._execute_sell(symbol)

    def _get_sector_stocks(self, sector: str) -> List[str]:
        """获取板块内股票"""
        # 简化实现
        return []

    def _execute_sell(self, symbol: str):
        """执行卖出"""
        if symbol not in self.positions:
            return

        price = self.get_current_price(symbol)
        if not price:
            return

        position = self.position_manager.get_position(symbol)
        volume = position.get("volume", 0) if position else 0

        if volume <= 0:
            return

        exchange = self._get_exchange_from_symbol(symbol)
        vt_symbol = f"{symbol}.{exchange.value}"

        if hasattr(self, "sell"):
            self.sell(price, volume, vt_symbol)

        del self.positions[symbol]
        self.position_manager.remove_position(symbol)
