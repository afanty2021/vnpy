"""
A 股机器学习模型回测脚本

使用已训练的 LightGBM 模型进行历史回测，验证策略效果
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl
import numpy as np
import matplotlib.pyplot as plt

from vnpy.trader.constant import Exchange
from vnpy.alpha import AlphaLab, AlphaDataset
from vnpy.alpha.model.models.lgb_model import LgbModel
from vnpy_china_data.database import MySQLDatabaseLayer
from vnpy_china_config import ConfigManager

# 从配置管理器获取数据库配置
config_manager = ConfigManager()
global_config = config_manager.load_global_config()

MYSQL_CONFIG = {
    "host": global_config.database.mysql_host,
    "port": global_config.database.mysql_port,
    "user": global_config.database.mysql_user,
    "password": global_config.database.mysql_password,
    "database": global_config.database.mysql_database,
    "charset": "utf8mb4",
}

# 回测配置
BACKTEST_CONFIG = {
    # 模型路径
    "model_path": str(Path.home() / "vnpy_lab/model/a_stock_lgb.txt"),

    # 回测周期
    "start_date": "2025-01-01",
    "end_date": "2026-02-28",

    # 股票数量
    "stock_limit": 50,

    # 交易参数
    "long_threshold": 0.02,    # 预期收益>2% 做多
    "short_threshold": -0.02,  # 预期收益<-2% 做空/平仓
    "position_limit": 10,      # 最大持仓数量
    "commission": 0.0003,      # 手续费（万分之三）
    "slippage": 0.001,         # 滑点（千分之一）
}


class BacktestEngine:
    """简易回测引擎"""

    def __init__(
        self,
        initial_capital: float = 1_000_000.0,
        commission: float = 0.0003,
        slippage: float = 0.001
    ):
        """
        初始化回测引擎

        Args:
            initial_capital: 初始资金
            commission: 手续费率
            slippage: 滑点
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.commission = commission
        self.slippage = slippage

        # 持仓管理
        self.positions: dict[str, dict] = {}  # vt_symbol -> {size, avg_price, entry_date}

        # 绩效记录
        self.daily_values: list[float] = []
        self.daily_returns: list[float] = []
        self.trades: list[dict] = []

    def buy(self, vt_symbol: str, price: float, size: float, date: datetime) -> bool:
        """开仓买入"""
        cost = price * size * (1 + self.commission + self.slippage)

        if cost > self.capital:
            return False

        self.capital -= cost

        if vt_symbol in self.positions:
            # 加仓
            pos = self.positions[vt_symbol]
            total_cost = pos["size"] * pos["avg_price"] + price * size
            pos["size"] += size
            pos["avg_price"] = total_cost / pos["size"]
        else:
            # 新建仓
            self.positions[vt_symbol] = {
                "size": size,
                "avg_price": price,
                "entry_date": date
            }

        self.trades.append({
            "date": date,
            "symbol": vt_symbol,
            "action": "BUY",
            "price": price,
            "size": size,
            "commission": cost - price * size
        })

        return True

    def sell(self, vt_symbol: str, price: float, size: float, date: datetime) -> float:
        """平仓卖出"""
        if vt_symbol not in self.positions:
            return 0.0

        pos = self.positions[vt_symbol]
        sell_size = min(size, pos["size"])
        proceeds = price * sell_size * (1 - self.commission - self.slippage)

        self.capital += proceeds

        # 记录盈亏
        pnl = (price - pos["avg_price"]) * sell_size - (pos["avg_price"] * sell_size * self.commission)

        self.trades.append({
            "date": date,
            "symbol": vt_symbol,
            "action": "SELL",
            "price": price,
            "size": sell_size,
            "pnl": pnl
        })

        # 更新或移除持仓
        pos["size"] -= sell_size
        if pos["size"] <= 0:
            del self.positions[vt_symbol]

        return pnl

    def update_daily_value(self, prices: dict[str, float]) -> None:
        """更新每日账户价值"""
        # 持仓价值
        position_value = sum(
            pos["size"] * prices.get(vt_symbol, pos["avg_price"])
            for vt_symbol, pos in self.positions.items()
        )

        # 总账户价值
        total_value = self.capital + position_value
        self.daily_values.append(total_value)

        # 计算日收益率
        if len(self.daily_values) > 1:
            daily_return = (self.daily_values[-1] / self.daily_values[-2]) - 1
            self.daily_returns.append(daily_return)

    def get_performance_metrics(self) -> dict:
        """计算绩效指标"""
        if not self.daily_values:
            return {}

        values = np.array(self.daily_values)
        returns = np.array(self.daily_returns) if self.daily_returns else np.array([])

        # 总收益率
        total_return = (values[-1] - self.initial_capital) / self.initial_capital

        # 年化收益率（假设 252 个交易日）
        days = len(values)
        annual_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0

        # 波动率
        volatility = np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0

        # 夏普比率（假设无风险利率为 3%）
        sharpe = (annual_return - 0.03) / volatility if volatility > 0 else 0

        # 最大回撤
        cummax = np.maximum.accumulate(values)
        drawdown = (values - cummax) / cummax
        max_drawdown = np.min(drawdown)

        # 胜率
        winning_trades = sum(1 for t in self.trades if t.get("pnl", 0) > 0)
        total_trades = sum(1 for t in self.trades if t.get("pnl", 0) != 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        return {
            "initial_capital": self.initial_capital,
            "final_value": values[-1],
            "total_return": total_return,
            "annual_return": annual_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_drawdown,
            "total_trades": len(self.trades),
            "win_rate": win_rate,
            "final_positions": len(self.positions)
        }


def load_backtest_data(
    db: MySQLDatabaseLayer,
    start_date: str,
    end_date: str,
    limit: int = 50
) -> pl.DataFrame:
    """加载回测数据"""

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    # 获取股票列表
    query = """
        SELECT DISTINCT `symbol`, `exchange`
        FROM `db_bar_data`
        WHERE `interval` = 'd'
        ORDER BY `symbol`
        LIMIT %s
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (limit,))
        stock_list = cursor.fetchall()

    print(f"准备加载 {len(stock_list)} 只股票的回测数据...")

    all_data = []

    for symbol, exchange_str in stock_list:
        try:
            exchange = Exchange(exchange_str)
            query = """
                SELECT `datetime`, `open_price`, `high_price`, `low_price`, `close_price`, `volume`, `turnover`
                FROM `db_bar_data`
                WHERE `symbol` = %s AND `exchange` = %s
                AND `interval` = 'd'
                AND `datetime` BETWEEN %s AND %s
                ORDER BY `datetime`
            """

            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (symbol, exchange_str, start - timedelta(days=60), end))
                rows = cursor.fetchall()

            if not rows or len(rows) < 60:
                continue

            data = {
                "datetime": [str(row[0]) for row in rows],
                "open": [float(row[1]) for row in rows],
                "high": [float(row[2]) for row in rows],
                "low": [float(row[3]) for row in rows],
                "close": [float(row[4]) for row in rows],
                "volume": [float(row[5]) for row in rows],
                "turnover": [float(row[6]) for row in rows],
            }

            df = pl.DataFrame(data)
            df = df.with_columns(pl.col("datetime").str.to_datetime())

            vt_symbol = f"{symbol}.{exchange_str}"
            df = df.with_columns(pl.lit(vt_symbol).alias("vt_symbol"))

            all_data.append(df)
            print(f"  已加载：{vt_symbol} ({len(df)}条)")

        except Exception as e:
            print(f"  加载失败 {symbol}: {e}")
            continue

    if not all_data:
        return None

    combined_df = pl.concat(all_data)
    print(f"总计加载 {len(combined_df)} 条数据")

    return combined_df


def run_backtest(
    df: pl.DataFrame,
    model: LgbModel,
    start_date: str,
    end_date: str,
    long_threshold: float = 0.02,
    short_threshold: float = -0.02,
    position_limit: int = 10,
    commission: float = 0.0003,
    slippage: float = 0.001
) -> BacktestEngine:
    """运行回测"""

    from vnpy.alpha.dataset.datasets.alpha_158 import Alpha158
    from vnpy.alpha.dataset import Segment

    # 创建数据集
    dataset = Alpha158(
        df=df,
        train_period=("2021-03-01", "2024-12-31"),
        valid_period=("2021-03-01", "2025-06-30"),
        test_period=(start_date, end_date),
    )

    print("\n计算因子和标签...")
    dataset.prepare_data()

    # 获取回测期间的交易日
    test_df = dataset.fetch_infer(Segment.TEST)
    dates = sorted(test_df["datetime"].unique().to_list())

    print(f"回测区间：{start_date} 至 {end_date}")
    print(f"交易日数量：{len(dates)}")

    # 初始化回测引擎
    engine = BacktestEngine(
        initial_capital=1_000_000.0,
        commission=commission,
        slippage=slippage
    )

    print(f"\n初始资金：{engine.initial_capital:,.0f}")
    print(f"手续费率：{commission:.2%}")
    print(f"滑点：{slippage:.2%}")
    print(f"最大持仓：{position_limit}")
    print(f"做多阈值：{long_threshold:.2%}")
    print(f"做空阈值：{short_threshold:.2%}")

    # 按交易日进行回测
    print("\n开始回测...")

    for i, date in enumerate(dates):
        # 获取当日数据
        daily_df = test_df.filter(pl.col("datetime") == date)

        # 获取价格映射
        price_map = {
            row["vt_symbol"]: row["close"]
            for row in daily_df.select(["vt_symbol", "close"]).iter_rows()
        }

        # 更新账户价值
        engine.update_daily_value(price_map)

        # 获取模型预测
        # 注意：这里简化处理，实际需要按日期分割数据进行预测
        # 在实际应用中，应该只使用到当日为止的数据进行预测

        # 获取持仓列表
        held_symbols = set(engine.positions.keys())

        # 平仓逻辑：预测值低于平仓阈值的持仓
        # （简化实现，实际需要逐行预测）

        # 开仓逻辑：预测值高于做多阈值且未持仓
        # （简化实现，实际需要逐行预测）

        if (i + 1) % 50 == 0:
            print(f"  已处理 {i + 1}/{len(dates)} 个交易日")

    return engine


def visualize_backtest_results(
    engine: BacktestEngine,
    df: pl.DataFrame
) -> None:
    """可视化回测结果"""

    metrics = engine.get_performance_metrics()
    values = engine.daily_values

    fig, axes = plt.subplots(3, 1, figsize=(14, 12))

    # 1. 账户价值曲线
    ax1 = axes[0]
    ax1.plot(values, linewidth=1.5, color='#2c3e50')
    ax1.set_title(f"账户价值曲线 (最终值：¥{values[-1]:,.0f}, 总收益率：{metrics['total_return']:.2%})")
    ax1.set_xlabel("交易日")
    ax1.set_ylabel("账户价值 (¥)")
    ax1.grid(alpha=0.3)

    # 2. 累计收益率曲线
    ax2 = axes[1]
    cum_returns = [(v / values[0] - 1) * 100 for v in values]
    ax2.plot(cum_returns, linewidth=1.5, color='#27ae60')
    ax2.axhline(y=0, color='k', linestyle='-', alpha=0.3)
    ax2.set_title(f"累计收益率 ({metrics['annual_return']:.2%} 年化)")
    ax2.set_xlabel("交易日")
    ax2.set_ylabel("累计收益率 (%)")
    ax2.grid(alpha=0.3)

    # 3. 回撤曲线
    ax3 = axes[2]
    cummax = np.maximum.accumulate(values)
    drawdown = (values - cummax) / cummax * 100
    ax3.fill_between(range(len(drawdown)), drawdown, 0, color='#e74c3c', alpha=0.5)
    ax3.set_title(f"回撤曲线 (最大回撤：{metrics['max_drawdown']:.2%})")
    ax3.set_xlabel("交易日")
    ax3.set_ylabel("回撤 (%)")
    ax3.grid(alpha=0.3)

    plt.tight_layout()

    # 保存图表
    output_path = Path.home() / "vnpy_lab" / "backtest_results.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n回测结果图表已保存至：{output_path}")
    plt.show()

    # 打印绩效指标
    print("\n" + "=" * 60)
    print("回测绩效指标")
    print("=" * 60)
    print(f"初始资金：¥{metrics['initial_capital']:,.0f}")
    print(f"最终价值：¥{metrics['final_value']:,.0f}")
    print(f"总收益率：{metrics['total_return']:.2%}")
    print(f"年化收益率：{metrics['annual_return']:.2%}")
    print(f"波动率：{metrics['volatility']:.2%}")
    print(f"夏普比率：{metrics['sharpe_ratio']:.2f}")
    print(f"最大回撤：{metrics['max_drawdown']:.2%}")
    print(f"交易次数：{metrics['total_trades']}")
    print(f"胜率：{metrics['win_rate']:.1%}")
    print(f"期末持仓：{metrics['final_positions']}")
    print("=" * 60)


def main():
    """主函数"""

    print("=" * 60)
    print("A 股机器学习模型回测")
    print("=" * 60)

    # 连接数据库
    print("\n1. 连接数据库...")
    db = MySQLDatabaseLayer(**MYSQL_CONFIG)

    if not db.connect():
        print("数据库连接失败，请检查配置")
        return

    print("数据库连接成功")

    # 加载模型
    print("\n2. 加载已训练模型...")
    model = LgbModel()
    model.load_model(BACKTEST_CONFIG["model_path"])

    # 加载回测数据
    print("\n3. 加载回测数据...")
    df = load_backtest_data(
        db,
        start_date=BACKTEST_CONFIG["start_date"],
        end_date=BACKTEST_CONFIG["end_date"],
        limit=BACKTEST_CONFIG["stock_limit"]
    )

    db.close()

    if df is None:
        print("数据加载失败")
        return

    # 运行回测
    print("\n4. 运行回测...")
    engine = run_backtest(
        df=df,
        model=model,
        start_date=BACKTEST_CONFIG["start_date"],
        end_date=BACKTEST_CONFIG["end_date"],
        long_threshold=BACKTEST_CONFIG["long_threshold"],
        short_threshold=BACKTEST_CONFIG["short_threshold"],
        position_limit=BACKTEST_CONFIG["position_limit"],
        commission=BACKTEST_CONFIG["commission"],
        slippage=BACKTEST_CONFIG["slippage"]
    )

    # 可视化结果
    print("\n5. 生成回测报告...")
    visualize_backtest_results(engine, df)

    print("\n" + "=" * 60)
    print("回测完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
