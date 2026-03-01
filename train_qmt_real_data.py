#!/usr/bin/env python3
"""
使用QMT真实历史数据进行增量训练

从MySQL数据库加载QMT历史数据，使用vnpy.alpha模块训练LightGBM模型
"""

import sys
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

import polars as pl
import numpy as np
import pymysql

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy.alpha import AlphaLab, AlphaDataset, AlphaModel
from vnpy.alpha.dataset import Segment

# MySQL配置
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "vnpy",
    "password": "Vnpy2024!",
    "database": "vnpy_china",
    "charset": "utf8mb4",
}

# ============================================================
# 数据加载
# ============================================================

def load_qmt_bars_from_mysql(
    symbols: list[str] | None = None,
    start_date: str = "2021-01-01",
    end_date: str = "2025-12-31",
    limit_symbols: int = 50
) -> pl.DataFrame:
    """
    从MySQL数据库加载QMT历史数据

    Parameters
    ----------
    symbols : list[str] | None
        股票代码列表，None表示自动选择
    start_date : str
        开始日期
    end_date : str
        结束日期
    limit_symbols : int
        限制股票数量

    Returns
    -------
    pl.DataFrame
        包含OHLCV数据的DataFrame
    """
    print(f"\n正在从MySQL加载数据...")
    print(f"  日期范围: {start_date} ~ {end_date}")

    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()

    # 如果没有指定股票，自动选择数据量最大的股票
    if symbols is None:
        print(f"  自动选择数据最丰富的 {limit_symbols} 只股票...")
        cursor.execute(f"""
            SELECT symbol, COUNT(*) as count
            FROM db_bar_data
            WHERE `datetime` >= %s AND `datetime` <= %s
            GROUP BY symbol
            ORDER BY count DESC
            LIMIT {limit_symbols}
        """, (start_date, end_date))
        symbols = [row[0] for row in cursor.fetchall()]
        print(f"  选择了 {len(symbols)} 只股票")

    # 构建查询
    placeholders = ','.join(['%s'] * len(symbols))
    query = f"""
        SELECT
            `datetime`,
            symbol,
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

    # 转换为DataFrame
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        raise ValueError("没有查询到数据，请检查日期范围和股票代码")

    df = pl.DataFrame(
        rows,
        schema=[
            "datetime", "symbol", "open", "high", "low", "close",
            "volume", "turnover"
        ],
        orient="row"
    )

    print(f"  ✓ 加载了 {len(df)} 条记录")
    print(f"  ✓ 日期范围: {df['datetime'].min()} ~ {df['datetime'].max()}")
    print(f"  ✓ 股票数量: {df['symbol'].n_unique()}")

    return df


def create_features_from_bars(df: pl.DataFrame) -> pl.DataFrame:
    """
    从K线数据计算Alpha特征

    Parameters
    ----------
    df : pl.DataFrame
        原始K线数据

    Returns
    -------
    pl.DataFrame
        包含特征和标签的数据
    """
    print(f"\n正在计算特征...")

    # 按股票分组计算特征
    dfs = []

    for symbol in df['symbol'].unique():
        symbol_df = df.filter(pl.col('symbol') == symbol).sort('datetime')

        # 基础价格特征
        symbol_df = symbol_df.with_columns([
            # 收益率
            (pl.col('close') / pl.col('open') - 1).alias('return_daily'),
            (pl.col('high') / pl.col('low') - 1).alias('return_high_low'),
            (pl.col('close') / pl.col('close').shift(1) - 1).alias('return_prev'),

            # 波动率
            ((pl.col('high') - pl.col('low')) / pl.col('close')).alias('volatility_daily'),

            # 成交量特征
            (pl.col('volume') / pl.col('volume').rolling_mean(20)).alias('volume_ratio'),

            # 价格位置
            ((pl.col('close') - pl.col('low')) / (pl.col('high') - pl.col('low') + 0.001)).alias('price_position'),
        ])

        # 滚动统计特征
        symbol_df = symbol_df.with_columns([
            pl.col('close').rolling_mean(5).alias('ma5'),
            pl.col('close').rolling_mean(10).alias('ma10'),
            pl.col('close').rolling_mean(20).alias('ma20'),
            pl.col('close').rolling_std(20).alias('std20'),
        ])

        # 动量特征
        symbol_df = symbol_df.with_columns([
            (pl.col('close') / pl.col('close').shift(5) - 1).alias('momentum_5d'),
            (pl.col('close') / pl.col('close').shift(10) - 1).alias('momentum_10d'),
            (pl.col('close') / pl.col('close').shift(20) - 1).alias('momentum_20d'),
        ])

        # 标签：未来5日收益率
        symbol_df = symbol_df.with_columns([
            (pl.col('close').shift(-5) / pl.col('close') - 1).alias('label')
        ])

        dfs.append(symbol_df)

    # 合并所有股票数据
    result_df = pl.concat(dfs)

    # 移除包含NaN的行（由于滚动窗口和shift产生的）
    result_df = result_df.drop_nans()

    # 确保所有特征列都是float类型
    float_cols = [
        'return_daily', 'return_high_low', 'return_prev',
        'volatility_daily', 'volume_ratio', 'price_position',
        'ma5', 'ma10', 'ma20', 'std20',
        'momentum_5d', 'momentum_10d', 'momentum_20d',
        'open', 'high', 'low', 'close', 'volume', 'turnover'
    ]

    for col in float_cols:
        if col in result_df.columns:
            result_df = result_df.with_columns([
                pl.col(col).cast(pl.Float64)
            ])

    print(f"  ✓ 计算了 {len(result_df.columns) - 8} 个特征")
    print(f"  ✓ 有效样本数: {len(result_df)}")

    return result_df


# ============================================================
# 简化的AlphaDataset
# ============================================================

class QMAlphaDataset(AlphaDataset):
    """使用QMT数据的简化数据集"""

    def __init__(self, df: pl.DataFrame, train_period, valid_period, test_period):
        super().__init__(
            df=df,
            train_period=train_period,
            valid_period=valid_period,
            test_period=test_period
        )
        # 直接使用处理后的数据
        self.learn_df = df
        self.infer_df = df


# ============================================================
# 训练流程
# ============================================================

def run_training_with_qmt_data():
    """使用QMT真实数据进行训练"""

    print("\n" + "="*70)
    print(" 使用QMT真实数据进行增量训练")
    print("="*70)

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    lab_path = Path(temp_dir) / "alpha_lab"

    try:
        # ============================================================
        # 1. 加载数据
        # ============================================================
        print("\n[1/5] 加载QMT历史数据...")

        df = load_qmt_bars_from_mysql(
            start_date="2021-01-01",
            end_date="2024-12-31",
            limit_symbols=100  # 使用100只股票
        )

        # ============================================================
        # 2. 特征工程
        # ============================================================
        print("\n[2/5] 特征工程...")

        feature_df = create_features_from_bars(df)

        # 准备训练数据
        feature_df = feature_df.with_columns([
            (pl.col('symbol') + ".SSE").alias('vt_symbol')
        ])

        # 选择特征列
        feature_cols = [
            'return_daily', 'return_high_low', 'return_prev',
            'volatility_daily', 'volume_ratio', 'price_position',
            'ma5', 'ma10', 'ma20', 'std20',
            'momentum_5d', 'momentum_10d', 'momentum_20d'
        ]

        # 创建最终数据集
        final_df = feature_df.select([
            'datetime', 'vt_symbol',
            *feature_cols,
            'label'
        ])

        # ============================================================
        # 3. 创建数据集
        # ============================================================
        print("\n[3/5] 创建数据集...")

        dataset = QMAlphaDataset(
            df=final_df,
            train_period=("2021-01-01", "2023-12-31"),
            valid_period=("2024-01-01", "2024-06-30"),
            test_period=("2024-07-01", "2024-12-31")
        )

        print(f"  训练集样本: {len(dataset.learn_df.filter(pl.col('datetime') <= datetime(2023, 12, 31)))}")
        print(f"  验证集样本: {len(dataset.learn_df.filter((pl.col('datetime') > datetime(2023, 12, 31)) & (pl.col('datetime') <= datetime(2024, 6, 30))))}")
        print(f"  测试集样本: {len(dataset.learn_df.filter(pl.col('datetime') > datetime(2024, 6, 30)))}")

        # ============================================================
        # 4. 初始训练
        # ============================================================
        print("\n[4/5] 初始训练...")

        lab = AlphaLab(str(lab_path))
        lab.save_dataset("qmt_stock_data", dataset)

        print("  开始训练 LightGBM 模型...")
        model, version = lab.train_model_incremental(
            model_name="qmt_lgb_model",
            dataset=dataset,
            model_type="lgb",
            num_boost_round=500,
            incremental=False  # 强制完整训练
        )

        print(f"  ✓ 模型训练完成: {version.version_id}")
        print(f"  ✓ 增量训练: {version.is_incremental}")

        # ============================================================
        # 5. 增量训练（使用最新数据）
        # ============================================================
        print("\n[5/5] 增量训练...")

        # 加载2025年的新数据
        print("  加载2025年新数据进行增量训练...")
        new_df = load_qmt_bars_from_mysql(
            start_date="2025-01-01",
            end_date="2025-12-31",
            limit_symbols=100
        )

        new_feature_df = create_features_from_bars(new_df)
        new_feature_df = new_feature_df.with_columns([
            (pl.col('symbol') + ".SSE").alias('vt_symbol')
        ])

        new_final_df = new_feature_df.select([
            'datetime', 'vt_symbol',
            *feature_cols,
            'label'
        ])

        new_dataset = QMAlphaDataset(
            df=new_final_df,
            train_period=("2025-01-01", "2025-06-30"),
            valid_period=("2025-07-01", "2025-09-30"),
            test_period=("2025-10-01", "2025-12-31")
        )

        print("  开始增量训练...")
        incremental_model, incremental_version = lab.train_model_incremental(
            model_name="qmt_lgb_model",  # 使用相同名称
            dataset=new_dataset,
            model_type="lgb",
            num_boost_round=200,  # 增量使用更少轮数
            incremental=True  # 增量训练
        )

        print(f"  ✓ 增量训练完成: {incremental_version.version_id}")
        print(f"  ✓ 基于版本: {incremental_version.base_version}")

        # ============================================================
        # 测试总结
        # ============================================================
        print("\n" + "="*70)
        print(" 训练总结")
        print("="*70)

        versions = lab.list_model_versions("qmt_lgb_model")
        print(f"✓ 创建了 {len(versions)} 个模型版本")
        for v in versions:
            mode = "增量" if v.is_incremental else "完整"
            print(f"  - {v.version_id}: {mode}训练")

        # 性能测试
        print("\n性能测试:")
        predictions = model.predict(dataset, Segment.TEST)
        actual = dataset.fetch_learn(Segment.TEST)['label'].to_numpy()

        # 转换为float类型
        predictions = np.array(predictions, dtype=np.float64)
        actual = np.array(actual, dtype=np.float64)

        mae = np.mean(np.abs(predictions - actual))
        rmse = np.sqrt(np.mean((predictions - actual) ** 2))

        print(f"  MAE:  {mae:.6f}")
        print(f"  RMSE: {rmse:.6f}")

        # 计算IC（信息系数）
        ic = np.corrcoef(predictions, actual)[0, 1]
        print(f"  IC:   {ic:.6f}")

        print("\n" + "="*70)
        print("🎉 使用QMT真实数据训练完成！")
        print("="*70)
        print(f"\n模型已保存到: {lab_path}")
        print("可以使用以下命令加载模型:")
        print(f"  lab = AlphaLab('{lab_path}')")
        print("  model = lab.load_model('qmt_lgb_model')")

        return True

    except Exception as e:
        print(f"\n✗ 训练失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 保留训练结果用于检查，不删除临时目录
        print(f"\n训练数据保存在: {temp_dir}")
        print(f"如需清理，请运行: rm -rf {temp_dir}")


if __name__ == "__main__":
    success = run_training_with_qmt_data()
    sys.exit(0 if success else 1)
