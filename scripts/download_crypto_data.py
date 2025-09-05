#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
加密货币数据下载脚本
简单易用的数据下载工具
"""

import os
import sys
import argparse
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rqalpha.data.bundle import update_crypto_bundle


def download_crypto_data(bundle_path="./test_crypto_bundle", create=True):
    """
    下载加密货币数据
    
    Args:
        bundle_path: 数据包保存路径
        create: 是否创建新数据包
    """
    print("🚀 开始下载加密货币数据...")
    print(f"📁 数据包路径: {bundle_path}")
    print(f"🔄 创建模式: {'是' if create else '否'}")
    print("-" * 50)
    
    try:
        # 下载数据
        success = update_crypto_bundle(bundle_path, create=create)
        
        if success:
            print("✅ 数据下载成功！")
            print(f"📁 数据包位置: {os.path.abspath(bundle_path)}")
            
            # 显示数据包内容
            print("\n📊 数据包内容:")
            if os.path.exists(bundle_path):
                for file in os.listdir(bundle_path):
                    file_path = os.path.join(bundle_path, file)
                    if os.path.isfile(file_path):
                        size = os.path.getsize(file_path)
                        print(f"  📄 {file}: {size:,} bytes")
            
            print("\n🎉 数据下载完成！现在可以运行策略了。")
            print("💡 运行策略: python examples/crypto_strategy_working.py")
            
        else:
            print("❌ 数据下载失败！")
            print("🔍 可能的原因:")
            print("  - 网络连接问题")
            print("  - Binance API 限制")
            print("  - 磁盘空间不足")
            print("  - 权限问题")
            
    except Exception as e:
        print(f"❌ 下载过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


def validate_bundle(bundle_path):
    """验证数据包完整性"""
    print(f"🔍 验证数据包: {bundle_path}")
    
    required_files = [
        "crypto_instruments.pk",
        "crypto_trading_dates.npy", 
        "crypto_spot.h5",
        "crypto_futures.h5"
    ]
    
    all_valid = True
    
    for file in required_files:
        file_path = os.path.join(bundle_path, file)
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"  ✅ {file}: {size:,} bytes")
        else:
            print(f"  ❌ 缺少文件: {file}")
            all_valid = False
    
    if all_valid:
        print("✅ 数据包验证通过！")
    else:
        print("❌ 数据包验证失败！")
    
    return all_valid


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="加密货币数据下载工具")
    parser.add_argument("--path", "-p", default="./test_crypto_bundle", 
                       help="数据包保存路径 (默认: ./test_crypto_bundle)")
    parser.add_argument("--update", "-u", action="store_true", 
                       help="更新现有数据包")
    parser.add_argument("--validate", "-v", action="store_true", 
                       help="验证数据包完整性")
    parser.add_argument("--list", "-l", action="store_true", 
                       help="列出现有数据包")
    
    args = parser.parse_args()
    
    if args.list:
        # 列出现有数据包
        print("📁 现有数据包:")
        if os.path.exists(args.path):
            for item in os.listdir(args.path):
                item_path = os.path.join(args.path, item)
                if os.path.isdir(item_path):
                    print(f"  📂 {item}")
        else:
            print("  📂 无数据包")
        return
    
    if args.validate:
        # 验证数据包
        validate_bundle(args.path)
        return
    
    # 下载数据
    create = not args.update
    download_crypto_data(args.path, create=create)


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 RQAlpha 加密货币数据下载工具")
    print("=" * 60)
    
    main()
