#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
加密货币策略示例
展示如何使用爆改后的 RQAlpha 进行加密货币交易
"""

import os
import sys
from datetime import datetime, date

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rqalpha import run_func
from rqalpha.const import INSTRUMENT_TYPE, DEFAULT_ACCOUNT_TYPE
from rqalpha.api import *


def init(context):
    """初始化函数"""
    # 设置加密货币账户
    context.crypto_account = context.accounts[DEFAULT_ACCOUNT_TYPE.CRYPTO]
    
    # 选择要交易的加密货币
    context.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    
    # 设置基准
    context.benchmark = 'BTCUSDT'
    
    # 设置调度器
    scheduler.run_daily(before_trading, time_rule=market_open(minute=0))
    scheduler.run_daily(handle_bar, time_rule=market_open(minute=0))
    
    print("加密货币策略初始化完成")
    print(f"交易标的: {context.symbols}")
    print(f"初始资金: {context.crypto_account.total_value}")


def before_trading(context, bar_dict):
    """交易前处理"""
    print(f"交易日期: {context.now}")
    print(f"账户总价值: {context.crypto_account.total_value:.2f}")


def handle_bar(context, bar_dict):
    """处理K线数据"""
    print(f"\n=== {context.now} 交易信号 ===")
    
    # 获取历史数据进行分析
    for symbol in context.symbols:
        try:
            # 获取最近5天的数据
            hist = history_bars(symbol, 5, '1d', ['close', 'volume'])
            if len(hist) > 0:
                current_price = hist['close'][-1]
                avg_price = hist['close'].mean()
                
                print(f"{symbol}: 当前价格={current_price:.2f}, 5日均价={avg_price:.2f}")
                
                # 简单的均线策略
                position = context.crypto_account.get_position(symbol)
                if current_price > avg_price and position.quantity == 0:
                    # 价格高于均线且无持仓，买入
                    order_target_percent(symbol, 0.33)
                    print(f"买入 {symbol}: {current_price:.2f}")
                elif current_price < avg_price and position.quantity > 0:
                    # 价格低于均线且有持仓，卖出
                    order_target_percent(symbol, 0)
                    print(f"卖出 {symbol}: {current_price:.2f}")
        except Exception as e:
            print(f"处理 {symbol} 时出错: {e}")
    
    # 显示当前持仓
    print("\n当前持仓:")
    for symbol in context.symbols:
        position = context.crypto_account.get_position(symbol)
        if position.quantity > 0:
            print(f"{symbol}: {position.quantity:.4f} 单位, 市值: {position.market_value:.2f}")


def run_crypto_strategy():
    """运行加密货币策略"""
    config = {
        "base": {
            "start_date": "2025-08-01",  # 使用有数据的日期
            "end_date": "2025-09-03",
            "frequency": "1d",
            "accounts": {
                DEFAULT_ACCOUNT_TYPE.CRYPTO: 1000000  # 100万初始资金
            }
        },
        "extra": {
            "log_level": "info",
        },
        "mod": {
            "sys_accounts": {
                "enabled": True,
                "account_type": DEFAULT_ACCOUNT_TYPE.CRYPTO
            },
            "sys_analyser": {
                "enabled": True,
                "benchmark": "BTCUSDT"
            },
            "sys_simulation": {
                "enabled": True,
                "matching_type": "current_bar"
            },
            "sys_data_source": {
                "enabled": True,
                "data_source": "rqalpha.data.crypto_data_source.CryptoDataSource",
                "data_source_path": "./test_crypto_bundle"
            }
        }
    }
    
    # 运行策略
    result = run_func(
        init=init, 
        before_trading=before_trading,
        handle_bar=handle_bar, 
        config=config
    )
    return result


if __name__ == "__main__":
    print("开始运行加密货币策略...")
    try:
        result = run_crypto_strategy()
        print("\n" + "="*50)
        print("策略运行完成!")
        print("="*50)
        
        # 显示回测结果
        if hasattr(result, 'total_returns'):
            print(f"总收益率: {result.total_returns:.2%}")
        if hasattr(result, 'annual_returns'):
            print(f"年化收益率: {result.annual_returns:.2%}")
        if hasattr(result, 'max_drawdown'):
            print(f"最大回撤: {result.max_drawdown:.2%}")
        if hasattr(result, 'sharpe'):
            print(f"夏普比率: {result.sharpe:.2f}")
        
        # 显示交易统计
        if hasattr(result, 'trades'):
            print(f"总交易次数: {len(result.trades)}")
        
        print("="*50)
        
    except Exception as e:
        print(f"策略运行失败: {e}")
        import traceback
        traceback.print_exc()
