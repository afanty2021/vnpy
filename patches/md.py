# -*- coding:utf-8 -*-
"""
@FileName  :md.py
@Time      :2022/11/8 17:14
@Author    :fsksf
"""

from vnpy.trader.object import (
    CancelRequest, OrderRequest, SubscribeRequest, TickData,
    ContractData, BarData, HistoryRequest
)
from vnpy.trader.constant import Interval, Exchange
import xtquant.xtdata
import xtquant.xttrader
import xtquant.xttype
from vnpy_qmt.utils import (
    From_VN_Exchange_map, TO_VN_Exchange_map, to_vn_contract,
    TO_VN_Product, to_vn_product, timestamp_to_datetime,
    to_qmt_code
)
from vnpy.trader.utility import ZoneInfo
from typing import List, Optional
from datetime import datetime as dt
import datetime

ZONE_INFO = ZoneInfo("Asia/Shanghai")


class MD:

    def __init__(self, gateway):
        self.gateway = gateway
        self.th = None
        self.limit_ups = {}
        self.limit_downs = {}
        # 量比分母缓存：{vt_symbol: 过去5日平均日成交量}，惰性查询，避免每 tick 重复取数。
        # 按交易日失效（5日均量次日会纳入新交易日数据），跨日 clear 重算；内存只留当天。
        self._avg_daily_vol_cache: dict = {}
        self._avg_daily_vol_date = None

    def close(self) -> None:
        pass

    def subscribe(self, req: SubscribeRequest) -> None:
        code = f'{req.symbol}.{From_VN_Exchange_map[req.exchange]}'
        xtquant.xtdata.subscribe_quote(
            stock_code=code,
            period='tick',
            callback=self.on_tick
        )
        # 订阅后主动拉一次最新 tick 快照并推送（解决收盘后/盘前无推送导致行情表格空白）
        # get_full_tick 返回 {code: tick_dict}，包装成 on_tick 期望的 {code: [tick_dict]} 格式
        try:
            snapshot = xtquant.xtdata.get_full_tick([code])
            if snapshot and code in snapshot and snapshot[code]:
                self.on_tick({code: [snapshot[code]]})
        except Exception as e:
            self.write_log(f'订阅 {code} 拉取快照失败: {e}')

    def connect(self, setting: dict) -> None:
        self.get_contract()
        return

    def get_contract(self):
        self.write_log('开始获取标的信息')
        contract_ids = set()
        bk = ['上期所', '上证A股', '上证B股', '中金所', '创业板', '大商所',
              '沪市ETF', '沪市指数', '沪深A股',
              '沪深B股', '沪深ETF', '沪深指数', '深市ETF',
              '深市基金', '深市指数', '深证A股', '深证B股', '科创板', '科创板CDR',
              ]
        for sector in bk:
            print(sector)
            stock_list = xtquant.xtdata.get_stock_list_in_sector(sector_name=sector)
            for symbol in stock_list:
                if symbol in contract_ids:
                    continue
                contract_ids.add(symbol)
                info = xtquant.xtdata.get_instrument_detail(symbol)
                contract_type = xtquant.xtdata.get_instrument_type(symbol)
                if info is None or contract_type is None:
                    continue
                try:
                    exchange = TO_VN_Exchange_map[info['ExchangeID']]
                except KeyError:

                    print('本gateway不支持的标的', symbol)
                    continue
                if exchange not in self.gateway.exchanges:
                    continue
                product = to_vn_product(contract_type)
                if product not in self.gateway.TRADE_TYPE:
                    continue

                c = ContractData(
                    gateway_name=self.gateway.gateway_name,
                    symbol=info['InstrumentID'],
                    exchange=exchange,
                    name=info['InstrumentName'],
                    product=product,
                    pricetick=info['PriceTick'],
                    size=100,
                    min_volume=100
                )
                self.limit_ups[c.vt_symbol] = info['UpStopPrice']
                self.limit_downs[c.vt_symbol] = info['DownStopPrice']
                self.gateway.on_contract(c)
        self.write_log('获取标的信息完成')

    def on_tick(self, datas):
        for code, data_list in datas.items():
            symbol, suffix = code.rsplit('.')
            exchange = TO_VN_Exchange_map[suffix]
            for data in data_list:
                ask_price = data['askPrice']
                ask_vol = data['askVol']
                bid_price = data['bidPrice']
                bid_vol = data['bidVol']
                dt = timestamp_to_datetime(data['time'])
                dt = dt.replace(tzinfo=ZONE_INFO)
                tick = TickData(
                    gateway_name=self.gateway.gateway_name,
                    symbol=symbol,
                    exchange=exchange,
                    datetime=dt,
                    last_price=data['lastPrice'],
                    volume=data['volume'],
                    open_price=data['open'],
                    high_price=data['high'],
                    low_price=data['low'],
                    pre_close=data['lastClose'],
                    limit_down=0,
                    limit_up=0,
                    ask_price_1=ask_price[0],
                    ask_price_2=ask_price[1],
                    ask_price_3=ask_price[2],
                    ask_price_4=ask_price[3],
                    ask_price_5=ask_price[4],

                    ask_volume_1=ask_vol[0],
                    ask_volume_2=ask_vol[1],
                    ask_volume_3=ask_vol[2],
                    ask_volume_4=ask_vol[3],
                    ask_volume_5=ask_vol[4],

                    bid_price_1=bid_price[0],
                    bid_price_2=bid_price[1],
                    bid_price_3=bid_price[2],
                    bid_price_4=bid_price[3],
                    bid_price_5=bid_price[4],

                    bid_volume_1=bid_vol[0],
                    bid_volume_2=bid_vol[1],
                    bid_volume_3=bid_vol[2],
                    bid_volume_4=bid_vol[3],
                    bid_volume_5=bid_vol[4],
                )
                contract = self.gateway.get_contract(tick.vt_symbol)
                if contract:
                    tick.name = contract.name
                tick.limit_up = self.limit_ups.get(tick.vt_symbol, None)
                tick.limit_down = self.limit_downs.get(tick.vt_symbol, None)

                # 填充 A 股增强字段到 extra（TickMonitor 显示成交额/量比/涨幅/分时均价）
                self._fill_tick_extra(tick, data, symbol, exchange, dt)

                self.gateway.on_tick(tick)

    def _fill_tick_extra(self, tick, data, symbol, exchange, dt) -> None:
        """计算 A 股增强字段，供 TickMonitor 显示成交额/量比/涨幅/分时均价。

        实盘口径：
            成交额 turnover     = amount（TickData 原生字段，直接赋值）
            涨幅 change_pct     = (last - pre_close) / pre_close * 100  → extra
            分时均价 avg_price  = amount / volume                        → extra
            量比 volume_ratio   = (volume/已交易分钟) / (5日日均量/240)   → extra

        turnover 是 TickData 原生字段直接赋值；其余3字段非原生，写入 extra（TickMonitor
        经 BaseMonitor._get_attr 的 extra fallback 读取）。
        """
        last: float = data['lastPrice']
        pre_close: float = data['lastClose']
        volume: float = data['volume']
        amount: float = data.get('amount', 0) or 0

        # 成交额（TickData 原生字段）
        tick.turnover = float(amount)

        # 涨幅（pre_close 为 0 时不除零）
        change_pct: float = (last - pre_close) / pre_close * 100 if pre_close else 0.0
        # 分时均价（xtdata volume 单位为"手"=×100股，amount 为元，须 /100 得每股均价）
        avg_price: float = amount / (volume * 100) if volume else 0.0

        # 量比
        trading_min: int = self._trading_minutes(dt)
        volume_ratio: float = 0.0
        if trading_min > 0:
            avg_daily_vol: float = self._get_avg_daily_vol(symbol, exchange, tick.vt_symbol, dt)
            if avg_daily_vol > 0:
                avg_vol_per_min: float = avg_daily_vol / 240
                vol_per_min_today: float = volume / trading_min
                volume_ratio = vol_per_min_today / avg_vol_per_min

        if tick.extra is None:
            tick.extra = {}
        tick.extra['change_pct'] = change_pct
        tick.extra['avg_price'] = avg_price
        tick.extra['volume_ratio'] = volume_ratio

    @staticmethod
    def _trading_minutes(dt) -> int:
        """A 股当日已交易分钟数（9:30-11:30 + 13:00-15:00，剔除午休）。

        开盘前返回 0，收盘后返回 240。
        """
        t = dt.time()
        if t < datetime.time(9, 30):
            return 0
        if t >= datetime.time(15, 0):
            return 240
        if t <= datetime.time(11, 30):
            return (t.hour - 9) * 60 + (t.minute - 30)
        if t < datetime.time(13, 0):
            return 120
        return 120 + (t.hour - 13) * 60 + t.minute

    def _get_avg_daily_vol(self, symbol, exchange, vt_symbol, dt) -> float:
        """惰性查询过去5日平均日成交量（股），作为量比分母。失败/无数据返回 0。

        查询结果按 vt_symbol 缓存：同一交易日内每个标的仅首次 tick 触发一次取数；
        跨交易日时 clear 重算（5日均量次日会纳入新数据，旧值失真）。内存只保留当天。
        """
        today = dt.date()
        if self._avg_daily_vol_date != today:
            self._avg_daily_vol_cache.clear()
            self._avg_daily_vol_date = today

        if vt_symbol in self._avg_daily_vol_cache:
            return self._avg_daily_vol_cache[vt_symbol]

        avg: float = 0.0
        try:
            qmt_code = to_qmt_code(symbol, exchange)
            result = xtquant.xtdata.get_local_data(
                field_list=['time', 'volume'],
                stock_list=[qmt_code],
                period='1d',
                count=5,
            )
            if isinstance(result, dict) and qmt_code in result:
                df = result[qmt_code]
                if df is not None and len(df) > 0 and 'volume' in df:
                    avg = float(df['volume'].iloc[-5:].mean())
        except Exception:
            avg = 0.0

        self._avg_daily_vol_cache[vt_symbol] = avg
        return avg

    def query_history(self, req) -> List[BarData]:
        """查询历史K线数据

        使用 QMT xtdata API 获取历史数据，支持 A 股和港股通。

        Args:
            req: 历史数据请求对象，可以是 HistoryRequest 对象或字典

        Returns:
            K线数据列表
        """
        try:
            # 兼容 HistoryRequest 对象和字典两种格式
            if isinstance(req, dict):
                # RPC 调用传递的是字典
                symbol = req.get('symbol')
                exchange = req.get('exchange')
                interval = req.get('interval')
                start = req.get('start')
                end = req.get('end')
            else:
                # HistoryRequest 对象
                symbol = req.symbol
                exchange = req.exchange
                interval = req.interval
                start = req.start
                end = req.end

            # 转换 interval 到 QMT period
            # interval 可能是 Interval 枚举或字符串
            if hasattr(interval, 'value'):
                interval_value = interval.value
            else:
                interval_value = str(interval)

            # 支持两种映射方式：枚举和字符串
            period_map = {
                # 枚举映射（只保留 vnpy 支持的 Interval 枚举）
                Interval.MINUTE: '1m',
                Interval.HOUR: '1h',
                Interval.DAILY: '1d',
                Interval.WEEKLY: '1w',
                # 字符串映射（兼容更多周期）
                '1m': '1m',
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '1h': '1h',
                '60m': '1h',
                'd': '1d',
                '1d': '1d',
                '1w': '1w',
            }
            # 获取 period 值：优先使用枚举，其次使用字符串值
            period = period_map.get(interval, period_map.get(interval_value, '1d'))

            # 转换日期格式为 YYYYMMDD
            if hasattr(start, 'strftime'):
                start_time = start.strftime('%Y%m%d')
            else:
                start_time = '20200101'

            if hasattr(end, 'strftime'):
                end_time = end.strftime('%Y%m%d')
            else:
                end_time = dt.now().strftime('%Y%m%d')

            # 构建 QMT 格式的股票代码
            # 对于港股通，需要使用特殊格式 (如 "0700.HK_SHTC")
            qmt_code = to_qmt_code(symbol, exchange)

            self.write_log(f'QMT 查询历史数据: {qmt_code}, period={period}, start={start_time}, end={end_time}')

            # 先下载数据到本地存储（miniQMT 必须先下载才能读取）
            # 使用 download_history_data2 支持批量下载
            if hasattr(xtquant.xtdata, 'download_history_data2'):
                self.write_log(f'QMT 正在下载数据: {qmt_code}...')
                try:
                    # 异步下载数据到本地
                    result = xtquant.xtdata.download_history_data2(
                        stock_list=[qmt_code],
                        period=period,
                        start_time=start_time,
                        end_time=end_time,
                        callback=lambda: None  # 空回调，因为我们是同步调用
                    )
                    self.write_log(f'QMT download_history_data2 返回: {result}')
                    # 等待下载完成（异步操作需要等待）
                    import time
                    time.sleep(2)  # 增加等待时间
                except Exception as e:
                    self.write_log(f'QMT 数据下载失败: {e}')
                    import traceback
                    self.write_log(f'详细错误: {traceback.format_exc()}')
            elif hasattr(xtquant.xtdata, 'download_history_data'):
                self.write_log(f'QMT 正在下载数据(单股): {qmt_code}...')
                try:
                    result = xtquant.xtdata.download_history_data(
                        stock_code=qmt_code,
                        period=period,
                        start_time=start_time,
                        end_time=end_time
                    )
                    self.write_log(f'QMT download_history_data 返回: {result}')
                    import time
                    time.sleep(2)
                except Exception as e:
                    self.write_log(f'QMT 数据下载失败: {e}')
                    import traceback
                    self.write_log(f'详细错误: {traceback.format_exc()}')

            # 从本地存储读取数据
            # 使用 get_local_data (更稳定，返回 pandas DataFrame)
            if hasattr(xtquant.xtdata, 'get_local_data'):
                data_list = xtquant.xtdata.get_local_data(
                    field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
                    stock_list=[qmt_code],
                    period=period,
                    start_time=start_time,
                    end_time=end_time,
                    dividend_type='front'  # 前复权
                )
            elif hasattr(xtquant.xtdata, 'get_market_data_ex'):
                # 备用方案：使用 get_market_data_ex
                data_list = xtquant.xtdata.get_market_data_ex(
                    stock_list=[qmt_code],
                    period=period,
                    start_time=start_time,
                    end_time=end_time,
                    dividend_type='front'  # 前复权
                )
            elif hasattr(xtquant.xtdata, 'get_hq'):
                # 兼容方案：使用 get_hq
                data_list = xtquant.xtdata.get_hq(
                    code=qmt_code,
                    start_date=start_time,
                    period=period,
                    dividend_type='front'
                )
            else:
                self.write_log(f'QMT xtdata 不支持历史数据查询')
                return []

            # 转换为 BarData 列表
            bars = []
            if data_list is None:
                return []

            # get_local_data 返回 {股票代码: DataFrame}
            if isinstance(data_list, dict) and qmt_code in data_list:
                df = data_list[qmt_code]
                # 遍历 DataFrame 的每一行
                for _, row in df.iterrows():
                    try:
                        # 解析时间 (时间戳格式)
                        time_value = row.get('time', row.get('datetime'))
                        if isinstance(time_value, (int, float)):
                            bar_time = timestamp_to_datetime(int(time_value))
                        elif hasattr(time_value, 'timestamp'):
                            bar_time = time_value.timestamp()
                            bar_time = timestamp_to_datetime(int(bar_time))
                        else:
                            continue

                        bar = BarData(
                            gateway_name=self.gateway.gateway_name,
                            symbol=symbol,
                            exchange=exchange,
                            datetime=bar_time,
                            interval=interval,
                            open_price=float(row.get('open', 0)),
                            high_price=float(row.get('high', 0)),
                            low_price=float(row.get('low', 0)),
                            close_price=float(row.get('close', 0)),
                            volume=float(row.get('volume', 0)),
                            turnover=float(row.get('amount', 0)),
                        )
                        bars.append(bar)
                    except Exception as e:
                        self.write_log(f'转换K线数据失败: {e}')
                        continue
            elif isinstance(data_list, dict):
                # get_market_data_ex 格式处理
                if qmt_code in data_list:
                    bar_list = data_list[qmt_code]
                    if isinstance(bar_list, (list, tuple)):
                        for bar_data in bar_list:
                            try:
                                # 解析时间
                                time_value = bar_data.get('time')
                                if isinstance(time_value, str):
                                    bar_time = dt.strptime(time_value, '%Y%m%d %H:%M:%S')
                                else:
                                    bar_time = timestamp_to_datetime(int(time_value))

                                bar = BarData(
                                    gateway_name=self.gateway.gateway_name,
                                    symbol=symbol,
                                    exchange=exchange,
                                    datetime=bar_time,
                                    interval=interval,
                                    open_price=float(bar_data.get('open', 0)),
                                    high_price=float(bar_data.get('high', 0)),
                                    low_price=float(bar_data.get('low', 0)),
                                    close_price=float(bar_data.get('close', 0)),
                                    volume=float(bar_data.get('volume', 0)),
                                    turnover=float(bar_data.get('amount', 0)),
                                )
                                bars.append(bar)
                            except Exception as e:
                                self.write_log(f'转换K线数据失败: {e}')
                                continue

            self.write_log(f'获取 {qmt_code} 历史数据: {len(bars)} 条')
            return bars

        except Exception as e:
            self.write_log(f'QMT 查询历史数据失败: {e}')
            return []

    def write_log(self, msg):
        self.gateway.write_log(f"[ md ] {msg}")