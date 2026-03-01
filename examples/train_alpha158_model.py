#!/usr/bin/env python3
"""
Alpha158 特征工程训练脚本

使用 vnpy.alpha.dataset.datasets.Alpha158 类计算 158 个技术因子，
从 MySQL 数据库加载 QMT 历史数据，训练 LightGBM 模型。

使用方法:
    python examples/train_alpha158_model.py --symbols "000001,000002" --start-date "2021-01-01" --end-date "2024-12-31"

依赖:
    - vnpy (核心框架)
    - vnpy.alpha (Alpha量化模块)
    - polars, numpy, lightgbm, matplotlib, pymysql

输出:
    - ~/vnpy_lab/model/alpha158_lgb.txt (训练好的模型)
    - ~/vnpy_lab/feature_importance.png (特征重要性图表)
"""

import sys
import argparse
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any

import polars as pl
import numpy as np
import pymysql
import matplotlib.pyplot as plt

from vnpy.trader.constant import Exchange
from vnpy.alpha.dataset import Segment
from vnpy.alpha.dataset.datasets.alpha_158 import Alpha158
from vnpy.alpha.model.models.lgb_model import LgbModel

# ============================================================
# 配置部分
# ============================================================

# MySQL 配置（从环境变量读取，提供默认值）
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "vnpy"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "vnpy_china"),
    "charset": "utf8mb4",
}

# 模型保存路径
LAB_PATH = Path.home() / "vnpy_lab"
MODEL_PATH = LAB_PATH / "model"
FEATURE_IMPORTANCE_PATH = LAB_PATH / "feature_importance.png"

# ============================================================
# 数据加载函数
# ============================================================

def load_data_from_mysql(
    symbols: list[str],
    start_date: str,
    end_date: str
) -> pl.DataFrame:
    """
    从 MySQL 数据库加载历史数据

    Parameters
    ----------
    symbols : list[str]
        股票代码列表，如 ["000001", "000002"]
    start_date : str
        开始日期，如 "2021-01-01"
    end_date : str
        结束日期，如 "2024-12-31"

    Returns
    -------
    pl.DataFrame
        包含 OHLCV 数据的 DataFrame
    """
    print(f"\n正在从 MySQL 加载数据...")
    print(f"  股票代码: {', '.join(symbols)}")
    print(f"  日期范围: {start_date} ~ {end_date}")

    conn = pymysql.connect(**MYSQL_CONFIG)

    try:
        # 使用上下文管理器确保游标关闭
        with conn.cursor() as cursor:
            # 构建查询
            placeholders = ','.join(['%s'] * len(symbols))
            query = f"""
                SELECT
                    `datetime`,
                    symbol,
                    `exchange`,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume,
                    turnover
                FROM db_bar_data
                WHERE `datetime` >= %s
                  AND `datetime` <= %s
                  AND symbol IN ({placeholders})
                  AND `interval` = 'd'
                ORDER BY symbol, `datetime`
            """

            cursor.execute(query, [start_date, end_date] + symbols)

            # 转换为 DataFrame
            rows = cursor.fetchall()

        if not rows:
            raise ValueError("没有查询到数据，请检查日期范围和股票代码")

        # 创建 DataFrame
        df = pl.DataFrame(
            rows,
            schema=[
                "datetime", "symbol", "exchange",
                "open", "high", "low", "close",
                "volume", "turnover"
            ],
            orient="row"
        )

        # 转换 datetime 列
        df = df.with_columns([
            pl.col("datetime").str.to_datetime()
        ])

        # 创建 vt_symbol 列 (symbol.exchange)
        df = df.with_columns([
            (pl.col("symbol") + "." + pl.col("exchange")).alias("vt_symbol")
        ])

        # 删除 exchange 列（已合并到 vt_symbol）
        df = df.drop("exchange")

        print(f"  ✓ 加载了 {len(df)} 条记录")
        print(f"  ✓ 日期范围: {df['datetime'].min()} ~ {df['datetime'].max()}")
        print(f"  ✓ 股票数量: {df['symbol'].n_unique()}")

        return df

    finally:
        conn.close()


# ============================================================
# 模型训练函数
# ============================================================

def train_alpha158_model(
    df: pl.DataFrame,
    train_period: tuple[str, str],
    valid_period: tuple[str, str],
    test_period: tuple[str, str],
    num_boost_round: int = 1000
) -> tuple[LgbModel, Alpha158]:
    """
    训练 Alpha158 模型

    Parameters
    ----------
    df : pl.DataFrame
        包含 OHLCV 数据的 DataFrame
    train_period : tuple[str, str]
        训练集时间范围
    valid_period : tuple[str, str]
        验证集时间范围
    test_period : tuple[str, str]
        测试集时间范围
    num_boost_round : int
        训练轮数

    Returns
    -------
    tuple[LgbModel, Alpha158]
        训练好的模型和数据集
    """
    print("\n正在准备 Alpha158 数据集...")

    # 创建 Alpha158 数据集
    dataset = Alpha158(
        df=df,
        train_period=train_period,
        valid_period=valid_period,
        test_period=test_period
    )

    print(f"  训练集: {train_period[0]} ~ {train_period[1]}")
    print(f"  验证集: {valid_period[0]} ~ {valid_period[1]}")
    print(f"  测试集: {test_period[0]} ~ {test_period[1]}")

    # 准备数据（计算特征）
    print("\n正在计算 Alpha158 因子...")
    dataset.prepare_data()
    print("  ✓ 因子计算完成")

    # 创建模型
    print("\n正在创建 LightGBM 模型...")
    model = LgbModel(
        learning_rate=0.1,
        num_leaves=31,
        num_boost_round=num_boost_round,
        early_stopping_rounds=50,
        log_evaluation_period=100,
        seed=42
    )

    # 训练模型
    print(f"\n正在训练模型（最多 {num_boost_round} 轮）...")
    model.fit(dataset)

    return model, dataset


# ============================================================
# 评估和保存函数
# ============================================================

def evaluate_and_save_model(
    model: LgbModel,
    dataset: Alpha158
) -> None:
    """
    评估模型并保存结果

    Parameters
    ----------
    model : LgbModel
        训练好的模型
    dataset : Alpha158
        数据集
    """
    print("\n正在评估模型...")

    # 预测测试集
    predictions = model.predict(dataset, Segment.TEST)
    actual = dataset.fetch_learn(Segment.TEST)['label'].to_numpy()

    # 计算评估指标
    mae = np.mean(np.abs(predictions - actual))
    rmse = np.sqrt(np.mean((predictions - actual) ** 2))
    ic = np.corrcoef(predictions, actual)[0, 1]

    print(f"  测试集评估:")
    print(f"    MAE:  {mae:.6f}")
    print(f"    RMSE: {rmse:.6f}")
    print(f"    IC:   {ic:.6f}")

    # 保存模型
    print(f"\n正在保存模型...")
    MODEL_PATH.mkdir(parents=True, exist_ok=True)
    model.save_model(MODEL_PATH / "alpha158_lgb.txt")
    print(f"  ✓ 模型已保存到: {MODEL_PATH / 'alpha158_lgb.txt'}")

    # 生成特征重要性图表
    print(f"\n正在生成特征重要性图表...")
    generate_feature_importance_plot(model)
    print(f"  ✓ 图表已保存到: {FEATURE_IMPORTANCE_PATH}")


def generate_feature_importance_plot(model: LgbModel) -> None:
    """
    生成特征重要性图表

    Parameters
    ----------
    model : LgbModel
        训练好的模型
    """
    try:
        if model.model is None:
            print("  警告: 模型未训练，无法生成特征重要性图表")
            return

        # 获取特征重要性
        importance = model.model.feature_importance(importance_type='gain')
        feature_names = model.model.feature_name()

        # 排序
        indices = np.argsort(importance)[::-1]

        # 只显示前 30 个特征
        top_n = 30
        indices = indices[:top_n]

        # 创建图表
        plt.figure(figsize=(12, 10))
        plt.title('Alpha158 特征重要性 (Top 30)')
        plt.barh(range(top_n), importance[indices][::-1], align='center')
        plt.yticks(range(top_n), [feature_names[i] for i in indices][::-1])
        plt.xlabel('重要性 (gain)')
        plt.tight_layout()

        # 保存图表
        plt.savefig(FEATURE_IMPORTANCE_PATH, dpi=150, bbox_inches='tight')
        plt.close()

    except Exception as e:
        print(f"  警告: 生成特征重要性图表失败 - {e}")
        plt.close()  # 确保图表资源被释放


# ============================================================
# 主函数
# ============================================================

def main():
    """主函数"""

    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='Alpha158 特征工程训练脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 训练两只股票的模型
  python examples/train_alpha158_model.py --symbols "000001,000002" --start-date "2021-01-01" --end-date "2024-12-31"

  # 使用更多训练轮数
  python examples/train_alpha158_model.py --symbols "000001,000002" --start-date "2021-01-01" --end-date "2024-12-31" --num-boost-round 2000
        """
    )

    parser.add_argument(
        '--symbols',
        type=str,
        required=True,
        help='股票代码列表，逗号分隔，如 "000001,000002"'
    )

    parser.add_argument(
        '--start-date',
        type=str,
        required=True,
        help='开始日期，格式: YYYY-MM-DD，如 2021-01-01'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        required=True,
        help='结束日期，格式: YYYY-MM-DD，如 2024-12-31'
    )

    parser.add_argument(
        '--num-boost-round',
        type=int,
        default=1000,
        help='训练轮数，默认 1000'
    )

    args = parser.parse_args()

    # 解析股票代码
    symbols = [s.strip() for s in args.symbols.split(',')]

    print("=" * 70)
    print(" Alpha158 特征工程训练")
    print("=" * 70)

    try:
        # 1. 加载数据
        df = load_data_from_mysql(
            symbols=symbols,
            start_date=args.start_date,
            end_date=args.end_date
        )

        # 2. 设置训练/验证/测试集
        # 将时间段分为三份：70% 训练，15% 验证，15% 测试
        start_dt = datetime.strptime(args.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(args.end_date, "%Y-%m-%d")
        total_days = (end_dt - start_dt).days

        train_end_dt = start_dt + timedelta(days=int(total_days * 0.7))
        valid_end_dt = start_dt + timedelta(days=int(total_days * 0.85))

        train_period = (args.start_date, train_end_dt.strftime("%Y-%m-%d"))
        valid_period = (train_end_dt.strftime("%Y-%m-%d"), valid_end_dt.strftime("%Y-%m-%d"))
        test_period = (valid_end_dt.strftime("%Y-%m-%d"), args.end_date)

        # 3. 训练模型（返回 model 和 dataset）
        model, dataset = train_alpha158_model(
            df=df,
            train_period=train_period,
            valid_period=valid_period,
            test_period=test_period,
            num_boost_round=args.num_boost_round
        )

        # 4. 评估并保存（使用返回的 dataset，避免重复创建）
        evaluate_and_save_model(model, dataset)

        print("\n" + "=" * 70)
        print(" 训练完成！")
        print("=" * 70)
        print(f"\n输出文件:")
        print(f"  - 模型: {MODEL_PATH / 'alpha158_lgb.txt'}")
        print(f"  - 特征重要性: {FEATURE_IMPORTANCE_PATH}")

        return 0

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
