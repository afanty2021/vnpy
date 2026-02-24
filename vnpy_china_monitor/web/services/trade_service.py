"""
交易服务

提供委托、撤单、查询等交易功能
"""

import logging
from typing import Any, Dict, List, Optional

from vnpy_china_monitor.web.rpc.client import RpcClientWrapper

logger = logging.getLogger(__name__)


class TradeService:
    """交易服务

    负责：
    - 委托下单
    - 委托撤销
    - 持仓查询
    - 成交查询
    - 资金查询
    - 交易数据格式化
    """

    def __init__(self, rpc_client: RpcClientWrapper):
        """初始化交易服务

        Args:
            rpc_client: RPC客户端
        """
        self.rpc_client = rpc_client

        # 委托缓存
        self._order_cache: Dict[str, Dict] = {}

        # 成交缓存
        self._trade_cache: Dict[str, Dict] = {}

        logger.info("TradeService initialized")

    def send_order(
        self,
        vt_symbol: str,
        direction: str,
        volume: float,
        price: float = 0,
        order_type: str = "limit",
    ) -> Optional[str]:
        """发送委托

        Args:
            vt_symbol: 合约代码
            direction: 方向（long/short）
            volume: 数量
            price: 价格（0表示市价）
            order_type: 委托类型

        Returns:
            委托ID，失败返回None
        """
        try:
            vt_orderid = self.rpc_client.send_order(
                vt_symbol=vt_symbol,
                direction=direction,
                volume=volume,
                price=price,
                order_type=order_type,
            )

            logger.info(
                f"Order sent: vt_orderid={vt_orderid}, "
                f"vt_symbol={vt_symbol}, direction={direction}, "
                f"volume={volume}, price={price}, type={order_type}"
            )

            return vt_orderid

        except Exception as e:
            logger.error(f"Failed to send order: {e}")
            return None

    def cancel_order(self, vt_orderid: str) -> bool:
        """撤销委托

        Args:
            vt_orderid: 委托ID

        Returns:
            是否成功
        """
        try:
            result = self.rpc_client.cancel_order(vt_orderid)

            logger.info(f"Order cancelled: vt_orderid={vt_orderid}, result={result}")

            # 从缓存中移除
            self._order_cache.pop(vt_orderid, None)

            return result

        except Exception as e:
            logger.error(f"Failed to cancel order {vt_orderid}: {e}")
            return False

    def get_orders(self, vt_orderid: Optional[str] = None) -> List[Dict]:
        """查询委托

        Args:
            vt_orderid: 委托ID，None表示所有委托

        Returns:
            委托列表
        """
        try:
            orders = self.rpc_client.get_orders(vt_orderid)

            # 更新缓存
            for order in orders:
                vt_orderid = order.get("vt_orderid")
                if vt_orderid:
                    self._order_cache[vt_orderid] = order

            return orders

        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            return []

    def get_trades(self, vt_orderid: Optional[str] = None) -> List[Dict]:
        """查询成交

        Args:
            vt_orderid: 委托ID，None表示所有成交

        Returns:
            成交列表
        """
        try:
            return self.rpc_client.call("get_trades", vt_orderid=vt_orderid)
        except Exception as e:
            logger.error(f"Failed to get trades: {e}")
            return []

    def get_account(self) -> Optional[Dict]:
        """获取账户资金

        Returns:
            账户数据
        """
        try:
            return self.rpc_client.get_account()
        except Exception as e:
            logger.error(f"Failed to get account: {e}")
            return None

    def get_positions(self) -> List[Dict]:
        """获取持仓

        Returns:
            持仓列表
        """
        try:
            return self.rpc_client.get_position()
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []

    def format_order(self, order: Dict) -> Dict:
        """格式化委托给前端

        Args:
            order: 委托数据

        Returns:
            格式化后的数据
        """
        return {
            "vt_orderid": order.get("vt_orderid"),
            "symbol": order.get("symbol"),
            "exchange": order.get("exchange"),
            "vt_symbol": order.get("vt_symbol"),
            "direction": order.get("direction"),
            "order_type": order.get("order_type"),
            "volume": order.get("volume", 0),
            "traded": order.get("traded", 0),
            "price": order.get("price", 0),
            "status": order.get("status"),
            "order_time": order.get("order_time", ""),
            "cancel_time": order.get("cancel_time", ""),
        }

    def format_position(self, position: Dict) -> Dict:
        """格式化持仓给前端

        Args:
            position: 持仓数据

        Returns:
            格式化后的数据
        """
        return {
            "vt_symbol": position.get("vt_symbol"),
            "symbol": position.get("symbol"),
            "exchange": position.get("exchange"),
            "direction": position.get("direction"),
            "volume": position.get("volume", 0),
            "yd_volume": position.get("yd_volume", 0),
            "available": position.get("available", 0),
            "frozen": position.get("frozen", 0),
            "price": position.get("price", 0),
            "pnl": position.get("pnl", 0),
            "update_time": position.get("update_time", ""),
        }

    def format_account(self, account: Dict) -> Dict:
        """格式化账户给前端

        Args:
            account: 账户数据

        Returns:
            格式化后的数据
        """
        return {
            "accountid": account.get("accountid"),
            "balance": account.get("balance", 0),
            "available": account.get("available", 0),
            "frozen": account.get("frozen", 0),
            "position_profit": account.get("position_profit", 0),
            "close_profit": account.get("close_profit", 0),
            "datetime": account.get("datetime", ""),
        }
