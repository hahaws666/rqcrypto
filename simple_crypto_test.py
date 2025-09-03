#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的加密货币策略测试
"""

import os
import sys
from datetime import datetime, date

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rqalpha.data.crypto_data_source import CryptoDataSource
from rqalpha.const import INSTRUMENT_TYPE, DEFAULT_ACCOUNT_TYPE
import pandas as pd

def test_crypto_data_source():
    """测试加密货币数据源"""
    print("测试加密货币数据源...")
    
    # 创建数据源
    data_source = CryptoDataSource("./test_crypto_bundle")
    
    # 获取合约信息
    instruments = list(data_source.get_instruments())
    print(f"获取到 {len(instruments)} 个合约")
    
    # 显示前5个合约
    for i, instrument in enumerate(instruments[:5]):
        print(f"{i+1}. {instrument.order_book_id} - {instrument.type}")
    
    # 测试获取K线数据
    if instruments:
        # 找一个有数据的合约
        test_instrument = None
        for inst in instruments:
            if inst.order_book_id == 'BTCUSDT':
                test_instrument = inst
                break
        
        if not test_instrument:
            test_instrument = instruments[0]
            
        print(f"\n测试获取 {test_instrument.order_book_id} 的K线数据...")
        
        try:
            # 获取最近5天的数据
            bars = data_source.history_bars(
                test_instrument, 5, '1d', 
                ['open', 'high', 'low', 'close', 'volume'], 
                datetime.now()
            )
            print(f"获取到 {len(bars)} 条K线数据")
            
            if len(bars) > 0:
                print("最近5天数据:")
                for i, bar in enumerate(bars):
                    print(f"  第{i+1}天: O={bar['open']:.2f}, H={bar['high']:.2f}, "
                          f"L={bar['low']:.2f}, C={bar['close']:.2f}, V={bar['volume']:.2f}")
        except Exception as e:
            print(f"获取K线数据失败: {e}")
    
    # 测试交易日历
    calendars = data_source.get_trading_calendars()
    crypto_calendar = calendars.get('CRYPTO')
    if crypto_calendar is not None:
        print(f"\n加密货币交易日历: {len(crypto_calendar)} 天")
        print(f"最近5个交易日: {crypto_calendar[-5:]}")
    
    print("\n数据源测试完成!")

def test_simple_strategy():
    """测试简单策略逻辑"""
    print("\n测试简单策略逻辑...")
    
    # 模拟策略逻辑
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    data_source = CryptoDataSource("./test_crypto_bundle")
    
    for symbol in symbols:
        try:
            # 查找对应的合约
            instruments = list(data_source.get_instruments())
            instrument = None
            for inst in instruments:
                if inst.order_book_id == symbol:
                    instrument = inst
                    break
            
            if instrument:
                # 获取历史数据
                bars = data_source.history_bars(
                    instrument, 5, '1d', 
                    ['close'], 
                    datetime.now()
                )
                
                if len(bars) >= 2:
                    current_price = bars[-1]['close']
                    prev_price = bars[-2]['close']
                    change = (current_price - prev_price) / prev_price * 100
                    
                    print(f"{symbol}: 当前价格={current_price:.2f}, "
                          f"涨跌幅={change:+.2f}%")
                    
                    # 简单策略：涨了就买，跌了就卖
                    if change > 1:
                        print(f"  -> 买入信号 (涨幅{change:.2f}%)")
                    elif change < -1:
                        print(f"  -> 卖出信号 (跌幅{change:.2f}%)")
                    else:
                        print(f"  -> 持有 (涨跌幅{change:.2f}%)")
                else:
                    print(f"{symbol}: 数据不足")
            else:
                print(f"{symbol}: 合约未找到")
                
        except Exception as e:
            print(f"{symbol}: 处理失败 - {e}")
    
    print("\n策略逻辑测试完成!")

if __name__ == "__main__":
    print("开始测试加密货币策略组件...")
    print("="*50)
    
    try:
        test_crypto_data_source()
        test_simple_strategy()
        
        print("\n" + "="*50)
        print("所有测试完成!")
        print("="*50)
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
