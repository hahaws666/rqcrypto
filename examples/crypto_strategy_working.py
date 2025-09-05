#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工作版加密货币策略示例
使用5年历史数据包，正确配置数据源，使用爆改后的 RQAlpha 进行加密货币交易
"""

import os
import sys
from datetime import datetime, date

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rqalpha import run_func
from rqalpha.const import INSTRUMENT_TYPE, DEFAULT_ACCOUNT_TYPE, POSITION_DIRECTION
from rqalpha.api import *
# 暂时注释掉CryptoDataSource，使用内置数据源
# from rqalpha.data.crypto_data_source import CryptoDataSource


def init(context):
    """初始化函数"""
    # 检查数据源
    from rqalpha.environment import Environment
    env = Environment.get_instance()
    print(f"数据源类型: {type(env.data_source)}")
    print(f"数据源类名: {env.data_source.__class__.__name__}")
    print(f"数据源模块: {env.data_source.__class__.__module__}")

    # 选择要交易的加密货币
    context.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    print(f"\n选择的交易对: {context.symbols}")
    
    print("加密货币策略初始化完成")
    print(f"交易标的: {context.symbols}")
    print(f"初始资金: {context.portfolio.total_value}")


def before_trading(context):
    """交易前处理"""
    print(f"交易日期: {context.now}")
    print(f"账户总价值: {context.portfolio.total_value:.2f}")


def handle_bar(context, bar_dict):
    """处理K线数据"""
    print(f"\n=== {context.now} 交易信号 ===")
    
    # 获取历史数据进行分析
    for symbol in context.symbols:
        try:
            # 获取最近5天的数据（直接使用字符串）
            hist = history_bars(symbol, 5, '1d', ['close', 'volume'])
            if len(hist) > 0:
                current_price = hist['close'][-1]
                avg_price = hist['close'].mean()
                
                print(f"{symbol}: 当前价格={current_price:.2f}, 5日均价={avg_price:.2f}")
                
                # 简单的均线策略
                try:
                    # 获取加密货币账户
                    crypto_account = context.portfolio.accounts["CRYPTO"]
                    # 获取持仓（多头方向）
                    position = crypto_account.get_position(symbol, POSITION_DIRECTION.LONG)
                    
                    # 获取持仓数量（确保是数值）
                    position_quantity = float(position.quantity) if hasattr(position, 'quantity') else 0.0
                    
                    if current_price > avg_price and position_quantity == 0:
                        # 价格高于均线且无持仓，买入
                        # 计算买入数量（10万金额）
                        buy_amount = 100000 / current_price
                        print(f"  🚀 尝试买入 {symbol}: {current_price:.2f}, 数量: {buy_amount:.4f}")
                        order_shares(symbol, buy_amount)  # 买入指定数量
                        print(f"  ✅ 买入订单已提交 {symbol}")
                    elif current_price < avg_price and position_quantity > 0:
                        # 价格低于均线且有持仓，卖出
                        print(f"  💰 尝试卖出 {symbol}: {current_price:.2f}, 数量: {position_quantity:.4f}")
                        order_shares(symbol, -position_quantity)  # 卖出所有持仓
                        print(f"  ✅ 卖出订单已提交 {symbol}")
                except Exception as e:
                    print(f"  ❌ 交易 {symbol} 时出错: {e}")
                    import traceback
                    print(f"  错误详情: {traceback.format_exc()}")
                
                # 显示交易信号
                if current_price > avg_price:
                    print(f"  📈 {symbol} 看涨信号: 价格 {current_price:.2f} > 均线 {avg_price:.2f}")
                else:
                    print(f"  📉 {symbol} 看跌信号: 价格 {current_price:.2f} < 均线 {avg_price:.2f}")
        except Exception as e:
            print(f"处理 {symbol} 时出错: {e}")
    
    # 显示当前持仓
    print("\n当前持仓:")

    for symbol in context.symbols:
        try:
            # 获取加密货币账户
            crypto_account = context.portfolio.accounts["CRYPTO"]
            # 获取持仓（多头方向）
            position = crypto_account.get_position(symbol, POSITION_DIRECTION.LONG)
            position_quantity = float(position.quantity) if hasattr(position, 'quantity') else 0.0
            if position_quantity > 0:
                print(f"{symbol}: {position_quantity:.4f} 单位, 市值: {position.market_value:.2f}")
            else:
                print(f"{symbol}: 没有持仓")
        except Exception as e:
            import traceback
            print(f"获取 {symbol} 持仓信息时出错: {e}")
            print(f"错误详情: {traceback.format_exc()}")


def run_crypto_strategy():
    """运行加密货币策略"""
    # 直接使用字符串值
    CRYPTO_ACCOUNT_TYPE = "CRYPTO"
    
    config = {
        "base": {
            "start_date": "2020-01-01",
            "end_date": "2024-12-31",
            "frequency": "1d",
            "data_bundle_path": "./data_download/test_5year_crypto_bundle",
            "accounts": {
                CRYPTO_ACCOUNT_TYPE: 1000000  # 100万初始资金
            }
        },
        "extra": {
            "log_level": "info",
        },
        "mod": {
            "sys_accounts": {
                "enabled": True,
                "account_type": CRYPTO_ACCOUNT_TYPE
            },
            "sys_analyser": {
                "enabled": False  # 禁用分析器，避免CRYPTO账户类型错误
            },
            "sys_simulation": {
                "enabled": True,
                "matching_type": "current_bar"
            },
            "sys_transaction_cost": {
                "enabled": True,
                "crypto_commission_rate": 0.001,  # 加密货币手续费率 0.1%
                "crypto_min_commission": 0.0,     # 最小手续费 0
                "stock_commission_multiplier": 1,  # 股票手续费倍率
                "futures_commission_multiplier": 1,  # 期货手续费倍率
                "tax_multiplier": 1  # 印花税倍率
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
    print("开始运行工作版加密货币策略...")
    print("注意：这个版本展示了问题所在，实际需要正确的数据源配置")
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
