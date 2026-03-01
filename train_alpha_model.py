"""
A 股机器学习模型训练脚本

从 MySQL 数据库加载历史行情数据，使用 vnpy.alpha 模块训练 LightGBM 模型
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
    # 数据范围
    "start_date": "2021-03-01",
    "end_date": "2026-02-28",

    # 训练周期划分
    "train_end": "2024-12-31",
    "valid_end": "2025-06-30",

    # 模型配置
    "model_type": "lgb",  # lgb / lasso / mlp
    "label_period": 5,  # 预测周期（天）

    # 股票数量
    "stock_limit": 50,  # 训练股票数量
}


def load_bar_data_from_db(
    db: MySQLDatabaseLayer,
    symbol: str,
    exchange: Exchange,
    start: datetime,
    end: datetime
) -> pl.DataFrame:
    """从数据库加载 K 线数据"""

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

        # 转换为 DataFrame - 先构建数据字典，再创建 DataFrame
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
    """获取数据库中的所有股票列表"""

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
) -> pl.DataFrame:
    """批量加载多只股票数据"""

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


def prepare_dataset(df: pl.DataFrame) -> AlphaDataset:
    """准备训练数据集"""

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


def train_model(lab_path: str, dataset: AlphaDataset) -> Any:
    """训练模型"""

    # 创建实验室
    lab = AlphaLab(lab_path)

    # 保存数据集
    print("保存数据集...")
    lab.save_dataset("a_stock_dataset", dataset)

    # 使用 LightGBM 模型
    from vnpy.alpha.model.models.lgb_model import LgbModel

    model = LgbModel(
        learning_rate=0.1,
        num_leaves=31,
        num_boost_round=1000,
        early_stopping_rounds=50,
        log_evaluation_period=100,
        seed=42
    )

    # 训练模型
    print(f"训练 {TRAIN_CONFIG['model_type']} 模型...")
    model.fit(dataset)

    # 保存模型
    print("保存模型...")
    model_path = lab.model_path / "a_stock_lgb.txt"
    model.save_model(model_path)

    return model


def evaluate_model(model: Any, dataset: AlphaDataset) -> None:
    """评估模型性能"""

    print("\n=== 模型评估 ===")

    # 显示特征重要性
    print("特征重要性:")
    model.detail()

    # 获取测试集预测
    from vnpy.alpha.dataset import Segment
    predictions = model.predict(dataset, Segment.TEST)

    print(f"\n预测结果形状：{predictions.shape}")
    print(f"预测均值：{np.mean(predictions):.6f}")
    print(f"预测标准差：{np.std(predictions):.6f}")
    print(f"预测最小值：{np.min(predictions):.6f}")
    print(f"预测最大值：{np.max(predictions):.6f}")


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
    print("=" * 60)


if __name__ == "__main__":
    main()
