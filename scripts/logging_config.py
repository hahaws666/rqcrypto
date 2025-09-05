#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RQAlpha策略日志配置
在策略中导入此模块即可使用统一日志系统
"""

import os
import sys
import logging
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.setup_logging import setup_logging, get_logger, log_strategy_event, log_data_event, log_api_event

# 初始化日志系统
log_file = setup_logging(log_level=logging.INFO)

# 导出常用的日志函数
__all__ = [
    'get_logger',
    'log_strategy_event', 
    'log_data_event',
    'log_api_event',
    'log_file'
]

# 创建策略专用的日志器
strategy_logger = get_logger("strategy")
data_logger = get_logger("data")
api_logger = get_logger("api")

def log_trade_action(action, symbol, quantity=None, price=None, value=None):
    """
    记录交易动作
    
    Args:
        action: 交易动作 (buy, sell, hold)
        symbol: 交易标的
        quantity: 数量
        price: 价格
        value: 价值
    """
    if action == "buy":
        message = f"🟢 买入 {symbol}"
    elif action == "sell":
        message = f"🔴 卖出 {symbol}"
    else:
        message = f"⏸️ 持有 {symbol}"
    
    if quantity:
        message += f" 数量: {quantity}"
    if price:
        message += f" 价格: ${price:.2f}"
    if value:
        message += f" 价值: ${value:,.0f}"
    
    strategy_logger.info(message)

def log_portfolio_status(portfolio):
    """
    记录投资组合状态
    
    Args:
        portfolio: 投资组合对象
    """
    total_value = portfolio.total_value
    cash = portfolio.cash
    positions_count = len([p for p in portfolio.positions.values() if p.quantity > 0])
    
    strategy_logger.info(f"📊 投资组合状态 - 总价值: ${total_value:,.0f}, 现金: ${cash:,.0f}, 持仓数: {positions_count}")

def log_market_cap_selection(selected_symbols, market_cap_data):
    """
    记录市值选股结果
    
    Args:
        selected_symbols: 选中的币种列表
        market_cap_data: 市值数据
    """
    strategy_logger.info(f"🎯 市值选股完成 - 选中 {len(selected_symbols)} 个币种")
    
    for symbol in selected_symbols[:5]:  # 只显示前5个
        if symbol in market_cap_data:
            market_cap = market_cap_data[symbol]
            strategy_logger.info(f"  {symbol}: 市值 ${market_cap:,.0f}")
    
    if len(selected_symbols) > 5:
        strategy_logger.info(f"  ... 还有 {len(selected_symbols) - 5} 个币种")

def log_data_download(api_name, symbols_count, success=True):
    """
    记录数据下载
    
    Args:
        api_name: API名称
        symbols_count: 币种数量
        success: 是否成功
    """
    if success:
        data_logger.info(f"📥 {api_name} 数据下载成功 - 获取 {symbols_count} 个币种数据")
    else:
        data_logger.error(f"❌ {api_name} 数据下载失败")

def log_bundle_generation(bundle_path, symbols_count, success=True):
    """
    记录Bundle生成
    
    Args:
        bundle_path: Bundle路径
        symbols_count: 币种数量
        success: 是否成功
    """
    if success:
        data_logger.info(f"📦 Bundle生成成功 - 路径: {bundle_path}, 币种数: {symbols_count}")
    else:
        data_logger.error(f"❌ Bundle生成失败 - 路径: {bundle_path}")

def log_api_request(api_name, endpoint, status_code=None, response_time=None):
    """
    记录API请求
    
    Args:
        api_name: API名称
        endpoint: 端点
        status_code: 状态码
        response_time: 响应时间
    """
    message = f"🌐 {api_name} API请求 - 端点: {endpoint}"
    if status_code:
        message += f", 状态码: {status_code}"
    if response_time:
        message += f", 响应时间: {response_time:.2f}s"
    
    if status_code and status_code >= 400:
        api_logger.error(message)
    else:
        api_logger.info(message)

def log_error(error_type, message, exception=None):
    """
    记录错误
    
    Args:
        error_type: 错误类型
        message: 错误消息
        exception: 异常对象
    """
    error_logger = get_logger("error")
    error_logger.error(f"❌ {error_type}: {message}")
    
    if exception:
        error_logger.error(f"异常详情: {str(exception)}", exc_info=True)

def log_performance(operation, duration, details=None):
    """
    记录性能信息
    
    Args:
        operation: 操作名称
        duration: 耗时
        details: 详细信息
    """
    perf_logger = get_logger("performance")
    message = f"⏱️ {operation} 耗时: {duration:.2f}s"
    if details:
        message += f" - {details}"
    perf_logger.info(message)

# 在模块加载时记录
strategy_logger.info("🚀 日志系统初始化完成")
strategy_logger.info(f"📁 日志文件: {log_file}")
