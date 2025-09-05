#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析bundle/crypto_spot.h5文件内容
"""

import os
import sys
import pandas as pd
import h5py
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def analyze_crypto_spot_h5():
    """分析crypto_spot.h5文件内容"""
    print("🔍 分析bundle/crypto_spot.h5文件内容...")
    print("=" * 60)
    
    h5_file_path = "./test_crypto_bundle/crypto_spot.h5"
    
    if not os.path.exists(h5_file_path):
        print(f"❌ 文件不存在: {h5_file_path}")
        return
    
    print(f"📁 文件路径: {h5_file_path}")
    print(f"📄 文件大小: {os.path.getsize(h5_file_path)} 字节")
    
    try:
        # 使用h5py读取HDF5文件
        with h5py.File(h5_file_path, 'r') as f:
            print(f"\n📊 HDF5文件结构:")
            print(f"   根组键: {list(f.keys())}")
            
            # 遍历所有组和数据集
            def print_structure(name, obj):
                if isinstance(obj, h5py.Dataset):
                    print(f"   📄 数据集: {name}")
                    print(f"      形状: {obj.shape}")
                    print(f"      数据类型: {obj.dtype}")
                    if obj.size < 100:  # 如果数据量不大，显示一些样本
                        print(f"      样本数据: {obj[:]}")
                    else:
                        print(f"      前5个值: {obj[:5]}")
                elif isinstance(obj, h5py.Group):
                    print(f"   📁 组: {name}")
                    print(f"      子项: {list(obj.keys())}")
            
            f.visititems(print_structure)
            
            # 尝试用pandas读取
            print(f"\n📊 尝试用pandas读取...")
            try:
                # 读取所有数据
                df = pd.read_hdf(h5_file_path, key='data')
                print(f"✅ 成功读取数据")
                print(f"   数据形状: {df.shape}")
                print(f"   列名: {list(df.columns)}")
                print(f"   数据类型:")
                print(df.dtypes)
                print(f"\n📋 前10行数据:")
                print(df.head(10))
                print(f"\n📋 最后10行数据:")
                print(df.tail(10))
                
                # 统计信息
                print(f"\n📊 数据统计:")
                print(f"   总行数: {len(df)}")
                print(f"   总列数: {len(df.columns)}")
                print(f"   内存使用: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
                
                # 如果有日期列，显示日期范围
                date_columns = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
                if date_columns:
                    for col in date_columns:
                        print(f"   {col} 范围: {df[col].min()} 到 {df[col].max()}")
                
                # 如果有价格列，显示价格统计
                price_columns = [col for col in df.columns if any(x in col.lower() for x in ['price', 'close', 'open', 'high', 'low'])]
                if price_columns:
                    print(f"\n💰 价格列统计:")
                    for col in price_columns:
                        if df[col].dtype in ['float64', 'int64']:
                            print(f"   {col}: 最小值={df[col].min():.4f}, 最大值={df[col].max():.4f}, 平均值={df[col].mean():.4f}")
                
                # 如果有成交量列，显示成交量统计
                volume_columns = [col for col in df.columns if 'volume' in col.lower()]
                if volume_columns:
                    print(f"\n📈 成交量列统计:")
                    for col in volume_columns:
                        if df[col].dtype in ['float64', 'int64']:
                            print(f"   {col}: 最小值={df[col].min():.2f}, 最大值={df[col].max():.2f}, 平均值={df[col].mean():.2f}")
                
            except Exception as e:
                print(f"❌ pandas读取失败: {e}")
                
                # 尝试读取特定的键
                print(f"\n🔍 尝试读取特定键...")
                with h5py.File(h5_file_path, 'r') as f:
                    for key in f.keys():
                        try:
                            data = f[key][:]
                            print(f"   键 '{key}': 形状={data.shape}, 类型={data.dtype}")
                            if data.size < 20:
                                print(f"      数据: {data}")
                        except Exception as e2:
                            print(f"   键 '{key}': 读取失败 - {e2}")
    
    except Exception as e:
        print(f"❌ 读取HDF5文件失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    analyze_crypto_spot_h5()
