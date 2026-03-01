#!/usr/bin/env python3
"""
VeighNa A股交易系统端到端测试

测试范围：
1. 数据库连接和数据查询
2. Alpha158因子计算
3. LightGBM模型训练
4. RPC-QMT连接（如果服务器可用）
5. 实时信号生成

使用方法：
    conda run -n Quant-3.11 python test_e2e_full.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def print_header(title: str) -> None:
    """打印测试标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_result(name: str, passed: bool, detail: str = "") -> None:
    """打印测试结果"""
    status = "✓ 通过" if passed else "✗ 失败"
    print(f"[{status}] {name}")
    if detail:
        print(f"       {detail}")


# ==================== 测试1: 数据库连接 ====================

def test_database_connection() -> bool:
    """测试数据库连接"""
    print_header("测试1: 数据库连接")

    try:
        from vnpy_china_config import ConfigManager

        cfg = ConfigManager()
        global_config = cfg.load_global_config()
        db = global_config.database

        print(f"数据库配置:")
        print(f"  Host: {db.mysql_host}:{db.mysql_port}")
        print(f"  User: {db.mysql_user}")
        print(f"  Database: {db.mysql_database}")

        # 测试连接
        import pymysql
        conn = pymysql.connect(
            host=db.mysql_host,
            port=db.mysql_port,
            user=db.mysql_user,
            password=db.mysql_password,
            database=db.mysql_database,
            charset='utf8mb4'
        )

        # 获取统计信息
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM db_bar_data")
        bar_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM db_bar_data")
        stock_count = cursor.fetchone()[0]

        cursor.execute("SELECT MIN(datetime), MAX(datetime) FROM db_bar_data")
        date_range = cursor.fetchone()

        conn.close()

        print(f"\n数据库统计:")
        print(f"  K线记录数: {bar_count:,}")
        print(f"  股票数量: {stock_count}")
        print(f"  日期范围: {date_range[0]} ~ {date_range[1]}")

        print_result("数据库连接", True)
        return True

    except Exception as e:
        print_result("数据库连接", False, str(e))
        return False


# ==================== 测试2: 数据查询 ====================

def test_data_query() -> bool:
    """测试数据查询功能"""
    print_header("测试2: 数据查询")

    try:
        from vnpy_china_data.service import ChinaDataService
        from vnpy.trader.constant import Exchange, Interval

        service = ChinaDataService()
        service.connect()

        # 测试查询单只股票
        symbol = "000001"
        end = datetime.now()
        start = end - timedelta(days=30)

        bars = service.get_bar_data(
            symbol=symbol,
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
            start=start,
            end=end
        )

        print(f"\n查询测试 - {symbol}:")
        print(f"  请求范围: {start.date()} ~ {end.date()}")
        print(f"  返回数据: {len(bars)} 条")

        if bars:
            print(f"  首条: {bars[0].datetime} O:{bars[0].open} H:{bars[0].high} L:{bars[0].low} C:{bars[0].close}")
            print(f"  末条: {bars[-1].datetime} O:{bars[-1].open} H:{bars[-1].high} L:{bars[-1].low} C:{bars[-1].close}")

        # 测试批量查询
        symbols = ["000001", "000002", "000004"]
        print(f"\n批量查询测试:")

        for sym in symbols:
            bars = service.get_bar_data(
                symbol=sym,
                exchange=Exchange.SZSE,
                interval=Interval.DAILY,
                start=start,
                end=end
            )
            print(f"  {sym}: {len(bars)} 条")

        service.disconnect()

        print_result("数据查询", True)
        return True

    except Exception as e:
        import traceback
        traceback.print_exc()
        print_result("数据查询", False, str(e))
        return False


# ==================== 测试3: Alpha158因子计算 ====================

def test_alpha158() -> bool:
    """测试Alpha158因子计算"""
    print_header("测试3: Alpha158因子计算")

    try:
        from vnpy_china_data.service import ChinaDataService
        from vnpy.trader.constant import Exchange, Interval
        from vnpy.alpha import AlphaDataset
        from vnpy.alpha.dataset import Segment
        from vnpy.alpha.dataset.datasets.alpha_158 import Alpha158
        import polars as pl
        from datetime import datetime, timedelta

        print("加载数据...")

        # 加载3只股票的数据
        service = ChinaDataService()
        service.connect()

        symbols = ["000001", "000002", "000004"]
        end = datetime(2026, 2, 20)
        start = datetime(2025, 1, 1)

        all_bars = []
        for sym in symbols:
            bars = service.get_bar_data(
                symbol=sym,
                exchange=Exchange.SZSE,
                interval=Interval.DAILY,
                start=start,
                end=end
            )
            print(f"  {sym}: {len(bars)} 条")
            all_bars.extend(bars)

        service.disconnect()

        if len(all_bars) < 100:
            print_result("Alpha158因子计算", False, "数据量不足")
            return False

        print(f"\n总数据量: {len(all_bars)} 条")

        # 创建数据集
        print("\n创建AlphaDataset...")

        # 准备数据格式
        segment = Segment(
            symbol="000001",
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
            start=start,
            end=end,
            bars=all_bars
        )

        dataset = AlphaDataset(
            segments=[segment],
            forward_days=5,
            train_start=datetime(2025, 1, 1),
            train_end=datetime(2025, 6, 30),
            val_start=datetime(2025, 7, 1),
            val_end=datetime(2025, 9, 30),
            test_start=datetime(2025, 10, 1),
            test_end=datetime(2026, 2, 20),
        )

        # 计算Alpha158因子
        print("\n计算Alpha158因子...")
        alpha_158 = Alpha158()
        df = alpha_158.calculate(dataset)

        print(f"\n因子计算结果:")
        print(f"  形状: {df.shape}")
        print(f"  列数: {len(df.columns)}")

        # 显示前几列
        print(f"  列名示例: {df.columns[:10]}")

        print_result("Alpha158因子计算", True)
        return True

    except Exception as e:
        import traceback
        traceback.print_exc()
        print_result("Alpha158因子计算", False, str(e))
        return False


# ==================== 测试4: 模型训练 ====================

def test_model_training() -> bool:
    """测试模型训练"""
    print_header("测试4: LightGBM模型训练")

    try:
        from vnpy_china_data.service import ChinaDataService
        from vnpy.trader.constant import Exchange, Interval
        from vnpy.alpha import AlphaDataset
        from vnpy.alpha.dataset import Segment
        from vnpy.alpha.dataset.datasets.alpha_158 import Alpha158
        from vnpy.alpha.model.models.lgb_model import LgbModel
        import lightgbm as lgb
        from datetime import datetime

        print("加载训练数据...")

        # 加载10只股票的数据
        service = ChinaDataService()
        service.connect()

        symbols = [f"{i:06d}" for i in range(1, 11)]  # 000001-000010
        end = datetime(2026, 2, 20)
        start = datetime(2025, 1, 1)

        all_bars = []
        for sym in symbols:
            bars = service.get_bar_data(
                symbol=sym,
                exchange=Exchange.SZSE,
                interval=Interval.DAILY,
                start=start,
                end=end
            )
            if len(bars) > 50:
                all_bars.extend(bars)
                print(f"  {sym}: {len(bars)} 条")

        service.disconnect()

        print(f"\n总数据量: {len(all_bars)} 条")

        # 创建数据集
        segment = Segment(
            symbol="000001",
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
            start=start,
            end=end,
            bars=all_bars
        )

        dataset = AlphaDataset(
            segments=[segment],
            forward_days=5,
            train_start=datetime(2025, 1, 1),
            train_end=datetime(2025, 6, 30),
            val_start=datetime(2025, 7, 1),
            val_end=datetime(2025, 9, 30),
            test_start=datetime(2025, 10, 1),
            test_end=datetime(2026, 2, 20),
        )

        # 计算因子
        print("\n计算Alpha158因子...")
        alpha_158 = Alpha158()
        df = alpha_158.calculate(dataset)

        # 准备训练数据
        import numpy as np
        import polars as pl

        # 提取特征和标签
        feature_cols = [c for c in df.columns if c not in ['symbol', 'datetime', 'target']]
        X = df['feature'].to_numpy()
        y = df['target'].to_numpy()

        # 过滤NaN
        valid_mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X = X[valid_mask]
        y = y[valid_mask]

        print(f"\n训练数据:")
        print(f"  样本数: {len(X)}")
        print(f"  特征数: {X.shape[1]}")

        # 训练模型
        print("\n训练LightGBM模型...")

        model = LgbModel()
        model.train(
            X_train=X[:int(len(X)*0.7)],
            y_train=y[:int(len(y)*0.7)],
            X_val=X[int(len(X)*0.7):],
            y_val=y[int(len(y)*0.7):],
            num_boost_round=100,
        )

        # 保存模型
        model_path = Path.home() / "vnpy_lab/model/test_lgb.txt"
        model_path.parent.mkdir(parents=True, exist_ok=True)
        model.save(str(model_path))

        print(f"\n模型已保存: {model_path}")

        print_result("LightGBM模型训练", True)
        return True

    except Exception as e:
        import traceback
        traceback.print_exc()
        print_result("LightGBM模型训练", False, str(e))
        return False


# ==================== 测试5: RPC连接 ====================

def test_rpc_connection() -> bool:
    """测试RPC-QMT连接"""
    print_header("测试5: RPC-QMT连接")

    try:
        from vnpy_china_config import ConfigManager
        from vnpy.rpc import RpcClient
        import time

        cfg = ConfigManager()
        global_config = cfg.load_global_config()

        rpc_config = global_config.rpc
        qmt_config = global_config.qmt

        print(f"RPC配置:")
        print(f"  REQ地址: {rpc_config.rep_address}")
        print(f"  SUB地址: {rpc_config.pub_address}")
        print(f"  QMT启用: {qmt_config.enabled}")
        print(f"  使用RPC: {qmt_config.use_rpc}")

        # 尝试连接
        print("\n尝试连接RPC服务器...")

        class TestClient(RpcClient):
            def __init__(self):
                super().__init__()
                self.received = []

            def callback(self, topic: str, data) -> None:
                self.received.append((topic, data))

        client = TestClient()

        try:
            client.start(rpc_config.rep_address, rpc_config.pub_address)
            time.sleep(1)

            print("  ✓ RPC客户端已启动")

            # 尝试查询
            try:
                contracts = client.query_contracts(timeout=3000)
                print(f"  ✓ 查询到合约: {len(contracts) if contracts else 0} 个")
            except Exception as e:
                print(f"  ⚠ 查询失败: {e}")

            client.stop()
            print("  ✓ RPC连接测试通过")

            print_result("RPC-QMT连接", True)
            return True

        except Exception as e:
            print(f"  ✗ 连接失败: {e}")
            print(f"  提示: 确保Windows QMT RPC服务器已启动")
            print_result("RPC-QMT连接", False, str(e))
            return False

    except Exception as e:
        import traceback
        traceback.print_exc()
        print_result("RPC-QMT连接", False, str(e))
        return False


# ==================== 测试6: 实时信号生成 ====================

def test_realtime_signals() -> bool:
    """测试实时信号生成"""
    print_header("测试6: 实时信号生成")

    try:
        from vnpy_china_data.service import ChinaDataService
        from vnpy.trader.constant import Exchange, Interval
        import numpy as np
        from datetime import datetime

        print("模拟实时信号生成...")

        # 加载数据
        service = ChinaDataService()
        service.connect()

        symbols = ["000001", "000002", "000004"]
        end = datetime(2026, 2, 20)
        start = end - timedelta(days=60)

        signals = []

        for sym in symbols:
            bars = service.get_bar_data(
                symbol=sym,
                exchange=Exchange.SZSE,
                interval=Interval.DAILY,
                start=start,
                end=end
            )

            if len(bars) >= 30:
                # 简单策略：当日涨幅 > 2% 做多，< -2% 做空
                latest = bars[-1]
                prev = bars[-2]

                change = (latest.close - prev.close) / prev.close

                if change > 0.02:
                    signal = "做多"
                elif change < -0.02:
                    signal = "做空"
                else:
                    signal = "持仓"

                signals.append({
                    "symbol": sym,
                    "signal": signal,
                    "change": f"{change*100:.2f}%",
                    "price": latest.close
                })

                print(f"  {sym}: {signal} (涨跌幅: {change*100:.2f}%)")

        service.disconnect()

        # 统计
        long_count = sum(1 for s in signals if s["signal"] == "做多")
        short_count = sum(1 for s in signals if s["signal"] == "做空")
        hold_count = sum(1 for s in signals if s["signal"] == "持仓")

        print(f"\n信号统计:")
        print(f"  做多: {long_count}")
        print(f"  做空: {short_count}")
        print(f"  持仓: {hold_count}")

        print_result("实时信号生成", True)
        return True

    except Exception as e:
        import traceback
        traceback.print_exc()
        print_result("实时信号生成", False, str(e))
        return False


# ==================== 主函数 ====================

def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("  VeighNa A股交易系统 端到端测试")
    print("="*60)
    print(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Python版本: {sys.version}")

    # 运行所有测试
    results = {}

    # 测试1: 数据库连接
    results["数据库连接"] = test_database_connection()

    # 测试2: 数据查询
    results["数据查询"] = test_data_query()

    # 测试3: Alpha158因子
    results["Alpha158因子"] = test_alpha158()

    # 测试4: 模型训练
    results["模型训练"] = test_model_training()

    # 测试5: RPC连接（可选）
    print("\n[可选] 测试RPC连接需要Windows QMT服务器运行中")
    results["RPC连接"] = test_rpc_connection()

    # 测试6: 实时信号
    results["实时信号"] = test_realtime_signals()

    # 打印总结
    print_header("测试总结")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✓" if result else "✗"
        print(f"  {status} {name}")

    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️  {total - passed} 项测试失败")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
