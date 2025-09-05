#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志系统设置
自动将所有日志写入到 logs/ 目录下的文件中
"""

import os
import sys
import logging
from datetime import datetime
import logging.handlers

def setup_logging(log_level=logging.INFO, log_dir="logs"):
    """
    设置统一的日志系统
    
    Args:
        log_level: 日志级别，默认INFO
        log_dir: 日志目录，默认logs
    """
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)
    
    # 生成日志文件名（按日期）
    today = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(log_dir, f"rqalpha_crypto_{today}.log")
    
    # 创建根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建文件处理器（按大小轮转）
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到根日志器
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # 设置第三方库的日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('h5py').setLevel(logging.WARNING)
    
    print(f"✅ 日志系统已设置完成")
    print(f"📁 日志文件: {log_file}")
    print(f"📊 日志级别: {logging.getLevelName(log_level)}")
    
    return log_file

def get_logger(name):
    """
    获取指定名称的日志器
    
    Args:
        name: 日志器名称
        
    Returns:
        Logger对象
    """
    return logging.getLogger(name)

def log_function_call(func):
    """
    装饰器：自动记录函数调用
    """
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.info(f"🔧 调用函数: {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"✅ 函数 {func.__name__} 执行成功")
            return result
        except Exception as e:
            logger.error(f"❌ 函数 {func.__name__} 执行失败: {str(e)}")
            raise
    return wrapper

def log_strategy_event(event_type, message, **kwargs):
    """
    记录策略事件
    
    Args:
        event_type: 事件类型 (info, warning, error, trade)
        message: 事件消息
        **kwargs: 额外参数
    """
    logger = get_logger("strategy")
    
    # 根据事件类型选择日志级别
    if event_type == "trade":
        logger.info(f"💰 {message}")
    elif event_type == "warning":
        logger.warning(f"⚠️ {message}")
    elif event_type == "error":
        logger.error(f"❌ {message}")
    else:
        logger.info(f"ℹ️ {message}")
    
    # 记录额外参数
    if kwargs:
        for key, value in kwargs.items():
            logger.debug(f"  {key}: {value}")

def log_data_event(event_type, message, **kwargs):
    """
    记录数据事件
    
    Args:
        event_type: 事件类型 (download, process, error)
        message: 事件消息
        **kwargs: 额外参数
    """
    logger = get_logger("data")
    
    if event_type == "download":
        logger.info(f"📥 {message}")
    elif event_type == "process":
        logger.info(f"🔄 {message}")
    elif event_type == "error":
        logger.error(f"❌ {message}")
    else:
        logger.info(f"ℹ️ {message}")
    
    if kwargs:
        for key, value in kwargs.items():
            logger.debug(f"  {key}: {value}")

def log_api_event(event_type, message, **kwargs):
    """
    记录API事件
    
    Args:
        event_type: 事件类型 (request, response, error)
        message: 事件消息
        **kwargs: 额外参数
    """
    logger = get_logger("api")
    
    if event_type == "request":
        logger.info(f"🌐 {message}")
    elif event_type == "response":
        logger.info(f"📡 {message}")
    elif event_type == "error":
        logger.error(f"❌ {message}")
    else:
        logger.info(f"ℹ️ {message}")
    
    if kwargs:
        for key, value in kwargs.items():
            logger.debug(f"  {key}: {value}")

if __name__ == "__main__":
    # 测试日志系统
    setup_logging()
    
    logger = get_logger("test")
    logger.info("测试日志系统")
    logger.warning("这是一个警告")
    logger.error("这是一个错误")
    
    log_strategy_event("trade", "买入BTCUSDT", symbol="BTCUSDT", quantity=100)
    log_data_event("download", "下载币安数据", symbols=50)
    log_api_event("request", "请求CoinGecko API", endpoint="/coins/markets")
