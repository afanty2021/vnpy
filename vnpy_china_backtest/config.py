"""
A股增强回测配置

提供模块级别的配置管理
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BacktestConfig:
    """回测全局配置"""

    # 交易成本配置
    commission_rate: float = 0.0003       # 佣金费率 万3
    min_commission: float = 5.0          # 最低佣金 5元
    stamp_duty_rate: float = 0.001       # 印花税 千1 (仅卖出)
    transfer_fee_rate: float = 0.00001   # 过户费 万0.1 (双向)
    handling_fee_rate: float = 0.0000685 # 经手费 万0.0685 (双向)

    # 滑点配置
    slippage_model: str = "percent"      # 滑点模型类型
    slippage_value: float = 0.001        # 滑点值

    # 涨跌停配置
    enable_price_limit: bool = True       # 启用涨跌停限制
    allow_limit_up_buy: bool = False     # 允许涨停买入
    allow_limit_down_sell: bool = False  # 允许跌停卖出

    # T+1配置
    enable_t1: bool = True                # 启用T+1规则

    # 回测配置
    initial_capital: float = 1_000_000    # 初始资金
    annual_days: int = 240                # 年交易日天数


# 全局默认配置
default_config = BacktestConfig()


def get_config() -> BacktestConfig:
    """获取默认配置"""
    return default_config


def update_config(**kwargs) -> None:
    """更新默认配置"""
    global default_config
    for key, value in kwargs.items():
        if hasattr(default_config, key):
            setattr(default_config, key, value)
