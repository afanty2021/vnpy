# -*- coding: utf-8 -*-
"""
通达信函数映射表

将通达信公式函数映射到vnpy/Pandas函数
"""

from typing import Dict, Callable, Any, List, Optional
import pandas as pd
import numpy as np


class FunctionInfo:
    """函数信息"""

    def __init__(
        self,
        name: str,
        tdx_name: str,
        vnpy_name: Optional[str] = None,
        param_count: Optional[int] = None,
        param_range: Optional[tuple] = None,
        description: str = "",
        implementation: Optional[Callable] = None
    ):
        self.name = name                    # vnpy函数名
        self.tdx_name = tdx_name            # 通达信函数名
        self.vnpy_name = vnpy_name or name  # vnpy实际调用函数名
        self.param_count = param_count      # 参数数量
        self.param_range = param_range      # 参数范围 (min, max)
        self.description = description      # 函数描述
        self.implementation = implementation # 自定义实现

    def __repr__(self) -> str:
        return f"FunctionInfo({self.name}, {self.tdx_name})"


class FunctionMapper:
    """函数映射器"""

    def __init__(self):
        """初始化函数映射器"""
        self._functions: Dict[str, FunctionInfo] = {}
        self._tdx_to_vnpy: Dict[str, FunctionInfo] = {}
        self._init_built_in_functions()

    def _init_built_in_functions(self) -> None:
        """初始化内置函数映射"""
        # 数学函数
        self.register(FunctionInfo("abs", "ABS", description="绝对值"))
        self.register(FunctionInfo("max", "MAX", param_range=(1, 2), description="最大值"))
        self.register(FunctionInfo("min", "MIN", param_range=(1, 2), description="最小值"))
        self.register(FunctionInfo("round", "ROUND", param_count=1, description="四舍五入"))
        self.register(FunctionInfo("ceil", "CEILING", param_count=1, description="向上取整"))
        self.register(FunctionInfo("floor", "FLOOR", param_count=1, description="向下取整"))
        self.register(FunctionInfo("sqrt", "SQRT", param_count=1, description="平方根"))
        self.register(FunctionInfo("pow", "POW", param_count=2, description="幂运算"))
        self.register(FunctionInfo("log", "LN", param_count=1, description="自然对数"))
        self.register(FunctionInfo("log10", "LOG10", param_count=1, description="常用对数"))
        self.register(FunctionInfo("exp", "EXP", param_count=1, description="指数"))
        self.register(FunctionInfo("sin", "SIN", param_count=1, description="正弦"))
        self.register(FunctionInfo("cos", "COS", param_count=1, description="余弦"))
        self.register(FunctionInfo("tan", "TAN", param_count=1, description="正切"))

        # 统计函数
        self.register(FunctionInfo("mean", "MA", param_range=(1, 2), description="简单移动平均"))
        self.register(FunctionInfo("ema", "EMA", param_count=2, description="指数移动平均"))
        self.register(FunctionInfo("sma", "SMA", param_count=3, description="平滑移动平均"))
        self.register(FunctionInfo("std", "STD", param_range=(1, 2), description="标准差"))
        self.register(FunctionInfo("var", "VAR", param_range=(1, 2), description="方差"))
        self.register(FunctionInfo("sum", "SUM", param_range=(1, 2), description="求和"))
        self.register(FunctionInfo("count", "COUNT", param_range=(1, 2), description="计数"))

        # 行情函数
        self.register(FunctionInfo("open", "OPEN", description="开盘价"))
        self.register(FunctionInfo("high", "HIGH", description="最高价"))
        self.register(FunctionInfo("low", "LOW", description="最低价"))
        self.register(FunctionInfo("close", "CLOSE", description="收盘价"))
        self.register(FunctionInfo("volume", "VOL", description="成交量"))
        self.register(FunctionInfo("amount", "AMO", description="成交额"))
        self.register(FunctionInfo("advance", "ADVANCE", description="上涨家数"))
        self.register(FunctionInfo("decline", "DECLINE", description="下跌家数"))

        # 技术指标函数
        self.register(FunctionInfo("ma", "MA", param_count=2, description="移动平均"))
        self.register(FunctionInfo("ema", "EMA", param_count=2, description="指数移动平均"))
        self.register(FunctionInfo("sma", "SMA", param_count=3, description="平滑移动平均"))
        self.register(FunctionInfo("dma", "DMA", param_count=2, description="动态移动平均"))
        self.register(FunctionInfo("wma", "WMA", param_count=2, description="加权移动平均"))

        # K线形态
        self.register(FunctionInfo("cross", "CROSS", param_count=2, description="金叉/上穿"))
        self.register(FunctionInfo("cross_down", "CROSSDOWN", param_count=2, description="死叉/下穿"))

        # 时间函数
        self.register(FunctionInfo("year", "YEAR", description="年份"))
        self.register(FunctionInfo("month", "MONTH", description="月份"))
        self.register(FunctionInfo("day", "DAY", description="日期"))
        self.register(FunctionInfo("hour", "HOUR", description="小时"))
        self.register(FunctionInfo("minute", "MINUTE", description="分钟"))
        self.register(FunctionInfo("weekday", "WEEKDAY", description="星期"))
        self.register(FunctionInfo("barstotal", "TOTALBARSCOUNT", description="总K线数"))
        self.register(FunctionInfo("barscount", "BARSCOUNT", description="当前K线位置"))

        # 逻辑函数
        self.register(FunctionInfo("if", "IF", param_count=3, description="条件函数"))
        self.register(FunctionInfo("iff", "IFF", param_count=3, description="条件函数(别名)"))
        self.register(FunctionInfo("between", "BETWEEN", param_count=3, description="介于"))
        self.register(FunctionInfo("inblock", "INBLOCK", param_count=1, description="属于板块"))

        # 引用函数
        self.register(FunctionInfo("ref", "REF", param_count=2, description="引用若干周期前的值"))
        self.register(FunctionInfo("refx", "REFX", param_count=2, description="引用若干周期后的值"))
        self.register(FunctionInfo("hhv", "HHV", param_range=(1, 2), description="最高值"))
        self.register(FunctionInfo("llv", "LLV", param_range=(1, 2), description="最低值"))
        self.register(FunctionInfo("hhvbars", "HHVBARS", param_range=(1, 2), description="最高值位置"))
        self.register(FunctionInfo("llvbars", "LLVBARS", param_range=(1, 2), description="最低值位置"))

    def register(self, func_info: FunctionInfo) -> None:
        """注册函数"""
        self._functions[func_info.name.lower()] = func_info
        self._tdx_to_vnpy[func_info.tdx_name.upper()] = func_info

    def get_by_name(self, name: str) -> Optional[FunctionInfo]:
        """通过vnpy函数名获取函数信息"""
        return self._functions.get(name.lower())

    def get_by_tdx_name(self, tdx_name: str) -> Optional[FunctionInfo]:
        """通过通达信函数名获取函数信息"""
        return self._tdx_to_vnpy.get(tdx_name.upper())

    def translate(self, tdx_name: str) -> Optional[str]:
        """将通达信函数名转换为vnpy函数名"""
        func_info = self.get_by_tdx_name(tdx_name)
        return func_info.name if func_info else None

    def is_valid_call(self, tdx_name: str, arg_count: int) -> bool:
        """检查函数调用是否有效"""
        func_info = self.get_by_tdx_name(tdx_name)
        if not func_info:
            return False

        if func_info.param_count is not None:
            return arg_count == func_info.param_count

        if func_info.param_range is not None:
            min_args, max_args = func_info.param_range
            return min_args <= arg_count <= max_args

        return True

    def list_functions(self, category: Optional[str] = None) -> List[FunctionInfo]:
        """列出所有函数或指定类别的函数"""
        all_functions = list(self._functions.values())
        # TODO: 添加分类支持
        return all_functions

    def get_function_code(self, tdx_name: str, *args) -> str:
        """生成函数调用的Python代码"""
        func_info = self.get_by_tdx_name(tdx_name)
        if not func_info:
            raise ValueError(f"未知函数: {tdx_name}")

        # 如果有自定义实现
        if func_info.implementation:
            return f"{func_info.implementation.__name__}({', '.join(map(str, args))})"

        # 生成vnpy函数调用
        return f"{func_info.vnpy_name}({', '.join(map(str, args))})"


# 全局函数映射器实例
_global_mapper: Optional[FunctionMapper] = None


def get_global_mapper() -> FunctionMapper:
    """获取全局函数映射器"""
    global _global_mapper
    if _global_mapper is None:
        _global_mapper = FunctionMapper()
    return _global_mapper


# 内置函数实现示例

def tdx_cross(x, y):
    """通达信CROSS函数：x上穿y"""
    if isinstance(x, (pd.Series, np.ndarray)) and isinstance(y, (pd.Series, np.ndarray)):
        return (x > y) & (x.shift(1) <= y.shift(1))
    return x > y


def tdx_ma(data, period):
    """通达信MA函数：简单移动平均"""
    return data.rolling(window=period).mean()


def tdx_ema(data, period):
    """通达信EMA函数：指数移动平均"""
    return data.ewm(span=period, adjust=False).mean()


def tdx_ref(data, offset):
    """通达信REF函数：引用若干周期前的值"""
    return data.shift(offset)


def tdx_hhv(data, period=None):
    """通达信HHV函数：最高值"""
    if period is None:
        return data.cummax()
    return data.rolling(window=period).max()


def tdx_llv(data, period=None):
    """通达信LLV函数：最低值"""
    if period is None:
        return data.cummin()
    return data.rolling(window=period).min()
