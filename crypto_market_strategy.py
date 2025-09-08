# -*- coding: utf-8 -*-
"""
加密货币市值轮动策略
每天买入市值最小的30家加密货币
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# 添加rqalpha路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rqalpha.api import *
from rqalpha.api import subscribe, order_shares

# 导入日志系统
from scripts.logging_config import (
    get_logger, log_strategy_event, log_data_event, log_api_event,
    log_trade_action, log_portfolio_status, log_market_cap_selection,
    log_error, log_performance
)


def init(context):
    """初始化函数"""
    # 获取日志器
    logger = get_logger("strategy")
    
    # 策略参数
    context.stock_count = 30  # 持仓数量
    context.rebalance_period = 1  # 调仓周期（天）
    context.last_rebalance_date = None
    
    # 数据文件路径
    context.market_cap_file = "data_download/bundle/binance_coingecko_market_cap_365d.csv"
    context.bundle_dir = "data_download/test_5year_crypto_bundle"
    
    log_strategy_event("info", "开始初始化策略")
    
    # 加载市值数据
    context.market_cap_data = load_market_cap_data(context.market_cap_file)
    
    # 获取可交易的币种列表
    context.available_symbols = get_available_symbols(context.bundle_dir)
    
    # 订阅一些默认的币种以确保有数据
    default_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
    for symbol in default_symbols:
        if symbol in context.available_symbols:
            try:
                subscribe(symbol)
                log_strategy_event("info", f"初始化订阅币种: {symbol}")
            except Exception as e:
                log_strategy_event("warning", f"初始化订阅失败: {symbol}, 错误: {e}")
    


def load_market_cap_data(file_path):
    """加载市值数据"""
    try:
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['date'])
        log_data_event("process", f"成功加载市值数据: {len(df)} 条记录", file_path=file_path)
        return df
    except Exception as e:
        log_error("data_load", f"加载市值数据失败: {e}", exception=e)
        return pd.DataFrame()


def get_available_symbols(bundle_dir):
    """获取可交易的币种列表"""
    available_symbols = set()
    
    # 检查现货数据
    spot_file = os.path.join(bundle_dir, "crypto_spot.h5")
    if os.path.exists(spot_file):
        import h5py
        with h5py.File(spot_file, 'r') as f:
            spot_symbols = list(f.keys())
            available_symbols.update(spot_symbols)
            log_data_event("process", f"加载现货数据: {len(spot_symbols)} 个交易对", file=spot_file)
    
    # 检查期货数据
    futures_file = os.path.join(bundle_dir, "crypto_futures.h5")
    if os.path.exists(futures_file):
        import h5py
        with h5py.File(futures_file, 'r') as f:
            futures_symbols = list(f.keys())
            available_symbols.update(futures_symbols)
            log_data_event("process", f"加载期货数据: {len(futures_symbols)} 个交易对", file=futures_file)
    
    log_data_event("process", f"总可交易币种: {len(available_symbols)} 个")
    return list(available_symbols)


def validate_symbol_data_availability(symbol, context):
    """验证币种是否有可用的历史数据"""
    try:
        # 检查币种是否在数据源中
        if symbol not in context.available_symbols:
            log_strategy_event("debug", f"币种不在可用列表中: {symbol}")
            return False
        
        # 简化验证：只要币种在可用列表中就认为有数据
        # 实际的数据验证将在bar_dict中进行
        log_strategy_event("debug", f"币种验证通过: {symbol}")
        return True
        
    except Exception as e:
        log_strategy_event("debug", f"验证币种数据失败 {symbol}: {e}")
        return False


def get_smallest_market_cap_coins(context, current_date):
    """获取当前日期市值最小的币种"""
    # 检查市值数据是否为空
    if context.market_cap_data.empty:
        log_strategy_event("warning", "市值数据为空，使用默认币种")
        # 返回一些默认的币种
        default_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        available_defaults = [s for s in default_symbols if s in context.available_symbols][:context.stock_count]
        
        # 订阅默认币种
        for symbol in available_defaults:
            try:
                # 使用subscribe函数订阅股票
                subscribe(symbol)
                log_strategy_event("info", f"订阅默认币种: {symbol}")
            except Exception as e:
                log_strategy_event("warning", f"订阅默认币种失败: {symbol}, 错误: {e}")
        
        return available_defaults
    
    # 获取当前日期的市值数据（直接使用日期匹配）
    current_data = context.market_cap_data[
        context.market_cap_data['date'].dt.date == current_date
    ].copy()
    
    if current_data.empty:
        log_strategy_event("warning", f"{current_date} 没有市值数据，使用所有可用数据")
        # 如果没有当前日期的数据，使用所有数据
        current_data = context.market_cap_data
    
    # 创建币种符号映射（添加USDT后缀）
    symbol_mapping = {}
    for usdt_symbol in context.available_symbols:
        if usdt_symbol.endswith('USDT'):
            base_symbol = usdt_symbol[:-4]  # 去掉USDT
            symbol_mapping[base_symbol] = usdt_symbol
        else:
            # 如果币种名称没有USDT后缀，直接使用
            symbol_mapping[usdt_symbol] = usdt_symbol
    
    # 过滤出可交易的币种
    available_data = current_data[
        current_data['symbol'].isin(symbol_mapping.keys())
    ].copy()
    
    if available_data.empty:
        log_strategy_event("warning", f"{current_date} 没有可交易的币种数据")
        return []
    
    # 按市值排序，选择最小的30个
    available_data = available_data.sort_values('market_cap_usd', ascending=True)
    smallest_coins = available_data.head(context.stock_count)
    
    # 转换为交易符号格式并验证数据可用性
    symbols = []
    market_cap_data = {}
    validated_count = 0
    
    for _, row in smallest_coins.iterrows():
        base_symbol = row['symbol']
        usdt_symbol = symbol_mapping.get(base_symbol)
        
        if usdt_symbol:
            # 验证币种是否有可用的历史数据
            if validate_symbol_data_availability(usdt_symbol, context):
                # 订阅币种
                try:
                    subscribe(usdt_symbol)
                    symbols.append(usdt_symbol)
                    market_cap_data[usdt_symbol] = row['market_cap_usd']
                    validated_count += 1
                    log_strategy_event("debug", f"✅ 验证通过并订阅: {base_symbol} -> {usdt_symbol}")
                except Exception as e:
                    log_strategy_event("warning", f"订阅币种失败: {usdt_symbol}, 错误: {e}")
            else:
                log_strategy_event("debug", f"❌ 数据不可用: {base_symbol} -> {usdt_symbol}")
            
            # 如果已经找到足够的币种，就停止
            if len(symbols) >= context.stock_count:
                break
    
    log_strategy_event("info", f"{current_date} 选择最小市值币种: {len(symbols)} 个 (验证通过: {validated_count})")
    
    if len(symbols) > 0:
        log_market_cap_selection(symbols, market_cap_data)
    else:
        log_strategy_event("warning", f"没有找到可用的币种数据，尝试使用默认币种")
        # 使用默认币种作为备选
        default_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        for symbol in default_symbols:
            if symbol in context.available_symbols and validate_symbol_data_availability(symbol, context):
                try:
                    subscribe(symbol)
                    symbols.append(symbol)
                    log_strategy_event("info", f"使用默认币种并订阅: {symbol}")
                    if len(symbols) >= context.stock_count:
                        break
                except Exception as e:
                    log_strategy_event("warning", f"订阅默认币种失败: {symbol}, 错误: {e}")
    
    return symbols


def rebalance_portfolio(context, target_symbols, bar_dict):
    """调仓函数"""
    # 获取当前持
    current_positions = list(context.portfolio.positions.keys())
    
    # 计算需要卖出的币种
    to_sell = [symbol for symbol in current_positions if symbol not in target_symbols]
    
    # 计算需要买入的币种
    to_buy = [symbol for symbol in target_symbols if symbol not in current_positions]
    
    log_strategy_event("info", f"开始调仓 - 卖出: {len(to_sell)} 个, 买入: {len(to_buy)} 个")
    
    # 卖出不需要的币种
    for symbol in to_sell:
        if context.portfolio.positions[symbol].quantity > 0:
            quantity = context.portfolio.positions[symbol].quantity
            order_result = order_shares(symbol, -quantity)
            log_trade_action("sell", symbol, quantity=quantity, order_result=order_result)
    
    # 买入新的币种
    if target_symbols:
        total_value = context.portfolio.total_value
        value_per_stock = total_value / len(target_symbols)
        
        for symbol in to_buy:
            # 使用 history_bars 获取当前价格
            try:
                hist = history_bars(symbol, 1, '1d', ['close'])
                if len(hist) > 0:
                    current_price = hist['close'][-1]
                    if current_price > 0 and not np.isnan(current_price):
                        shares_to_buy = int(value_per_stock / current_price)
                        if shares_to_buy > 0:
                            order_result = order_shares(symbol, shares_to_buy)
                            log_trade_action("buy", symbol, quantity=shares_to_buy, price=current_price, value=value_per_stock, order_result=order_result)
                            
                            # 检查订单状态
                            if order_result:
                                log_strategy_event("info", f"订单提交成功: {symbol}, 数量: {shares_to_buy}, 订单ID: {order_result}")
                            else:
                                log_strategy_event("error", f"订单提交失败: {symbol}, 数量: {shares_to_buy}")
                        else:
                            log_strategy_event("warning", f"跳过买入 {symbol}: 计算数量为0 (价格: {current_price}, 分配价值: {value_per_stock})")
                    else:
                        log_strategy_event("warning", f"跳过买入 {symbol}: 价格无效 ({current_price})")
                else:
                    log_strategy_event("warning", f"跳过买入 {symbol}: 无法获取历史数据")
            except Exception as e:
                log_strategy_event("error", f"获取 {symbol} 价格数据失败: {e}")


def handle_bar(context, bar_dict):
    """主策略逻辑"""
    current_date = context.now.date()
    
    # 检查是否需要调仓
    if (context.last_rebalance_date is None or 
        (current_date - context.last_rebalance_date).days >= context.rebalance_period):
        
        log_strategy_event("info", f"调仓日期: {current_date}")
        
        # 获取市值最小的币种
        target_symbols = get_smallest_market_cap_coins(context, current_date)
        
        if target_symbols:
            # 执行调仓
            rebalance_portfolio(context, target_symbols, bar_dict)
            context.last_rebalance_date = current_date
            
            # 记录调仓信息
            log_strategy_event("info", f"调仓完成，持仓币种: {len(target_symbols)} 个")
            log_portfolio_status(context.portfolio)
        else:
            log_strategy_event("warning", "无法获取目标币种，跳过调仓")


def before_trading(context):
    """交易前处理"""
    pass


def after_trading(context):
    """交易后处理"""
    pass


def after_trading_end(context):
    """交易结束后处理"""
    # 记录每日收益
    total_value = context.portfolio.total_value
    log_strategy_event("info", f"总资产: ${total_value:,.2f}")
    
    # 记录持仓信息
    positions = context.portfolio.positions
    active_positions = {k: v for k, v in positions.items() if v.quantity > 0}
    if active_positions:
        log_strategy_event("info", f"当前持仓: {len(active_positions)} 个币种")
        for symbol, position in list(active_positions.items())[:5]:  # 显示前5个
            log_strategy_event("info", f"{symbol}: {position.quantity:.4f} (${position.value:.2f})")


if __name__ == "__main__":
    # 策略配置
    config = {
        'base': {
            'start_date': '2024-09-10',
            'end_date': '2025-08-30',
            'frequency': '1d',
            'benchmark': 'BTCUSDT',
            'data_bundle_path': './data_download/test_5year_crypto_bundle',
            'accounts': {
                'CRYPTO': 1000000  # 100万初始资金
            }
        },
        'extra': {
            'log_level': 'info',
            'user_system_log_disabled': False,
            'user_system_log_level': 'info'
        },
        'mod': {
            'sys_accounts': {
                'enabled': True,
                'account_type': 'CRYPTO'
            },
            'sys_simulation': {
                'enabled': True,
                'matching_type': 'current_bar'
            },
            'sys_transaction_cost': {
                'enabled': True,
                'crypto_commission_rate': 0.001,  # 加密货币手续费率 0.1%
                'crypto_min_commission': 0.0,     # 最小手续费 0
            },
            'sys_progress': {
                'enabled': False,
                'show': False
            },
            'sys_analyser': {
                'enabled': True,  # 启用分析器模块生成图表
                'output_file': 'crypto_strategy_report.html',
                'plot': True
            },
            'sys_risk': {
                'enabled': False  # 禁用风险模块，避免scipy依赖
            }
        }
    }

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # 运行策略
    from rqalpha import run_func
    run_func(init=init, handle_bar=handle_bar, config=config)
