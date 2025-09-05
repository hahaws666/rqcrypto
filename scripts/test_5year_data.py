#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试5年数据下载功能
"""

import os
import sys
import h5py
import numpy as np
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rqalpha.data.bundle import update_crypto_bundle


def test_5year_data():
    """测试5年数据下载"""
    print("🚀 开始测试5年数据下载...")
    print("=" * 60)
    
    # 设置数据路径
    bundle_path = "./test_5year_crypto_bundle"
    
    # 创建目录
    os.makedirs(bundle_path, exist_ok=True)
    
    print(f"📁 数据将保存到: {bundle_path}")
    
    try:
        # 更新加密货币数据包
        print("📊 开始下载5年加密货币数据...")
        success = update_crypto_bundle(bundle_path, create=True)
        
        if success:
            print("✅ 数据下载成功！")
            
            # 分析下载的数据
            analyze_downloaded_data(bundle_path)
        else:
            print("❌ 数据下载失败！")
            
    except Exception as e:
        print(f"❌ 下载过程中出错: {e}")
        import traceback
        traceback.print_exc()


def analyze_downloaded_data(bundle_path):
    """分析下载的数据"""
    print("\n📊 分析下载的数据...")
    print("=" * 40)
    
    # 检查文件是否存在
    spot_file = os.path.join(bundle_path, 'crypto_spot.h5')
    futures_file = os.path.join(bundle_path, 'crypto_futures.h5')
    
    if os.path.exists(spot_file):
        print(f"✅ 现货数据文件存在: {os.path.getsize(spot_file)} 字节")
        analyze_h5_file(spot_file, "现货")
    else:
        print("❌ 现货数据文件不存在")
    
    if os.path.exists(futures_file):
        print(f"✅ 期货数据文件存在: {os.path.getsize(futures_file)} 字节")
        analyze_h5_file(futures_file, "期货")
    else:
        print("❌ 期货数据文件不存在")


def analyze_h5_file(file_path, data_type):
    """分析H5文件内容"""
    try:
        with h5py.File(file_path, 'r') as f:
            symbols = list(f.keys())
            print(f"   📈 {data_type}数据包含 {len(symbols)} 个交易对")
            
            if symbols:
                # 分析第一个交易对的数据
                first_symbol = symbols[0]
                data = f[first_symbol]
                print(f"   📅 {first_symbol} 数据量: {len(data)} 条记录")
                
                if len(data) > 0:
                    # 获取日期范围
                    first_date = data[0]['datetime']
                    last_date = data[-1]['datetime']
                    
                    # 转换日期格式
                    first_date_str = datetime.strptime(str(first_date), '%Y%m%d%H%M%S').strftime('%Y-%m-%d')
                    last_date_str = datetime.strptime(str(last_date), '%Y%m%d%H%M%S').strftime('%Y-%m-%d')
                    
                    print(f"   📅 日期范围: {first_date_str} 到 {last_date_str}")
                    
                    # 计算实际天数
                    days = (datetime.strptime(str(last_date), '%Y%m%d%H%M%S') - 
                           datetime.strptime(str(first_date), '%Y%m%d%H%M%S')).days + 1
                    print(f"   📊 实际天数: {days} 天")
                    
                    # 显示前几条数据
                    print(f"   📋 {first_symbol} 前3条数据:")
                    for i in range(min(3, len(data))):
                        record = data[i]
                        date_str = datetime.strptime(str(record['datetime']), '%Y%m%d%H%M%S').strftime('%Y-%m-%d')
                        print(f"      {date_str}: 开盘={record['open']:.4f}, 收盘={record['close']:.4f}, 成交量={record['volume']:.2f}")
    
    except Exception as e:
        print(f"   ❌ 分析{data_type}数据时出错: {e}")


if __name__ == "__main__":
    test_5year_data()
