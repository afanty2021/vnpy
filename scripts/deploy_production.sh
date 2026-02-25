#!/bin/bash
# VeighNa A股交易系统 - 生产环境部署脚本
#
# 使用方法：
# bash scripts/deploy_production.sh

set -e  # 遇到错误立即退出

echo "======================================"
echo "VeighNa A股交易系统 - 生产环境部署"
echo "======================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "${GREEN}✓ 项目目录: $PROJECT_ROOT${NC}"

# 1. 环境检查
echo ""
echo "=== 1. 环境检查 ==="

# 检查 Python
if ! command -v python &> /dev/null; then
    echo -e "${RED}✗ Python 未安装${NC}"
    exit 1
fi
PYTHON_VERSION=$(python --version | awk '{print $2}')
echo -e "${GREEN}✓ Python 版本: $PYTHON_VERSION${NC}"

# 检查 MySQL
if ! command -v mysql &> /dev/null; then
    echo -e "${YELLOW}⚠ MySQL 命令未找到，请手动检查${NC}"
else
    MYSQL_VERSION=$(mysql --version)
    echo -e "${GREEN}✓ $MYSQL_VERSION${NC}"
fi

# 检查 Redis
if ! command -v redis-cli &> /dev/null; then
    echo -e "${YELLOW}⚠ Redis 命令未找到，请手动检查${NC}"
else
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✓ Redis 运行中${NC}"
    else
        echo -e "${RED}✗ Redis 未运行${NC}"
        exit 1
    fi
fi

# 2. 创建目录结构
echo ""
echo "=== 2. 创建目录结构 ==="

DIRS=(".vntrader_china/config" ".vntrader_china/logs" ".vntrader_china/data" "logs" "data")
for dir in "${DIRS[@]}"; do
    mkdir -p "$dir"
    echo -e "${GREEN}✓ 创建目录: $dir${NC}"
done

# 3. 配置文件部署
echo ""
echo "=== 3. 部署配置文件 ==="

CONFIG_FILES=("global_production.yaml" "data_production.yaml" "monitor_production.yaml")
for config in "${CONFIG_FILES[@]}"; do
    if [ -f "config_templates/$config" ]; then
        cp "config_templates/$config" ".vntrader_china/config/$config"
        echo -e "${GREEN}✓ 部署配置: $config${NC}"
    else
        echo -e "${YELLOW}⚠ 配置文件不存在: $config${NC}"
    fi
done

# 4. 加载环境变量
echo ""
echo "=== 4. 加载环境变量 ==="

if [ -f ".env.production" ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
    echo -e "${GREEN}✓ 环境变量已加载${NC}"
else
    echo -e "${YELLOW}⚠ .env.production 文件不存在${NC}"
    echo "请创建 .env.production 文件并配置环境变量"
fi

# 5. 数据库初始化
echo ""
echo "=== 5. 数据库初始化 ==="

read -p "是否初始化数据库？(y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python -c "
from vnpy_china_data import DatabaseManager
db = DatabaseManager()
db.create_tables()
print('✓ 数据库初始化完成')
" 2>/dev/null || echo -e "${YELLOW}⚠ 数据库初始化跳过（需先配置环境变量）${NC}"
fi

# 6. 运行测试
echo ""
echo "=== 6. 运行测试 ==="

read -p "是否运行系统测试？(y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python -m pytest tests/ --ignore=tests/test_alpha101.py --ignore=tests/test_gateway.py -q --tb=no
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 所有测试通过${NC}"
    else
        echo -e "${RED}✗ 部分测试失败，请检查${NC}"
    fi
fi

# 7. 启动提示
echo ""
echo "======================================"
echo -e "${GREEN}✓ 部署完成！${NC}"
echo "======================================"
echo ""
echo "后续步骤："
echo "1. 编辑 .vntrader_china/config/ 中的配置文件"
echo "2. 确保 QMT 交易客户端已登录"
echo "3. 运行交易系统："
echo "   python examples/veighna_trader/run_qmt.py"
echo ""
echo "4. 或启动 Web 监控系统："
echo "   cd vnpy_china_monitor && python run_web.py"
echo ""
echo "5. 查看日志："
echo "   tail -f .vntrader_china/logs/vnpy_china.log"
echo ""
