"""数据管理模块

提供数据预加载和定时更新功能。

本模块定义两个核心组件：
- DataPreloader：批量预加载历史数据（K线、龙虎榜、北向资金、板块）
- DataUpdateScheduler：按配置时间定时从数据服务获取最新数据

两个组件均与 vnpy_china_data.ChinaDataService 解耦，接受任意实现了
对应方法的数据服务实例（测试中可使用 Mock）。
"""
import threading
import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Callable, Optional, List, Dict, Any

from vnpy.trader.constant import Exchange, Interval

logger = logging.getLogger(__name__)

# 检测 vnpy_china_data 是否可用（影响 create_data_manager 的行为日志）
try:
    from vnpy_china_data import ChinaDataService  # noqa: F401
    CHINA_DATA_AVAILABLE = True
except ImportError:
    CHINA_DATA_AVAILABLE = False

# 事件定义
EVENT_DATA_PRELOAD_START = "eDataPreloadStart"
EVENT_DATA_PRELOAD_COMPLETE = "eDataPreloadComplete"
EVENT_DATA_UPDATE_START = "eDataUpdateStart"
EVENT_DATA_UPDATE_COMPLETE = "eDataUpdateComplete"


@dataclass
class PreloadConfig:
    """数据预加载配置

    用于 DataPreloader.preload 方法，描述预加载的日期范围、品种范围及各数据类别开关。
    """
    # 日期范围（默认近3年）
    start_date: date = field(default_factory=lambda: date.today() - timedelta(days=365 * 3))
    end_date: date = field(default_factory=date.today)
    # 股票代码列表，None 表示使用默认成分股/指数
    symbols: Optional[List[str]] = None
    # 各数据类别开关
    enable_bar_data: bool = True
    enable_dragon_tiger: bool = True
    enable_northbound: bool = True
    enable_sector: bool = True
    # K线周期（ChinaDataService.get_bar_data 必填参数），默认日线
    interval: Interval = Interval.DAILY
    # 并发加载（保留字段，当前实现为顺序加载）
    concurrent: bool = True
    # 批量加载大小（保留字段，用于未来分批加载）
    batch_size: int = 50


@dataclass
class UpdateConfig:
    """数据更新配置

    用于 DataUpdateScheduler，描述每日定时更新的时间、星期及回补天数。
    """
    # 每日更新时间，HH:MM 格式
    update_time: str = "15:30"
    # 需要更新的星期（0=周一, 6=周日），默认工作日周二至周六（适配 A 股收盘后更新）
    update_weekdays: List[int] = field(default_factory=lambda: [1, 2, 3, 4, 5])
    # 向前回补天数（用于补齐缺失的交易日数据）
    lookback_days: int = 5
    # 各数据类别开关
    enable_bar: bool = True
    enable_dragon_tiger: bool = True
    enable_northbound: bool = True
    enable_sector: bool = True
    # K线更新品种列表：仅 enable_bar=True 且本字段非空时才执行 bar 更新；
    # None（默认）表示不主动触发 bar 更新，避免无目的的全市场扫描。
    # 此字段用于消除 enable_bar 契约不一致（之前定义但 trigger_update_now 未处理）。
    bar_symbols: Optional[List[str]] = None
    # K线周期（与 PreloadConfig.interval 含义一致，默认日线）
    bar_interval: Interval = Interval.DAILY


def _safe_count(obj: Any) -> int:
    """安全计算对象包含的数据条数

    兼容 None / list / 单个对象 / DataFrame 等返回值：
    - None 计 0
    - 有 __len__ 的对象返回其长度
    - 其他单个对象计 1
    """
    if obj is None:
        return 0
    try:
        return len(obj)
    except TypeError:
        return 1


def _resolve_exchange(symbol: str) -> Exchange:
    """根据股票代码推断交易所

    A 股 symbol 跨交易所（SZSE/SSE），不能在 PreloadConfig 里固定单一 exchange，
    因此按 symbol 后缀/前缀推断：
    - 后缀 .SZ / .SZSE → 深交所 SZSE
    - 后缀 .SH / .SSE → 上交所 SSE
    - 无后缀时按代码前缀：6 开头（含 688 科创板）→ SSE，其余 → SZSE
    """
    s = symbol.upper()
    if s.endswith(".SZ") or s.endswith(".SZSE"):
        return Exchange.SZSE
    if s.endswith(".SH") or s.endswith(".SSE"):
        return Exchange.SSE
    # 无后缀：按代码前缀推断（6/9/11/B 上交所，其余深交所）
    # 6xxxxx 主板、688xxx 科创板 → 上交所
    code = s.replace(".SZ", "").replace(".SH", "").replace(".SZSE", "").replace(".SSE", "")
    if code.startswith("6"):
        return Exchange.SSE
    return Exchange.SZSE


class DataPreloader:
    """数据预加载器

    负责从数据服务批量加载历史数据。
    线程安全：通过 _lock 保护 _is_preloading 标志和进度状态。
    """

    def __init__(
        self,
        data_service: Optional[Any] = None,
        event_engine: Optional[Any] = None
    ):
        """初始化预加载器

        Args:
            data_service: A股数据服务实例（ChinaDataService 或 Mock），
                         需实现 get_bar_data/get_dragon_tiger_data/
                         get_northbound_flow/get_sector_list 方法
            event_engine: 事件引擎实例，用于发送预加载开始/完成事件
        """
        self.data_service = data_service
        self.event_engine = event_engine

        self._lock = threading.Lock()
        self._is_preloading: bool = False
        self._progress_total: int = 0
        self._progress_completed: int = 0
        self._stats: Dict[str, int] = {}

    def preload(
        self,
        config: PreloadConfig,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, int]:
        """执行数据预加载

        按 config 中启用的数据类别顺序调用 data_service 对应方法，累加返回数据条数，
        并通过 progress_callback 报告进度。

        Args:
            config: 预加载配置
            progress_callback: 进度回调，签名为 (completed, total, task)

        Returns:
            统计字典，key 为数据类别（如 "bar"/"dragon_tiger"/"northbound"/"sector"），
            value 为对应数据条数。无 data_service 时返回空字典 {}。
        """
        # 无数据服务：直接返回空统计（test_preload_without_data_service 期望 {}）
        if not self.data_service:
            logger.warning("数据服务未初始化，预加载返回空统计")
            return {}

        # 进入预加载状态
        with self._lock:
            self._is_preloading = True
            self._stats = {}
            self._progress_completed = 0

        # 计算总任务数（仅统计已启用的数据类别）
        total = 0
        if config.enable_bar_data:
            total += 1
        if config.enable_dragon_tiger:
            total += 1
        if config.enable_northbound:
            total += 1
        if config.enable_sector:
            total += 1

        with self._lock:
            self._progress_total = total

        # 发送预加载开始事件
        self._put_event(EVENT_DATA_PRELOAD_START, {
            "start_date": config.start_date,
            "end_date": config.end_date,
            "total": total,
        })

        # success 标志用于在 finally 中区分"正常完成"与"异常退出"，
        # 默认 False，仅在 try 块正常执行到末尾（即将 return）时置 True。
        # 消费者可在 COMPLETE 事件 data["success"] 据此判断是否需要重试。
        success = False

        try:
            logger.info(
                f"开始预加载数据: {config.start_date} 至 {config.end_date}, "
                f"共 {total} 个任务"
            )

            # K线数据（按品种循环，需要 exchange/interval/start/end）
            if config.enable_bar_data:
                self._preload_bars(config, progress_callback, total)

            # 龙虎榜数据（按日期范围逐日获取，此处简化为 end_date 单日快照）
            if config.enable_dragon_tiger:
                count = self._preload_dragon_tiger(config)
                with self._lock:
                    self._stats["dragon_tiger"] = count
                    self._progress_completed += 1
                    completed = self._progress_completed
                logger.info(f"龙虎榜数据加载完成: {count} 条")
                if progress_callback:
                    progress_callback(completed, total, "龙虎榜数据")

            # 北向资金数据
            if config.enable_northbound:
                count = self._preload_northbound(config)
                with self._lock:
                    self._stats["northbound"] = count
                    self._progress_completed += 1
                    completed = self._progress_completed
                logger.info(f"北向资金数据加载完成: {count} 条")
                if progress_callback:
                    progress_callback(completed, total, "北向资金数据")

            # 板块数据
            if config.enable_sector:
                count = self._preload_sector()
                with self._lock:
                    self._stats["sector"] = count
                    self._progress_completed += 1
                    completed = self._progress_completed
                logger.info(f"板块数据加载完成: {count} 条")
                if progress_callback:
                    progress_callback(completed, total, "板块数据")

            logger.info(f"数据预加载完成: {self._stats}")
            # 全部分支正常执行完毕，标记成功（finally 据此发 success=True）
            success = True
            return dict(self._stats)

        except Exception as e:
            # 异常路径：success 保持 False，事件消费者可据此重试
            logger.error(f"数据预加载失败: {e}")
            return dict(self._stats)

        finally:
            with self._lock:
                self._is_preloading = False
            # 发送预加载完成事件，data 中携带 success 字段
            # success=True 表示全部数据类别正常加载完成，
            # success=False 表示中途异常退出（stats 可能部分填充）
            event_data = dict(self._stats)
            event_data["success"] = success
            self._put_event(EVENT_DATA_PRELOAD_COMPLETE, event_data)

    def _preload_bars(
        self,
        config: PreloadConfig,
        progress_callback: Optional[Callable[[int, int, str], None]],
        total: int
    ) -> None:
        """预加载K线数据

        遍历 config.symbols 调用 data_service.get_bar_data，累加条数到 _stats["bar"]。
        若未指定 symbols 则跳过品种级加载（避免无目的的全市场扫描）。
        """
        symbols = config.symbols or []
        total_bars = 0

        # 转换为 datetime 范围
        start_dt = datetime.combine(config.start_date, datetime.min.time())
        end_dt = datetime.combine(config.end_date, datetime.max.time())

        for symbol in symbols:
            try:
                # ChinaDataService.get_bar_data 真实签名：
                #   get_bar_data(symbol, exchange, interval, start, end) -> List[BarData]
                # exchange 按 symbol 推断（symbols 可能跨交易所），
                # interval 由 PreloadConfig.interval 指定（默认 DAILY）
                exchange = _resolve_exchange(symbol)
                interval = config.interval
                bars = self.data_service.get_bar_data(symbol, exchange, interval, start_dt, end_dt)
                total_bars += _safe_count(bars)
            except Exception as e:
                logger.warning(f"加载 {symbol} K线数据失败: {e}")

        with self._lock:
            self._stats["bar"] = total_bars
            self._progress_completed += 1
            completed = self._progress_completed

        logger.info(f"K线数据加载完成: {total_bars} 条")
        if progress_callback:
            progress_callback(completed, total, "K线数据")

    def _preload_dragon_tiger(self, config: PreloadConfig) -> int:
        """预加载龙虎榜数据（end_date 当日快照）"""
        try:
            data = self.data_service.get_dragon_tiger_data(config.end_date)
            return _safe_count(data)
        except Exception as e:
            logger.warning(f"加载龙虎榜数据失败: {e}")
            return 0

    def _preload_northbound(self, config: PreloadConfig) -> int:
        """预加载北向资金数据（end_date 当日快照）

        Note: get_northbound_flow 可能返回单个对象（非 list），_safe_count 兼容处理。
        """
        try:
            data = self.data_service.get_northbound_flow(config.end_date)
            return _safe_count(data)
        except Exception as e:
            logger.warning(f"加载北向资金数据失败: {e}")
            return 0

    def _preload_sector(self) -> int:
        """预加载板块列表"""
        try:
            data = self.data_service.get_sector_list()
            return _safe_count(data)
        except Exception as e:
            logger.warning(f"加载板块数据失败: {e}")
            return 0

    def _put_event(self, event_type: str, data: Any) -> None:
        """发送事件到事件引擎

        event_engine 可能为 None 或 Mock，统一容错处理。
        """
        if not self.event_engine:
            return
        try:
            # 兼容 vnpy.event.EventEngine.put(Event) 与 Mock.put
            from vnpy.event import Event
            self.event_engine.put(Event(event_type, data))
        except ImportError:
            # 测试环境或 vnpy 不可用时，直接传 (type, data) 元组
            try:
                self.event_engine.put((event_type, data))
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"发送事件 {event_type} 失败: {e}")

    def is_preloading(self) -> bool:
        """是否正在预加载"""
        with self._lock:
            return self._is_preloading

    def get_preload_progress(self) -> Dict[str, Any]:
        """获取预加载进度

        Returns:
            {
                "is_preloading": bool,
                "progress": {"total": int, "completed": int},
                "stats": Dict[str, int]
            }
        """
        with self._lock:
            return {
                "is_preloading": self._is_preloading,
                "progress": {
                    "total": self._progress_total,
                    "completed": self._progress_completed,
                },
                "stats": dict(self._stats),
            }


class DataUpdateScheduler:
    """数据更新调度器

    负责按配置时间定时从数据服务获取最新数据。
    当前实现为同步逻辑（不依赖后台线程），start/trigger_update_now 可在
    测试与生产中安全调用。
    """

    def __init__(
        self,
        data_service: Optional[Any] = None,
        event_engine: Optional[Any] = None
    ):
        """初始化调度器

        Args:
            data_service: A股数据服务实例
            event_engine: 事件引擎实例
        """
        self.data_service = data_service
        self.event_engine = event_engine

        # 默认配置，使 get_config() 立即可用
        self.config: UpdateConfig = UpdateConfig()

        # 调度器运行状态
        self._running: bool = False
        self._lock = threading.Lock()

        # 更新统计
        self._stats: Dict[str, Any] = {
            "last_update_time": None,
            "total_updates": 0,
        }

    def is_running(self) -> bool:
        """调度器是否在运行"""
        with self._lock:
            return self._running

    def start(self) -> bool:
        """启动调度器

        Returns:
            是否成功启动。无 data_service 时返回 False。
        """
        if not self.data_service:
            logger.warning("数据服务未初始化，调度器启动失败")
            return False

        with self._lock:
            if self._running:
                logger.info("调度器已在运行")
                return True
            self._running = True

        logger.info(
            f"数据更新调度器已启动，更新时间: {self.config.update_time}, "
            f"星期: {self.config.update_weekdays}"
        )
        return True

    def stop(self) -> None:
        """停止调度器"""
        with self._lock:
            self._running = False
        logger.info("数据更新调度器已停止")

    def trigger_update_now(self) -> bool:
        """立即触发一次数据更新

        Returns:
            是否成功触发并完成更新。
        """
        if not self.data_service:
            logger.warning("数据服务未初始化，无法触发更新")
            return False

        # 发送更新开始事件
        self._put_event(EVENT_DATA_UPDATE_START, {"time": datetime.now()})

        try:
            logger.info("开始执行数据更新")
            end_date = date.today()
            start_date = end_date - timedelta(days=self.config.lookback_days)

            update_stats: Dict[str, int] = {}

            if self.config.enable_dragon_tiger:
                try:
                    data = self.data_service.get_dragon_tiger_data(end_date)
                    update_stats["dragon_tiger"] = _safe_count(data)
                except Exception as e:
                    logger.warning(f"更新龙虎榜数据失败: {e}")

            if self.config.enable_northbound:
                try:
                    data = self.data_service.get_northbound_flow(end_date)
                    update_stats["northbound"] = _safe_count(data)
                except Exception as e:
                    logger.warning(f"更新北向资金数据失败: {e}")

            if self.config.enable_sector:
                try:
                    data = self.data_service.get_sector_list()
                    update_stats["sector"] = _safe_count(data)
                except Exception as e:
                    logger.warning(f"更新板块数据失败: {e}")

            # K线数据：仅当显式配置 bar_symbols 时才更新，
            # 否则跳过（避免无目的的全市场扫描触发限流）
            if self.config.enable_bar:
                bar_symbols = self.config.bar_symbols or []
                if bar_symbols:
                    try:
                        interval = self.config.bar_interval
                        start_dt = datetime.combine(start_date, datetime.min.time())
                        end_dt = datetime.combine(end_date, datetime.max.time())
                        bar_count = 0
                        for symbol in bar_symbols:
                            try:
                                exchange = _resolve_exchange(symbol)
                                bars = self.data_service.get_bar_data(
                                    symbol, exchange, interval, start_dt, end_dt
                                )
                                bar_count += _safe_count(bars)
                            except Exception as e:
                                logger.warning(f"更新 {symbol} K线数据失败: {e}")
                        update_stats["bar"] = bar_count
                    except Exception as e:
                        logger.warning(f"更新K线数据失败: {e}")
                else:
                    logger.debug(
                        "enable_bar=True 但未配置 bar_symbols，跳过K线更新"
                    )

            # 更新统计
            with self._lock:
                self._stats["last_update_time"] = datetime.now()
                self._stats["total_updates"] = self._stats.get("total_updates", 0) + 1

            logger.info(f"数据更新完成: {update_stats}")

            # 发送更新完成事件
            self._put_event(EVENT_DATA_UPDATE_COMPLETE, update_stats)

            return True

        except Exception as e:
            logger.error(f"数据更新失败: {e}")
            return False

    def update_config(self, new_config: UpdateConfig) -> None:
        """更新调度器配置"""
        with self._lock:
            self.config = new_config
        logger.info(
            f"调度器配置已更新: 时间={new_config.update_time}, "
            f"星期={new_config.update_weekdays}, 回补={new_config.lookback_days}天"
        )

    def get_config(self) -> UpdateConfig:
        """获取当前配置"""
        with self._lock:
            return self.config

    def get_stats(self) -> Dict[str, Any]:
        """获取更新统计

        Returns:
            {"last_update_time": Optional[datetime], "total_updates": int}
        """
        with self._lock:
            return dict(self._stats)

    def _should_update_today(self) -> bool:
        """判断今天是否需要更新

        基于 self.config.update_weekdays 判断，weekday() 周一=0。
        """
        today_weekday = datetime.now().weekday()
        return today_weekday in (self.config.update_weekdays or [])

    def _put_event(self, event_type: str, data: Any) -> None:
        """发送事件到事件引擎"""
        if not self.event_engine:
            return
        try:
            from vnpy.event import Event
            self.event_engine.put(Event(event_type, data))
        except ImportError:
            try:
                self.event_engine.put((event_type, data))
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"发送事件 {event_type} 失败: {e}")


def create_data_manager(
    data_service: Optional[Any] = None,
    event_engine: Optional[Any] = None
) -> tuple:
    """创建数据管理器

    工厂函数，创建并返回 (DataPreloader, DataUpdateScheduler) 元组。

    Args:
        data_service: A股数据服务实例
        event_engine: 事件引擎实例

    Returns:
        (preloader, scheduler) 元组
    """
    preloader = DataPreloader(data_service, event_engine)
    scheduler = DataUpdateScheduler(data_service, event_engine)

    if not CHINA_DATA_AVAILABLE:
        logger.warning("vnpy_china_data 不可用，数据管理器功能将受限")

    return preloader, scheduler
