"""
A股分析引擎
管理A股市场数据分析功能
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date
from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine
from vnpy.trader.object import TickData, BarData
from vnpy.trader.constant import Exchange

# 导入分析器
from .level2.analyzer import Level2Analyzer
from .money_flow.analyzer import MoneyFlowAnalyzer
from .technical.analyzer import TechnicalAnalyzer
from .auction.analyzer import AuctionAnalyzer
from .objects.types import TickFlowData

# 导入数据服务（用于获取历史资金流向数据）
try:
    from vnpy_china_data import get_data_service
    CHINA_DATA_AVAILABLE = True
except ImportError:
    CHINA_DATA_AVAILABLE = False


class ChinaAnalysisEngine(BaseEngine):
    """A股分析引擎

    提供A股市场特色分析功能：
    - Level-2行情分析
    - 资金流向分析
    - 技术指标增强
    - 集合竞价分析
    """

    engine_name: str = "ChinaAnalysisApp"

    def __init__(self, main_engine: Any, event_engine: EventEngine) -> None:
        """初始化引擎"""
        super().__init__(main_engine, event_engine, self.engine_name)

        # 分析器字典
        self.analyzers: Dict[str, Any] = {}

        # 内置分析器实例
        self.level2_analyzer: Optional[Level2Analyzer] = None
        self.money_flow_analyzer: Optional[MoneyFlowAnalyzer] = None
        self.technical_analyzer: Optional[TechnicalAnalyzer] = None
        self.auction_analyzer: Optional[AuctionAnalyzer] = None

        # 注册事件监听
        self.register_event()

    def init(self) -> None:
        """引擎初始化"""
        # 创建Level-2分析器
        self.level2_analyzer = Level2Analyzer()
        self.add_analyzer("level2", self.level2_analyzer)

        # 创建资金流向分析器
        self.money_flow_analyzer = MoneyFlowAnalyzer()
        self.add_analyzer("money_flow", self.money_flow_analyzer)

        # 创建技术指标分析器
        self.technical_analyzer = TechnicalAnalyzer()
        self.add_analyzer("technical", self.technical_analyzer)

        # 创建集合竞价分析器
        self.auction_analyzer = AuctionAnalyzer()
        self.add_analyzer("auction", self.auction_analyzer)

        self.write_log("A股分析引擎初始化完成")

    def get_level2_analysis(self, symbol: str) -> Dict[str, Any]:
        """获取Level-2分析结果

        Args:
            symbol: 股票代码

        Returns:
            Level-2分析结果字典
        """
        if not self.level2_analyzer:
            return {}
        return self.level2_analyzer.get_comprehensive_analysis(symbol)

    def get_money_flow_analysis(self, symbol: str) -> Dict[str, Any]:
        """获取资金流向分析结果

        Args:
            symbol: 股票代码

        Returns:
            资金流向分析结果字典
        """
        if not self.money_flow_analyzer:
            return {}
        return self.money_flow_analyzer.get_comprehensive_analysis(symbol)

    def get_technical_analysis(self, symbol: str, sector_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取技术指标分析结果

        Args:
            symbol: 股票代码
            sector_codes: 相关板块代码列表

        Returns:
            技术指标分析结果字典
        """
        if not self.technical_analyzer:
            return {}
        return self.technical_analyzer.get_comprehensive_analysis(symbol, sector_codes)

    def get_auction_analysis(self, symbol: str, auction_data: Dict[str, Any], market_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取集合竞价分析结果

        Args:
            symbol: 股票代码
            auction_data: 集合竞价数据
            market_data: 市场数据（可选）

        Returns:
            集合竞价分析结果字典
        """
        if not self.auction_analyzer:
            return {}
        return self.auction_analyzer.get_comprehensive_analysis(symbol, auction_data, market_data)

    def get_historical_money_flow(
        self,
        symbol: str,
        exchange: Exchange = Exchange.SZSE,
        trade_date: date = None,
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict[str, Any]]:
        """获取历史资金流向数据（从Tushare）

        Args:
            symbol: 股票代码
            exchange: 交易所
            trade_date: 单个交易日期
            start_date: 开始日期（与end_date配合使用）
            end_date: 结束日期（与start_date配合使用）

        Returns:
            资金流向数据列表
        """
        if not CHINA_DATA_AVAILABLE:
            self.write_log("警告: vnpy_china_data 模块不可用，无法获取历史资金流向数据")
            return []

        try:
            from vnpy_china_data.models import MoneyFlowData

            # 获取数据服务
            service = get_data_service()

            # 确保服务已连接
            if not service.connected:
                service.connect()

            # 获取资金流向数据
            moneyflow_list = service.get_moneyflow(
                symbol=symbol,
                exchange=exchange,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            # 转换为字典格式供UI使用
            result = []
            for mf in moneyflow_list:
                result.append({
                    "symbol": mf.symbol,
                    "name": mf.name,
                    "trade_date": mf.trade_date.isoformat(),
                    "close_price": mf.close_price,
                    "change_pct": mf.change_pct,
                    # 超大单
                    "super_large_buy": mf.super_large_buy,
                    "super_large_sell": mf.super_large_sell,
                    "super_large_net": mf.super_large_net,
                    "super_large_buy_amount": mf.super_large_buy_amount,
                    "super_large_sell_amount": mf.super_large_sell_amount,
                    "super_large_net_amount": mf.super_large_net_amount,
                    # 大单
                    "large_buy": mf.large_buy,
                    "large_sell": mf.large_sell,
                    "large_net": mf.large_net,
                    "large_buy_amount": mf.large_buy_amount,
                    "large_sell_amount": mf.large_sell_amount,
                    "large_net_amount": mf.large_net_amount,
                    # 中单
                    "medium_buy": mf.medium_buy,
                    "medium_sell": mf.medium_sell,
                    "medium_net": mf.medium_net,
                    "medium_buy_amount": mf.medium_buy_amount,
                    "medium_sell_amount": mf.medium_sell_amount,
                    "medium_net_amount": mf.medium_net_amount,
                    # 小单
                    "small_buy": mf.small_buy,
                    "small_sell": mf.small_sell,
                    "small_net": mf.small_net,
                    "small_buy_amount": mf.small_buy_amount,
                    "small_sell_amount": mf.small_sell_amount,
                    "small_net_amount": mf.small_net_amount,
                    # 汇总
                    "main_net_amount": mf.main_net_amount,
                    "total_net_amount": mf.total_net_amount,
                })

            return result

        except Exception as e:
            self.write_log(f"获取历史资金流向数据失败: {e}")
            return []

    def update_money_flow(self, symbol: str, tick_flows: List[TickFlowData]) -> Optional[Dict[str, Any]]:
        """更新资金流向数据

        Args:
            symbol: 股票代码
            tick_flows: 逐笔成交列表

        Returns:
            分析结果
        """
        if not self.money_flow_analyzer:
            return None
        result = self.money_flow_analyzer.analyze(symbol, tick_flows)
        return {
            "symbol": symbol,
            "datetime": datetime.now(),
            "main_inflow": result.main_inflow,
            "net_inflow": result.net_inflow,
            "super_large_inflow": result.super_large_inflow,
            "large_inflow": result.large_inflow,
            "medium_inflow": result.medium_inflow,
            "small_inflow": result.small_inflow
        }

    def register_event(self) -> None:
        """注册事件监听"""
        # 订阅Tick事件用于Level-2分析
        self.event_engine.register("tick", self.process_tick_event)

        # 订阅Bar事件用于技术分析
        self.event_engine.register("bar", self.process_bar_event)

    def process_tick_event(self, event: Event) -> None:
        """处理Tick行情事件"""
        tick: TickData = event.data
        # 分发给所有分析器
        for analyzer in self.analyzers.values():
            if hasattr(analyzer, "on_tick"):
                analyzer.on_tick(tick)

    def process_bar_event(self, event: Event) -> None:
        """处理K线行情事件"""
        bar: BarData = event.data
        # 分发给所有分析器
        for analyzer in self.analyzers.values():
            if hasattr(analyzer, "on_bar"):
                analyzer.on_bar(bar)

    def add_analyzer(self, name: str, analyzer: Any) -> None:
        """添加分析器"""
        self.analyzers[name] = analyzer
        self.write_log(f"分析器 {name} 已添加")

    def remove_analyzer(self, name: str) -> None:
        """移除分析器"""
        if name in self.analyzers:
            del self.analyzers[name]
            self.write_log(f"分析器 {name} 已移除")

    def get_analyzer(self, name: str) -> Optional[Any]:
        """获取分析器"""
        return self.analyzers.get(name)

    def get_all_analyzers(self) -> Dict[str, Any]:
        """获取所有分析器"""
        return self.analyzers.copy()


__all__ = ["ChinaAnalysisEngine"]
