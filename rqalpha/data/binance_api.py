# -*- coding: utf-8 -*-
"""
Binance API 集成模块
用于获取加密货币市场数据
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
import time
import logging

logger = logging.getLogger(__name__)


class BinanceAPI:
    """Binance API 客户端"""
    
    BASE_URL = "https://api.binance.com"
    FUTURES_BASE_URL = "https://fapi.binance.com"
    
    def __init__(self, api_key: str = None, secret_key: str = None, testnet: bool = False):
        """
        初始化 Binance API 客户端
        
        Args:
            api_key: API 密钥
            secret_key: 密钥
            testnet: 是否使用测试网
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet
        
        if testnet:
            self.BASE_URL = "https://testnet.binance.vision"
            self.FUTURES_BASE_URL = "https://testnet.binancefuture.com"
    
    def _make_request(self, endpoint: str, params: Dict = None, futures: bool = False) -> Dict:
        """发送 HTTP 请求"""
        base_url = self.FUTURES_BASE_URL if futures else self.BASE_URL
        url = f"{base_url}{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Binance API request failed: {e}")
            raise
    
    def get_exchange_info(self, futures: bool = False) -> Dict:
        """获取交易所信息"""
        endpoint = "/fapi/v1/exchangeInfo" if futures else "/api/v3/exchangeInfo"
        return self._make_request(endpoint, futures=futures)
    
    def get_symbols(self, futures: bool = False) -> List[str]:
        """获取所有交易对符号"""
        exchange_info = self.get_exchange_info(futures)
        symbols = []
        for symbol_info in exchange_info['symbols']:
            if symbol_info['status'] == 'TRADING':
                symbols.append(symbol_info['symbol'])
        return symbols
    
    def get_klines(self, symbol: str, interval: str, start_time: Union[str, int, datetime] = None, 
                   end_time: Union[str, int, datetime] = None, limit: int = 1000, futures: bool = False) -> pd.DataFrame:
        """
        获取K线数据
        
        Args:
            symbol: 交易对符号，如 'BTCUSDT'
            interval: 时间间隔，如 '1d', '1h', '1m'
            start_time: 开始时间
            end_time: 结束时间
            limit: 限制条数，最大1000
            futures: 是否期货数据
        """
        endpoint = "/fapi/v1/klines" if futures else "/api/v3/klines"
        
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': min(limit, 1000)
        }
        
        # 只有当start_time和end_time都存在时才添加时间参数
        # 注意：Binance API对时间参数很敏感，建议只使用limit参数
        if start_time and end_time:
            # 检查时间范围是否合理（不超过1000条数据）
            if isinstance(start_time, datetime):
                start_ts = int(start_time.timestamp() * 1000)
            elif isinstance(start_time, str):
                start_ts = int(pd.to_datetime(start_time).timestamp() * 1000)
            else:
                start_ts = start_time
                
            if isinstance(end_time, datetime):
                end_ts = int(end_time.timestamp() * 1000)
            elif isinstance(end_time, str):
                end_ts = int(pd.to_datetime(end_time).timestamp() * 1000)
            else:
                end_ts = end_time
            
            # 只有当时间范围合理时才添加时间参数
            time_diff = end_ts - start_ts
            if time_diff > 0 and time_diff < 1000 * 24 * 60 * 60 * 1000:  # 1000天的毫秒数
                params['startTime'] = start_ts
                params['endTime'] = end_ts
        
        data = self._make_request(endpoint, params, futures=futures)
        
        # 转换为 DataFrame
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # 数据类型转换
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
        
        for col in ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df['number_of_trades'] = pd.to_numeric(df['number_of_trades'], errors='coerce')
        
        return df
    
    def get_24hr_ticker(self, symbol: str = None, futures: bool = False) -> Union[Dict, List[Dict]]:
        """获取24小时价格变动统计"""
        endpoint = "/fapi/v1/ticker/24hr" if futures else "/api/v3/ticker/24hr"
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return self._make_request(endpoint, params, futures=futures)
    
    def get_ticker_price(self, symbol: str = None, futures: bool = False) -> Union[Dict, List[Dict]]:
        """获取最新价格"""
        endpoint = "/fapi/v1/ticker/price" if futures else "/api/v3/ticker/price"
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return self._make_request(endpoint, params, futures=futures)
    
    def get_order_book(self, symbol: str, limit: int = 100, futures: bool = False) -> Dict:
        """获取订单簿"""
        endpoint = "/fapi/v1/depth" if futures else "/api/v3/depth"
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        return self._make_request(endpoint, params, futures=futures)
    
    def get_recent_trades(self, symbol: str, limit: int = 500, futures: bool = False) -> List[Dict]:
        """获取最近成交记录"""
        endpoint = "/fapi/v1/aggTrades" if futures else "/api/v3/aggTrades"
        params = {
            'symbol': symbol,
            'limit': min(limit, 1000)
        }
        
        return self._make_request(endpoint, params, futures=futures)
    
    def get_server_time(self, futures: bool = False) -> Dict:
        """获取服务器时间"""
        endpoint = "/fapi/v1/time" if futures else "/api/v3/time"
        return self._make_request(endpoint, futures=futures)


class BinanceDataProvider:
    """Binance 数据提供者，适配 RQAlpha 数据接口"""
    
    def __init__(self, api_key: str = None, secret_key: str = None, testnet: bool = False):
        self.api = BinanceAPI(api_key, secret_key, testnet)
        self._symbols_cache = {}
        self._last_update = {}
    
    def get_all_symbols(self, futures: bool = False) -> List[str]:
        """获取所有交易对"""
        cache_key = f"symbols_{futures}"
        if cache_key not in self._symbols_cache:
            self._symbols_cache[cache_key] = self.api.get_symbols(futures)
        return self._symbols_cache[cache_key]
    
    def get_price_data(self, symbol: str, start_date: Union[str, datetime], 
                      end_date: Union[str, datetime], fields: List[str] = None, 
                      futures: bool = False) -> pd.DataFrame:
        """
        获取价格数据，适配 RQAlpha 接口
        
        Args:
            symbol: 交易对符号
            start_date: 开始日期
            end_date: 结束日期
            fields: 需要的字段
            futures: 是否期货数据
        """
        # 转换日期格式
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)
        
        # 限制数据范围，避免请求过多数据
        if (end_date - start_date).days > 1000:
            start_date = end_date - pd.Timedelta(days=1000)
        
        # 获取日线数据
        df = self.api.get_klines(symbol, '1d', start_date, end_date, futures=futures)
        
        if df.empty:
            return df
        
        # 重命名列以匹配 RQAlpha 格式
        df = df.rename(columns={
            'open_time': 'datetime',
            'open': 'open',
            'high': 'high', 
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'quote_asset_volume': 'total_turnover'
        })
        
        # 添加缺失字段
        df['prev_close'] = df['close'].shift(1)
        df['limit_up'] = np.nan  # 加密货币没有涨跌停限制
        df['limit_down'] = np.nan
        
        # 期货特有字段
        if futures:
            df['settlement'] = df['close']  # 简化处理
            df['prev_settlement'] = df['settlement'].shift(1)
            df['open_interest'] = np.nan  # 需要单独获取
        
        # 设置索引
        df = df.set_index('datetime')
        
        # 过滤字段
        if fields:
            available_fields = [f for f in fields if f in df.columns]
            df = df[available_fields]
        
        return df
    
    def get_instruments_info(self, futures: bool = False) -> List[Dict]:
        """获取合约信息"""
        exchange_info = self.api.get_exchange_info(futures)
        instruments = []
        
        for symbol_info in exchange_info['symbols']:
            if symbol_info['status'] == 'TRADING':
                instrument = {
                    'order_book_id': symbol_info['symbol'],
                    'symbol': symbol_info['symbol'],
                    'type': 'CryptoFuture' if futures else 'CryptoSpot',
                    'exchange': 'BINANCE_FUTURES' if futures else 'BINANCE',
                    'listed_date': datetime(2017, 1, 1),  # 默认上市日期
                    'de_listed_date': None,
                    'round_lot': 1,
                    'tick_size': float(symbol_info['filters'][0]['tickSize']) if symbol_info['filters'] else 0.01,
                    'contract_multiplier': 1,
                    'underlying_symbol': symbol_info['baseAsset'],
                    'quote_currency': symbol_info['quoteAsset']
                }
                instruments.append(instrument)
        
        return instruments
    
    def get_trading_calendar(self, start_date: datetime, end_date: datetime) -> pd.DatetimeIndex:
        """获取加密货币交易日历（7x24小时）"""
        # 加密货币是7x24小时交易，生成所有日期
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        return dates


# 全局实例
_binance_provider = None

def get_binance_provider(api_key: str = None, secret_key: str = None, testnet: bool = False) -> BinanceDataProvider:
    """获取全局 Binance 数据提供者实例"""
    global _binance_provider
    if _binance_provider is None:
        _binance_provider = BinanceDataProvider(api_key, secret_key, testnet)
    return _binance_provider
