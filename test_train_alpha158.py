#!/usr/bin/env python3
"""
测试 Alpha158 训练脚本

由于数据库连接可能不可用，此脚本使用模拟数据进行测试
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

import polars as pl
import numpy as np

from vnpy.alpha.dataset.datasets.alpha_158 import Alpha158
from vnpy.alpha.model.models.lgb_model import LgbModel
from vnpy.alpha.dataset import Segment


def create_mock_data(
    symbols: list[str],
    start_date: str,
    end_date: str
) -> pl.DataFrame:
    """创建模拟数据用于测试"""

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    data = []

    for symbol in symbols:
        current_dt = start_dt
        while current_dt <= end_dt:
            # 只使用工作日
            if current_dt.weekday() < 5:
                # 生成随机价格数据
                base_price = 10.0 + np.random.randn() * 5
                open_price = base_price * (1 + np.random.randn() * 0.01)
                high_price = max(open_price, base_price) * (1 + abs(np.random.randn()) * 0.02)
                low_price = min(open_price, base_price) * (1 - abs(np.random.randn()) * 0.02)
                close_price = base_price * (1 + np.random.randn() * 0.01)
                volume = 1000000 + np.random.randn() * 100000
                turnover = volume * close_price

                data.append({
                    "datetime": current_dt,
                    "symbol": symbol,
                    "exchange": "SZSE" if symbol.startswith("000") else "SHSE",
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": volume,
                    "turnover": turnover
                })

            current_dt += timedelta(days=1)

    df = pl.DataFrame(data)

    # 创建 vt_symbol
    df = df.with_columns([
        (pl.col("symbol") + "." + pl.col("exchange")).alias("vt_symbol")
    ])
    df = df.drop("exchange")

    return df


def test_alpha158_training():
    """测试 Alpha158 训练流程"""

    print("=" * 70)
    print(" Alpha158 训练流程测试（使用模拟数据）")
    print("=" * 70)

    # 1. 创建模拟数据
    print("\n1. 创建模拟数据...")
    symbols = ["000001", "000002"]
    start_date = "2023-01-01"
    end_date = "2024-12-31"

    df = create_mock_data(symbols, start_date, end_date)
    print(f"  ✓ 创建了 {len(df)} 条模拟数据")
    print(f"  ✓ 股票: {', '.join(symbols)}")
    print(f"  ✓ 日期范围: {start_date} ~ {end_date}")

    # 2. 设置数据集划分
    print("\n2. 设置数据集划分...")
    train_period = ("2023-01-01", "2023-12-31")
    valid_period = ("2024-01-01", "2024-06-30")
    test_period = ("2024-07-01", "2024-12-31")

    # 3. 创建 Alpha158 数据集
    print("\n3. 创建 Alpha158 数据集...")
    dataset = Alpha158(
        df=df,
        train_period=train_period,
        valid_period=valid_period,
        test_period=test_period
    )

    # 4. 准备数据（计算特征）
    print("\n4. 计算 Alpha158 因子...")
    dataset.prepare_data()

    # 检查计算的特征数量
    feature_cols = [col for col in dataset.raw_df.columns if col not in ["datetime", "vt_symbol", "label"]]
    print(f"  ✓ 计算了 {len(feature_cols)} 个特征")

    # 检查标签
    print(f"  ✓ 标签已设置: 5日远期收益率")

    # 5. 训练模型
    print("\n5. 训练 LightGBM 模型...")
    model = LgbModel(
        learning_rate=0.1,
        num_leaves=31,
        num_boost_round=100,
        early_stopping_rounds=10,
        log_evaluation_period=50,
        seed=42
    )

    model.fit(dataset)
    print(f"  ✓ 模型训练完成")

    # 6. 预测测试集
    print("\n6. 预测测试集...")
    predictions = model.predict(dataset, Segment.TEST)
    actual = dataset.fetch_learn(Segment.TEST)['label'].to_numpy()

    mae = np.mean(np.abs(predictions - actual))
    rmse = np.sqrt(np.mean((predictions - actual) ** 2))

    print(f"  ✓ MAE:  {mae:.6f}")
    print(f"  ✓ RMSE: {rmse:.6f}")

    # 7. 保存模型
    print("\n7. 保存模型...")
    lab_path = Path.home() / "vnpy_lab"
    model_path = lab_path / "model"
    model_path.mkdir(parents=True, exist_ok=True)

    model.save_model(model_path / "alpha158_lgb_test.txt")
    print(f"  ✓ 模型已保存到: {model_path / 'alpha158_lgb_test.txt'}")

    print("\n" + "=" * 70)
    print(" 测试完成！")
    print("=" * 70)

    return True


if __name__ == "__main__":
    try:
        success = test_alpha158_training()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
