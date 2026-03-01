#!/usr/bin/env python3
"""
RPC实时信号生成脚本

通过RPC连接到Windows QMT服务器，订阅实时行情数据，
使用Alpha158因子和LightGBM模型生成实时交易信号。

功能特点：
1. RPC连接管理（自动重连）
2. 历史数据窗口维护（滚动更新）
3. Alpha158因子实时计算
4. LightGBM模型预测
5. 交易信号生成（做多/做空/持仓）
6. Rich终端UI实时显示
"""

import sys
import time
import signal
import logging
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque, defaultdict
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

import polars as pl
import numpy as np
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from vnpy.rpc import RpcClient
from vnpy.trader.object import TickData, BarData
from vnpy.trader.constant import Exchange
from vnpy.alpha import AlphaDataset
from vnpy.alpha.dataset import Segment
from vnpy.alpha.dataset.datasets.alpha_158 import Alpha158
from vnpy.alpha.model.models.lgb_model import LgbModel


# ==================== 配置参数 ====================

# RPC配置
RPC_CONFIG = {
    "req_address": "tcp://192.168.2.168:2014",
    "sub_address": "tcp://192.168.2.168:4102",
    "reconnect_interval": 5,  # 重连间隔（秒）
    "max_reconnect_attempts": 10,  # 最大重连次数（新增）
}

# 模型配置
MODEL_CONFIG = {
    "model_path": str(Path.home() / "vnpy_lab/model/a_stock_lgb.txt"),
}

# 信号配置
SIGNAL_CONFIG = {
    "long_threshold": 0.02,    # 做多阈值（2%）
    "short_threshold": -0.02,  # 做空阈值（-2%）
    "window_size": 60,         # 历史数据窗口（天数）
    "min_data_points": 30,     # 最小数据点数
}

# 股票池配置
STOCK_POOL = [
    # 这里配置要监控的股票列表
    # 示例: ("000001", "SZSE"), ("600000", "SSE")
    # 为空时将从RPC获取合约列表
]


# ==================== 实时信号管理器 ====================

class RealtimeSignalManager:
    """
    实时信号管理器

    功能：
    1. 管理RPC连接和数据订阅
    2. 维护历史数据窗口
    3. 计算Alpha158因子（使用缓存优化）
    4. 生成交易信号
    5. 提供信号查询接口
    """

    def __init__(
        self,
        rpc_req_address: str,
        rpc_sub_address: str,
        model_path: str,
        long_threshold: float = 0.02,
        short_threshold: float = -0.02,
        window_size: int = 60
    ):
        # RPC配置
        self.req_address = rpc_req_address
        self.sub_address = rpc_sub_address
        self.rpc_client: Optional[RpcClient] = None
        self.connected = False
        self.reconnect_attempts = 0  # 重连尝试次数计数器

        # 模型
        self.model_path = model_path
        self.model = LgbModel()
        self.model_loaded = False

        # 信号阈值
        self.long_threshold = long_threshold
        self.short_threshold = short_threshold

        # 历史数据窗口 {vt_symbol: deque}
        self.data_windows: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self.window_size = window_size

        # 实时信号 {vt_symbol: {"prediction": float, "signal": int, "timestamp": datetime}}
        self.signals: Dict[str, dict] = {}

        # Alpha158数据集（用于因子计算）
        self.dataset: Optional[Alpha158] = None

        # 因子缓存：{vt_symbol: {"df": pl.DataFrame, "last_update": datetime}}
        # 使用缓存避免重复计算因子，提升性能
        self.factor_cache: Dict[str, dict] = {}

        # 统计信息
        self.stats = {
            "last_update": None,
            "total_predictions": 0,
            "long_signals": 0,
            "short_signals": 0,
            "hold_signals": 0,
        }

    def load_model(self) -> bool:
        """加载模型"""
        try:
            self.model.load_model(self.model_path)
            self.model_loaded = True
            logger.info(f"模型加载成功: {self.model_path}")
            return True
        except FileNotFoundError as e:
            logger.error(f"模型文件不存在: {self.model_path}, 错误: {e}")
            return False
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            return False

    def connect(self) -> bool:
        """连接RPC服务器"""
        try:
            # 创建RPC客户端
            class SignalRpcClient(RpcClient):
                def __init__(self, manager):
                    super().__init__()
                    self.manager = manager

                def callback(self, topic: str, data) -> None:
                    """接收服务器推送的数据"""
                    if topic == "tick":
                        self.manager.on_tick(data)
                    elif topic == "bar":
                        self.manager.on_bar(data)

            self.rpc_client = SignalRpcClient(self)
            self.rpc_client.start(self.req_address, self.sub_address)

            # 订阅tick数据
            self.rpc_client.subscribe_topic("tick")

            self.connected = True
            self.reconnect_attempts = 0  # 连接成功后重置重连计数器
            logger.info(f"RPC连接成功: {self.req_address}")
            return True

        except ConnectionError as e:
            logger.error(f"RPC连接失败（网络错误）: {e}")
            return False
        except TimeoutError as e:
            logger.error(f"RPC连接失败（超时）: {e}")
            return False
        except Exception as e:
            logger.error(f"RPC连接失败（未知错误）: {e}")
            return False

    def disconnect(self) -> None:
        """断开RPC连接"""
        if self.rpc_client:
            try:
                self.rpc_client.stop()
                self.rpc_client.join()
                self.connected = False
                logger.info("RPC连接已断开")
            except Exception as e:
                logger.error(f"断开RPC连接时出错: {e}")
                self.connected = False

    def on_tick(self, tick: TickData) -> None:
        """
        处理Tick数据

        将tick数据转换为1分钟K线并更新数据窗口
        """
        vt_symbol = tick.vt_symbol

        # 获取当前时间窗口
        now = tick.datetime
        bar_datetime = now.replace(second=0, microsecond=0)

        # 获取或创建当前K线
        current_bar = self._get_or_create_bar(vt_symbol, bar_datetime)

        # 更新K线数据
        if current_bar["volume"] == 0:
            # 新K线
            current_bar.update({
                "datetime": bar_datetime,
                "open": tick.last_price,
                "high": tick.last_price,
                "low": tick.last_price,
                "close": tick.last_price,
                "volume": tick.volume,
                "turnover": tick.turnover,
            })
        else:
            # 更新现有K线
            current_bar["high"] = max(current_bar["high"], tick.last_price)
            current_bar["low"] = min(current_bar["low"], tick.last_price)
            current_bar["close"] = tick.last_price
            current_bar["volume"] += tick.volume
            current_bar["turnover"] += tick.turnover

    def on_bar(self, bar: BarData) -> None:
        """处理K线数据"""
        vt_symbol = bar.vt_symbol
        bar_data = {
            "datetime": bar.datetime,
            "open": bar.open_price,
            "high": bar.high_price,
            "low": bar.low_price,
            "close": bar.close_price,
            "volume": bar.volume,
            "turnover": bar.turnover,
        }

        # 添加到数据窗口
        self.data_windows[vt_symbol].append(bar_data)

        # 检查是否需要生成信号
        window = self.data_windows[vt_symbol]
        if len(window) >= self.window_size:
            self._generate_signal(vt_symbol)

    def _get_or_create_bar(self, vt_symbol: str, bar_datetime: datetime) -> dict:
        """获取或创建当前K线"""
        window = self.data_windows[vt_symbol]

        if not window:
            # 创建新K线
            new_bar = {
                "datetime": bar_datetime,
                "open": 0,
                "high": 0,
                "low": 0,
                "close": 0,
                "volume": 0,
                "turnover": 0,
            }
            window.append(new_bar)
            return new_bar

        # 检查最后一条K线是否是同一时间
        last_bar = window[-1]
        if last_bar["datetime"] == bar_datetime:
            return last_bar
        else:
            # 创建新K线
            new_bar = {
                "datetime": bar_datetime,
                "open": 0,
                "high": 0,
                "low": 0,
                "close": 0,
                "volume": 0,
                "turnover": 0,
            }
            window.append(new_bar)
            return new_bar

    def _generate_signal(self, vt_symbol: str) -> None:
        """生成交易信号（使用缓存优化因子计算）"""
        if not self.model_loaded:
            logger.warning(f"模型未加载，跳过信号生成: {vt_symbol}")
            return

        window = self.data_windows[vt_symbol]
        if len(window) < self.window_size:
            return

        try:
            # 转换为DataFrame
            data = list(window)
            df = pl.DataFrame(data)

            # 添加vt_symbol列
            df = df.with_columns(pl.lit(vt_symbol).alias("vt_symbol"))

            # 获取当前K线的时间戳
            current_datetime = df["datetime"][-1]

            # 检查缓存：只有当数据窗口更新时才重新计算因子
            if vt_symbol in self.factor_cache:
                cached_info = self.factor_cache[vt_symbol]
                # 如果缓存的数据是最新的，直接使用缓存的预测结果
                if cached_info["last_update"] == current_datetime:
                    logger.debug(f"使用缓存的因子数据: {vt_symbol}")
                    # 使用缓存的数据集进行预测
                    predictions = self.model.predict(cached_info["dataset"], Segment.TEST)
                    self._process_prediction(vt_symbol, predictions)
                    return

            # 创建数据集并计算因子（未命中缓存）
            logger.debug(f"计算 {vt_symbol} 的Alpha158因子...")
            dataset = Alpha158(
                df=df,
                train_period=("2020-01-01", "2024-12-31"),
                valid_period=("2020-01-01", "2024-12-31"),
                test_period=("2020-01-01", "2025-12-31"),
            )
            dataset.prepare_data()
            dataset.process_data()

            # 缓存处理后的数据集（包含计算好的因子）
            self.factor_cache[vt_symbol] = {
                "dataset": dataset,
                "last_update": current_datetime,
            }

            # 进行预测
            predictions = self.model.predict(dataset, Segment.TEST)
            self._process_prediction(vt_symbol, predictions)

        except pl.exceptions.ComputeError as e:
            logger.error(f"计算因子时出错（数据不足） {vt_symbol}: {e}")
        except ValueError as e:
            logger.error(f"生成信号失败（数据格式错误） {vt_symbol}: {e}")
        except Exception as e:
            logger.error(f"生成信号失败（未知错误） {vt_symbol}: {e}", exc_info=True)

    def _process_prediction(self, vt_symbol: str, predictions: np.ndarray) -> None:
        """处理预测结果并生成信号"""
        if len(predictions) > 0:
            pred = predictions[-1]  # 取最新预测值

            # 生成信号
            if pred > self.long_threshold:
                signal = 1  # 做多
                self.stats["long_signals"] += 1
            elif pred < self.short_threshold:
                signal = -1  # 做空
                self.stats["short_signals"] += 1
            else:
                signal = 0  # 持仓
                self.stats["hold_signals"] += 1

            # 更新信号
            self.signals[vt_symbol] = {
                "prediction": float(pred),
                "signal": signal,
                "timestamp": datetime.now(),
            }

            self.stats["total_predictions"] += 1
            self.stats["last_update"] = datetime.now()

            logger.debug(f"{vt_symbol} 信号生成完成: 预测={pred:.4f}, 信号={signal}")

    def load_initial_data(self, symbols: List[Tuple[str, str]]) -> None:
        """
        加载初始历史数据

        TODO: 此方法当前为空实现，实际使用时需要实现以下功能之一：
        1. 从RPC服务器查询历史数据（需要RPC服务器支持）
        2. 从本地CSV文件加载历史数据（推荐用于开发测试）
        3. 从数据库加载历史数据（如MySQL、PostgreSQL）

        推荐方案：
        - 开发环境：从本地CSV文件加载
        - 生产环境：通过RPC查询或从数据库加载

        Parameters
        ----------
        symbols : List[Tuple[str, str]]
            股票列表 [(symbol, exchange), ...]

        示例代码（从本地CSV加载）:
        ---------------------------
        for symbol, exchange_str in symbols:
            vt_symbol = f"{symbol}.{exchange_str}"
            csv_path = f"data/{vt_symbol}.csv"

            if Path(csv_path).exists():
                df = pl.read_csv(csv_path, try_parse_dates=True)
                for row in df.iter_rows(named=True):
                    self.data_windows[vt_symbol].append({
                        "datetime": row["datetime"],
                        "open": row["open"],
                        "high": row["high"],
                        "low": row["low"],
                        "close": row["close"],
                        "volume": row["volume"],
                        "turnover": row.get("turnover", 0),
                    })
                logger.info(f"已加载 {vt_symbol} 的历史数据，共 {len(df)} 条")
        """
        if not self.rpc_client or not self.connected:
            logger.warning("RPC未连接，无法加载历史数据")
            return

        logger.info("开始加载初始历史数据...")

        for symbol, exchange_str in symbols:
            try:
                vt_symbol = f"{symbol}.{exchange_str}"

                # TODO: 实现历史数据加载逻辑
                # 当前为空实现，系统需要等待60天积累数据才能生成信号
                #
                # 推荐实现方案：
                # 1. 从本地CSV文件加载（最简单）
                #    df = pl.read_csv(f"data/{vt_symbol}.csv")
                #    for row in df.iter_rows(named=True):
                #        self.data_windows[vt_symbol].append(...)
                #
                # 2. 从数据库加载（推荐）
                #    df = pl.read_database(f"SELECT * FROM {vt_symbol}...", conn)
                #
                # 3. 通过RPC查询（需要RPC服务器支持）
                #    history = self.rpc_client.query_history(symbol, exchange_str)

                logger.debug(f"跳过 {vt_symbol} 的历史数据加载（待实现）")
                pass

            except FileNotFoundError as e:
                logger.warning(f"历史数据文件不存在 {vt_symbol}: {e}")
            except pl.exceptions.ComputeError as e:
                logger.error(f"解析历史数据失败 {vt_symbol}: {e}")
            except Exception as e:
                logger.error(f"加载历史数据失败 {vt_symbol}: {e}", exc_info=True)
                continue

        logger.info("初始数据加载完成")

    def get_top_signals(self, n: int = 10) -> Tuple[List[dict], List[dict]]:
        """
        获取Top N做多和做空信号

        Returns
        -------
        Tuple[List[dict], List[dict]]
            (做多信号列表, 做空信号列表)
        """
        # 按预测值排序
        sorted_signals = sorted(
            self.signals.items(),
            key=lambda x: x[1]["prediction"],
            reverse=True
        )

        # 提取做多和做空信号
        long_signals = [
            {"vt_symbol": k, **v}
            for k, v in sorted_signals
            if v["signal"] == 1
        ][:n]

        short_signals = [
            {"vt_symbol": k, **v}
            for k, v in sorted_signals
            if v["signal"] == -1
        ][:n]

        return long_signals, short_signals

    def get_hold_signals(self, n: int = 20) -> List[dict]:
        """
        获取持仓信号列表

        Returns
        -------
        List[dict]
            持仓信号列表
        """
        hold_signals = [
            {"vt_symbol": k, **v}
            for k, v in self.signals.items()
            if v["signal"] == 0
        ]

        # 按预测值绝对值排序
        hold_signals.sort(key=lambda x: abs(x["prediction"]), reverse=True)

        return hold_signals[:n]


# ==================== Rich UI显示 ====================

class SignalDisplay:
    """
    信号显示界面

    使用Rich库创建终端UI
    """

    def __init__(self, manager: RealtimeSignalManager):
        self.manager = manager
        self.console = Console()

    def create_layout(self) -> Layout:
        """创建布局"""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right"),
        )

        return layout

    def render_header(self) -> Panel:
        """渲染头部"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stats = self.manager.stats

        text = Text()
        text.append("RPC实时信号系统", style="bold cyan")
        text.append(f"  |  时间: {now}", style="dim")
        text.append(f"\n预测总数: {stats['total_predictions']}  |  ", style="green")
        text.append(f"做多: {stats['long_signals']}  |  ", style="bold green")
        text.append(f"做空: {stats['short_signals']}  |  ", style="bold red")
        text.append(f"持仓: {stats['hold_signals']}", style="yellow")

        return Panel(text, title="状态", border_style="cyan")

    def render_long_signals(self) -> Panel:
        """渲染做多信号"""
        table = Table(title="Top 10 做多信号", show_header=True, header_style="bold green")
        table.add_column("股票", style="cyan", width=15)
        table.add_column("预测值", style="green", width=10)
        table.add_column("信号", width=6)
        table.add_column("时间", style="dim", width=19)

        long_signals, _ = self.manager.get_top_signals(10)

        for item in long_signals:
            signal_text = "[bold green]做多[/bold green]"
            time_str = item["timestamp"].strftime("%H:%M:%S")

            table.add_row(
                item["vt_symbol"],
                f"{item['prediction']:+.4f}",
                signal_text,
                time_str
            )

        if not long_signals:
            table.add_row("", "", "", "")

        return Panel(table, title="做多", border_style="green")

    def render_short_signals(self) -> Panel:
        """渲染做空信号"""
        table = Table(title="Top 10 做空信号", show_header=True, header_style="bold red")
        table.add_column("股票", style="cyan", width=15)
        table.add_column("预测值", style="red", width=10)
        table.add_column("信号", width=6)
        table.add_column("时间", style="dim", width=19)

        _, short_signals = self.manager.get_top_signals(10)

        for item in short_signals:
            signal_text = "[bold red]做空[/bold red]"
            time_str = item["timestamp"].strftime("%H:%M:%S")

            table.add_row(
                item["vt_symbol"],
                f"{item['prediction']:+.4f}",
                signal_text,
                time_str
            )

        if not short_signals:
            table.add_row("", "", "", "")

        return Panel(table, title="做空", border_style="red")

    def render_hold_signals(self) -> Panel:
        """渲染持仓信号"""
        table = Table(title="持仓股票 (Top 20)", show_header=True, header_style="bold yellow")
        table.add_column("股票", style="cyan", width=15)
        table.add_column("预测值", width=10)
        table.add_column("时间", style="dim", width=19)

        hold_signals = self.manager.get_hold_signals(20)

        for item in hold_signals:
            time_str = item["timestamp"].strftime("%H:%M:%S")

            table.add_row(
                item["vt_symbol"],
                f"{item['prediction']:+.4f}",
                time_str
            )

        if not hold_signals:
            table.add_row("", "", "")

        return Panel(table, title="持仓", border_style="yellow")

    def render_footer(self) -> Panel:
        """渲染底部"""
        text = Text()
        text.append("按 ", style="dim")
        text.append("Ctrl+C", style="bold red")
        text.append(" 退出", style="dim")

        status = "[green]已连接[/green]" if self.manager.connected else "[red]未连接[/red]"
        text.append(f"  |  RPC状态: {status}", style="")

        return Panel(text, border_style="dim")

    def update_display(self) -> Layout:
        """更新显示"""
        layout = self.create_layout()

        layout["header"].update(self.render_header())
        layout["left"].update(self.render_long_signals())
        layout["right"].update(self.render_short_signals())
        # layout["footer"].update(self.render_footer())  # 注释掉以避免布局问题

        return layout


# ==================== 主程序 ====================

def main():
    """主函数"""

    print("=" * 60)
    print("RPC实时信号生成系统")
    print("=" * 60)

    # 创建信号管理器
    manager = RealtimeSignalManager(
        rpc_req_address=RPC_CONFIG["req_address"],
        rpc_sub_address=RPC_CONFIG["sub_address"],
        model_path=MODEL_CONFIG["model_path"],
        long_threshold=SIGNAL_CONFIG["long_threshold"],
        short_threshold=SIGNAL_CONFIG["short_threshold"],
        window_size=SIGNAL_CONFIG["window_size"],
    )

    # 加载模型
    print("\n1. 加载模型...")
    if not manager.load_model():
        print("模型加载失败，程序退出")
        return
    print(f"   模型已加载: {MODEL_CONFIG['model_path']}")

    # 连接RPC
    print("\n2. 连接RPC服务器...")
    print(f"   REQ: {RPC_CONFIG['req_address']}")
    print(f"   SUB: {RPC_CONFIG['sub_address']}")

    if not manager.connect():
        print("RPC连接失败，程序退出")
        return
    print("   RPC已连接")

    # 创建显示界面
    display = SignalDisplay(manager)

    # 信号处理
    running = True

    def signal_handler(signum, frame):
        nonlocal running
        running = False
        print("\n正在退出...")

    signal.signal(signal.SIGINT, signal_handler)

    # 主循环
    print("\n3. 启动实时监控...")
    print("   等待行情数据...\n")

    try:
        with Live(display.update_display(), refresh_per_second=1) as live:
            while running:
                # 更新显示
                live.update(display.update_display())

                # 检查连接状态
                if not manager.connected:
                    max_attempts = RPC_CONFIG.get("max_reconnect_attempts", 10)

                    if manager.reconnect_attempts < max_attempts:
                        manager.reconnect_attempts += 1
                        logger.info(
                            f"连接断开，尝试重连 ({manager.reconnect_attempts}/{max_attempts})..."
                        )
                        time.sleep(RPC_CONFIG["reconnect_interval"])

                        if manager.connect():
                            logger.info("重连成功")
                        else:
                            if manager.reconnect_attempts >= max_attempts:
                                logger.error(
                                    f"重连失败，已达到最大重试次数 ({max_attempts})，程序退出"
                                )
                                running = False
                                break
                    else:
                        logger.error("已达到最大重连次数，程序退出")
                        running = False
                        break

                # 短暂休眠
                time.sleep(0.5)

    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.error(f"程序异常退出: {e}", exc_info=True)
    finally:
        # 清理资源
        logger.info("正在断开连接...")
        manager.disconnect()
        logger.info("程序已退出")


if __name__ == "__main__":
    main()
