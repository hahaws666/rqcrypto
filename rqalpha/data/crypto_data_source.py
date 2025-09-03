# -*- coding: utf-8 -*-
"""
加密货币数据源实现
基于 Binance API 提供加密货币数据
"""

import os
import pickle
import h5py
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Union
from itertools import groupby

from rqalpha.const import INSTRUMENT_TYPE, TRADING_CALENDAR_TYPE
from rqalpha.interface import AbstractDataSource
from rqalpha.model.instrument import Instrument
from rqalpha.utils.datetime_func import convert_date_to_int, convert_int_to_date, convert_int_to_datetime
from rqalpha.utils.exception import RQInvalidArgument
from rqalpha.utils.functools import lru_cache
from rqalpha.utils.typing import DateLike
from rqalpha.environment import Environment
from rqalpha.data.base_data_source.storage_interface import (
    AbstractCalendarStore, AbstractDateSet, AbstractDayBarStore, 
    AbstractDividendStore, AbstractInstrumentStore
)
from rqalpha.data.base_data_source.storages import (
    DateSet, DayBarStore, InstrumentStore, SimpleFactorStore
)
from rqalpha.data.binance_api import get_binance_provider


class CryptoDayBarStore(AbstractDayBarStore):
    """加密货币日线数据存储"""
    
    def __init__(self, file_path: str):
        self._file_path = file_path
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """确保文件存在"""
        if not os.path.exists(self._file_path):
            with h5py.File(self._file_path, 'w') as f:
                pass  # 创建空文件
    
    def get_bars(self, order_book_id: str) -> np.ndarray:
        """获取指定合约的所有K线数据"""
        try:
            with h5py.File(self._file_path, 'r') as f:
                if order_book_id in f:
                    return f[order_book_id][:]
                else:
                    return np.array([])
        except (OSError, KeyError):
            return np.array([])
    
    def get_date_range(self, order_book_id: str) -> tuple:
        """获取数据日期范围"""
        bars = self.get_bars(order_book_id)
        if len(bars) == 0:
            return None, None
        return bars['datetime'][0], bars['datetime'][-1]
    
    def store_bars(self, order_book_id: str, bars: np.ndarray):
        """存储K线数据"""
        with h5py.File(self._file_path, 'a') as f:
            if order_book_id in f:
                del f[order_book_id]
            if len(bars) > 0:
                f.create_dataset(order_book_id, data=bars)


class CryptoTradingCalendarStore(AbstractCalendarStore):
    """加密货币交易日历存储（7x24小时）"""
    
    def __init__(self, start_date: date = date(2017, 1, 1), end_date: date = date(2030, 12, 31)):
        self._start_date = start_date
        self._end_date = end_date
        self._calendar = self._generate_crypto_calendar()
    
    def _generate_crypto_calendar(self) -> pd.DatetimeIndex:
        """生成加密货币交易日历（7x24小时，每天都是交易日）"""
        return pd.date_range(start=self._start_date, end=self._end_date, freq='D')
    
    def get_trading_calendar(self) -> pd.DatetimeIndex:
        """获取交易日历"""
        return self._calendar


class CryptoDataSource(AbstractDataSource):
    """加密货币数据源"""
    
    # 与RQAlpha标准格式保持一致
    CRYPTO_FIELDS = ['datetime', 'open', 'close', 'high', 'low', 'prev_close', 'volume', 'total_turnover']
    CRYPTO_FUTURES_FIELDS = CRYPTO_FIELDS + ['settlement', 'prev_settlement', 'open_interest']
    
    def __init__(self, path: str, api_key: str = None, secret_key: str = None, testnet: bool = False):
        """
        初始化加密货币数据源
        
        Args:
            path: 数据存储路径
            api_key: Binance API 密钥
            secret_key: Binance 密钥
            testnet: 是否使用测试网
        """
        # print(f"=== CryptoDataSource.__init__ 被调用 ===")
        # print(f"path: {path}")
        if not os.path.exists(path):
            os.makedirs(path)
        
        self._path = path
        self._binance_provider = get_binance_provider(api_key, secret_key, testnet)
        
        # 初始化存储
        self._day_bars = {
            INSTRUMENT_TYPE.CRYPTO_SPOT: CryptoDayBarStore(os.path.join(path, 'crypto_spot.h5')),
            INSTRUMENT_TYPE.CRYPTO_FUTURE: CryptoDayBarStore(os.path.join(path, 'crypto_futures.h5')),
        }
        
        # 初始化合约信息
        self._instruments_stores = {}
        self._ins_id_or_sym_type_map = {}
        self._load_instruments()
        
        # 交易日历
        self._calendar_providers = {
            TRADING_CALENDAR_TYPE.CRYPTO: CryptoTradingCalendarStore()
        }
        
        # 其他存储（加密货币不需要分红、除权等）
        self._dividends = {}
        self._split_factors = {}
        self._ex_cum_factor = SimpleFactorStore(os.path.join(path, 'crypto_ex_factor.h5'))
        self._suspend_days = []  # 加密货币不停牌
        self._st_stock_days = DateSet(os.path.join(path, 'crypto_st_days.h5'))  # 空实现
    
    def _load_instruments(self):
        """加载合约信息"""
        instruments = []
        
        # 加载现货合约
        spot_instruments = self._binance_provider.get_instruments_info(futures=False)
        for info in spot_instruments:
            info['type'] = INSTRUMENT_TYPE.CRYPTO_SPOT
            instruments.append(Instrument(info))
        
        # 加载期货合约
        futures_instruments = self._binance_provider.get_instruments_info(futures=True)
        for info in futures_instruments:
            info['type'] = INSTRUMENT_TYPE.CRYPTO_FUTURE
            instruments.append(Instrument(info))
        
        # 注册合约存储
        for ins_type in [INSTRUMENT_TYPE.CRYPTO_SPOT, INSTRUMENT_TYPE.CRYPTO_FUTURE]:
            self.register_instruments_store(InstrumentStore(instruments, ins_type))
    
    def register_day_bar_store(self, instrument_type, store):
        """注册日线数据存储"""
        self._day_bars[instrument_type] = store
    
    def register_instruments_store(self, instruments_store):
        """注册合约存储"""
        instrument_type = instruments_store.instrument_type
        for id_or_sym in instruments_store.all_id_and_syms:
            self._ins_id_or_sym_type_map[id_or_sym] = instrument_type
        self._instruments_stores[instrument_type] = instruments_store
    
    def register_dividend_store(self, instrument_type, dividend_store):
        """注册分红存储（加密货币不需要）"""
        pass
    
    def register_split_store(self, instrument_type, split_store):
        """注册拆股存储（加密货币不需要）"""
        pass
    
    def register_calendar_store(self, calendar_type, calendar_store):
        """注册交易日历存储"""
        self._calendar_providers[calendar_type] = calendar_store
    
    def append_suspend_date_set(self, date_set):
        """添加停牌日期集（加密货币不需要）"""
        pass
    
    @lru_cache(2048)
    def get_dividend(self, instrument):
        """获取分红数据（加密货币不需要）"""
        return None
    
    def get_trading_minutes_for(self, order_book_id, trading_dt):
        """获取交易分钟（加密货币7x24小时）"""
        # 加密货币7x24小时交易，返回全天1440分钟
        start_time = trading_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return [start_time + timedelta(minutes=i) for i in range(1440)]
    
    def get_trading_calendars(self):
        """获取交易日历"""
        return {t: store.get_trading_calendar() for t, store in self._calendar_providers.items()}
    
    def get_instruments(self, id_or_syms=None, types=None):
        """获取合约信息"""
        if id_or_syms is not None:
            ins_type_getter = lambda i: self._ins_id_or_sym_type_map.get(i)
            type_id_iter = groupby(sorted(id_or_syms, key=ins_type_getter), key=ins_type_getter)
        else:
            type_id_iter = ((t, None) for t in types or self._instruments_stores.keys())
        
        for ins_type, id_or_syms in type_id_iter:
            if ins_type is not None and ins_type in self._instruments_stores:
                yield from self._instruments_stores[ins_type].get_instruments(id_or_syms)
    
    def get_share_transformation(self, order_book_id):
        """获取股份变更（加密货币不需要）"""
        return None
    
    def is_suspended(self, order_book_id, dates):
        """是否停牌（加密货币不停牌）"""
        return [False] * len(dates)
    
    def is_st_stock(self, order_book_id, dates):
        """是否ST股票（加密货币不需要）"""
        return [False] * len(dates)
    
    @lru_cache(None)
    def _all_day_bars_of(self, instrument):
        """获取合约的所有日线数据"""
        return self._day_bars[instrument.type].get_bars(instrument.order_book_id)
    
    @lru_cache(None)
    def _filtered_day_bars(self, instrument):
        """获取过滤后的日线数据"""
        bars = self._all_day_bars_of(instrument)
        return bars[bars['volume'] > 0]
    
    def get_bar(self, instrument, dt, frequency):
        """获取单根K线"""
        if frequency != '1d':
            raise NotImplementedError("Only daily bars are supported for crypto")
        
        bars = self._all_day_bars_of(instrument)
        if len(bars) <= 0:
            return None
        
        dt = np.uint64(convert_date_to_int(dt))
        pos = bars['datetime'].searchsorted(dt)
        if pos >= len(bars) or bars['datetime'][pos] != dt:
            return None
        
        return bars[pos]
    
    def get_open_auction_bar(self, instrument, dt):
        """获取集合竞价数据（加密货币没有集合竞价）"""
        day_bar = self.get_bar(instrument, dt, "1d")
        if day_bar is None:
            bar = dict.fromkeys(self.CRYPTO_FIELDS, np.nan)
        else:
            bar = {k: day_bar[k] if k in day_bar.dtype.names else np.nan for k in self.CRYPTO_FIELDS}
        bar["last"] = bar["open"]
        return bar
    
    def get_settle_price(self, instrument, date):
        """获取结算价（仅期货）"""
        if instrument.type != INSTRUMENT_TYPE.CRYPTO_FUTURE:
            return np.nan
        
        bar = self.get_bar(instrument, date, '1d')
        if bar is None:
            return np.nan
        return bar.get('settlement', bar['close'])
    
    def get_ex_cum_factor(self, order_book_id):
        """获取除权因子（加密货币不需要）"""
        return None
    
    def history_bars(self, instrument, bar_count, frequency, fields, dt,
                     skip_suspended=True, include_now=False,
                     adjust_type='none', adjust_orig=None):
        """获取历史K线数据"""
        if frequency not in ['1d', '1w']:
            raise NotImplementedError("Only daily and weekly bars are supported for crypto")
        
        # 加密货币不需要过滤停牌
        bars = self._all_day_bars_of(instrument)
        
        # 字段验证
        if fields is not None:
            if len(bars) > 0 and bars.dtype.names is not None:
                valid_fields = bars.dtype.names
            else:
                # 如果没有数据，使用默认字段
                valid_fields = self.CRYPTO_FIELDS
            if not self._are_fields_valid(fields, valid_fields):
                raise RQInvalidArgument("invalid fields: {}".format(fields))
        
        if len(bars) <= 0:
            return bars
        
        # 周线重采样
        if frequency == '1w':
            return self._resample_week_bars(bars, bar_count, fields, dt, include_now)
        
        # 日线数据
        dt = np.uint64(convert_date_to_int(dt))
        i = bars['datetime'].searchsorted(dt, side='right')
        left = i - bar_count if i >= bar_count else 0
        bars = bars[left:i]
        
        # 加密货币不需要复权
        return bars if fields is None else bars[fields]
    
    def _resample_week_bars(self, bars, bar_count, fields, dt, include_now):
        """重采样为周线数据"""
        df_bars = pd.DataFrame(bars)
        df_bars['datetime'] = df_bars.apply(lambda x: convert_int_to_datetime(x['datetime']), axis=1)
        df_bars = df_bars.set_index('datetime')
        
        # 重采样规则
        resample_rules = {
            'open': 'first',
            'close': 'last',
            'high': 'max',
            'low': 'min',
            'volume': 'sum',
            'total_turnover': 'sum'
        }
        
        if fields and isinstance(fields, str):
            fields = [fields]
        
        if fields:
            resample_rules = {k: v for k, v in resample_rules.items() if k in fields}
        
        df_bars = df_bars.resample('W-Fri').agg(resample_rules)
        df_bars = df_bars.dropna()
        df_bars = df_bars[-bar_count:]
        df_bars = df_bars.reset_index()
        df_bars['datetime'] = df_bars.apply(lambda x: np.uint64(convert_date_to_int(x['datetime'].date())), axis=1)
        
        return df_bars.to_records()
    
    @staticmethod
    def _are_fields_valid(fields, valid_fields):
        """验证字段是否有效"""
        if fields is None:
            return True
        if valid_fields is None:
            return False
        if isinstance(fields, str):
            return fields in valid_fields
        for field in fields:
            if field not in valid_fields:
                return False
        return True
    
    def current_snapshot(self, instrument, frequency, dt):
        """获取当前快照（需要实时数据）"""
        raise NotImplementedError("Real-time data not implemented yet")
    
    @lru_cache(2048)
    def get_split(self, instrument):
        """获取拆股数据（加密货币不需要）"""
        return None
    
    def available_data_range(self, frequency):
        """获取可用数据范围"""
        if frequency in ['tick', '1d']:
            # 获取第一个合约的数据范围
            for store in self._day_bars.values():
                try:
                    # 直接检查H5文件中的数据集
                    with h5py.File(store._file_path, 'r') as f:
                        if len(f.keys()) > 0:
                            first_symbol = list(f.keys())[0]
                            date_range = store.get_date_range(first_symbol)
                            if date_range:
                                start, end = date_range
                                return convert_int_to_date(start).date(), convert_int_to_date(end).date()
                except Exception as e:
                    print(f"Error getting date range: {e}")
                    continue
        return date.min, date.max
    
    def get_yield_curve(self, start_date, end_date, tenor=None):
        """获取收益率曲线（加密货币不需要）"""
        return None
    
    def get_futures_trading_parameters(self, instrument, dt):
        """获取期货交易参数"""
        # 简化实现，返回默认参数
        from rqalpha.data.base_data_source.storages import FuturesTradingParameters
        return FuturesTradingParameters(
            close_commission_ratio=0.0004,  # 0.04%
            close_commission_today_ratio=0.0004,
            commission_type="by_volume",
            open_commission_ratio=0.0004,
            long_margin_ratio=0.1,  # 10倍杠杆
            short_margin_ratio=0.1
        )
    
    def get_merge_ticks(self, order_book_id_list, trading_date, last_dt=None):
        """获取合并tick数据"""
        raise NotImplementedError("Tick data not implemented yet")
    
    def history_ticks(self, instrument, count, dt):
        """获取历史tick数据"""
        raise NotImplementedError("Tick data not implemented yet")
    
    def get_algo_bar(self, id_or_ins, start_min, end_min, dt):
        """获取算法交易bar"""
        raise NotImplementedError("Algo bars not implemented yet")
    
    def get_open_auction_volume(self, instrument, dt):
        """获取集合竞价成交量"""
        bar = self.get_open_auction_bar(instrument, dt)
        return bar.get('volume', 0)
    
    def update_data(self, symbols: List[str] = None, start_date: date = None, end_date: date = None):
        """
        更新数据
        
        Args:
            symbols: 要更新的交易对列表，None表示更新所有
            start_date: 开始日期
            end_date: 结束日期
        """
        if start_date is None:
            start_date = date.today() - timedelta(days=30)
        if end_date is None:
            end_date = date.today()
        
        if symbols is None:
            # 获取所有交易对
            spot_symbols = self._binance_provider.get_all_symbols(futures=False)
            futures_symbols = self._binance_provider.get_all_symbols(futures=True)
            symbols = spot_symbols + futures_symbols
        
        for symbol in symbols:
            try:
                # 确定合约类型
                if symbol in self._binance_provider.get_all_symbols(futures=True):
                    instrument_type = INSTRUMENT_TYPE.CRYPTO_FUTURE
                    futures = True
                else:
                    instrument_type = INSTRUMENT_TYPE.CRYPTO_SPOT
                    futures = False
                
                # 获取数据
                df = self._binance_provider.get_price_data(
                    symbol, start_date, end_date, futures=futures
                )
                
                if not df.empty:
                    # 转换为numpy数组
                    df = df.reset_index()
                    df['datetime'] = df['datetime'].apply(lambda x: convert_date_to_int(x.date()))
                    bars = df.to_records()
                    
                    # 存储数据
                    self._day_bars[instrument_type].store_bars(symbol, bars)
                    
            except Exception as e:
                print(f"Failed to update data for {symbol}: {e}")
                continue
