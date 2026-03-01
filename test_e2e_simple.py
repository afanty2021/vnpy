#!/usr/bin/env python3
"""
VeighNa A股交易系统端到端测试 - 简化版

使用方法：
    conda run -n Quant-3.11 python test_e2e_simple.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_1_database():
    """测试1: 数据库连接"""
    print("\n" + "="*50)
    print("测试1: 数据库连接")
    print("="*50)

    try:
        from vnpy_china_config import ConfigManager

        cfg = ConfigManager()
        global_config = cfg.load_global_config()
        db = global_config.database

        import pymysql
        conn = pymysql.connect(
            host=db.mysql_host,
            port=db.mysql_port,
            user=db.mysql_user,
            password=db.mysql_password,
            database=db.mysql_database,
            charset='utf8mb4'
        )

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM db_bar_data")
        bar_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM db_bar_data")
        stock_count = cursor.fetchone()[0]

        cursor.execute("SELECT MIN(datetime), MAX(datetime) FROM db_bar_data")
        date_range = cursor.fetchone()

        conn.close()

        print(f"✓ K线记录数: {bar_count:,}")
        print(f"✓ 股票数量: {stock_count}")
        print(f"✓ 日期范围: {date_range[0]} ~ {date_range[1]}")

        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        return False


def test_2_data_query():
    """测试2: 数据查询"""
    print("\n" + "="*50)
    print("测试2: 数据查询")
    print("="*50)

    try:
        from vnpy_china_data.service import ChinaDataService
        from vnpy.trader.constant import Exchange, Interval

        service = ChinaDataService()
        service.connect()

        end = datetime.now()
        start = end - timedelta(days=30)

        bars = service.get_bar_data(
            symbol="000001",
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
            start=start,
            end=end
        )

        service.disconnect()

        print(f"✓ 查询000001: {len(bars)} 条")

        if bars:
            print(f"  最新价: {bars[-1].close}")

        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"✗ 失败: {e}")
        return False


def test_3_alpha158():
    """测试3: Alpha158因子计算"""
    print("\n" + "="*50)
    print("测试3: Alpha158因子计算")
    print("="*50)

    try:
        from vnpy_china_data.service import ChinaDataService
        from vnpy.trader.constant import Exchange, Interval
        from vnpy.alpha.dataset.datasets.alpha_158 import Alpha158
        from vnpy.alpha import AlphaDataset
        from vnpy.alpha.dataset import Segment
        import numpy as np
        from datetime import datetime

        # 加载数据
        service = ChinaDataService()
        service.connect()

        symbols = ["000001", "000002"]
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

        print(f"总数据: {len(all_bars)} 条")

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

        # 计算Alpha158因子
        print("计算Alpha158因子...")
        alpha_158 = Alpha158()
        df = alpha_158.calculate(dataset)

        print(f"✓ 因子形状: {df.shape}")
        print(f"✓ 特征列数: {len([c for c in df.columns if c.startswith('alpha')])}")

        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"✗ 失败: {e}")
        return False


def test_4_model():
    """测试4: 模型训练"""
    print("\n" + "="*50)
    print("测试4: 模型训练")
    print("="*50)

    try:
        from vnpy_china_data.service import ChinaDataService
        from vnpy.trader.constant import Exchange, Interval
        from vnpy.alpha.model.models.lgb_model import LgbModel
        import numpy as np
        from datetime import datetime

        # 加载数据
        service = ChinaDataService()
        service.connect()

        symbols = [f"{i:06d}" for i in range(1, 6)]  # 000001-000005
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

        print(f"总数据: {len(all_bars)} 条")

        # 准备简单特征
        if len(all_bars) < 50:
            print("✗ 数据不足")
            return False

        # 提取收盘价序列
        closes = np.array([b.close for b in all_bars])
        volumes = np.array([b.volume for b in all_bars])

        # 简单特征：收益率、成交量变化
        returns = np.diff(closes) / closes[:-1]
        volume_change = np.diff(volumes) / (volumes[:-1] + 1e-8)

        # 标签：未来5日收益率
        future_returns = (closes[5:] - closes[:-5]) / closes[:-5]

        # 对齐
        min_len = min(len(returns), len(volume_change), len(future_returns))
        X = np.column_stack([
            returns[-min_len:],
            volume_change[-min_len:]
        ])
        y = future_returns[-min_len:]

        # 过滤NaN
        valid = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X = X[valid]
        y = y[valid]

        print(f"训练数据: {X.shape}")

        # 训练
        print("训练模型...")
        model = LgbModel()

        split = int(len(X) * 0.8)
        model.train(
            X_train=X[:split],
            y_train=y[:split],
            X_val=X[split:],
            y_val=y[split:],
            num_boost_round=50,
        )

        # 保存
        model_path = Path.home() / "vnpy_lab/model/test_e2e_lgb.txt"
        model_path.parent.mkdir(parents=True, exist_ok=True)
        model.save(str(model_path))

        print(f"✓ 模型已保存: {model_path}")

        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"✗ 失败: {e}")
        return False


def test_5_rpc():
    """测试5: RPC连接"""
    print("\n" + "="*50)
    print("测试5: RPC-QMT连接")
    print("="*50)

    try:
        from vnpy_china_config import ConfigManager
        from vnpy.rpc import RpcClient
        import time

        cfg = ConfigManager()
        global_config = cfg.load_global_config()

        rpc_config = global_config.rpc

        print(f"尝试连接: {rpc_config.rep_address}")

        class TestClient(RpcClient):
            def __init__(self):
                super().__init__()
                self.received = []

            def callback(self, topic, data):
                self.received.append((topic, data))

        client = TestClient()

        try:
            client.start(rpc_config.rep_address, rpc_config.pub_address)
            time.sleep(1)

            contracts = client.query_contracts(timeout=3000)
            print(f"✓ 查询到合约: {len(contracts) if contracts else 0} 个")

            client.stop()
            return True

        except Exception as e:
            print(f"⚠ RPC服务器未启动: {e}")
            print("  (需要在Windows上运行run_qmt_server.py)")
            return False

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"✗ 失败: {e}")
        return False


def test_6_signals():
    """测试6: 信号生成"""
    print("\n" + "="*50)
    print("测试6: 信号生成")
    print("="*50)

    try:
        from vnpy_china_data.service import ChinaDataService
        from vnpy.trader.constant import Exchange, Interval
        from datetime import datetime

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

            if len(bars) >= 2:
                latest = bars[-1]
                prev = bars[-2]
                change = (latest.close - prev.close) / prev.close

                if change > 0.02:
                    signal = "做多"
                elif change < -0.02:
                    signal = "做空"
                else:
                    signal = "持仓"

                signals.append({"symbol": sym, "signal": signal, "change": f"{change*100:.2f}%"})
                print(f"  {sym}: {signal} ({change*100:.2f}%)")

        service.disconnect()

        print(f"✓ 生成 {len(signals)} 个信号")

        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"✗ 失败: {e}")
        return False


def main():
    print("="*50)
    print("VeighNa A股系统 端到端测试")
    print(f"时间: {datetime.now()}")
    print("="*50)

    results = {}

    results["数据库连接"] = test_1_database()
    results["数据查询"] = test_2_data_query()
    results["Alpha158因子"] = test_3_alpha158()
    results["模型训练"] = test_4_model()
    results["RPC连接"] = test_5_rpc()
    results["信号生成"] = test_6_signals()

    print("\n" + "="*50)
    print("测试总结")
    print("="*50)

    for name, passed in results.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {name}")

    passed = sum(1 for v in results.values() if v)
    print(f"\n通过: {passed}/{len(results)}")

    if passed == len(results):
        print("\n🎉 全部通过!")
    else:
        print(f"\n⚠️  {len(results) - passed} 项失败")


if __name__ == "__main__":
    main()
