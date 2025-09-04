# -*- coding: utf-8 -*-
"""
加密货币交易 API
支持加密货币的买卖交易功能
"""

import datetime
from decimal import Decimal, getcontext
from itertools import chain
from typing import Dict, List, Optional, Union, Tuple, Callable
import math
from collections import defaultdict

import numpy as np
import pandas as pd
from rqalpha.api import export_as_api
from rqalpha.apis.api_abstract import (order, order_percent, order_shares,
                                       order_target_percent,
                                       order_target_value, order_to,
                                       order_value,
                                       common_rules, TUPLE_PRICE_OR_STYLE_TYPE, PRICE_OR_STYLE_TYPE)
from rqalpha.utils.functools import instype_singledispatch
from rqalpha.apis.api_base import (assure_instrument, assure_order_book_id,
                                   cal_style, calc_open_close_style)
from rqalpha.const import (DEFAULT_ACCOUNT_TYPE, EXECUTION_PHASE,
                           INSTRUMENT_TYPE, ORDER_TYPE, POSITION_DIRECTION,
                           POSITION_EFFECT, SIDE)
from rqalpha.core.execution_context import ExecutionContext
from rqalpha.core.events import Event, EVENT
from rqalpha.environment import Environment
from rqalpha.model.instrument import Instrument
from rqalpha.model.order import LimitOrder, MarketOrder, Order, OrderStyle, ALGO_ORDER_STYLES
from rqalpha.utils.arg_checker import apply_rules, verify_that
from rqalpha.utils.datetime_func import to_date
from rqalpha.utils.exception import RQInvalidArgument
from rqalpha.utils.i18n import gettext as _
from rqalpha.utils.logger import user_log
from rqalpha.utils.typing import DateLike


def _get_crypto_account():
    """获取加密货币账户"""
    env = Environment.get_instance()
    return env.portfolio.accounts[DEFAULT_ACCOUNT_TYPE.CRYPTO]


def _get_crypto_position(order_book_id, direction=POSITION_DIRECTION.LONG):
    """获取加密货币持仓"""
    account = _get_crypto_account()
    return account.get_position(order_book_id, direction)


@export_as_api
@ExecutionContext.enforce_phase(EXECUTION_PHASE.ON_INIT,
                                EXECUTION_PHASE.BEFORE_TRADING,
                                EXECUTION_PHASE.ON_BAR,
                                EXECUTION_PHASE.AFTER_TRADING,
                                EXECUTION_PHASE.SCHEDULED)
@apply_rules(*common_rules)
def order_shares(id_or_ins, amount, price_or_style=None, price=None, style=None):
    # type: (Union[str, Instrument], int, PRICE_OR_STYLE_TYPE, Optional[float], Optional[OrderStyle]) -> Optional[Order]
    """
    指定数量的买/卖单，适用于加密货币交易
    
    Args:
        id_or_ins: 合约ID或合约对象
        amount: 交易数量，正数代表买入，负数代表卖出
        price_or_style: 价格或订单类型
        price: 价格（如果price_or_style是OrderStyle）
        style: 订单类型（如果price_or_style是价格）
    
    Returns:
        Order: 订单对象
    """
    order_book_id = assure_order_book_id(id_or_ins)
    instrument = assure_instrument(order_book_id)
    
    # 检查是否为加密货币合约
    if instrument.type not in [INSTRUMENT_TYPE.CRYPTO_SPOT, INSTRUMENT_TYPE.CRYPTO_FUTURE]:
        raise RQInvalidArgument(_("order_shares only support crypto instruments"))
    
    # 检查数量
    if amount == 0:
        return None
    
    # 确定交易方向和数量
    if amount > 0:
        side = SIDE.BUY
        quantity = amount
    else:
        side = SIDE.SELL
        quantity = -amount
    
    # 处理价格和订单类型
    if price_or_style is None:
        price = None
        order_style = MarketOrder()
    elif isinstance(price_or_style, OrderStyle):
        price = None
        order_style = price_or_style
    else:
        price = price_or_style
        order_style = LimitOrder(price)
    
    # 创建订单
    order_obj = Order()
    order_obj._order_book_id = order_book_id
    order_obj._quantity = quantity
    order_obj._side = side
    order_obj._style = order_style
    order_obj._position_effect = POSITION_EFFECT.OPEN
    
    # 提交订单
    return order_obj


@export_as_api
@ExecutionContext.enforce_phase(EXECUTION_PHASE.ON_INIT,
                                EXECUTION_PHASE.BEFORE_TRADING,
                                EXECUTION_PHASE.ON_BAR,
                                EXECUTION_PHASE.AFTER_TRADING,
                                EXECUTION_PHASE.SCHEDULED)
@apply_rules(*common_rules)
def order_value(id_or_ins, cash_amount, price_or_style=None, price=None, style=None):
    # type: (Union[str, Instrument], float, PRICE_OR_STYLE_TYPE, Optional[float], Optional[OrderStyle]) -> Optional[Order]
    """
    使用指定金额买入/卖出，适用于加密货币交易
    
    Args:
        id_or_ins: 合约ID或合约对象
        cash_amount: 交易金额，正数代表买入，负数代表卖出
        price_or_style: 价格或订单类型
        price: 价格（如果price_or_style是OrderStyle）
        style: 订单类型（如果price_or_style是价格）
    
    Returns:
        Order: 订单对象
    """
    order_book_id = assure_order_book_id(id_or_ins)
    instrument = assure_instrument(order_book_id)
    
    # 检查是否为加密货币合约
    if instrument.type not in [INSTRUMENT_TYPE.CRYPTO_SPOT, INSTRUMENT_TYPE.CRYPTO_FUTURE]:
        raise RQInvalidArgument(_("order_value only support crypto instruments"))
    
    # 检查金额
    if cash_amount == 0:
        return None
    
    # 获取当前价格
    if price_or_style is None or isinstance(price_or_style, OrderStyle):
        # 市价单，需要获取当前价格
        from rqalpha.api import get_current_data
        current_data = get_current_data()
        if order_book_id not in current_data:
            raise RQInvalidArgument(_("Cannot get current price for {}").format(order_book_id))
        current_price = current_data[order_book_id].last_price
    else:
        current_price = price_or_style
    
    # 计算交易数量
    if cash_amount > 0:
        side = SIDE.BUY
        quantity = cash_amount / current_price
    else:
        side = SIDE.SELL
        quantity = -cash_amount / current_price
    
    # 处理价格和订单类型
    if price_or_style is None:
        price = None
        order_style = MarketOrder()
    elif isinstance(price_or_style, OrderStyle):
        price = None
        order_style = price_or_style
    else:
        price = price_or_style
        order_style = LimitOrder(price)
    
    # 创建订单
    order_obj = Order()
    order_obj._order_book_id = order_book_id
    order_obj._quantity = quantity
    order_obj._side = side
    order_obj._style = order_style
    order_obj._position_effect = POSITION_EFFECT.OPEN
    
    # 提交订单
    return order_obj


@export_as_api
@ExecutionContext.enforce_phase(EXECUTION_PHASE.ON_INIT,
                                EXECUTION_PHASE.BEFORE_TRADING,
                                EXECUTION_PHASE.ON_BAR,
                                EXECUTION_PHASE.AFTER_TRADING,
                                EXECUTION_PHASE.SCHEDULED)
@apply_rules(*common_rules)
def order_target_value(id_or_ins, cash_amount, price_or_style=None, price=None, style=None):
    # type: (Union[str, Instrument], float, TUPLE_PRICE_OR_STYLE_TYPE, Optional[float], Optional[OrderStyle]) -> Optional[Order]
    """
    调整持仓到目标金额，适用于加密货币交易
    
    Args:
        id_or_ins: 合约ID或合约对象
        cash_amount: 目标金额
        price_or_style: 价格或订单类型
        price: 价格（如果price_or_style是OrderStyle）
        style: 订单类型（如果price_or_style是价格）
    
    Returns:
        Order: 订单对象
    """
    order_book_id = assure_order_book_id(id_or_ins)
    instrument = assure_instrument(order_book_id)
    
    # 检查是否为加密货币合约
    if instrument.type not in [INSTRUMENT_TYPE.CRYPTO_SPOT, INSTRUMENT_TYPE.CRYPTO_FUTURE]:
        raise RQInvalidArgument(_("order_target_value only support crypto instruments"))
    
    # 获取当前持仓
    position = _get_crypto_position(order_book_id)
    current_value = position.market_value
    
    # 计算需要调整的金额
    target_value = cash_amount
    delta_value = target_value - current_value
    
    if abs(delta_value) < 1e-6:  # 几乎相等，不需要交易
        return None
    
    # 使用order_value进行交易
    return order_value(order_book_id, delta_value, price_or_style, price, style)


@export_as_api
@ExecutionContext.enforce_phase(EXECUTION_PHASE.ON_INIT,
                                EXECUTION_PHASE.BEFORE_TRADING,
                                EXECUTION_PHASE.ON_BAR,
                                EXECUTION_PHASE.AFTER_TRADING,
                                EXECUTION_PHASE.SCHEDULED)
@apply_rules(*common_rules)
def order_percent(id_or_ins, percent, price_or_style=None, price=None, style=None):
    # type: (Union[str, Instrument], float, PRICE_OR_STYLE_TYPE, Optional[float], Optional[OrderStyle]) -> Optional[Order]
    """
    使用投资组合百分比进行交易，适用于加密货币交易
    
    Args:
        id_or_ins: 合约ID或合约对象
        percent: 投资组合百分比，正数代表买入，负数代表卖出
        price_or_style: 价格或订单类型
        price: 价格（如果price_or_style是OrderStyle）
        style: 订单类型（如果price_or_style是价格）
    
    Returns:
        Order: 订单对象
    """
    order_book_id = assure_order_book_id(id_or_ins)
    instrument = assure_instrument(order_book_id)
    
    # 检查是否为加密货币合约
    if instrument.type not in [INSTRUMENT_TYPE.CRYPTO_SPOT, INSTRUMENT_TYPE.CRYPTO_FUTURE]:
        raise RQInvalidArgument(_("order_percent only support crypto instruments"))
    
    # 获取投资组合总价值
    account = _get_crypto_account()
    total_value = account.total_value
    
    # 计算交易金额
    cash_amount = total_value * percent
    
    # 使用order_value进行交易
    return order_value(order_book_id, cash_amount, price_or_style, price, style)


@export_as_api
@ExecutionContext.enforce_phase(EXECUTION_PHASE.ON_INIT,
                                EXECUTION_PHASE.BEFORE_TRADING,
                                EXECUTION_PHASE.ON_BAR,
                                EXECUTION_PHASE.AFTER_TRADING,
                                EXECUTION_PHASE.SCHEDULED)
@apply_rules(*common_rules)
def order_target_percent(id_or_ins, percent, price_or_style=None, price=None, style=None):
    # type: (Union[str, Instrument], float, TUPLE_PRICE_OR_STYLE_TYPE, Optional[float], Optional[OrderStyle]) -> Optional[Order]
    """
    调整持仓到目标百分比，适用于加密货币交易
    
    Args:
        id_or_ins: 合约ID或合约对象
        percent: 目标投资组合百分比
        price_or_style: 价格或订单类型
        price: 价格（如果price_or_style是OrderStyle）
        style: 订单类型（如果price_or_style是价格）
    
    Returns:
        Order: 订单对象
    """
    order_book_id = assure_order_book_id(id_or_ins)
    instrument = assure_instrument(order_book_id)
    
    # 检查是否为加密货币合约
    if instrument.type not in [INSTRUMENT_TYPE.CRYPTO_SPOT, INSTRUMENT_TYPE.CRYPTO_FUTURE]:
        raise RQInvalidArgument(_("order_target_percent only support crypto instruments"))
    
    # 获取投资组合总价值
    account = _get_crypto_account()
    total_value = account.total_value
    
    # 计算目标金额
    target_value = total_value * percent
    
    # 使用order_target_value进行交易
    return order_target_value(order_book_id, target_value, price_or_style, price, style)


@export_as_api
@ExecutionContext.enforce_phase(EXECUTION_PHASE.ON_INIT,
                                EXECUTION_PHASE.BEFORE_TRADING,
                                EXECUTION_PHASE.ON_BAR,
                                EXECUTION_PHASE.AFTER_TRADING,
                                EXECUTION_PHASE.SCHEDULED)
@apply_rules(*common_rules)
def order_to(order_book_id, quantity, price_or_style=None, price=None, style=None):
    # type: (Union[str, Instrument], int, PRICE_OR_STYLE_TYPE, Optional[float], Optional[OrderStyle]) -> List[Order]
    """
    智能调仓函数，适用于加密货币交易
    
    Args:
        order_book_id: 合约ID或合约对象
        quantity: 目标数量
        price_or_style: 价格或订单类型
        price: 价格（如果price_or_style是OrderStyle）
        style: 订单类型（如果price_or_style是价格）
    
    Returns:
        List[Order]: 订单列表
    """
    order_book_id = assure_order_book_id(order_book_id)
    instrument = assure_instrument(order_book_id)
    
    # 检查是否为加密货币合约
    if instrument.type not in [INSTRUMENT_TYPE.CRYPTO_SPOT, INSTRUMENT_TYPE.CRYPTO_FUTURE]:
        raise RQInvalidArgument(_("order_to only support crypto instruments"))
    
    # 获取当前持仓
    position = _get_crypto_position(order_book_id)
    current_quantity = position.quantity
    
    # 计算需要调整的数量
    delta_quantity = quantity - current_quantity
    
    if abs(delta_quantity) < 1e-6:  # 几乎相等，不需要交易
        return []
    
    # 使用order_shares进行交易
    order_obj = order_shares(order_book_id, delta_quantity, price_or_style, price, style)
    return [order_obj] if order_obj else []


@export_as_api
@apply_rules(verify_that("quantity").is_number(), *common_rules)
@instype_singledispatch
def order(order_book_id, quantity, price_or_style=None, price=None, style=None):
    # type: (Union[str, Instrument], int, PRICE_OR_STYLE_TYPE, Optional[float], Optional[OrderStyle]) -> List[Order]
    """
    全品种通用智能调仓函数，适用于加密货币交易
    
    Args:
        order_book_id: 合约ID或合约对象
        quantity: 交易数量，正数代表买入，负数代表卖出
        price_or_style: 价格或订单类型
        price: 价格（如果price_or_style是OrderStyle）
        style: 订单类型（如果price_or_style是价格）
        
    Returns:
        List[Order]: 订单列表
    """
    # 获取合约信息
    instrument = assure_instrument(order_book_id)
    order_book_id = assure_order_book_id(instrument)
    
    # 计算订单类型
    order_style = cal_style(price_or_style, price, style)
    
    # 确定交易方向
    side = SIDE.BUY if quantity > 0 else SIDE.SELL
    quantity = abs(quantity)
    
    # 创建订单
    order_obj = Order()
    order_obj._order_book_id = order_book_id
    order_obj._quantity = quantity
    order_obj._side = side
    order_obj._style = order_style
    order_obj._position_effect = POSITION_EFFECT.OPEN
    
    # 提交订单
    return [order_obj]
