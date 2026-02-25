"""
测试Tushare资金流向数据获取（直接API测试）
"""

import os
import tushare as ts
from datetime import date, timedelta

def test_tushare_moneyflow():
    """测试Tushare资金流向数据获取"""
    # 获取Token
    token = os.getenv("TUSHARE_TOKEN", "")
    if not token:
        print("错误: TUSHARE_TOKEN 环境变量未设置")
        print("请设置环境变量: export TUSHARE_TOKEN=your_token")
        return

    print(f"Tushare Token: {token[:10]}...")

    # 初始化API
    pro = ts.pro_api(token)

    # 测试资金流向接口
    print("\n正在测试 moneyflow 接口...")

    # 获取最近的交易日期
    today = date.today()
    test_date = today - timedelta(days=1)  # 昨天

    # 尝试多个日期
    for days_offset in range(10):
        test_date = today - timedelta(days=days_offset)
        date_str = test_date.strftime("%Y%m%d")

        print(f"\n尝试获取 {date_str} 的数据...")

        try:
            # 获取平安银行(000001.SZ)的资金流向数据
            df = pro.moneyflow(
                ts_code="000001.SZ",
                trade_date=date_str
            )

            if not df.empty:
                print(f"成功获取 {date_str} 的数据！")
                print(f"\n共 {len(df)} 条记录")
                print("\n数据示例:")
                print(df.head().to_string())

                # 解析第一条数据
                row = df.iloc[0]
                print(f"\n资金流向详情:")
                print(f"  交易日期: {row['trade_date']}")
                print(f"  收盘价: {row['close']}")
                print(f"  涨跌幅: {row['pct_chg']}%")
                print(f"\n  超大单净流入: {row['buy_m_vol_elg'] - row['sell_m_vol_elg']} 手")
                print(f"  大单净流入: {row['buy_m_vol_lg'] - row['sell_m_vol_lg']} 手")
                print(f"  中单净流入: {row['buy_m_vol_md'] - row['sell_m_vol_md']} 手")
                print(f"  小单净流入: {row['buy_m_vol_sm'] - row['sell_m_vol_sm']} 手")

                return True
            else:
                print(f"{date_str} 无数据")

        except Exception as e:
            print(f"获取 {date_str} 数据失败: {e}")
            continue

    print("\n未获取到任何数据")
    print("可能原因:")
    print("1. Tushare Token 权限不足（需要积分才能访问moneyflow接口）")
    print("2. 测试的日期都不是交易日")
    print("3. 网络连接问题")
    return False


if __name__ == "__main__":
    test_tushare_moneyflow()
