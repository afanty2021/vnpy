"""
A 股机器学习模型预测脚本

使用已训练的 LightGBM 模型对最新数据进行预测，生成交易信号
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

# 预测配置
PREDICT_CONFIG = {
    # 模型路径
    "model_path": str(Path.home() / "vnpy_lab/model/a_stock_lgb.txt"),
    "dataset_path": str(Path.home() / "vnpy_lab/dataset/a_stock_dataset.pkl"),

    # 预测股票数量
    "stock_limit": 50,

    # 交易信号阈值
    "long_threshold": 0.02,   # 预期收益>2% 做多
    "short_threshold": -0.02, # 预期收益<-2% 做空/平仓
}


def load_latest_data(
    db: MySQLDatabaseLayer,
    end_date: str,
    lookback_days: int = 60,
    stock_list: list[tuple[str, str]] | None = None,
    limit: int = 50
) -> pl.DataFrame:
    """加载最新数据用于预测"""

    end = datetime.strptime(end_date, "%Y-%m-%d")
    start = end - timedelta(days=lookback_days)

    if stock_list is None:
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

    print(f"准备加载 {len(stock_list)} 只股票的最新数据...")

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
                cursor.execute(query, (symbol, exchange_str, start, end))
                rows = cursor.fetchall()

            if not rows or len(rows) < 30:  # 至少需要 30 天数据
                continue

            # 转换为 DataFrame
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

            # 添加 vt_symbol 列
            vt_symbol = f"{symbol}.{exchange_str}"
            df = df.with_columns(pl.lit(vt_symbol).alias("vt_symbol"))

            all_data.append(df)
            print(f"  已加载：{vt_symbol} ({len(df)}条)")

        except Exception as e:
            print(f"  加载失败 {symbol}: {e}")
            continue

    if not all_data:
        return None

    # 合并所有数据
    combined_df = pl.concat(all_data)
    print(f"总计加载 {len(combined_df)} 条数据")

    return combined_df


def prepare_prediction_dataset(
    df: pl.DataFrame,
    original_dataset: AlphaDataset
) -> AlphaDataset:
    """准备预测数据集"""

    from vnpy.alpha.dataset.datasets.alpha_158 import Alpha158

    # 使用与训练时相同的周期配置（仅用于计算因子）
    dataset = Alpha158(
        df=df,
        train_period=("2021-03-01", "2024-12-31"),
        valid_period=("2021-03-01", "2025-06-30"),
        test_period=("2021-03-01", "2026-02-28"),
    )

    return dataset


def generate_signals(
    predictions: np.ndarray,
    index_df: pl.DataFrame,
    long_threshold: float = 0.02,
    short_threshold: float = -0.02
) -> pl.DataFrame:
    """生成交易信号"""

    # 创建信号 DataFrame
    signals = index_df.select(["datetime", "vt_symbol"]).clone()
    signals = signals.with_columns(
        pl.lit(predictions).alias("prediction"),
        pl.lit(0).alias("signal"),  # 0=持仓，1=做多，-1=做空/平仓
    )

    # 根据预测值生成信号
    signals = signals.with_columns(
        pl.when(pl.col("prediction") > long_threshold)
        .then(pl.lit(1))  # 做多信号
        .when(pl.col("prediction") < short_threshold)
        .then(pl.lit(-1))  # 做空/平仓信号
        .otherwise(pl.lit(0))  # 持仓
        .alias("signal")
    )

    return signals


def analyze_signals(signals: pl.DataFrame) -> dict:
    """分析交易信号统计"""

    total = len(signals)
    long_count = (signals["signal"] == 1).sum()
    short_count = (signals["signal"] == -1).sum()
    hold_count = (signals["signal"] == 0).sum()

    # 按股票分组统计
    stock_signals = signals.groupby("vt_symbol").agg([
        pl.col("prediction").mean().alias("avg_prediction"),
        pl.col("signal").mean().alias("avg_signal"),
        pl.col("prediction").std().alias("prediction_std"),
    ])

    # 按日期分组统计
    date_signals = signals.groupby("datetime").agg([
        pl.col("prediction").mean().alias("avg_prediction"),
        pl.col("signal").sum().alias("net_signal"),
    ])

    return {
        "total": total,
        "long_count": long_count,
        "short_count": short_count,
        "hold_count": hold_count,
        "long_pct": long_count / total * 100,
        "short_pct": short_count / total * 100,
        "hold_pct": hold_count / total * 100,
        "stock_signals": stock_signals,
        "date_signals": date_signals,
    }


def visualize_signals(signals: pl.DataFrame, stats: dict) -> None:
    """可视化交易信号"""

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. 信号分布饼图
    ax1 = axes[0, 0]
    labels = ['做多', '持仓', '做空/平仓']
    sizes = [stats['long_count'], stats['hold_count'], stats['short_count']]
    colors = ['#2ecc71', '#95a5a6', '#e74c3c']
    ax1.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors)
    ax1.set_title('交易信号分布')

    # 2. 每日净信号（做多 - 做空）
    ax2 = axes[0, 1]
    date_signals = stats['date_signals'].sort("datetime")
    ax2.bar(
        range(len(date_signals)),
        date_signals["net_signal"].to_list(),
        color=['#e74c3c' if x < 0 else '#2ecc71' if x > 0 else '#95a5a6'
               for x in date_signals["net_signal"].to_list()]
    )
    ax2.set_xlabel('交易日')
    ax2.set_ylabel('净信号数量')
    ax2.set_title('每日净信号（做多 - 做空）')
    ax2.grid(axis='y', alpha=0.3)

    # 3. 股票平均预测值分布
    ax3 = axes[1, 0]
    stock_signals = stats['stock_signals'].sort("avg_prediction", descending=True)
    stocks = stock_signals["vt_symbol"].to_list()[:20]  # 前 20 只
    preds = stock_signals["avg_prediction"].to_list()[:20]
    colors = ['#2ecc71' if x > 0 else '#e74c3c' for x in preds]
    ax3.barh(stocks, preds, color=colors)
    ax3.set_xlabel('平均预测值')
    ax3.set_title('Top 20 股票平均预测值')
    ax3.invert_yaxis()

    # 4. 预测值分布直方图
    ax4 = axes[1, 1]
    predictions = signals["prediction"].to_list()
    ax4.hist(predictions, bins=50, color='steelblue', alpha=0.7, edgecolor='black')
    ax4.axvline(x=PREDICT_CONFIG["long_threshold"], color='g', linestyle='--',
                label=f'做多阈值 ({PREDICT_CONFIG["long_threshold"]})')
    ax4.axvline(x=PREDICT_CONFIG["short_threshold"], color='r', linestyle='--',
                label=f'做空阈值 ({PREDICT_CONFIG["short_threshold"]})')
    ax4.axvline(x=0, color='k', linestyle='-', alpha=0.5)
    ax4.set_xlabel('预测值（5 日预期收益率）')
    ax4.set_ylabel('频数')
    ax4.set_title('预测值分布')
    ax4.legend()
    ax4.grid(axis='y', alpha=0.3)

    plt.tight_layout()

    # 保存图表
    output_path = Path.home() / "vnpy_lab" / "signal_analysis.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n信号分析图表已保存至：{output_path}")
    plt.show()


def main():
    """主函数"""

    print("=" * 60)
    print("A 股机器学习模型预测")
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
    print(f"   模型路径：{PREDICT_CONFIG['model_path']}")

    model = LgbModel()
    model.load_model(PREDICT_CONFIG["model_path"])

    # 获取最新日期
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n3. 加载最新数据（截止：{today}）...")

    df = load_latest_data(
        db,
        end_date=today,
        lookback_days=90,  # 加载 90 天数据用于计算因子
        limit=PREDICT_CONFIG["stock_limit"]
    )

    db.close()

    if df is None:
        print("数据加载失败")
        return

    # 准备预测数据集
    print("\n4. 准备预测数据集...")
    print("   正在计算 Alpha158 因子...")

    dataset = prepare_prediction_dataset(df, None)
    dataset.prepare_data()

    # 进行预测
    print("\n5. 生成预测...")
    from vnpy.alpha.dataset import Segment

    predictions = model.predict(dataset, Segment.TEST)

    # 创建索引 DataFrame
    index_df = dataset.fetch_infer(Segment.TEST).select(["datetime", "vt_symbol"])

    print(f"   预测结果数量：{len(predictions)}")
    print(f"   预测均值：{np.mean(predictions):.6f}")
    print(f"   预测标准差：{np.std(predictions):.6f}")

    # 生成交易信号
    print("\n6. 生成交易信号...")
    print(f"   做多阈值：{PREDICT_CONFIG['long_threshold']:.2%}")
    print(f"   做空阈值：{PREDICT_CONFIG['short_threshold']:.2%}")

    signals = generate_signals(
        predictions,
        index_df,
        long_threshold=PREDICT_CONFIG["long_threshold"],
        short_threshold=PREDICT_CONFIG["short_threshold"]
    )

    # 分析信号
    print("\n7. 信号统计分析...")
    stats = analyze_signals(signals)

    print(f"\n{'='*50}")
    print("交易信号统计")
    print(f"{'='*50}")
    print(f"总样本数：{stats['total']}")
    print(f"做多信号：{stats['long_count']} ({stats['long_pct']:.1f}%)")
    print(f"持仓信号：{stats['hold_count']} ({stats['hold_pct']:.1f}%)")
    print(f"做空信号：{stats['short_count']} ({stats['short_pct']:.1f}%)")
    print(f"{'='*50}")

    # 显示 Top 10 做多股票
    print("\nTop 10 做多股票（平均预测值最高）:")
    top_long = stats['stock_signals'].sort("avg_prediction", descending=True).head(10)
    for row in top_long.iter_rows():
        print(f"  {row[0]}: {row[1]:+.4f}")

    # 显示 Top 10 做空股票
    print("\nTop 10 做空股票（平均预测值最低）:")
    top_short = stats['stock_signals'].sort("avg_prediction", descending=False).head(10)
    for row in top_short.iter_rows():
        print(f"  {row[0]}: {row[1]:+.4f}")

    # 可视化
    print("\n8. 生成信号分析图表...")
    visualize_signals(signals, stats)

    # 保存信号到文件
    print("\n9. 保存交易信号...")
    output_path = Path.home() / "vnpy_lab" / "signals"
    output_path.mkdir(parents=True, exist_ok=True)

    signal_file = output_path / f"signals_{today}.csv"
    signals.write_csv(signal_file)
    print(f"交易信号已保存至：{signal_file}")

    print("\n" + "=" * 60)
    print("预测完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
