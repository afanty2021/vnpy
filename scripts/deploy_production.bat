@echo off
REM VeighNa A股交易系统 - 生产环境部署脚本 (Windows)
REM
REM 使用方法：
REM scripts\deploy_production.bat

echo ======================================
echo VeighNa A股交易系统 - 生产环境部署
echo ======================================
echo.

REM 项目根目录
set PROJECT_ROOT=%~dp0
cd /d "%PROJECT_ROOT%"

echo [√] 项目目录: %PROJECT_ROOT%
echo.

REM 1. 环境检查
echo === 1. 环境检查 ===

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [×] Python 未安装
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [√] Python 版本: %PYTHON_VERSION%

REM 2. 创建目录结构
echo.
echo === 2. 创建目录结构 ===

if not exist ".vntrader_china\config" mkdir ".vntrader_china\config"
echo [√] 创建目录: .vntrader_china\config

if not exist ".vntrader_china\logs" mkdir ".vntrader_china\logs"
echo [√] 创建目录: .vntrader_china\logs

if not exist ".vntrader_china\data" mkdir ".vntrader_china\data"
echo [√] 创建目录: .vntrader_china\data

if not exist "logs" mkdir "logs"
echo [√] 创建目录: logs

if not exist "data" mkdir "data"
echo [√] 创建目录: data

REM 3. 配置文件部署
echo.
echo === 3. 部署配置文件 ===

if exist "config_templates\global_production.yaml" (
    copy /Y "config_templates\global_production.yaml" ".vntrader_china\config\global_production.yaml" >nul
    echo [√] 部署配置: global_production.yaml
) else (
    echo [!] 配置文件不存在: global_production.yaml
)

if exist "config_templates\data_production.yaml" (
    copy /Y "config_templates\data_production.yaml" ".vntrader_china\config\data_production.yaml" >nul
    echo [√] 部署配置: data_production.yaml
) else (
    echo [!] 配置文件不存在: data_production.yaml
)

if exist "config_templates\monitor_production.yaml" (
    copy /Y "config_templates\monitor_production.yaml" ".vntrader_china\config\monitor_production.yaml" >nul
    echo [√] 部署配置: monitor_production.yaml
) else (
    echo [!] 配置文件不存在: monitor_production.yaml
)

REM 4. 运行测试
echo.
echo === 4. 运行测试 ===

set /p RUN_TESTS="是否运行系统测试？(y/N): "
if /i "%RUN_TESTS%"=="y" (
    conda run -n Quant-3.11 python -m pytest tests/ --ignore=tests/test_alpha101.py --ignore=tests/test_gateway.py -q --tb=no
    if %errorlevel% equ 0 (
        echo [√] 所有测试通过
    ) else (
        echo [×] 部分测试失败，请检查
    )
)

REM 5. 启动提示
echo.
echo ======================================
echo [√] 部署完成！
echo ======================================
echo.
echo 后续步骤：
echo 1. 编辑 .vntrader_china\config\ 中的配置文件
echo 2. 确保 QMT 交易客户端已登录
echo 3. 运行交易系统：
echo    python examples\veighna_trader\run_qmt.py
echo.
echo 4. 或启动 Web 监控系统：
echo    cd vnpy_china_monitor ^&^& python run_web.py
echo.
echo 5. 查看日志：
echo    tail -f .vntrader_china\logs\vnpy_china.log
echo.

pause
