# -*- coding:utf-8 -*-
"""
@FileName  :utils.py
@Time      :2022/11/8 17:07
@Author    :fsksf
"""
import datetime
from vnpy.trader.object import OrderRequest
from vnpy.trader.constant import Exchange, Product, OrderType, Direction, Status
from vnpy.trader.utility import ZoneInfo
from xtquant import xtconstant

From_VN_Exchange_map = {
    Exchange.CFFEX: 'CFF',
    Exchange.SSE: 'SH',
    Exchange.SZSE: 'SZ',
    Exchange.SHFE: 'SHF',
    Exchange.CZCE: 'CZC',
    Exchange.DCE: 'DCE',
    # 港股通交易所映射
    Exchange.SHHK: 'HK_SHTC',  # 沪港通
    Exchange.SZHK: 'HK_SZTC',  # 深港通
    Exchange.SEHK: 'HK',       # 香港本地
}

TO_VN_Exchange_map = {v: k for k, v in From_VN_Exchange_map.items()}


From_VN_Trade_Type = {
    Direction.LONG: xtconstant.STOCK_BUY,
    Direction.SHORT: xtconstant.STOCK_SELL,
}


TO_VN_Trade_Type = {v: k for k, v in From_VN_Trade_Type.items()}


TO_VN_ORDER_STATUS = {
    xtconstant.ORDER_UNREPORTED: Status.SUBMITTING,
    xtconstant.ORDER_WAIT_REPORTING: Status.SUBMITTING,
    xtconstant.ORDER_REPORTED: Status.NOTTRADED,
    xtconstant.ORDER_REPORTED_CANCEL: Status.NOTTRADED,
    xtconstant.ORDER_PARTSUCC_CANCEL: Status.PARTTRADED,
    xtconstant.ORDER_PART_CANCEL: Status.CANCELLED,
    xtconstant.ORDER_CANCELED: Status.CANCELLED,
    xtconstant.ORDER_PART_SUCC: Status.PARTTRADED,
    xtconstant.ORDER_SUCCEEDED: Status.ALLTRADED,
    xtconstant.ORDER_JUNK: Status.REJECTED,
    xtconstant.ORDER_UNKNOWN: Status.REJECTED
}


def from_vn_price_type(req: OrderRequest):
    if req.type == OrderType.LIMIT:
        return xtconstant.FIX_PRICE
    elif req.type == OrderType.MARKET:
        return xtconstant.LATEST_PRICE


def to_vn_contract(symbol):
    code, suffix = symbol.rsplit('.')
    exchange = TO_VN_Exchange_map[suffix]
    return code, exchange


TO_VN_Product = {
    'index': Product.INDEX,
    'stock': Product.EQUITY,
    'fund': Product.FUND,
    'etf': Product.ETF,
}


def to_vn_product(dic: dict):
    if dic.get('etf'):
        return Product.ETF
    for k, v in dic.items():
        if v:
            break
    return TO_VN_Product[k]


def to_qmt_code(symbol, exchange):
    suffix = From_VN_Exchange_map[exchange]
    return f'{symbol}.{suffix}'


# A股交易时间统一按 Asia/Shanghai（UTC+8）。fromtimestamp 不带 tz 会取宿主机本地时区，
# 部署到非 UTC+8 主机会让 tick/order/trade 时间整体偏移。
_SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def timestamp_to_datetime(tint):
    st = len(str(tint))
    if st != 10:
        p = st - 10
        tint = tint / 10**p
    return datetime.datetime.fromtimestamp(tint, tz=_SHANGHAI_TZ)