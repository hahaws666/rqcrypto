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
from rqalpha.utils import is_valid_price
from rqalpha.utils.arg_checker import apply_rules, verify_that
from rqalpha.utils.datetime_func import to_date
from rqalpha.utils.exception import RQInvalidArgument
from rqalpha.utils.i18n import gettext as _
from rqalpha.utils.logger import user_log, user_system_log
from rqalpha.utils.typing import DateLike

# 使用Decimal 解决浮点数运算精度问题
getcontext().prec = 10


def _get_crypto_account():
    """获取加密货币账户"""
    env = Environment.get_instance()
    return env.portfolio.accounts[DEFAULT_ACCOUNT_TYPE.CRYPTO]


def _get_crypto_position(order_book_id, direction=POSITION_DIRECTION.LONG):
    """获取加密货币持仓"""
    account = _get_crypto_account()
    return account.get_position(order_book_id, direction)


def _get_account_position_ins(id_or_ins):
    """获取账户、持仓和合约信息"""
    ins = assure_instrument(id_or_ins)
    try:
        account = Environment.get_instance().portfolio.accounts[DEFAULT_ACCOUNT_TYPE.CRYPTO]
    except KeyError:
        raise KeyError(_(
                u"order_book_id: {order_book_id} needs crypto account, please set and try again!"
            ).format(order_book_id=ins.order_book_id))
    position = account.get_position(ins.order_book_id, POSITION_DIRECTION.LONG)
    return account, position, ins


def _round_order_quantity(ins, quantity, method: Callable = int) -> int:
    """四舍五入订单数量"""
    # round_lot = ins.round_lot
    try:
        # 对于加密货币，暂时注释掉最小交易单位限制，直接返回原数量
        # rounded_quantity = method(Decimal(quantity) / Decimal(round_lot)) * round_lot
        # if rounded_quantity == 0 and abs(quantity) > 0:
        #     # 如果原数量不为0但四舍五入后为0，返回最小交易单位
        #     return round_lot if quantity > 0 else -round_lot
        # return rounded_quantity
        # return int(quantity)  # 直接返回整数化的数量
        return quantity
    except ValueError:
        raise


def _get_order_style_price(order_book_id, style):
    """获取订单类型对应的价格"""
    if isinstance(style, LimitOrder):
        return style.get_limit_price()
    env = Environment.get_instance()
    if isinstance(style, MarketOrder):
        return env.data_proxy.get_last_price(order_book_id)
    if isinstance(style, ALGO_ORDER_STYLES):
        price, _ = env.data_proxy.get_algo_bar(order_book_id, style, env.calendar_dt)
        return price
    raise RuntimeError(f"no support {style} order style")


def _submit_order(ins, amount, side, position_effect, style, current_quantity, auto_switch_order_value, zero_amount_as_exception=True):
    """提交订单的核心函数"""
    env = Environment.get_instance()
    if isinstance(style, LimitOrder) and np.isnan(style.get_limit_price()):
        raise RQInvalidArgument(_(u"Limit order price should not be nan."))
    price = env.data_proxy.get_last_price(ins.order_book_id)
    if not is_valid_price(price):
        reason = _(u"Order Creation Failed: [{order_book_id}] No market data").format(order_book_id=ins.order_book_id)
        env.order_creation_failed(order_book_id=ins.order_book_id, reason=reason)
        return

    if (side == SIDE.BUY and current_quantity != -amount) or (side == SIDE.SELL and current_quantity != abs(amount)):
        # 对于加密货币，也需要四舍五入到最小交易单位
        amount = _round_order_quantity(ins, amount)

    if amount == 0:
        if zero_amount_as_exception:
            reason = _(u"Order Creation Failed: 0 order quantity, order_book_id={order_book_id}").format(order_book_id=ins.order_book_id)
            env.order_creation_failed(order_book_id=ins.order_book_id, reason=reason)
        return
    
    # 使用 Order.__from_create__ 创建订单
    order = Order.__from_create__(ins.order_book_id, abs(amount), side, style, position_effect)
    
    if side == SIDE.BUY and auto_switch_order_value:
        account, position, ins = _get_account_position_ins(ins)
        # 对于加密货币，我们简化现金验证逻辑
        if account.cash < amount * price:
            user_system_log.warn(_(
                "insufficient cash, use all remaining cash({}) to create order"
            ).format(account.cash))
            return _order_value(account, position, ins, account.cash, style)
    
    return env.submit_order(order)


def _order_shares(ins, amount, style, quantity, auto_switch_order_value, zero_amount_as_exception=True):
    """按数量下单的辅助函数"""
    side, position_effect = (SIDE.BUY, POSITION_EFFECT.OPEN) if amount > 0 else (SIDE.SELL, POSITION_EFFECT.CLOSE)
    print(f"submitting crypto order: {ins}, {amount}, {style}, {quantity}, {auto_switch_order_value}, {zero_amount_as_exception}")
    return _submit_order(ins, amount, side, position_effect, style, quantity, auto_switch_order_value, zero_amount_as_exception)


def _order_value(account, position, ins, cash_amount, style, zero_amount_as_exception=True):
    """按金额下单的辅助函数"""
    env = Environment.get_instance()
    if cash_amount > 0:
        cash_amount = min(cash_amount, account.cash)
    if isinstance(style, LimitOrder):
        price = style.get_limit_price()
    else:
        price = env.data_proxy.get_last_price(ins.order_book_id)
        if not is_valid_price(price):
            reason = _(u"Order Creation Failed: [{order_book_id}] No market data").format(order_book_id=ins.order_book_id)
            env.order_creation_failed(order_book_id=ins.order_book_id, reason=reason)
            return

    amount = int(Decimal(cash_amount) / Decimal(price))
    round_lot = int(ins.round_lot)
    if cash_amount > 0:
        amount = _round_order_quantity(ins, amount)
        while amount > 0:
            expected_transaction_cost = env.get_order_transaction_cost(Order.__from_create__(
                ins.order_book_id, amount, SIDE.BUY, LimitOrder(price), POSITION_EFFECT.OPEN
            ))
            if amount * price + expected_transaction_cost <= cash_amount:
                break
            amount -= round_lot
        else:
            if zero_amount_as_exception:
                reason = _(u"Order Creation Failed: 0 order quantity, order_book_id={order_book_id}").format(order_book_id=ins.order_book_id)
                env.order_creation_failed(order_book_id=ins.order_book_id, reason=reason)
            return

    if amount < 0:
        amount = max(amount, -position.closable)

    return _order_shares(ins, amount, style, position.quantity, auto_switch_order_value=False, zero_amount_as_exception=zero_amount_as_exception)


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
    print(f"order_shares: {id_or_ins}, {amount}, {price_or_style}, {price}, {style}")
    order_book_id = assure_order_book_id(id_or_ins)
    instrument = assure_instrument(order_book_id)
    
    # 检查是否为加密货币合约
    if instrument.type not in [INSTRUMENT_TYPE.CRYPTO_SPOT, INSTRUMENT_TYPE.CRYPTO_FUTURE]:
        raise RQInvalidArgument(_("order_shares only support crypto instruments"))
    
    # 检查数量
    if amount == 0:
        return None
    
    # 获取账户和持仓信息
    account, position, ins = _get_account_position_ins(id_or_ins)
    
    # 使用辅助函数处理订单
    auto_switch_order_value = Environment.get_instance().config.mod.sys_accounts.auto_switch_order_value
    return _order_shares(
        ins, amount, cal_style(price, style, price_or_style), position.quantity,
        auto_switch_order_value
    )


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
    
    # 获取账户和持仓信息
    account, position, ins = _get_account_position_ins(id_or_ins)
    
    # 使用辅助函数处理订单
    return _order_value(account, position, ins, cash_amount, cal_style(price, style, price_or_style))


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
    
    # 获取账户和持仓信息
    account, position, ins = _get_account_position_ins(id_or_ins)
    open_style, close_style = calc_open_close_style(price, style, price_or_style)
    
    if cash_amount == 0:
        return _submit_order(
            ins, position.closable, SIDE.SELL, POSITION_EFFECT.CLOSE, close_style, position.quantity, False
        )
    
    _delta = cash_amount - position.market_value
    _style = open_style if _delta > 0 else close_style
    return _order_value(account, position, ins, _delta, _style, zero_amount_as_exception=False)


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
    
    # 获取账户和持仓信息
    account, position, ins = _get_account_position_ins(id_or_ins)
    
    # 使用辅助函数处理订单
    return _order_value(account, position, ins, account.total_value * percent, cal_style(price, style, price_or_style))


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
    
    # 获取账户和持仓信息
    account, position, ins = _get_account_position_ins(id_or_ins)
    open_style, close_style = calc_open_close_style(price, style, price_or_style)
    
    if percent == 0:
        return _submit_order(
            ins, position.closable, SIDE.SELL, POSITION_EFFECT.CLOSE, close_style, position.quantity, False
        )
    
    _delta = account.total_value * percent - position.market_value
    _style = open_style if _delta > 0 else close_style
    return _order_value(account, position, ins, _delta, _style, zero_amount_as_exception=False)


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
    position = Environment.get_instance().portfolio.get_position(order_book_id, POSITION_DIRECTION.LONG)
    open_style, close_style = calc_open_close_style(price, style, price_or_style)
    quantity = quantity - position.quantity
    _style = open_style if quantity > 0 else close_style
    result_order = order_shares(order_book_id, quantity, price, _style, price_or_style)
    if result_order:
        return [result_order]
    return []


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
    result_order = order_shares(order_book_id, quantity, price, style, price_or_style)
    if result_order:
        return [result_order]
    return []
