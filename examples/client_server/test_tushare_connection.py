"""
测试 Tushare 连接

验证 Tushare token 是否正确配置并可以获取数据。
"""
import os
import sys
from datetime import date

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_tushare_connection():
    """测试 Tushare 连接"""
    print("=== Tushare 连接测试 ===\n")

    # 1. 检查环境变量
    token = os.getenv("TUSHARE_TOKEN", "")
    print(f"1. 环境变量检查:")
    print(f"   TUSHARE_TOKEN: {'***已设置***' if token else '未设置'}")

    if not token:
        print("\n   错误: TUSHARE_TOKEN 环境变量未设置!")
        print("   请设置环境变量:")
        print("   export TUSHARE_TOKEN=你的token")
        return False

    # 2. 测试 Tushare API
    print(f"\n2. 测试 Tushare API:")
    try:
        import tushare as ts
        print("   tushare 库已安装")

        pro = ts.pro_api(token)
        print("   Pro API 初始化成功")

        # 测试获取 token 信息
        try:
            token_info = pro.token
            print(f"   Token 有效: ✓")
        except Exception as e:
            print(f"   Token 验证失败: {e}")
            return False

        # 3. 测试获取龙虎榜数据
        print(f"\n3. 测试龙虎榜数据查询:")
        trade_date = date.today().strftime("%Y%m%d")
        print(f"   查询日期: {trade_date}")

        df = pro.top_list(trade_date=trade_date)
        print(f"   数据行数: {len(df)}")

        if len(df) > 0:
            print(f"   ✓ 成功获取 {len(df)} 条龙虎榜记录")
            print(f"\n   前3条记录:")
            for idx, row in df.head(3).iterrows():
                print(f"   {idx+1}. {row['ts_code']} {row['name']} 净买入: {row.get('amount_buy', 0)/10000:.2f}万")
            return True
        else:
            print(f"   今天没有龙虎榜数据（可能是非交易日）")
            return True

    except ImportError as e:
        print(f"   ✗ tushare 库未安装: {e}")
        print("   请运行: pip install tushare")
        return False
    except Exception as e:
        print(f"   ✗ API 调用失败: {e}")
        return False

    return True


def test_config_loading():
    """测试配置加载"""
    print("\n\n=== 配置加载测试 ===\n")

    try:
        from vnpy_china_config import ConfigManager
        print("ConfigManager 导入成功")

        config_manager = ConfigManager()
        config = config_manager.get_config("data")
        print(f"Data config 加载成功")

        print(f"\ntushare_token 配置值: {'***已设置***' if config.tushare_token else '未设置'}")

        if config.tushare_token:
            print("   ✓ 配置中有 token")
        else:
            print("   ✗ 配置中没有 token")
            print("   可能原因:")
            print("   1. 配置文件中使用环境变量引用但环境变量未设置")
            print("   2. 配置文件未正确加载")

    except Exception as e:
        print(f"配置加载失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 测试 Tushare 连接
    tushare_ok = test_tushare_connection()

    # 测试配置加载
    test_config_loading()

    print("\n\n=== 总结 ===")
    if tushare_ok:
        print("✓ Tushare API 可用，龙虎榜数据应该能正常获取")
    else:
        print("✗ Tushare API 不可用，请检查:")
        print("  1. TUSHARE_TOKEN 环境变量是否设置")
        print("  2. tushare 库是否安装: pip install tushare")
        print("  3. Token 是否有效")
