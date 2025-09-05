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
    
    log_strategy_event("info", f"策略初始化完成 - 可交易币种: {len(context.available_symbols)}, 市值数据: {len(context.market_cap_data)}")


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


def get_smallest_market_cap_coins(context, current_date):
    """获取当前日期市值最小的币种"""
    # 获取当前日期的市值数据（直接使用日期匹配）
    current_data = context.market_cap_data[
        context.market_cap_data['date'].dt.date == current_date
    ].copy()
    
    if current_data.empty:
        log_strategy_event("warning", f"{current_date} 没有市值数据")
        return []
    
    # 创建币种符号映射（去掉USDT后缀）
    symbol_mapping = {}
    for usdt_symbol in context.available_symbols:
        if usdt_symbol.endswith('USDT'):
            base_symbol = usdt_symbol[:-4]  # 去掉USDT
            symbol_mapping[base_symbol] = usdt_symbol
    
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
    
    # 转换为交易符号格式
    symbols = []
    market_cap_data = {}
    for _, row in smallest_coins.iterrows():
        base_symbol = row['symbol']
        usdt_symbol = symbol_mapping.get(base_symbol)
        if usdt_symbol:
            symbols.append(usdt_symbol)
            market_cap_data[usdt_symbol] = row['market_cap_usd']
    
    log_strategy_event("info", f"{current_date} 选择最小市值币种: {len(symbols)} 个")
    if len(symbols) > 0:
        log_market_cap_selection(symbols, market_cap_data)
    
    return symbols


def rebalance_portfolio(context, target_symbols, bar_dict):
    """调仓函数"""
    # 获取当前持仓
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
            order_shares(symbol, -quantity)
            log_trade_action("sell", symbol, quantity=quantity)
    
    # 买入新的币种
    if target_symbols:
        total_value = context.portfolio.total_value
        value_per_stock = total_value / len(target_symbols)
        
        for symbol in to_buy:
            # 获取当前价格
            if symbol in bar_dict:
                current_price = bar_dict[symbol].close
                if current_price > 0:
                    shares_to_buy = int(value_per_stock / current_price)
                    if shares_to_buy > 0:
                        order_shares(symbol, shares_to_buy)
                        log_trade_action("buy", symbol, quantity=shares_to_buy, price=current_price, value=value_per_stock)


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
            'accounts': {
                'crypto': 1000000  # 100万初始资金
            }
        },
        'extra': {
            'log_level': 'info',
            'user_system_log_disabled': False,
            'user_system_log_level': 'info'
        },
        'mod': {
            'sys_progress': {
                'enabled': True,
                'show': True
            },
            'sys_analyser': {
                'enabled': False  # 禁用分析器模块，避免scipy依赖
            },
            'sys_risk': {
                'enabled': False  # 禁用风险模块，避免scipy依赖
            }
        }
    }
    
    # 运行策略
    from rqalpha import run_func
    run_func(init=init, handle_bar=handle_bar, config=config)
