"""
行情服务

提供行情订阅、查询等功能
"""

import logging
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional

from vnpy_china_monitor.web.rpc.client import RpcClientWrapper

logger = logging.getLogger(__name__)


class MarketService:
    """行情服务

    负责：
    - 行情订阅管理
    - 实时行情缓存
    - K线数据查询
    - 行情数据格式化
    """

    def __init__(self, rpc_client: RpcClientWrapper, cache_size: int = 1000):
        """初始化行情服务

        Args:
            rpc_client: RPC客户端
            cache_size: 缓存大小
        """
        self.rpc_client = rpc_client

        # 实时行情缓存
        self._tick_cache: Dict[str, Dict] = {}

        # K线数据缓存
        self._bar_cache: Dict[str, deque] = {}

        # 订阅的合约列表
        self._subscribed_symbols: set[str] = set()

        # 缓存大小
        self._cache_size = cache_size

        logger.info("MarketService initialized")

    def subscribe(self, vt_symbol: str) -> bool:
        """订阅行情

        Args:
            vt_symbol: 合约代码

        Returns:
            是否成功
        """
        try:
            if vt_symbol in self._subscribed_symbols:
                logger.debug(f"Already subscribed: {vt_symbol}")
                return True

            # 通过RPC订阅
            self.rpc_client.call("subscribe", vt_symbol=vt_symbol)
            self._subscribed_symbols.add(vt_symbol)

            logger.info(f"Subscribed to market: {vt_symbol}")
            return True

        except Exception as e:
            logger.error(f"Failed to subscribe {vt_symbol}: {e}")
            return False

    def unsubscribe(self, vt_symbol: str) -> bool:
        """取消订阅

        Args:
            vt_symbol: 合约代码

        Returns:
            是否成功
        """
        try:
            self._subscribed_symbols.discard(vt_symbol)

            # 通过RPC取消订阅
            self.rpc_client.call("unsubscribe", vt_symbol=vt_symbol)

            logger.info(f"Unsubscribed from market: {vt_symbol}")
            return True

        except Exception as e:
            logger.error(f"Failed to unsubscribe {vt_symbol}: {e}")
            return False

    def get_tick(self, vt_symbol: str) -> Optional[Dict]:
        """获取最新行情

        Args:
            vt_symbol: 合约代码

        Returns:
            行情数据
        """
        return self._tick_cache.get(vt_symbol)

    def get_all_ticks(self) -> Dict[str, Dict]:
        """获取所有缓存的行情

        Returns:
            行情字典
        """
        return self._tick_cache.copy()

    def get_history_bars(
        self,
        vt_symbol: str,
        interval: str,
        count: int = 100,
    ) -> List[Dict]:
        """获取历史K线

        Args:
            vt_symbol: 合约代码
            interval: K线周期（1m/5m/15m/30m/1h/1d）
            count: 数量

        Returns:
            K线列表
        """
        try:
            return self.rpc_client.get_history_bars(vt_symbol, interval, count)
        except Exception as e:
            logger.error(f"Failed to get history bars: {e}")
            return []

    def update_tick(self, tick_data: Dict) -> None:
        """更新行情数据

        Args:
            tick_data: 行情数据
        """
        vt_symbol = tick_data.get("vt_symbol")
        if not vt_symbol:
            return

        self._tick_cache[vt_symbol] = {
            **tick_data,
            "update_time": datetime.now().isoformat(),
        }

    def format_tick(self, vt_symbol: str) -> Optional[Dict]:
        """格式化行情数据给前端

        Args:
            vt_symbol: 合约代码

        Returns:
            格式化后的数据
        """
        tick = self._tick_cache.get(vt_symbol)
        if not tick:
            return None

        return {
            "symbol": tick.get("symbol"),
            "exchange": tick.get("exchange"),
            "vt_symbol": tick.get("vt_symbol"),
            "last_price": tick.get("last_price", 0),
            "open_price": tick.get("open_price", 0),
            "high_price": tick.get("high_price", 0),
            "low_price": tick.get("low_price", 0),
            "volume": tick.get("volume", 0),
            "turnover": tick.get("turnover", 0),
            "bid_price_1": tick.get("bid_price_1", 0),
            "ask_price_1": tick.get("ask_price_1", 0),
            "bid_volume_1": tick.get("bid_volume_1", 0),
            "ask_volume_1": tick.get("ask_volume_1", 0),
            "datetime": tick.get("datetime", ""),
        }

    def get_subscribed_symbols(self) -> List[str]:
        """获取已订阅的合约列表

        Returns:
            合约列表
        """
        return list(self._subscribed_symbols)
