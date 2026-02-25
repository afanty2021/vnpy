"""
A股策略GUI引擎
管理A股策略的GUI集成功能
"""

from typing import Dict, Any, Optional, List
from datetime import date
from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine


class ChinaStrategyGuiEngine(BaseEngine):
    """A股策略GUI引擎

    提供A股策略的GUI管理功能：
    - 策略生命周期管理
    - 龙虎榜数据查询
    - 北向资金数据查询
    - 板块轮动数据查询
    - 事件驱动数据查询
    - 可转债数据查询
    """

    engine_name: str = "ChinaStrategyApp"

    def __init__(self, main_engine: Any, event_engine: EventEngine) -> None:
        """初始化引擎"""
        super().__init__(main_engine, event_engine, self.engine_name)

        # 策略引擎引用
        self.strategy_engine: Optional[Any] = None

        # 数据服务引用
        self.data_service: Optional[Any] = None

        # 直接在__init__中初始化
        self._init_components()

    def _init_components(self) -> None:
        """初始化组件"""
        try:
            from .engine import ChinaStrategyEngine
            from .data_service import get_data_service

            # 初始化策略引擎
            self.strategy_engine = ChinaStrategyEngine(self.main_engine, self.event_engine)
            self.main_engine.write_log("A股策略引擎初始化成功", "ChinaStrategyApp")

            # 获取或创建数据服务单例
            self.data_service = get_data_service()
            self.main_engine.write_log("策略数据服务初始化成功", "ChinaStrategyApp")

        except ImportError as e:
            self.main_engine.write_log(f"警告：无法导入策略组件：{e}", "ChinaStrategyApp")
        except Exception as e:
            self.main_engine.write_log(f"组件初始化异常：{e}", "ChinaStrategyApp")

    def init(self) -> None:
        """引擎初始化（由VeighNa框架调用）"""
        # 组件已在__init__中初始化
        pass

    # ========== 策略管理方法 ==========

    def get_all_strategies(self) -> Dict[str, Any]:
        """获取所有策略

        Returns:
            策略字典 {strategy_name: strategy_object}
        """
        if not self.strategy_engine:
            self.main_engine.write_log("错误：策略引擎未初始化", "ChinaStrategyApp")
            return {}

        try:
            strategies = self.strategy_engine.get_all_strategies()
            self.main_engine.write_log(f"获取策略列表，共{len(strategies)}个", "ChinaStrategyApp")
            return strategies
        except Exception as e:
            self.main_engine.write_log(f"获取策略列表失败：{e}", "ChinaStrategyApp")
            return {}

    def start_strategy(self, strategy_name: str) -> bool:
        """启动策略

        Args:
            strategy_name: 策略名称

        Returns:
            是否启动成功
        """
        if not self.strategy_engine:
            self.main_engine.write_log("错误：策略引擎未初始化", "ChinaStrategyApp")
            return False

        try:
            self.main_engine.write_log(f"启动策略：{strategy_name}", "ChinaStrategyApp")
            result = self.strategy_engine.start_strategy(strategy_name)
            if result:
                self.main_engine.write_log(f"策略 {strategy_name} 启动成功", "ChinaStrategyApp")
            else:
                self.main_engine.write_log(f"策略 {strategy_name} 启动失败", "ChinaStrategyApp")
            return result
        except Exception as e:
            self.main_engine.write_log(f"启动策略失败：{e}", "ChinaStrategyApp")
            return False

    def stop_strategy(self, strategy_name: str) -> bool:
        """停止策略

        Args:
            strategy_name: 策略名称

        Returns:
            是否停止成功
        """
        if not self.strategy_engine:
            self.main_engine.write_log("错误：策略引擎未初始化", "ChinaStrategyApp")
            return False

        try:
            self.main_engine.write_log(f"停止策略：{strategy_name}", "ChinaStrategyApp")
            result = self.strategy_engine.stop_strategy(strategy_name)
            if result:
                self.main_engine.write_log(f"策略 {strategy_name} 停止成功", "ChinaStrategyApp")
            else:
                self.main_engine.write_log(f"策略 {strategy_name} 停止失败", "ChinaStrategyApp")
            return result
        except Exception as e:
            self.main_engine.write_log(f"停止策略失败：{e}", "ChinaStrategyApp")
            return False

    def get_strategy_status(self, strategy_name: str) -> Dict[str, Any]:
        """获取策略状态

        Args:
            strategy_name: 策略名称

        Returns:
            策略状态信息
        """
        if not self.strategy_engine:
            return {"status": "engine_not_initialized"}

        strategy = self.strategy_engine.get_strategy(strategy_name)
        if not strategy:
            return {"status": "not_found"}

        status = {
            "strategy_name": strategy_name,
            "active": getattr(strategy, "active", False),
            "trading": getattr(strategy, "trading", False),
        }

        # 获取策略参数
        if hasattr(strategy, "get_parameters"):
            try:
                status["parameters"] = strategy.get_parameters()
            except Exception:
                pass

        # 获取策略变量
        if hasattr(strategy, "get_variables"):
            try:
                status["variables"] = strategy.get_variables()
            except Exception:
                pass

        return status

    # ========== 龙虎榜数据方法 ==========

    def query_dragon_tiger(self, trade_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """查询龙虎榜数据

        Args:
            trade_date: 交易日期，默认为当天

        Returns:
            龙虎榜数据列表
        """
        if not self.data_service:
            self.main_engine.write_log("错误：数据服务未初始化", "ChinaStrategyApp")
            return []

        if trade_date is None:
            trade_date = date.today()

        try:
            self.main_engine.write_log(f"查询龙虎榜数据：{trade_date}", "ChinaStrategyApp")
            data = self.data_service.get_dragon_tiger_data(trade_date)
            self.main_engine.write_log(f"查询完成，共{len(data)}条记录", "ChinaStrategyApp")
            return data
        except Exception as e:
            self.main_engine.write_log(f"查询龙虎榜数据失败：{e}", "ChinaStrategyApp")
            return []

    # ========== 北向资金数据方法 ==========

    def query_northbound_flow(self, trade_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        """查询北向资金流向

        Args:
            trade_date: 交易日期，默认为当天

        Returns:
            北向资金流向数据
        """
        if not self.data_service:
            self.main_engine.write_log("错误：数据服务未初始化", "ChinaStrategyApp")
            return None

        if trade_date is None:
            trade_date = date.today()

        try:
            self.main_engine.write_log(f"查询北向资金流向：{trade_date}", "ChinaStrategyApp")
            data = self.data_service.get_northbound_flow(trade_date)
            if data:
                net_inflow = data.get("net_inflow", 0)
                self.main_engine.write_log(f"查询完成，净流入：{net_inflow / 100000000:.2f}亿元", "ChinaStrategyApp")
            else:
                self.main_engine.write_log("未查询到北向资金数据", "ChinaStrategyApp")
            return data
        except Exception as e:
            self.main_engine.write_log(f"查询北向资金流向失败：{e}", "ChinaStrategyApp")
            return None

    def query_stock_holding(self, symbol: str, trade_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        """查询持股变化

        Args:
            symbol: 股票代码
            trade_date: 交易日期，默认为当天

        Returns:
            持股变化数据
        """
        if not self.data_service:
            self.main_engine.write_log("错误：数据服务未初始化", "ChinaStrategyApp")
            return None

        if trade_date is None:
            trade_date = date.today()

        try:
            self.main_engine.write_log(f"查询持股变化：{symbol} @ {trade_date}", "ChinaStrategyApp")
            data = self.data_service.get_stock_holding(symbol, trade_date)
            return data
        except Exception as e:
            self.main_engine.write_log(f"查询持股变化失败：{e}", "ChinaStrategyApp")
            return None

    def query_sector_preference(self, trade_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """查询板块偏好

        Args:
            trade_date: 交易日期，默认为当天

        Returns:
            板块偏好数据列表
        """
        if not self.data_service:
            self.main_engine.write_log("错误：数据服务未初始化", "ChinaStrategyApp")
            return []

        if trade_date is None:
            trade_date = date.today()

        try:
            self.main_engine.write_log(f"查询板块偏好：{trade_date}", "ChinaStrategyApp")
            # 获取主要板块的数据
            sectors = ["半导体", "新能源", "医药生物", "食品饮料", "计算机"]
            result = []
            for sector in sectors:
                data = self.data_service.get_sector_data(sector, trade_date)
                if data:
                    result.append(data)
            self.main_engine.write_log(f"查询完成，共{len(result)}个板块", "ChinaStrategyApp")
            return result
        except Exception as e:
            self.main_engine.write_log(f"查询板块偏好失败：{e}", "ChinaStrategyApp")
            return []

    # ========== 板块轮动数据方法 ==========

    def query_sector_strength(self, sector: str, trade_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        """查询板块强度

        Args:
            sector: 板块名称
            trade_date: 交易日期，默认为当天

        Returns:
            板块强度数据
        """
        if not self.data_service:
            self.main_engine.write_log("错误：数据服务未初始化", "ChinaStrategyApp")
            return None

        if trade_date is None:
            trade_date = date.today()

        try:
            self.main_engine.write_log(f"查询板块强度：{sector} @ {trade_date}", "ChinaStrategyApp")
            data = self.data_service.get_sector_data(sector, trade_date)
            return data
        except Exception as e:
            self.main_engine.write_log(f"查询板块强度失败：{e}", "ChinaStrategyApp")
            return None

    def query_rotation_signal(self, trade_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """查询轮动信号

        Args:
            trade_date: 交易日期，默认为当天

        Returns:
            轮动信号列表
        """
        if not self.data_service:
            self.main_engine.write_log("错误：数据服务未初始化", "ChinaStrategyApp")
            return []

        if trade_date is None:
            trade_date = date.today()

        try:
            self.main_engine.write_log(f"查询轮动信号：{trade_date}", "ChinaStrategyApp")
            # 获取主要板块并计算强度排序
            sectors = ["半导体", "新能源", "医药生物", "食品饮料", "计算机"]
            result = []
            for sector in sectors:
                data = self.data_service.get_sector_data(sector, trade_date)
                if data:
                    result.append({
                        "sector": sector,
                        "change_pct": data.get("change_pct", 0),
                        "volume": data.get("volume", 0),
                        "signal": "buy" if data.get("change_pct", 0) > 2 else "hold"
                    })
            # 按涨跌幅排序
            result.sort(key=lambda x: x["change_pct"], reverse=True)
            self.main_engine.write_log(f"查询完成，共{len(result)}个信号", "ChinaStrategyApp")
            return result
        except Exception as e:
            self.main_engine.write_log(f"查询轮动信号失败：{e}", "ChinaStrategyApp")
            return []

    # ========== 事件驱动数据方法 ==========

    def query_earnings_forecast(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """查询业绩预告

        Args:
            symbol: 股票代码
            days: 查询天数

        Returns:
            业绩预告列表
        """
        if not self.data_service:
            self.main_engine.write_log("错误：数据服务未初始化", "ChinaStrategyApp")
            return []

        try:
            self.main_engine.write_log(f"查询业绩预告：{symbol} 最近{days}天", "ChinaStrategyApp")
            data = self.data_service.get_earnings_forecast(symbol, days)
            self.main_engine.write_log(f"查询完成，共{len(data)}条记录", "ChinaStrategyApp")
            return data
        except Exception as e:
            self.main_engine.write_log(f"查询业绩预告失败：{e}", "ChinaStrategyApp")
            return []

    def query_policy_events(self, days: int = 30) -> List[Dict[str, Any]]:
        """查询政策事件

        Args:
            days: 查询天数

        Returns:
            政策事件列表
        """
        # 简化实现，返回空列表
        self.main_engine.write_log(f"查询政策事件：最近{days}天", "ChinaStrategyApp")
        return []

    # ========== 可转债数据方法 ==========

    def query_convertible_bonds(self) -> List[Dict[str, Any]]:
        """查询可转债列表

        Returns:
            可转债列表
        """
        if not self.data_service:
            self.main_engine.write_log("错误：数据服务未初始化", "ChinaStrategyApp")
            return []

        try:
            self.main_engine.write_log("查询可转债列表", "ChinaStrategyApp")
            data = self.data_service.get_convertible_bonds()
            self.main_engine.write_log(f"查询完成，共{len(data)}只可转债", "ChinaStrategyApp")
            return data
        except Exception as e:
            self.main_engine.write_log(f"查询可转债列表失败：{e}", "ChinaStrategyApp")
            return []

    # ========== 服务状态方法 ==========

    def get_engine_status(self) -> Dict[str, Any]:
        """获取引擎状态

        Returns:
            引擎状态信息
        """
        status = {
            "strategy_engine_loaded": self.strategy_engine is not None,
            "data_service_loaded": self.data_service is not None,
        }

        if self.strategy_engine:
            status["strategy_count"] = len(self.strategy_engine.get_all_strategies())

        return status


__all__ = ["ChinaStrategyGuiEngine"]
