"""
A股风险管理器

整合 vnpy_riskmanager 和 A股规则引擎
"""

from typing import Optional

from vnpy_riskmanager.engine import RiskEngine
from vnpy_china_rules.engine import ChinaStockRulesEngine
from vnpy_china_rules.datasource import DataSourceManager


class AStockRiskManager:
    """A股风险管理器"""

    def __init__(self, main_engine, event_engine):
        self.main_engine = main_engine
        self.event_engine = event_engine

        # 初始化 vnpy_riskmanager
        self.risk_engine: Optional[RiskEngine] = None

        # 初始化 A股规则引擎
        self.china_rules_engine: Optional[ChinaStockRulesEngine] = None

    def initialize(self, qmt_gateway=None, tushare_token=None):
        """初始化风控系统"""
        # 1. 初始化数据源
        datasource_manager = DataSourceManager()

        if qmt_gateway:
            from vnpy_china_rules.datasource import QMTDataSource
            qmt_source = QMTDataSource(qmt_gateway)
            datasource_manager.register_source("qmt", qmt_source, primary=True)

        if tushare_token:
            from vnpy_china_rules.datasource import TushareDataSource
            tushare_source = TushareDataSource(tushare_token)
            datasource_manager.register_source("tushare", tushare_source)

        # 2. 初始化A股规则引擎
        self.china_rules_engine = ChinaStockRulesEngine(datasource_manager)

        # 3. 初始化vnpy_riskmanager
        self._init_risk_manager()

    def _init_risk_manager(self):
        """初始化风控引擎"""
        from vnpy_riskmanager import RiskManagerApp

        # 添加风控应用
        self.main_engine.add_app(RiskManagerApp)
        self.risk_engine = self.main_engine.get_engine(RiskEngine)

        # 注册自定义规则
        self._register_custom_rules()

    def _register_custom_rules(self):
        """注册自定义规则"""
        # 动态加载 rules/ 目录下的规则
        from pathlib import Path
        import importlib.util

        rules_path = Path(__file__).parent / "rules"
        for file in rules_path.glob("*_rule.py"):
            if file.name.startswith("_"):
                continue

            # 动态导入模块
            try:
                module_name = f"vnpy_china_rules.risk.rules.{file.stem}"
                spec = importlib.util.spec_from_file_location(module_name, file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.write_log(f"成功加载风控规则: {file.stem}")
            except Exception as e:
                self.write_log(f"加载风控规则失败 {file.stem}: {str(e)}")

    def get_risk_engine(self) -> RiskEngine:
        """获取风控引擎"""
        return self.risk_engine

    def get_china_rules_engine(self) -> ChinaStockRulesEngine:
        """获取A股规则引擎"""
        return self.china_rules_engine


def create_risk_manager(main_engine, event_engine, qmt_gateway=None, tushare_token=None):
    """
    便捷函数：创建并初始化A股风控管理器

    Args:
        main_engine: 主引擎
        event_engine: 事件引擎
        qmt_gateway: QMT网关实例（可选）
        tushare_token: Tushare token（可选）

    Returns:
        AStockRiskManager: 风控管理器实例
    """
    risk_manager = AStockRiskManager(main_engine, event_engine)
    risk_manager.initialize(qmt_gateway=qmt_gateway, tushare_token=tushare_token)
    return risk_manager
