# -*- coding: utf-8 -*-
"""
加密货币交易成本计算器
"""

from rqalpha.interface import AbstractTransactionCostDecider
from rqalpha.environment import Environment
from rqalpha.const import SIDE
from rqalpha.model.trade import Trade
from rqalpha.model.order import Order


class CryptoTransactionCostDecider(AbstractTransactionCostDecider):
    """
    加密货币交易成本计算器
    加密货币通常只有手续费，没有印花税
    """
    
    def __init__(self, commission_rate=0.001, min_commission=0.0):
        """
        初始化加密货币交易成本计算器
        
        Args:
            commission_rate: 手续费率，默认0.1%
            min_commission: 最小手续费，默认0
        """
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.env = Environment.get_instance()

    def get_trade_tax(self, trade: Trade) -> float:
        """
        计算指定交易应付的印花税
        加密货币没有印花税，返回0
        """
        return 0.0

    def get_trade_commission(self, trade: Trade) -> float:
        """
        计算指定交易应付的佣金
        """
        commission = trade.last_price * trade.last_quantity * self.commission_rate
        return max(commission, self.min_commission)

    def get_order_transaction_cost(self, order: Order) -> float:
        """
        计算指定订单应付的交易成本（税 + 费）
        """
        # 获取订单价格和数量
        if hasattr(order, 'frozen_price') and order.frozen_price is not None:
            price = order.frozen_price
        else:
            # 如果没有冻结价格，使用当前价格
            try:
                current_data = self.env.get_current_data()
                price = current_data[order.order_book_id].last_price
            except:
                price = 1.0  # 默认价格
        
        quantity = abs(order.quantity)
        
        # 计算手续费
        commission = price * quantity * self.commission_rate
        commission = max(commission, self.min_commission)
        
        # 加密货币没有印花税
        tax = 0.0
        
        return commission + tax
    
    def get_transaction_cost_with_value(self, value: float, side: SIDE) -> float:
        """
        计算指定价格交易应付的交易成本（税 + 费）
        """
        # 计算手续费
        commission = abs(value) * self.commission_rate
        commission = max(commission, self.min_commission)
        
        # 加密货币没有印花税
        tax = 0.0
        
        return commission + tax
