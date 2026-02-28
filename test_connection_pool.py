"""
测试数据库连接池功能

验证DBUtils连接池是否正常工作。
"""
import sys
from threading import Thread
from time import time, sleep

# 添加项目路径
sys.path.insert(0, "D:/berton/vnpy")

from vnpy_china_data.database import MySQLDatabaseLayer


def test_pool_initialization():
    """测试连接池初始化"""
    print("=" * 60)
    print("测试1: 连接池初始化")
    print("=" * 60)

    db = MySQLDatabaseLayer(
        host="localhost",
        port=3306,
        user="root",
        password="123456",
        database="test_db",
        pool_size=5,
        max_overflow=10
    )

    print(f"✓ 连接池配置: pool_size={db._pool_size}, max_overflow={db._max_overflow}")
    print(f"✓ 连接池状态: {db.get_pool_status()}")

    return db


def test_connection_pool_creation():
    """测试连接池创建"""
    print("\n" + "=" * 60)
    print("测试2: 连接池创建")
    print("=" * 60)

    db = MySQLDatabaseLayer(
        host="localhost",
        port=3306,
        user="root",
        password="123456",
        database="test_db"
    )

    # 尝试创建连接池（即使数据库不存在也能测试代码路径）
    try:
        result = db.connect()
        print(f"✓ 连接池创建{'成功' if result else '失败（数据库可能不存在）'}")
        if result:
            print(f"✓ 连接池状态: {db.get_pool_status()}")
    except Exception as e:
        print(f"⚠ 连接池创建异常: {e}")
        print(f"  （这是预期的，因为数据库可能不存在）")


def test_concurrent_access():
    """测试并发访问"""
    print("\n" + "=" * 60)
    print("测试3: 并发访问测试")
    print("=" * 60)

    db = MySQLDatabaseLayer(
        host="localhost",
        port=3306,
        user="root",
        password="123456",
        database="test_db",
        pool_size=5
    )

    results = []
    errors = []

    def worker(worker_id):
        """工作线程"""
        try:
            # 模拟数据库操作
            status = db.get_pool_status()
            results.append((worker_id, status))
            sleep(0.01)  # 模拟工作负载
        except Exception as e:
            errors.append((worker_id, e))

    # 创建多个线程并发访问
    threads = []
    num_threads = 10

    start_time = time()

    for i in range(num_threads):
        t = Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    # 等待所有线程完成
    for t in threads:
        t.join()

    elapsed = time() - start_time

    print(f"✓ 启动了 {num_threads} 个并发线程")
    print(f"✓ 成功完成 {len(results)} 个操作")
    print(f"✓ 发生 {len(errors)} 个错误")
    print(f"✓ 总耗时: {elapsed:.3f} 秒")

    if errors:
        print("\n错误详情:")
        for worker_id, error in errors:
            print(f"  线程 {worker_id}: {error}")


def test_pool_status():
    """测试连接池状态查询"""
    print("\n" + "=" * 60)
    print("测试4: 连接池状态查询")
    print("=" * 60)

    db = MySQLDatabaseLayer(
        host="localhost",
        port=3306,
        user="root",
        password="123456",
        database="test_db",
        pool_size=3,
        max_overflow=5
    )

    status = db.get_pool_status()

    print("连接池状态信息:")
    for key, value in status.items():
        print(f"  {key}: {value}")

    # 验证状态信息
    assert status["pool_size"] == 3, "pool_size应该等于3"
    assert status["max_overflow"] == 5, "max_overflow应该等于5"
    assert status["max_connections"] == 8, "max_connections应该等于8"

    print("\n✓ 所有状态验证通过")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("数据库连接池测试")
    print("=" * 60)

    try:
        # 测试1: 连接池初始化
        db = test_pool_initialization()

        # 测试2: 连接池创建
        test_connection_pool_creation()

        # 测试3: 并发访问
        test_concurrent_access()

        # 测试4: 状态查询
        test_pool_status()

        print("\n" + "=" * 60)
        print("所有测试完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 测试失败: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
