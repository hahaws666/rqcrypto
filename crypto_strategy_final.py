#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整的加密货币策略示例
展示如何使用爆改后的 RQAlpha 进行加密货币交易
"""

import os
import sys
from datetime import datetime, date

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rqalpha.data.crypto_data_source import CryptoDataSource
from rqalpha.const import INSTRUMENT_TYPE, DEFAULT_ACCOUNT_TYPE
import pandas as pd
import numpy as np

class CryptoStrategy:
    """加密货币策略类"""
    
    def __init__(self, data_path="./test_crypto_bundle"):
        """初始化策略"""
        self.data_source = CryptoDataSource(data_path)
        self.instruments = list(self.data_source.get_instruments())
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        self.positions = {}  # 持仓记录
        self.cash = 1000000  # 初始资金100万
        self.total_value = self.cash
        
        print(f"策略初始化完成")
        print(f"交易标的: {self.symbols}")
        print(f"初始资金: {self.cash:,.2f}")
        print(f"可用合约: {len(self.instruments)} 个")
    
    def get_instrument(self, symbol):
        """获取合约对象"""
        for inst in self.instruments:
            if inst.order_book_id == symbol:
                return inst
        return None
    
    def get_price_data(self, symbol, days=5):
        """获取价格数据"""
        instrument = self.get_instrument(symbol)
        if not instrument:
            return None
        
        try:
            bars = self.data_source.history_bars(
                instrument, days, '1d', 
                ['open', 'high', 'low', 'close', 'volume'], 
                datetime.now()
            )
            return bars
        except Exception as e:
            print(f"获取 {symbol} 数据失败: {e}")
            return None
    
    def calculate_indicators(self, symbol, days=20):
        """计算技术指标"""
        data = self.get_price_data(symbol, days)
        if data is None or len(data) < days:
            return None
        
        closes = [bar['close'] for bar in data]
        
        # 计算移动平均线
        ma5 = np.mean(closes[-5:])
        ma10 = np.mean(closes[-10:]) if len(closes) >= 10 else ma5
        ma20 = np.mean(closes[-20:]) if len(closes) >= 20 else ma10
        
        # 计算RSI
        if len(closes) >= 14:
            deltas = np.diff(closes)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains[-14:])
            avg_loss = np.mean(losses[-14:])
            if avg_loss != 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 100
        else:
            rsi = 50
        
        return {
            'current_price': closes[-1],
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'rsi': rsi,
            'volume': data[-1]['volume']
        }
    
    def generate_signals(self, symbol):
        """生成交易信号"""
        indicators = self.calculate_indicators(symbol)
        if not indicators:
            return 'HOLD'
        
        current_price = indicators['current_price']
        ma5 = indicators['ma5']
        ma10 = indicators['ma10']
        ma20 = indicators['ma20']
        rsi = indicators['rsi']
        
        # 多重条件判断
        signals = []
        
        # 均线信号
        if current_price > ma5 > ma10 > ma20:
            signals.append('BUY_MA')
        elif current_price < ma5 < ma10 < ma20:
            signals.append('SELL_MA')
        
        # RSI信号
        if rsi < 30:
            signals.append('BUY_RSI')
        elif rsi > 70:
            signals.append('SELL_RSI')
        
        # 综合判断
        if 'BUY_MA' in signals and 'BUY_RSI' in signals:
            return 'STRONG_BUY'
        elif 'BUY_MA' in signals or 'BUY_RSI' in signals:
            return 'BUY'
        elif 'SELL_MA' in signals and 'SELL_RSI' in signals:
            return 'STRONG_SELL'
        elif 'SELL_MA' in signals or 'SELL_RSI' in signals:
            return 'SELL'
        else:
            return 'HOLD'
    
    def execute_trade(self, symbol, signal, current_price):
        """执行交易"""
        position = self.positions.get(symbol, 0)
        target_allocation = 0.33  # 每个币种分配33%资金
        
        if signal in ['BUY', 'STRONG_BUY'] and position == 0:
            # 买入
            target_value = self.total_value * target_allocation
            quantity = target_value / current_price
            self.positions[symbol] = quantity
            self.cash -= target_value
            print(f"买入 {symbol}: {quantity:.4f} 单位 @ {current_price:.2f}")
            
        elif signal in ['SELL', 'STRONG_SELL'] and position > 0:
            # 卖出
            sell_value = position * current_price
            self.cash += sell_value
            print(f"卖出 {symbol}: {position:.4f} 单位 @ {current_price:.2f}")
            self.positions[symbol] = 0
    
    def update_portfolio_value(self):
        """更新投资组合价值"""
        total_value = self.cash
        for symbol, quantity in self.positions.items():
            if quantity > 0:
                data = self.get_price_data(symbol, 1)
                if data and len(data) > 0:
                    current_price = data[-1]['close']
                    total_value += quantity * current_price
        self.total_value = total_value
    
    def run_backtest(self, start_date, end_date):
        """运行回测"""
        print(f"\n开始回测: {start_date} 到 {end_date}")
        print("="*60)
        
        # 获取交易日历
        calendars = self.data_source.get_trading_calendars()
        crypto_calendar = calendars.get('CRYPTO')
        
        if crypto_calendar is None:
            print("无法获取交易日历")
            return
        
        # 过滤日期范围
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        trading_days = crypto_calendar[(crypto_calendar >= start_dt) & (crypto_calendar <= end_dt)]
        
        print(f"回测期间: {len(trading_days)} 个交易日")
        
        # 模拟每日交易
        for i, trading_day in enumerate(trading_days):
            print(f"\n第{i+1}天: {trading_day.strftime('%Y-%m-%d')}")
            
            # 更新投资组合价值
            self.update_portfolio_value()
            
            # 为每个币种生成交易信号
            for symbol in self.symbols:
                try:
                    indicators = self.calculate_indicators(symbol)
                    if indicators:
                        signal = self.generate_signals(symbol)
                        current_price = indicators['current_price']
                        
                        print(f"{symbol}: 价格={current_price:.2f}, "
                              f"MA5={indicators['ma5']:.2f}, "
                              f"RSI={indicators['rsi']:.1f}, "
                              f"信号={signal}")
                        
                        # 执行交易
                        self.execute_trade(symbol, signal, current_price)
                        
                except Exception as e:
                    print(f"处理 {symbol} 时出错: {e}")
            
            # 显示当前持仓
            print(f"现金: {self.cash:,.2f}")
            for symbol, quantity in self.positions.items():
                if quantity > 0:
                    data = self.get_price_data(symbol, 1)
                    if data and len(data) > 0:
                        current_price = data[-1]['close']
                        market_value = quantity * current_price
                        print(f"{symbol}: {quantity:.4f} 单位, "
                              f"市值: {market_value:,.2f}")
        
        # 最终结果
        self.update_portfolio_value()
        print("\n" + "="*60)
        print("回测完成!")
        print("="*60)
        print(f"初始资金: {1000000:,.2f}")
        print(f"最终价值: {self.total_value:,.2f}")
        print(f"总收益: {self.total_value - 1000000:,.2f}")
        print(f"总收益率: {(self.total_value - 1000000) / 1000000:.2%}")
        
        # 显示最终持仓
        print("\n最终持仓:")
        for symbol, quantity in self.positions.items():
            if quantity > 0:
                data = self.get_price_data(symbol, 1)
                if data and len(data) > 0:
                    current_price = data[-1]['close']
                    market_value = quantity * current_price
                    print(f"{symbol}: {quantity:.4f} 单位 @ {current_price:.2f}, "
                          f"市值: {market_value:,.2f}")

def main():
    """主函数"""
    print("加密货币策略回测系统")
    print("="*60)
    
    # 创建策略实例
    strategy = CryptoStrategy()
    
    # 运行回测
    strategy.run_backtest("2025-08-01", "2025-09-03")

if __name__ == "__main__":
    main()
