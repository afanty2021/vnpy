"""
A 股机器学习模型训练脚本

从 MySQL 数据库加载历史行情数据，使用 vnpy.alpha 模块训练 LightGBM 模型

使用方法:
    python examples/alpha_model_training.py

依赖:
    - vnpy (核心框架)
    - vnpy_china_data (数据库层)
    - vnpy_china_config (配置管理)
    - polars, numpy, lightgbm, matplotlib

输出:
    - /Users/berton/vnpy_lab/model/a_stock_lgb.txt  (训练好的模型)
    - /Users/berton/vnpy_lab/dataset/a_stock_dataset.pkl (处理后的数据集)
"""

import sys
from typing import Any
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl
import numpy as np

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy.alpha import AlphaLab, AlphaDataset, AlphaModel
from vnpy_china_data.database import MySQLDatabaseLayer
from vnpy_china_config import ConfigManager

# ============================================================
# 配置部分
# ============================================================

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

# 训练配置
TRAIN_CONFIG = {
    # 数据范围（5 年历史数据）
    "start_date": "2021-03-01",
    "end_date": "2026-02-28",

    # 训练周期划分
    "train_end": "2024-12-31",   # 训练集截止日期
    "valid_end": "2025-06-30",   # 验证集截止日期

    # 模型配置
    "model_type": "lgb",         # lgb / lasso / mlp
    "label_period": 5,           # 预测周期（天）

    # 股票数量
    "stock_limit": 50,           # 训练股票数量
}

# 模型超参数
MODEL_PARAMS = {
    "learning_rate": 0.1,        # 学习率
    "num_leaves": 31,            # 叶子节点数
    "num_boost_round": 1000,     # 最大训练轮数
    "early_stopping_rounds": 50, # 提前停止轮数
    "log_evaluation_period": 100,# 日志打印间隔
    "seed": 42,                  # 随机种子
}


# ============================================================
# 数据加载函数
# ============================================================

def load_bar_data_from_db(
    db: MySQLDatabaseLayer,
    symbol: str,
    exchange: Exchange,
    start: datetime,
    end: datetime
) -> pl.DataFrame | None:
    """
    从数据库加载单只股票的 K 线数据

    Args:
        db: 数据库实例
        symbol: 股票代码（如：000001）
        exchange: 交易所（如：Exchange.SZSE）
        start: 开始日期
        end: 结束日期

    Returns:
        polars.DataFrame: K 线数据，包含 datetime, open, high, low, close,volume, turnover 字段
        None: 如果未找到数据
    """

    # 查询数据库
    query = """
        SELECT `datetime`, `open_price`, `high_price`, `low_price`, `close_price`, `volume`, `turnover`
        FROM `db_bar_data`
        WHERE `symbol` = %s AND `exchange` = %s
        AND `interval` = 'd'
        AND `datetime` BETWEEN %s AND %s
        ORDER BY `datetime`
    """

    exchange_str = exchange.value

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (symbol, exchange_str, start, end))
        rows = cursor.fetchall()

        if not rows:
            print(f"未找到数据：{symbol}.{exchange}")
            return None

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

        # 转换 datetime 列为 Polars 的 datetime 类型
        df = df.with_columns(pl.col("datetime").str.to_datetime())

        return df


def get_stock_list(db: MySQLDatabaseLayer) -> list[tuple[str, str]]:
    """
    获取数据库中的所有股票列表

    Returns:
        list[tuple[str, str]]: 股票代码和交易所列表，如 [("000001", "SZSE"), ...]
    """

    query = """
        SELECT DISTINCT `symbol`, `exchange`
        FROM `db_bar_data`
        WHERE `interval` = 'd'
        ORDER BY `symbol`
    """

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        stocks = cursor.fetchall()

    return stocks


def load_all_stocks_data(
    db: MySQLDatabaseLayer,
    start: datetime,
    end: datetime,
    stock_list: list[tuple[str, str]] | None = None,
    limit: int = 50
) -> pl.DataFrame | None:
    """
    批量加载多只股票数据

    Args:
        db: 数据库实例
        start: 开始日期
        end: 结束日期
        stock_list: 股票列表，如果为 None 则自动获取
        limit: 最大股票数量

    Returns:
        polars.DataFrame: 合并后的多只股票数据，包含 vt_symbol 列
        None: 如果没有任何数据
    """

    if stock_list is None:
        stock_list = get_stock_list(db)[:limit]

    print(f"准备加载 {len(stock_list)} 只股票数据...")

    all_data = []

    for symbol, exchange_str in stock_list:
        try:
            exchange = Exchange(exchange_str)
            df = load_bar_data_from_db(db, symbol, exchange, start, end)

            if df is None or len(df) < 60:  # 至少需要 60 天数据
                continue

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


# ============================================================
# 数据集准备函数
# ============================================================

def prepare_dataset(df: pl.DataFrame) -> AlphaDataset:
    """
    准备训练数据集

    Args:
        df: 包含 K 线数据和 vt_symbol 列的 DataFrame

    Returns:
        AlphaDataset: 准备好的数据集，包含 Alpha158 因子
    """

    # 使用 Alpha158 因子集
    from vnpy.alpha.dataset.datasets.alpha_158 import Alpha158

    dataset = Alpha158(
        df=df,
        train_period=(
            TRAIN_CONFIG["start_date"],
            TRAIN_CONFIG["train_end"]
        ),
        valid_period=(
            TRAIN_CONFIG["start_date"],
            TRAIN_CONFIG["valid_end"]
        ),
        test_period=(
            TRAIN_CONFIG["start_date"],
            TRAIN_CONFIG["end_date"]
        ),
    )

    return dataset


# ============================================================
# 模型训练函数
# ============================================================

def train_model(lab_path: str, dataset: AlphaDataset) -> Any:
    """
    训练模型

    Args:
        lab_path: 实验室数据保存路径
        dataset: 准备好的数据集

    Returns:
        训练好的模型实例
    """

    # 创建实验室
    lab = AlphaLab(lab_path)

    # 保存数据集
    print("保存数据集...")
    lab.save_dataset("a_stock_dataset", dataset)

    # 使用 LightGBM 模型
    from vnpy.alpha.model.models.lgb_model import LgbModel

    model = LgbModel(
        learning_rate=MODEL_PARAMS["learning_rate"],
        num_leaves=MODEL_PARAMS["num_leaves"],
        num_boost_round=MODEL_PARAMS["num_boost_round"],
        early_stopping_rounds=MODEL_PARAMS["early_stopping_rounds"],
        log_evaluation_period=MODEL_PARAMS["log_evaluation_period"],
        seed=MODEL_PARAMS["seed"]
    )

    # 训练模型
    print(f"训练 {TRAIN_CONFIG['model_type']} 模型...")
    model.fit(dataset)

    # 保存模型
    print("保存模型...")
    model_path = lab.model_path / "a_stock_lgb.txt"
    model.save_model(model_path)

    return model


# ============================================================
# 模型评估函数
# ============================================================

def evaluate_model(model: Any, dataset: AlphaDataset) -> None:
    """
    评估模型性能

    Args:
        model: 训练好的模型
        dataset: 数据集
    """

    print("\n=== 模型评估 ===")

    # 显示特征重要性
    print("特征重要性:")
    model.detail()

    # 获取测试集预测
    from vnpy.alpha.dataset import Segment
    predictions = model.predict(dataset, Segment.TEST)

    print(f"\n预测结果统计:")
    print(f"  预测结果形状：{predictions.shape}")
    print(f"  预测均值：{np.mean(predictions):.6f} (日均收益预期)")
    print(f"  预测标准差：{np.std(predictions):.6f}")
    print(f"  预测最小值：{np.min(predictions):.6f}")
    print(f"  预测最大值：{np.max(predictions):.6f}")


# ============================================================
# 主函数
# ============================================================

def main():
    """主函数"""

    print("=" * 60)
    print("A 股机器学习模型训练")
    print("=" * 60)

    # 连接数据库
    print("\n1. 连接数据库...")
    print(f"   主机：{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}")
    print(f"   数据库：{MYSQL_CONFIG['database']}")

    db = MySQLDatabaseLayer(**MYSQL_CONFIG)

    if not db.connect():
        print("数据库连接失败，请检查配置")
        return

    print("数据库连接成功")

    # 加载数据
    print("\n2. 加载历史数据...")
    start = datetime.strptime(TRAIN_CONFIG["start_date"], "%Y-%m-%d")
    end = datetime.strptime(TRAIN_CONFIG["end_date"], "%Y-%m-%d")

    df = load_all_stocks_data(
        db,
        start,
        end,
        limit=TRAIN_CONFIG["stock_limit"]
    )

    if df is None:
        print("数据加载失败")
        return

    # 关闭数据库连接
    db.close()

    # 准备数据集
    print("\n3. 准备训练数据集...")
    print(f"   数据范围：{TRAIN_CONFIG['start_date']} ~ {TRAIN_CONFIG['end_date']}")
    print(f"   训练集截止：{TRAIN_CONFIG['train_end']}")
    print(f"   验证集截止：{TRAIN_CONFIG['valid_end']}")
    print(f"   因子数量：158 (Alpha158)")
    print(f"   预测周期：{TRAIN_CONFIG['label_period']}天")

    dataset = prepare_dataset(df)

    # 准备数据（计算因子和标签）
    print("\n正在计算因子和标签...")
    dataset.prepare_data()
    print("数据准备完成")

    # 训练模型
    print("\n4. 训练模型...")
    lab_path = str(Path.home() / "vnpy_lab")
    print(f"   模型类型：{TRAIN_CONFIG['model_type']}")
    print(f"   保存路径：{lab_path}")

    model = train_model(lab_path, dataset)

    # 评估模型
    print("\n5. 评估模型...")
    evaluate_model(model, dataset)

    print("\n" + "=" * 60)
    print("训练完成！")
    print(f"模型保存路径：{lab_path}/model/")
    print(f"数据集保存路径：{lab_path}/dataset/")
    print("=" * 60)


if __name__ == "__main__":
    main()
