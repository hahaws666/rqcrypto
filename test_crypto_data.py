#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试加密货币数据获取功能
"""

import os
import sys
import pandas as pd
from datetime import datetime, date, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rqalpha.data.binance_api import BinanceAPI, BinanceDataProvider
from rqalpha.data.crypto_data_source import CryptoDataSource
from rqalpha.data.bundle import update_crypto_bundle


def test_binance_api():
    """测试 Binance API 基本功能"""
    print("=== 测试 Binance API ===")
    
    api = BinanceAPI()
    
    # 测试获取交易对
    symbols = api.get_symbols()
    print(f"获取到 {len(symbols)} 个现货交易对")
    print(f"前10个交易对: {symbols[:10]}")
    
    # 测试获取K线数据
    df = api.get_klines('BTCUSDT', '1d', limit=5)
    print(f"\nBTCUSDT 最近5天数据:")
    print(df[['open_time', 'open', 'high', 'low', 'close', 'volume']].head())
    
    # 测试获取价格
    price = api.get_ticker_price('BTCUSDT')
    print(f"\nBTCUSDT 当前价格: {price['price']}")
    
    return True


def test_binance_provider():
    """测试 Binance 数据提供者"""
    print("\n=== 测试 Binance 数据提供者 ===")
    
    provider = BinanceDataProvider()
    
    # 测试获取合约信息
    instruments = provider.get_instruments_info(futures=False)
    print(f"获取到 {len(instruments)} 个现货合约")
    print(f"前5个合约: {[i['order_book_id'] for i in instruments[:5]]}")
    
    # 测试获取价格数据 - 使用更短的时间范围
    end_date = date.today()
    start_date = end_date - timedelta(days=3)
    
    try:
        df = provider.get_price_data('BTCUSDT', start_date, end_date, futures=False)
        if not df.empty:
            print(f"\nBTCUSDT 最近3天数据:")
            print(df[['open', 'high', 'low', 'close', 'volume']].head())
        else:
            print("\nBTCUSDT 数据为空")
    except Exception as e:
        print(f"\n获取BTCUSDT数据失败: {e}")
    
    return True


def test_crypto_data_source():
    """测试加密货币数据源"""
    print("\n=== 测试加密货币数据源 ===")
    
    # 创建测试数据目录
    test_data_path = "./test_crypto_data"
    if not os.path.exists(test_data_path):
        os.makedirs(test_data_path)
    
    # 初始化数据源
    data_source = CryptoDataSource(test_data_path)
    
    # 测试获取合约
    instruments = list(data_source.get_instruments(types=['CryptoSpot']))
    print(f"获取到 {len(instruments)} 个现货合约")
    
    if instruments:
        instrument = instruments[0]
        print(f"测试合约: {instrument.order_book_id}")
        
        # 测试获取K线数据
        try:
            bars = data_source.history_bars(
                instrument, 5, '1d', ['open', 'high', 'low', 'close', 'volume'], 
                datetime.now()
            )
            print(f"获取到 {len(bars)} 条K线数据")
            if len(bars) > 0:
                print("最近5天数据:")
                print(bars)
            else:
                print("没有获取到K线数据")
        except Exception as e:
            print(f"获取K线数据失败: {e}")
    
    # 测试交易日历
    calendar = data_source.get_trading_calendars()
    crypto_calendar = calendar.get('CRYPTO')
    if crypto_calendar is not None:
        print(f"\n加密货币交易日历: {len(crypto_calendar)} 天")
        print(f"最近5个交易日: {crypto_calendar[-5:]}")
    
    return True


def test_crypto_bundle_generation():
    """测试加密货币数据包生成"""
    print("\n=== 测试加密货币数据包生成 ===")
    
    test_data_path = "./test_crypto_bundle"
    if not os.path.exists(test_data_path):
        os.makedirs(test_data_path)
    
    try:
        # 生成加密货币数据包
        success = update_crypto_bundle(test_data_path, create=True, concurrency=1)
        print(f"数据包生成结果: {'成功' if success else '失败'}")
        
        # 检查生成的文件
        expected_files = [
            'crypto_instruments.pk',
            'crypto_trading_dates.npy',
            'crypto_spot.h5',
            'crypto_futures.h5'
        ]
        
        for file_name in expected_files:
            file_path = os.path.join(test_data_path, file_name)
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"✓ {file_name}: {size} bytes")
            else:
                print(f"✗ {file_name}: 文件不存在")
        
        return success
        
    except Exception as e:
        print(f"数据包生成失败: {e}")
        return False


def main():
    """主测试函数"""
    print("开始测试加密货币数据获取功能...")
    
    tests = [
        ("Binance API", test_binance_api),
        ("Binance 数据提供者", test_binance_provider),
        ("加密货币数据源", test_crypto_data_source),
        ("加密货币数据包生成", test_crypto_bundle_generation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"✓ {test_name}: {'通过' if result else '失败'}")
        except Exception as e:
            results.append((test_name, False))
            print(f"✗ {test_name}: 异常 - {e}")
    
    print(f"\n=== 测试总结 ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"通过: {passed}/{total}")
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")


if __name__ == "__main__":
    main()
