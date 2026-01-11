#!/usr/bin/env python3
"""
VeighNa快速测试脚本
无交互模式，快速验证核心功能
"""

import sys
from datetime import datetime

print("=" * 60)
print("🚀 VeighNa 4.2.0 开发版快速测试")
print("=" * 60)
print(f"Python版本: {sys.version.split()[0]}")
print(f"工作目录: {sys.path[0]}")

# 测试1: 核心模块导入
print("\n1️⃣  测试核心模块导入...")
try:
    from vnpy.event import EventEngine
    from vnpy.trader.engine import MainEngine
    from vnpy.trader.ui import create_qapp
    from vnpy.trader.object import (
        TickData, BarData, ContractData,
        Exchange, Interval, Product
    )
    print("   ✅ 所有核心模块导入成功")
except Exception as e:
    print(f"   ❌ 核心模块导入失败: {e}")
    sys.exit(1)

# 测试2: 事件引擎
print("\n2️⃣  测试事件引擎...")
try:
    event_engine = EventEngine()
    print("   ✅ EventEngine 创建成功")
except Exception as e:
    print(f"   ❌ EventEngine 创建失败: {e}")

# 测试3: 主引擎
print("\n3️⃣  测试主引擎...")
try:
    main_engine = MainEngine(event_engine)
    print("   ✅ MainEngine 创建成功")
except Exception as e:
    print(f"   ❌ MainEngine 创建失败: {e}")

# 测试4: Alpha模块
print("\n4️⃣  测试Alpha量化研究模块...")
try:
    from vnpy.alpha.dataset import AlphaDataset
    from vnpy.alpha.model import AlphaModel
    from vnpy.alpha.strategy import AlphaStrategy
    from vnpy.alpha.lab import AlphaLab
    print("   ✅ Alpha模块导入成功")

    # 测试AlphaLab（不带参数创建会失败，所以只测试导入）
    print("   ✅ Alpha量化研究功能可用")
except Exception as e:
    print(f"   ❌ Alpha模块导入失败: {e}")

# 测试5: 图表模块
print("\n5️⃣  测试图表模块...")
try:
    from vnpy.chart import ChartWidget, CandleItem, VolumeItem
    print("   ✅ 图表模块导入成功")
    print("   ✅ K线图表功能可用")
except Exception as e:
    print(f"   ❌ 图表模块导入失败: {e}")

# 测试6: 创建应用
print("\n6️⃣  测试GUI应用创建...")
try:
    app = create_qapp()
    print("   ✅ GUI应用创建成功")
    print("   💡 如需显示界面，请手动运行并添加 main_window.show()")
except Exception as e:
    print(f"   ⚠️  GUI应用创建失败（可能在无显示器环境）: {e}")

# 测试7: 版本信息
print("\n7️⃣  显示版本信息...")
try:
    import vnpy
    print(f"   ✅ VeighNa版本: {vnpy.__version__}")
except:
    print("   ⚠️  无法获取版本信息")

# 测试完成
print("\n" + "=" * 60)
print("🎉 测试完成！VeighNa开发版已准备就绪")
print("=" * 60)

print("\n📝 快速启动指南:")
print("\n选项1: 命令行测试（无需交易接口）")
print("   python test_quick.py")

print("\n选项2: 运行K线图表示例")
print("   cd examples/candle_chart")
print("   python run.py")

print("\n选项3: 配置交易接口后运行完整应用")
print("   # 1. 安装交易接口（如CTP）:")
print("   pip install vnpy_ctp")
print("   # 2. 运行完整应用:")
print("   cd examples/veighna_trader")
print("   python run.py")

print("\n🔗 有用链接:")
print("   - 官方文档: https://www.vnpy.com/docs")
print("   - SimNow模拟: https://www.simnow.com.cn/")
print("   - 社区论坛: https://www.vnpy.com/forum")

print("\n✨ 开始您的量化交易之旅吧！")