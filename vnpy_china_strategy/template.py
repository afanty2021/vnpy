"""
A股策略模板基类

继承自vnpy_ctastrategy的CtaTemplate，提供A股特色策略的通用功能。
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal

from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval

# 由于vnpy_ctastrategy可能是外部安装的，使用try-except处理
try:
    from vnpy_ctastrategy import CtaTemplate
except ImportError:
    # 如果未安装，提供基础实现
    CtaTemplate = object


class ChinaStrategyTemplate(CtaTemplate if CtaTemplate != object else object):
    """A股策略模板基类

    提供A股特色策略的通用功能：
    - 数据服务注入接口
    - K线数据获取
    - 当前价格获取
    - 仓位计算
    - 可交易性检查
    """

    # 策略参数列表
    parameters: List[str] = []

    # 策略变量列表
    variables: List[str] = []

    def __init__(
        self,
        cta_engine: Any,
        strategy_name: str,
        vt_symbol: str,
        setting: Dict[str, Any]
    ):
        """初始化策略模板

        Args:
            cta_engine: CTA引擎实例
            strategy_name: 策略名称
            vt_symbol: 合约代码
            setting: 策略配置参数
        """
        # 调用父类初始化
        if CtaTemplate != object and hasattr(super(), "__init__"):
            super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 保存CTA引擎引用
        self.cta_engine = cta_engine
        self.strategy_name = strategy_name
        self.vt_symbol = vt_symbol

        # 数据服务接口（由子类注入）
        self.data_service: Optional[Any] = None

        # 策略参数
        self.parameters = []
        self.variables = []

    def set_data_service(self, data_service: Any) -> None:
        """设置数据服务

        Args:
            data_service: 数据服务实例
        """
        self.data_service = data_service

    def get_bar_data(
        self,
        symbol: str,
        days: int,
        interval: Interval = Interval.DAILY
    ) -> List[BarData]:
        """获取K线数据

        Args:
            symbol: 股票代码
            days: 获取天数
            interval: K线周期

        Returns:
            K线数据列表
        """
        if self.data_service:
            end = datetime.now()
            start = end.replace(day=end.day - days)
            exchange = self._get_exchange_from_symbol(symbol)
            return self.data_service.get_bar_data(
                symbol, exchange, interval, start, end
            )
        return []

    def get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前价格

        Args:
            symbol: 股票代码

        Returns:
            当前价格，如果无法获取返回None
        """
        tick = self.get_tick(symbol)
        return tick.last_price if tick else None

    def calculate_position_size(
        self,
        price: float,
        risk_amount: float
    ) -> int:
        """计算仓位数量

        基于固定风险金额计算持仓手数。
        股票1手=100股。

        Args:
            price: 当前价格
            risk_amount: 风险金额

        Returns:
            持仓手数（整手）
        """
        if price <= 0:
            return 0
        # 固定风险金额/每手价值 = 持仓手数
        per_lot_value = price * 100  # 股票1手=100股
        size = int(risk_amount / per_lot_value)
        return max(1, size)  # 至少买1手

    def is_tradeable(self, symbol: str) -> bool:
        """检查是否可交易

        检查以下限制：
        - ST股票不可交易
        - 涨停板不可买入
        - 跌停板不可卖出

        Args:
            symbol: 股票代码

        Returns:
            是否可交易
        """
        # 检查ST股票
        if self.data_service:
            stock_info = self.data_service.get_stock_info(symbol)
            if stock_info and stock_info.get("is_st", False):
                self.write_log(f"跳过ST股票: {symbol}")
                return False

        # 检查涨跌停
        price = self.get_current_price(symbol)
        if price:
            tick = self.get_tick(symbol)
            if tick:
                # 涨停价 - 添加类型检查防止Mock对象比较
                limit_up = getattr(tick, 'limit_up', None)
                if limit_up is not None and isinstance(limit_up, (int, float)) and price >= limit_up:
                    self.write_log(f"跳过涨停股票: {symbol}")
                    return False
                # 跌停价 - 添加类型检查防止Mock对象比较
                limit_down = getattr(tick, 'limit_down', None)
                if limit_down is not None and isinstance(limit_down, (int, float)) and price <= limit_down:
                    self.write_log(f"跳过跌停股票: {symbol}")
                    return False
        return True

    def _get_exchange_from_symbol(self, symbol: str) -> Exchange:
        """从股票代码获取交易所

        Args:
            symbol: 股票代码

        Returns:
            交易所枚举
        """
        if symbol.startswith("6"):
            return Exchange.SSE  # 上海证券交易所
        elif symbol.startswith(("0", "3")):
            return Exchange.SZSE  # 深圳证券交易所
        else:
            return Exchange.SZSE  # 默认深圳

    def write_log(self, msg: str) -> None:
        """写日志

        Args:
            msg: 日志消息
        """
        if hasattr(self, "log_message"):
            self.log_message(msg)
        else:
            print(f"[{self.strategy_name}] {msg}")

    def get_tick(self, symbol: str) -> Optional[TickData]:
        """获取Tick数据

        Args:
            symbol: 股票代码

        Returns:
            Tick数据
        """
        # 从CTA引擎获取tick数据
        if self.cta_engine:
            vt_symbol = f"{symbol}.{self._get_exchange_from_symbol(symbol).value}"
            return self.cta_engine.get_tick(vt_symbol)
        return None


class ChinaStrategyBase:
    """A股策略基础类

    不依赖CtaTemplate的轻量级基础类，用于独立使用。
    """

    def __init__(self, strategy_name: str):
        """初始化基础类

        Args:
            strategy_name: 策略名称
        """
        self.strategy_name = strategy_name
        self.data_service: Optional[Any] = None
        self.positions: Dict[str, Dict] = {}

    def set_data_service(self, data_service: Any) -> None:
        """设置数据服务"""
        self.data_service = data_service

    def get_position(self, symbol: str) -> int:
        """获取持仓

        Args:
            symbol: 股票代码

        Returns:
            持仓数量
        """
        return self.positions.get(symbol, {}).get("volume", 0)

    def add_position(self, symbol: str, volume: int, price: float) -> None:
        """添加持仓

        Args:
            symbol: 股票代码
            volume: 持仓数量
            price: 持仓价格
        """
        self.positions[symbol] = {
            "volume": volume,
            "price": price,
            "datetime": datetime.now()
        }

    def remove_position(self, symbol: str) -> None:
        """移除持仓

        Args:
            symbol: 股票代码
        """
        if symbol in self.positions:
            del self.positions[symbol]
