"""
报表数据服务

封装数据源初始化、定时权益落库、行业采集，供 vnpy 主进程一键接入。

示例（vnpy 主进程启动后）：
    svc = ReportingDataService(main_engine=main_engine, config=global_config)
    svc.setup()                          # 初始化表
    svc.start_daily_equity("18:30")      # 每日 18:30 自动落库权益
    # 主进程退出时：svc.stop()
"""

from typing import Optional, Any
import logging
import os
from pathlib import Path

from .db import DataSourceDB
from .schema import init_schema
from .equity_collector import EquitySnapshotCollector
from .industry_collector import IndustryCollector
from .scheduler import DailyScheduler

logger = logging.getLogger(__name__)


class ReportingDataService:
    """报表数据服务（vnpy 主进程接入入口）"""

    def __init__(
        self,
        main_engine: Any,
        config: Optional[Any] = None,
        data_config: Optional[Any] = None,
        db: Optional[DataSourceDB] = None,
    ):
        """
        Args:
            main_engine: vnpy MainEngine
            config: vnpy_china_config.GlobalConfig（db 为 None 时必需，用于构造连接）
            data_config: vnpy_china_config.DataModuleConfig（含 tushare_token，
                collect_industry 默认读取）
            db: 已构造的 DataSourceDB（优先于 config）
        """
        self.main_engine = main_engine
        self.db = db if db is not None else DataSourceDB.from_global_config(config)
        self._data_config = data_config
        self.equity_collector = EquitySnapshotCollector(self.db, main_engine)
        self.industry_collector = IndustryCollector(self.db)
        self._scheduler: Optional[DailyScheduler] = None

    def setup(self) -> None:
        """初始化数据源表（幂等）"""
        init_schema(self.db)
        logger.info("ReportingDataService 初始化完成")

    def start_daily_equity(
        self, target_time: str = "18:30", skip_weekend: bool = True
    ) -> None:
        """启动每日定时权益落库

        Args:
            target_time: 触发时刻 "HH:MM"
            skip_weekend: 跳过周末（A股非交易日）
        """
        self._scheduler = DailyScheduler(
            target_time,
            callback=self.equity_collector.collect,
            skip_weekend=skip_weekend,
        )
        self._scheduler.start()

    def collect_industry(
        self,
        backend: str = "tushare",
        token: Optional[str] = None,
        sector_names: Optional[list] = None,
        sector_keywords: Optional[list] = None,
    ) -> int:
        """采集行业映射

        Args:
            backend: 'tushare'（默认，推荐，直接取 industry 字段）或
                     'qmt'（miniQMT 板块反查，精简版不可用）
            token: tushare token（backend='tushare' 时，None 读 TUSHARE_TOKEN）
            sector_names: backend='qmt' 时的显式行业板块名
            sector_keywords: backend='qmt' 时的板块名关键词

        Returns:
            落库映射条数
        """
        if backend == "tushare":
            # token 优先级：参数 > DataModuleConfig。> 环境变量
            token = (
                token
                or (self._data_config.tushare_token if self._data_config else "")
                or os.getenv("TUSHARE_TOKEN", "")
            )
            return self.industry_collector.collect_from_tushare(token)
        return self.industry_collector.collect(sector_names, sector_keywords)

    def stop(self) -> None:
        """停止定时任务（主进程退出时调用）"""
        if self._scheduler:
            self._scheduler.stop()

    def _resolve_tushare_token(self) -> str:
        """解析 tushare token

        优先级：环境变量 TUSHARE_TOKEN > data_development.yaml 嵌套结构。
        DataModuleConfig 因 yaml 嵌套与 flat 字段不匹配，此处绕过直接读 yaml。
        """
        # 环境变量
        token = os.getenv("TUSHARE_TOKEN", "")
        if token:
            return token
        # yaml 嵌套结构（data_development.yaml 的 tushare.token）
        try:
            import yaml
            yaml_path = (
                Path(__file__).resolve().parent.parent.parent
                / ".vntrader_china/config/data_development.yaml"
            )
            if yaml_path.exists():
                cfg = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
                token = cfg.get("tushare", {}).get("token", "")
                if token:
                    return token
        except Exception:
            pass
        return ""
