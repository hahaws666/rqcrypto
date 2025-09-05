#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用CoinGecko API获取所有币种过去365天的市值数据
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


class CoinGeckoAPI:
    """CoinGecko API客户端"""
    
    def __init__(self, api_key=None):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RQAlpha-Crypto-Analysis/1.0'
        })
        if api_key:
            self.session.headers.update({
                'x-cg-demo-api-key': api_key
            })
            # 在URL参数中添加API密钥
            self.api_key_param = {'x_cg_demo_api_key': api_key}
    
    def get_all_coins(self):
        """获取所有币种列表"""
        print("📊 获取所有币种列表...")
        url = f"{self.base_url}/coins/list"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            coins = response.json()
            print(f"✅ 成功获取 {len(coins)} 个币种")
            return coins
        except Exception as e:
            print(f"❌ 获取币种列表失败: {e}")
            return []
    
    def get_coin_market_cap_history(self, coin_id, days=365):
        """获取指定币种的市值历史数据"""
        url = f"{self.base_url}/coins/{coin_id}/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': days,
            'interval': 'daily'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            print(f"❌ 获取 {coin_id} 市值数据失败: {e}")
            return None
    
    def get_top_coins_market_cap(self, limit=100):
        """获取市值排名前N的币种"""
        print(f"📈 获取市值排名前 {limit} 的币种...")
        url = f"{self.base_url}/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': limit,
            'page': 1,
            'sparkline': False,
            'price_change_percentage': '1h,24h,7d,30d,1y'
        }
        
        # 如果有API密钥，添加到参数中
        if hasattr(self, 'api_key_param'):
            params.update(self.api_key_param)
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            coins = response.json()
            print(f"✅ 成功获取 {len(coins)} 个币种的市场数据")
            return coins
        except Exception as e:
            print(f"❌ 获取市场数据失败: {e}")
            return []


def get_market_cap_data():
    """获取市值数据的主函数"""
    print("🚀 开始获取CoinGecko市值数据...")
    print("=" * 60)
    
    # 使用API密钥
    api_key = "8dd32a6c-fd24-4d49-a3c3-e27fd29cb957"
    api = CoinGeckoAPI(api_key)
    
    # 1. 获取市值排名前30的币种（减少请求数量）
    top_coins = api.get_top_coins_market_cap(30)
    if not top_coins:
        print("❌ 无法获取币种数据")
        return None
    
    # 2. 准备数据存储
    market_cap_data = []
    
    print(f"\n📊 开始获取历史市值数据...")
    for i, coin in enumerate(top_coins, 1):
        coin_id = coin['id']
        symbol = coin['symbol'].upper()
        name = coin['name']
        current_market_cap = coin['market_cap']
        
        print(f"[{i:2d}/30] 获取 {symbol} ({name}) 的历史数据...")
        
        # 获取历史市值数据
        history_data = api.get_coin_market_cap_history(coin_id, 365)
        
        if history_data and 'market_caps' in history_data:
            # 处理历史数据
            for timestamp, market_cap in history_data['market_caps']:
                if market_cap is not None:
                    date = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')
                    market_cap_data.append({
                        'date': date,
                        'coin_id': coin_id,
                        'symbol': symbol,
                        'name': name,
                        'market_cap_usd': market_cap,
                        'market_cap_rank': coin.get('market_cap_rank', None)
                    })
        
        # 添加当前市值数据
        if current_market_cap:
            today = datetime.now().strftime('%Y-%m-%d')
            market_cap_data.append({
                'date': today,
                'coin_id': coin_id,
                'symbol': symbol,
                'name': name,
                'market_cap_usd': current_market_cap,
                'market_cap_rank': coin.get('market_cap_rank', None)
            })
        
        # 每获取5个币种后休息2分钟
        if i % 5 == 0 and i < len(top_coins):
            print(f"    ⏳ 已获取 {i} 个币种，休息2分钟...")
            time.sleep(120)  # 休息2分钟
        else:
            # 其他情况只休息0.5秒
            time.sleep(0.5)
    
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


def get_simple_market_cap_data():
    """获取简化的市值数据（避免API限制）"""
    print("🚀 开始获取CoinGecko简化市值数据...")
    print("=" * 60)
    
    # 使用API密钥
    api_key = "8dd32a6c-fd24-4d49-a3c3-e27fd29cb957"
    api = CoinGeckoAPI(api_key)
    
    # 获取市值排名前50的币种
    top_coins = api.get_top_coins_market_cap(50)
    if not top_coins:
        print("❌ 无法获取币种数据")
        return None
    
    # 创建简化的市值数据
    market_cap_data = []
    today = datetime.now().strftime('%Y-%m-%d')
    
    for coin in top_coins:
        market_cap_data.append({
            'date': today,
            'coin_id': coin['id'],
            'symbol': coin['symbol'].upper(),
            'name': coin['name'],
            'market_cap_usd': coin['market_cap'],
            'market_cap_rank': coin.get('market_cap_rank', None),
            'current_price': coin['current_price'],
            'price_change_24h': coin.get('price_change_percentage_24h', None),
            'price_change_7d': coin.get('price_change_percentage_7d_in_currency', None),
            'price_change_30d': coin.get('price_change_percentage_30d_in_currency', None),
            'price_change_1y': coin.get('price_change_percentage_1y_in_currency', None),
            'volume_24h': coin.get('total_volume', None),
            'circulating_supply': coin.get('circulating_supply', None),
            'total_supply': coin.get('total_supply', None),
            'max_supply': coin.get('max_supply', None)
        })
    
    # 创建DataFrame
    df = pd.DataFrame(market_cap_data)
    df = df.sort_values('market_cap_rank')
    
    # 保存数据
    output_file = "./bundle/coingecko_market_cap_current.csv"
    df.to_csv(output_file, index=False, encoding='utf-8')
    
    print(f"✅ 成功获取 {len(df)} 个币种的当前市值数据")
    print(f"💾 数据已保存到: {output_file}")
    
    # 显示前10个币种
    print(f"\n🏆 市值排名前10:")
    for i, row in df.head(10).iterrows():
        market_cap_b = row['market_cap_usd'] / 1e9
        price_change = row['price_change_24h']
        change_str = f"+{price_change:.2f}%" if price_change > 0 else f"{price_change:.2f}%"
        print(f"   {row['market_cap_rank']:2d}. {row['symbol']:8s} - ${market_cap_b:.2f}B ({change_str})")
    
    return output_file


if __name__ == "__main__":
    try:
        print("选择获取模式:")
        print("1. 获取历史365天市值数据（较慢，需要更多API调用）")
        print("2. 获取当前市值数据（快速）")
        
        choice = input("请选择 (1/2): ").strip()
        
        if choice == "1":
            csv_path = get_market_cap_data()
        else:
            csv_path = get_simple_market_cap_data()
        
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
