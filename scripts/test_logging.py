#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试日志系统
"""

import os
import sys
import time

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.logging_config import (
    setup_logging, get_logger, log_strategy_event, log_data_event, log_api_event,
    log_trade_action, log_portfolio_status, log_market_cap_selection,
    log_error, log_performance
)

def test_logging_system():
    """测试日志系统"""
    print("🚀 开始测试日志系统...")
    
    # 初始化日志系统
    log_file = setup_logging()
    print(f"📁 日志文件: {log_file}")
    
    # 测试基本日志
    logger = get_logger("test")
    logger.info("这是一条信息日志")
    logger.warning("这是一条警告日志")
    logger.error("这是一条错误日志")
    
    # 测试策略事件日志
    log_strategy_event("info", "策略初始化完成")
    log_strategy_event("trade", "买入BTCUSDT", symbol="BTCUSDT", quantity=100)
    log_strategy_event("warning", "市场波动较大")
    log_strategy_event("error", "数据获取失败")
    
    # 测试数据事件日志
    log_data_event("download", "下载币安数据", symbols=50)
    log_data_event("process", "处理H5文件", file="crypto_spot.h5")
    log_data_event("error", "文件读取失败", file="missing.h5")
    
    # 测试API事件日志
    log_api_event("request", "请求CoinGecko API", endpoint="/coins/markets")
    log_api_event("response", "API响应成功", status_code=200, response_time=1.5)
    log_api_event("error", "API请求失败", status_code=429)
    
    # 测试交易动作日志
    log_trade_action("buy", "BTCUSDT", quantity=100, price=50000, value=5000000)
    log_trade_action("sell", "ETHUSDT", quantity=50, price=3000, value=150000)
    log_trade_action("hold", "BNBUSDT")
    
    # 测试投资组合状态日志
    class MockPortfolio:
        def __init__(self):
            self.total_value = 1000000
            self.cash = 100000
            self.positions = {
                "BTCUSDT": MockPosition(100, 50000),
                "ETHUSDT": MockPosition(50, 3000)
            }
    
    class MockPosition:
        def __init__(self, quantity, value):
            self.quantity = quantity
            self.value = value
    
    portfolio = MockPortfolio()
    log_portfolio_status(portfolio)
    
    # 测试市值选股日志
    selected_symbols = ["ONEUSDT", "WANUSDT", "FLMUSDT", "COSUSDT", "DASHUSDT"]
    market_cap_data = {
        "ONEUSDT": 1340000,
        "WANUSDT": 2500000,
        "FLMUSDT": 5000000,
        "COSUSDT": 8000000,
        "DASHUSDT": 12000000
    }
    log_market_cap_selection(selected_symbols, market_cap_data)
    
    # 测试错误日志
    try:
        raise ValueError("这是一个测试错误")
    except Exception as e:
        log_error("test_error", "测试错误处理", exception=e)
    
    # 测试性能日志
    log_performance("数据下载", 2.5, "下载了100个币种的数据")
    log_performance("策略回测", 10.2, "回测了30天的数据")
    
    print("✅ 日志系统测试完成！")
    print(f"📄 请查看日志文件: {log_file}")

if __name__ == "__main__":
    test_logging_system()
