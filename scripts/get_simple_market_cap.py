#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用CoinGecko API获取过去365天的市值数据（简化版）
"""

import os
import sys
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def get_market_cap_data():
    """获取过去365天的市值数据"""
    print("🚀 开始获取CoinGecko市值数据...")
    print("=" * 60)
    
    # 使用API密钥
    api_key = "8dd32a6c-fd24-4d49-a3c3-e27fd29cb957"
    
    # 创建会话
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'RQAlpha-Crypto-Analysis/1.0',
        'x-cg-demo-api-key': api_key
    })
    
    # 1. 从bundle/crypto_currencies.csv读取所有币种
    print("📊 读取bundle/crypto_currencies.csv中的币种列表...")
    try:
        crypto_df = pd.read_csv('./bundle/crypto_currencies.csv')
        print(f"✅ 成功读取 {len(crypto_df)} 个币种")
        
        # 获取币种符号列表
        symbols = crypto_df['symbol'].tolist()
        print(f"📋 币种符号: {symbols[:10]}... (显示前10个)")
        
    except Exception as e:
        print(f"❌ 读取币种列表失败: {e}")
        return None
    
    # 2. 获取CoinGecko的币种ID映射
    print("🔍 获取CoinGecko币种ID映射...")
    try:
        response = session.get("https://api.coingecko.com/api/v3/coins/list", timeout=30)
        if response.status_code == 401:
            print("❌ API密钥无效，尝试不使用API密钥...")
            session.headers.pop('x-cg-demo-api-key', None)
            response = session.get("https://api.coingecko.com/api/v3/coins/list", timeout=30)
        
        response.raise_for_status()
        all_coins = response.json()
        print(f"✅ 成功获取 {len(all_coins)} 个CoinGecko币种")
        
        # 创建符号到ID的映射
        symbol_to_id = {}
        for coin in all_coins:
            symbol = coin['symbol'].upper()
            if symbol in symbols:
                symbol_to_id[symbol] = coin['id']
        
        print(f"✅ 找到 {len(symbol_to_id)} 个匹配的币种")
        
    except Exception as e:
        print(f"❌ 获取币种ID映射失败: {e}")
        return None
    
    # 3. 获取每个币种的历史市值数据
    market_cap_data = []
    matched_symbols = list(symbol_to_id.keys())
    total_symbols = len(matched_symbols)
    
    print(f"\n📊 开始获取历史市值数据...")
    print(f"📋 将处理 {total_symbols} 个匹配的币种")
    
    for i, symbol in enumerate(matched_symbols, 1):
        coin_id = symbol_to_id[symbol]
        
        print(f"[{i:3d}/{total_symbols}] 获取 {symbol} 的历史数据...")
        
        # 获取历史市值数据
        history_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        history_params = {
            'vs_currency': 'usd',
            'days': 365,
            'interval': 'daily'
        }
        
        try:
            response = session.get(history_url, params=history_params, timeout=30)
            
            if response.status_code == 401:
                print(f"    ⏳ API密钥无效，尝试不使用API密钥...")
                # 移除API密钥重试
                temp_session = requests.Session()
                temp_session.headers.update({
                    'User-Agent': 'RQAlpha-Crypto-Analysis/1.0'
                })
                response = temp_session.get(history_url, params=history_params, timeout=30)
            
            if response.status_code == 429:
                print(f"    ⏳ 遇到速率限制，等待10秒...")
                time.sleep(10)
                response = session.get(history_url, params=history_params, timeout=30)
            
            response.raise_for_status()
            history_data = response.json()
            
            if 'market_caps' in history_data:
                # 处理历史数据
                for timestamp, market_cap in history_data['market_caps']:
                    if market_cap is not None:
                        date = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')
                        market_cap_data.append({
                            'date': date,
                            'coin_id': coin_id,
                            'symbol': symbol,
                            'name': symbol,  # 使用符号作为名称
                            'market_cap_usd': market_cap,
                            'market_cap_rank': None  # 历史数据中没有排名
                        })
            
            print(f"    ✅ {symbol} 数据获取成功")
            
        except Exception as e:
            print(f"    ❌ {symbol} 数据获取失败: {e}")
        
        # 每获取5个币种后休息2分钟
        if i % 5 == 0 and i < total_symbols:
            print(f"    ⏳ 已获取 {i} 个币种，休息2分钟...")
            time.sleep(120)  # 休息2分钟
        else:
            # 其他情况只休息1秒
            time.sleep(1)
    
    # 3. 创建DataFrame
    df = pd.DataFrame(market_cap_data)
    
    if df.empty:
        print("❌ 没有获取到任何数据")
        return None
    
    # 4. 数据清理和排序
    df = df.sort_values(['date', 'market_cap_rank'])
    df = df.dropna(subset=['market_cap_usd'])
    
    print(f"\n✅ 成功获取 {len(df)} 条市值记录")
    print(f"📅 日期范围: {df['date'].min()} 到 {df['date'].max()}")
    print(f"🪙 涉及币种: {df['symbol'].nunique()} 个")
    
    # 5. 保存数据
    output_file = "./bundle/coingecko_market_cap_365d.csv"
    df.to_csv(output_file, index=False, encoding='utf-8')
    
    print(f"\n💾 数据已保存到: {output_file}")
    print(f"📄 文件大小: {os.path.getsize(output_file)} 字节")
    
    # 6. 显示统计信息
    print(f"\n📊 数据统计:")
    print(f"   总记录数: {len(df)}")
    print(f"   币种数量: {df['symbol'].nunique()}")
    print(f"   日期数量: {df['date'].nunique()}")
    print(f"   平均每日记录: {len(df) / df['date'].nunique():.1f}")
    
    # 显示前10条记录
    print(f"\n📋 前10条记录预览:")
    print(df.head(10).to_string(index=False))
    
    # 显示市值排名前10的币种
    print(f"\n🏆 当前市值排名前10:")
    latest_data = df[df['date'] == df['date'].max()].sort_values('market_cap_usd', ascending=False)
    for i, row in latest_data.head(10).iterrows():
        market_cap_b = row['market_cap_usd'] / 1e9
        print(f"   {row['market_cap_rank']:2d}. {row['symbol']:8s} - ${market_cap_b:.2f}B")
    
    print(f"\n🎉 市值数据获取完成！")
    print("=" * 60)
    
    return output_file


if __name__ == "__main__":
    try:
        csv_path = get_market_cap_data()
        if csv_path:
            print(f"\n✅ 成功生成CSV文件: {csv_path}")
        else:
            print(f"\n❌ 生成CSV文件失败")
    except KeyboardInterrupt:
        print(f"\n\n⏹️ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()
