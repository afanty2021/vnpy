"""
RPC客户端封装

提供到VeighNa RPC服务的连接和通信
"""

from vnpy_china_monitor.web.rpc.client import RpcClientWrapper, RpcConnectionState

__all__ = [
    "RpcClientWrapper",
    "RpcConnectionState",
]
