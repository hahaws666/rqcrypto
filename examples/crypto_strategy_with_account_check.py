#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增强版加密货币策略示例 - 带详细账户检测
在每次交易时自动检测账户状态，包括资金、持仓、订单等
"""

import os
import sys
from datetime import datetime, date

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rqalpha import run_func
from rqalpha.const import INSTRUMENT_TYPE, DEFAULT_ACCOUNT_TYPE, POSITION_DIRECTION, ORDER_STATUS
from rqalpha.api import *


def check_account_status(context, symbol=None, action=None):
    """检查账户状态"""
    print(f"\n{'='*60}")
    print(f"🔍 账户状态检测 - {context.now}")
    if symbol and action:
        print(f"📊 交易标的: {symbol} | 操作: {action}")
    print(f"{'='*60}")
    
    try:
        # 获取加密货币账户
        crypto_account = context.portfolio.accounts[DEFAULT_ACCOUNT_TYPE.CRYPTO]
        
        # 1. 账户基本信息
        print(f"💰 账户资金:")
        print(f"  - 总价值: {crypto_account.total_value:.2f} USDT")
        print(f"  - 可用资金: {crypto_account.cash:.2f} USDT")
        print(f"  - 持仓市值: {crypto_account.market_value:.2f} USDT")
        print(f"  - 冻结资金: {crypto_account.frozen_cash:.2f} USDT")
        
        # 2. 持仓详情
        print(f"\n📈 持仓详情:")
        total_position_value = 0
        for sym in context.symbols:
            try:
                position = crypto_account.get_position(sym, POSITION_DIRECTION.LONG)
                position_quantity = float(position.quantity) if hasattr(position, 'quantity') else 0.0
                if position_quantity > 0:
                    position_value = position.market_value
                    total_position_value += position_value
                    print(f"  - {sym}: {position_quantity:.6f} 单位, 市值: {position_value:.2f} USDT")
                else:
                    print(f"  - {sym}: 无持仓")
            except Exception as e:
                print(f"  - {sym}: 获取持仓失败 - {e}")
        
        # 3. 订单状态
        print(f"\n📋 订单状态:")
        try:
            # 获取所有订单
            orders = get_orders()
            if orders:
                active_orders = [order for order in orders if order.status in [ORDER_STATUS.PENDING_NEW, ORDER_STATUS.ACTIVE]]
                if active_orders:
                    for order in active_orders:
                        print(f"  - {order.order_book_id}: {order.side} {order.quantity:.6f} @ {order.price:.2f} [{order.status}]")
                else:
                    print(f"  - 无活跃订单")
            else:
                print(f"  - 无订单记录")
        except Exception as e:
            print(f"  - 获取订单失败: {e}")
        
        # 4. 交易统计
        print(f"\n📊 交易统计:")
        try:
            trades = get_trades()
            if trades:
                total_trades = len(trades)
                total_volume = sum(trade.quantity for trade in trades)
                total_turnover = sum(trade.price * trade.quantity for trade in trades)
                print(f"  - 总交易次数: {total_trades}")
                print(f"  - 总交易量: {total_volume:.6f}")
                print(f"  - 总成交额: {total_turnover:.2f} USDT")
            else:
                print(f"  - 无交易记录")
        except Exception as e:
            print(f"  - 获取交易统计失败: {e}")
        
        # 5. 风险指标
        print(f"\n⚠️ 风险指标:")
        try:
            # 计算仓位集中度
            if total_position_value > 0:
                for sym in context.symbols:
                    try:
                        position = crypto_account.get_position(sym, POSITION_DIRECTION.LONG)
                        position_quantity = float(position.quantity) if hasattr(position, 'quantity') else 0.0
                        if position_quantity > 0:
                            position_ratio = (position.market_value / total_position_value) * 100
                            print(f"  - {sym} 仓位占比: {position_ratio:.1f}%")
                    except:
                        pass
            
            # 计算资金利用率
            cash_ratio = (crypto_account.market_value / crypto_account.total_value) * 100 if crypto_account.total_value > 0 else 0
            print(f"  - 资金利用率: {cash_ratio:.1f}%")
            
            # 计算可用资金比例
            available_ratio = (crypto_account.cash / crypto_account.total_value) * 100 if crypto_account.total_value > 0 else 0
            print(f"  - 可用资金比例: {available_ratio:.1f}%")
            
        except Exception as e:
            print(f"  - 计算风险指标失败: {e}")
        
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"❌ 账户检测失败: {e}")
        import traceback
        print(f"错误详情: {traceback.format_exc()}")


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
    
    print("加密货币策略初始化完成")
    print(f"交易标的: {context.symbols}")
    print(f"初始资金: {context.portfolio.total_value}")
    
    # 初始账户检测
    check_account_status(context, "初始化", "开始")


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
                    crypto_account = context.portfolio.accounts[DEFAULT_ACCOUNT_TYPE.CRYPTO]
                    # 获取持仓（多头方向）
                    position = crypto_account.get_position(symbol, POSITION_DIRECTION.LONG)
                    
                    # 获取持仓数量（确保是数值）
                    position_quantity = float(position.quantity) if hasattr(position, 'quantity') else 0.0
                    
                    if current_price > avg_price and position_quantity == 0:
                        # 价格高于均线且无持仓，买入
                        # 计算买入数量（10万金额）
                        buy_amount = 100000 / current_price
                        print(f"  🚀 尝试买入 {symbol}: {current_price:.2f}, 数量: {buy_amount:.4f}")
                        
                        # 交易前账户检测
                        check_account_status(context, symbol, "买入前")
                        
                        order_shares(symbol, buy_amount)  # 买入指定数量
                        print(f"  ✅ 买入订单已提交 {symbol}")
                        
                        # 交易后账户检测
                        check_account_status(context, symbol, "买入后")
                        
                    elif current_price < avg_price and position_quantity > 0:
                        # 价格低于均线且有持仓，卖出
                        print(f"  💰 尝试卖出 {symbol}: {current_price:.2f}, 数量: {position_quantity:.4f}")
                        
                        # 交易前账户检测
                        check_account_status(context, symbol, "卖出前")
                        
                        order_shares(symbol, -position_quantity)  # 卖出所有持仓
                        print(f"  ✅ 卖出订单已提交 {symbol}")
                        
                        # 交易后账户检测
                        check_account_status(context, symbol, "卖出后")
                        
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
            crypto_account = context.portfolio.accounts[DEFAULT_ACCOUNT_TYPE.CRYPTO]
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
    config = {
        "base": {
            "start_date": "2025-08-05",
            "end_date": "2025-09-03",
            "frequency": "1d",
            "data_bundle_path": "./test_crypto_bundle",
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
    print("开始运行增强版加密货币策略（带账户检测）...")
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
