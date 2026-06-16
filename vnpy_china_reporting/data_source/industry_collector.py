"""
行业映射采集器

从 miniQMT（xtquant）采集股票→行业映射并落库。miniQMT 的 get_instrument_detail
不含行业字段，行业需通过板块接口反查：download_sector_data → get_sector_list →
get_stock_list_in_sector。

download_sector_data 下载全市场板块耗时较长（数分钟），故 collect() 设计为
一次性全量刷新，适合每日/每周定时调用，不建议实时调用。
"""

from typing import Optional, List
import logging

from .db import DataSourceDB
from .industry_store import IndustryStore

logger = logging.getLogger(__name__)

# 默认行业板块名关键词（miniQMT 板块命名因数据源而异，可按实际调整）
DEFAULT_INDUSTRY_KEYWORDS = ["行业", "申万", "SW", "中信"]


class IndustryCollector:
    """采集 miniQMT 行业映射并落库"""

    def __init__(self, db: DataSourceDB):
        """
        Args:
            db: 数据源连接
        """
        self.db = db
        self.store = IndustryStore(db)

    def discover_sectors(self) -> List[str]:
        """探测 miniQMT 全部板块（辅助确认行业板块结构）

        download_sector_data 后返回所有板块名，便于人工识别哪些是行业板块，
        再将其名称传给 collect(sector_names=...)。

        Returns:
            板块名列表
        """
        xt = self._import_xtdata()
        logger.info("下载板块数据（首次可能耗时数分钟）...")
        xt.download_sector_data()
        sectors = xt.get_sector_list() or []
        sectors = list(sectors)
        logger.info("共 %d 个板块", len(sectors))
        return sectors

    def collect(
        self,
        sector_names: Optional[List[str]] = None,
        sector_keywords: Optional[List[str]] = None,
    ) -> int:
        """采集行业映射并落库

        Args:
            sector_names: 显式行业板块名列表（优先使用，命中即作为该股票行业）
            sector_keywords: 行业板块名关键词过滤（sector_names 为 None 时生效），
                默认 DEFAULT_INDUSTRY_KEYWORDS

        Returns:
            落库映射条数
        """
        xt = self._import_xtdata()

        logger.info("下载板块数据（首次可能耗时数分钟）...")
        xt.download_sector_data()

        all_sectors = xt.get_sector_list() or []
        all_sectors = list(all_sectors)

        if sector_names:
            industry_sectors = [s for s in all_sectors if s in sector_names]
        else:
            kws = sector_keywords or DEFAULT_INDUSTRY_KEYWORDS
            industry_sectors = [s for s in all_sectors if any(k in s for k in kws)]

        logger.info("识别行业板块 %d 个（共 %d 板块）", len(industry_sectors), len(all_sectors))

        if not industry_sectors:
            logger.warning(
                "未识别到行业板块。请先调用 discover_sectors() 查看实际板块名，"
                "再通过 sector_names 或 sector_keywords 指定。"
            )
            return 0

        records = []  # (symbol, exchange, industry)
        for sector in industry_sectors:
            members = xt.get_stock_list_in_sector(sector) or []
            if not members:
                continue
            # 行业名取板块名末段（板块可能含路径前缀如 "沪深A股/行业/银行"）
            industry_name = sector.rsplit("/", 1)[-1].strip()
            for vt_symbol in members:
                symbol, exchange = self._parse_vt_symbol(vt_symbol)
                records.append((symbol, exchange, industry_name))

        if records:
            self.store.batch_upsert(records)
        logger.info("行业映射采集完成: %d 条（来自 %d 个行业板块）",
                    len(records), len(industry_sectors))
        return len(records)

    def collect_from_tushare(self, token: Optional[str] = None) -> int:
        """从 tushare stock_basic 采集行业映射并落库（推荐）

        tushare stock_basic 直接返回每只股票的 industry 字段，是 miniQMT 板块
        反查的可靠替代（miniQMT 精简版不支持板块下载）。

        Args:
            token: tushare token；为 None 时读环境变量 TUSHARE_TOKEN

        Returns:
            落库映射条数
        """
        import os
        token = token or os.getenv("TUSHARE_TOKEN", "")
        if not token:
            logger.error("未提供 tushare token（参数或 TUSHARE_TOKEN 环境变量）")
            return 0

        try:
            import tushare as ts
        except ImportError:
            logger.error("tushare 未安装，请 pip install tushare")
            return 0

        try:
            pro = ts.pro_api(token)
            df = pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,symbol,name,industry",
            )
        except Exception as e:
            logger.error("tushare stock_basic 调用失败: %s", e)
            return 0

        if df is None or df.empty:
            logger.warning("tushare stock_basic 返回空")
            return 0

        records = []
        for _, row in df.iterrows():
            symbol = str(row.get("symbol", "")).strip()
            industry = str(row.get("industry", "")).strip()
            if not symbol or not industry:
                continue
            # ts_code 形如 000001.SZ，取后缀作交易所
            ts_code = str(row.get("ts_code", ""))
            exchange = ts_code.split(".")[-1] if "." in ts_code else ""
            records.append((symbol, exchange, industry))

        if records:
            self.store.batch_upsert(records)
        logger.info("tushare 行业映射采集完成: %d 条", len(records))
        return len(records)

    @staticmethod
    def _import_xtdata():
        """延迟导入 xtdata（避免模块加载期依赖 xtquant）"""
        try:
            import xtquant.xtdata as xt
            xt.enable_hello = False
            return xt
        except ImportError as e:
            raise ImportError(
                "xtquant 未安装，无法采集行业映射。需 miniQMT 环境与 xtquant。"
            ) from e

    @staticmethod
    def _parse_vt_symbol(vt_symbol: str):
        """'000001.SZ' → ('000001', 'SZ')"""
        if "." in vt_symbol:
            sym, exch = vt_symbol.rsplit(".", 1)
            return sym, exch
        return vt_symbol, ""
