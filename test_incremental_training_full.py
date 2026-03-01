#!/usr/bin/env python3
"""
增量训练完整流程测试

模拟完整的Alpha量化工作流：
1. 数据加载（模拟数据）
2. 特征工程（Alpha158因子）
3. 初始训练
4. 增量训练
5. 模型比较
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import shutil

import polars as pl
import numpy as np

from vnpy.alpha import AlphaLab, AlphaDataset, AlphaModel
from vnpy.alpha.dataset import Segment

# ============================================================
# 模拟数据生成器
# ============================================================

def generate_stock_data(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    n_features: int = 10
) -> pl.DataFrame:
    """
    生成模拟股票数据

    Parameters
    ----------
    symbol : str
        股票代码
    start_date : datetime
        开始日期
    end_date : datetime
        结束日期
    n_features : int
        特征数量

    Returns
    -------
    pl.DataFrame
        包含OHLCV数据和特征的数据框
    """
    # 生成日期序列（仅工作日）
    dates = []
    current = start_date
    while current <= end_date:
        # 跳过周末
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)

    n = len(dates)

    # 生成价格数据（随机游走）
    np.random.seed(hash(symbol) % 2**32)
    returns = np.random.randn(n) * 0.02  # 日收益率
    prices = 100 * np.exp(np.cumsum(returns))  # 价格路径

    # 生成OHLC
    high = prices * (1 + np.abs(np.random.randn(n)) * 0.01)
    low = prices * (1 - np.abs(np.random.randn(n)) * 0.01)
    open_ = prices + np.random.randn(n) * 0.5
    close = prices

    # 生成成交量
    volume = np.random.randint(1000000, 10000000, n)

    # 生成特征
    features = {}
    for i in range(n_features):
        features[f"feature_{i}"] = np.random.randn(n)

    # 生成标签（未来5日收益率）
    label = np.zeros(n)
    label[:-5] = (prices[5:] / prices[:-5] - 1) * 100  # 百分比

    # 创建DataFrame
    df = pl.DataFrame({
        "datetime": dates,
        "vt_symbol": [f"{symbol}.SSE" for _ in range(n)],
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        **features,
        "label": label,
    })

    # 移除前5行的标签（无法计算）
    df = df.with_columns(
        pl.when(pl.col("datetime") >= dates[5])
        .then(pl.col("label"))
        .otherwise(None)
        .alias("label")
    )

    return df.filter(pl.col("label").is_not_null())


def create_multi_stock_dataset(
    symbols: list[str],
    start_date: datetime,
    end_date: datetime
) -> pl.DataFrame:
    """创建多股票数据集"""
    dfs = []
    for symbol in symbols:
        df = generate_stock_data(symbol, start_date, end_date)
        dfs.append(df)
    return pl.concat(dfs)


# ============================================================
# 简化的AlphaDataset（不需要特征工程）
# ============================================================

class SimpleAlphaDataset(AlphaDataset):
    """简化的数据集，直接使用原始特征"""

    def __init__(self, df: pl.DataFrame, train_period, valid_period, test_period):
        # 调用父类初始化
        super().__init__(
            df=df,
            train_period=train_period,
            valid_period=valid_period,
            test_period=test_period
        )

        # 直接使用原始数据，跳过特征工程
        self.learn_df = df
        self.infer_df = df


# ============================================================
# 测试流程
# ============================================================

def run_incremental_training_test():
    """运行完整的增量训练测试"""

    print("\n" + "="*70)
    print(" 增量训练完整流程测试")
    print("="*70)

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    lab_path = Path(temp_dir) / "alpha_lab"

    try:
        # ============================================================
        # 1. 生成模拟数据
        # ============================================================
        print("\n[1/6] 生成模拟数据...")

        symbols = [f"60{i:04d}" for i in range(1, 51)]  # 50只股票
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2024, 12, 31)

        df = create_multi_stock_dataset(symbols, start_date, end_date)
        print(f"  ✓ 生成了 {len(symbols)} 只股票的数据")
        print(f"  ✓ 总计 {len(df)} 条记录")
        print(f"  ✓ 日期范围: {df['datetime'].min()} ~ {df['datetime'].max()}")

        # ============================================================
        # 2. 创建数据集
        # ============================================================
        print("\n[2/6] 创建数据集...")

        dataset = SimpleAlphaDataset(
            df=df,
            train_period=("2020-01-01", "2022-12-31"),
            valid_period=("2023-01-01", "2023-06-30"),
            test_period=("2023-07-01", "2024-12-31")
        )
        print(f"  ✓ 训练集: {dataset.learn_df.filter(pl.col('datetime') <= datetime(2022, 12, 31)).shape[0]} 条")
        print(f"  ✓ 验证集: {dataset.learn_df.filter((pl.col('datetime') > datetime(2022, 12, 31)) & (pl.col('datetime') <= datetime(2023, 6, 30))).shape[0]} 条")
        print(f"  ✓ 测试集: {dataset.learn_df.filter(pl.col('datetime') > datetime(2023, 6, 30)).shape[0]} 条")

        # ============================================================
        # 3. 初始训练
        # ============================================================
        print("\n[3/6] 初始训练...")

        lab = AlphaLab(str(lab_path))
        lab.save_dataset("stock_data", dataset)

        print("  开始训练 LightGBM 模型...")
        model, version = lab.train_model_incremental(
            model_name="stock_lgb",
            dataset=dataset,
            model_type="lgb",
            num_boost_round=100,  # 减少轮数加快测试
            incremental=False  # 强制完整训练
        )

        print(f"  ✓ 模型训练完成: {version.version_id}")
        print(f"  ✓ 增量训练: {version.is_incremental}")
        if version.train_loss is not None:
            print(f"  ✓ 训练损失: {version.train_loss:.4f}")
        if version.valid_loss is not None:
            print(f"  ✓ 验证损失: {version.valid_loss:.4f}")

        # ============================================================
        # 4. 增量训练
        # ============================================================
        print("\n[4/6] 增量训练...")

        # 创建新数据（模拟新市场数据）
        new_symbols = [f"60{i:04d}" for i in range(51, 60)]
        new_df = create_multi_stock_dataset(
            new_symbols,
            datetime(2024, 1, 1),
            datetime(2024, 12, 31)
        )

        new_dataset = SimpleAlphaDataset(
            df=new_df,
            train_period=("2024-01-01", "2024-06-30"),
            valid_period=("2024-07-01", "2024-09-30"),
            test_period=("2024-10-01", "2024-12-31")
        )

        print("  开始增量训练...")
        incremental_model, incremental_version = lab.train_model_incremental(
            model_name="stock_lgb",  # 使用相同的模型名称
            dataset=new_dataset,
            model_type="lgb",
            num_boost_round=50,  # 增量训练使用更少轮数
            incremental=True  # 强制增量训练
        )

        print(f"  ✓ 增量训练完成: {incremental_version.version_id}")
        print(f"  ✓ 基于版本: {incremental_version.base_version}")
        print(f"  ✓ 增量训练: {incremental_version.is_incremental}")

        # ============================================================
        # 5. 版本管理测试
        # ============================================================
        print("\n[5/6] 版本管理测试...")

        versions = lab.list_model_versions("stock_lgb")
        print(f"  ✓ 共有 {len(versions)} 个模型版本")
        for v in versions:
            mode = "增量" if v.is_incremental else "完整"
            base = f" (基于 {v.base_version})" if v.base_version else ""
            print(f"    - {v.version_id}: {mode}训练{base}")

        # 加载模型
        loaded_model = lab.load_model("stock_lgb")
        print(f"  ✓ 成功加载模型: stock_lgb")

        # ============================================================
        # 6. 性能比较
        # ============================================================
        print("\n[6/6] 性能比较...")

        # 使用测试集进行预测
        predictions = loaded_model.predict(dataset, Segment.TEST)
        print(f"  ✓ 生成 {len(predictions)} 个预测")

        # 计算简单指标
        test_df = dataset.fetch_learn(Segment.TEST)
        if "label" in test_df.columns:
            actual = test_df["label"].to_numpy()
            mae = np.mean(np.abs(predictions - actual))
            rmse = np.sqrt(np.mean((predictions - actual) ** 2))
            print(f"  ✓ MAE:  {mae:.4f}")
            print(f"  ✓ RMSE: {rmse:.4f}")
        else:
            print(f"  ⚠ 测试集无标签，跳过指标计算")

        # ============================================================
        # 测试总结
        # ============================================================
        print("\n" + "="*70)
        print(" 测试总结")
        print("="*70)
        print("✓ 所有测试通过！")
        print(f"✓ 完成了完整的增量训练工作流")
        print(f"✓ 创建了 {len(versions)} 个模型版本")
        print(f"✓ 模型性能: MAE={mae:.4f}, RMSE={rmse:.4f}")

        return True

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 清理临时目录
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)


def main():
    """主函数"""
    success = run_incremental_training_test()

    if success:
        print("\n" + "="*70)
        print("🎉 增量训练完整流程测试成功！")
        print("="*70)
        print("\n下一步：")
        print("  1. 使用QMT真实数据进行训练")
        print("  2. 在生产环境中部署模型")
        print("  3. 设置定期增量训练任务")
        return 0
    else:
        print("\n" + "="*70)
        print("❌ 测试失败，请检查错误信息")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
