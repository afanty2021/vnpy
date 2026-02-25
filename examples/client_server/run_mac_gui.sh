#!/bin/bash
# Mac启动VeighNa GUI - 修复Qt窗口显示问题

# 设置Qt环境变量
export QT_QPA_PLATFORM=macx
export QT_AUTO_SCREEN_SCALE_FACTOR=1
export QT_MAC_DISABLE_HW_ACCELERATION=1

# 激活conda环境
source /opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh
conda activate Quant-3.11

# 进入目录
cd /Users/berton/Github/vnpy/examples/client_server

# 启动GUI
python run_qmt_client.py --mode gui
