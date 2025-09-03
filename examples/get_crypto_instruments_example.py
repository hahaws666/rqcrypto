#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取加密货币合约示例
演示如何使用 get_all_crypto_instruments 函数
"""

import os
import sys
from datetime import date

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rqalpha.data.crypto_data_source import CryptoDataSource
from rqalpha.const import INSTRUMENT_TYPE


def main():
    """主函数"""
    print("🚀 获取加密货币合约示例")
    print("=" * 50)
    
    # 创建数据源
    data_source = CryptoDataSource("./test_crypto_bundle")
    
    # 1. 获取所有合约
    print("📊 获取所有加密货币合约...")
    all_instruments = data_source.get_all_crypto_instruments()
    print(f"✅ 总共获取到 {len(all_instruments)} 个合约")
    
    # 2. 按类型统计
    spot_count = sum(1 for ins in all_instruments if ins.type == INSTRUMENT_TYPE.CRYPTO_SPOT)
    futures_count = sum(1 for ins in all_instruments if ins.type == INSTRUMENT_TYPE.CRYPTO_FUTURE)
    
    print(f"📈 现货合约: {spot_count} 个")
    print(f"📊 期货合约: {futures_count} 个")
    
    # 3. 获取指定日期的合约（目前返回所有合约）
    print(f"\n🗓️ 获取指定日期的合约...")
    date_instruments = data_source.get_all_crypto_instruments(date(2025, 8, 1))
    print(f"✅ 指定日期获取到 {len(date_instruments)} 个合约")
    
    # 4. 显示一些热门合约
    print(f"\n🔥 热门合约示例:")
    popular_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
    
    for symbol in popular_symbols:
        # 查找对应的合约
        instrument = next((ins for ins in all_instruments if ins.symbol == symbol), None)
        if instrument:
            instrument_type = "现货" if instrument.type == INSTRUMENT_TYPE.CRYPTO_SPOT else "期货"
            print(f"   {symbol}: {instrument.order_book_id} ({instrument_type})")
        else:
            print(f"   {symbol}: 未找到")
    
    # 5. 按交易所统计
    print(f"\n🏢 按交易所统计:")
    exchanges = {}
    for instrument in all_instruments:
        exchange = instrument.exchange
        exchanges[exchange] = exchanges.get(exchange, 0) + 1
    
    for exchange, count in exchanges.items():
        print(f"   {exchange}: {count} 个合约")
    
    # 6. 查找特定类型的合约
    print(f"\n🔍 查找特定类型的合约:")
    
    # 查找所有USDT交易对
    usdt_pairs = [ins for ins in all_instruments if ins.symbol.endswith('USDT')]
    print(f"   USDT交易对: {len(usdt_pairs)} 个")
    
    # 查找所有BTC交易对
    btc_pairs = [ins for ins in all_instruments if ins.symbol.endswith('BTC')]
    print(f"   BTC交易对: {len(btc_pairs)} 个")
    
    # 查找所有ETH交易对
    eth_pairs = [ins for ins in all_instruments if ins.symbol.endswith('ETH')]
    print(f"   ETH交易对: {len(eth_pairs)} 个")
    
    print(f"\n🎉 示例完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
