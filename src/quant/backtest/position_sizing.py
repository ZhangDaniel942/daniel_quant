#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/20 23:19
# @Author  : daniel
# @File    : position_sizing.py
# @Project : daniel_quant

"""
Description: 仓位管理
             仓位管理position_sizing负责决定想持有多少，交易执行engine负责把这个目标转换成实际成交的ETF份额。

# calculate_position_delta() - 计算当前仓位
#   ↓
# calculate_step_position() - 计算本次允许调整的仓位
#   ↓
# calculate_trade_value() - 计算本次需要交易多少钱
#   ├── BUY  -> calculate_buy_shares()  - 买入 / 计算买入股数
#   └── SELL -> calculate_sell_shares() - 卖出 / 计算卖出股数
"""

import math

def calculate_buy_shares(
    cash,
    trade_value,
    open_price,
    commission_rate=0.0003,
    slippage_rate=0.0002,
    lot_size=100,
):
    """
    根据本次计划买入金额，计算实际买入份额。

    cash: 当前可用现金
    trade_value: 本次计划买入金额（不含手续费）
    open_price: 当日开盘价
    """

    if cash < 0 or trade_value < 0:
        raise ValueError("现金和买入金额不能小于 0")

    if open_price <= 0:
        raise ValueError("开盘价必须大于 0")

    if lot_size <= 0:
        raise ValueError("交易单位必须大于 0")

    # 1. 买入滑点
    execution_price = open_price * (1 + slippage_rate)

    # 2. 根据计划金额计算理论股数
    theoretical_shares = trade_value / execution_price

    # 3. 按100股一手向下取整
    desired_shares = (
        math.floor(theoretical_shares / lot_size) * lot_size
    )

    # 4. 计算现金最多可以买多少股
    max_affordable_shares = math.floor(
        cash / (execution_price * (1 + commission_rate) * lot_size)
    ) * lot_size

    # 5. 实际买入数量不能超过计划数量和可购买数量
    buy_shares = min(desired_shares, max_affordable_shares)

    # 6. 计算成交金额和手续费
    trade_amount = buy_shares * execution_price
    commission = trade_amount * commission_rate
    total_cost = trade_amount + commission

    return {
        "shares": buy_shares,
        "execution_price": execution_price,
        "trade_amount": trade_amount,
        "commission": commission,
        "total_cost": total_cost,
    }


def calculate_sell_shares(
    shares,
    open_price,
    trade_value=None,
    commission_rate=0.0003,
    slippage_rate=0.0002,
    lot_size=100,
):
    """
    根据本次计划卖出金额，计算实际卖出份额。

    shares: 当前持有份额
    trade_value: 本次计划卖出金额
                 None表示全部清仓
    """

    if shares < 0:
        raise ValueError("持仓份额不能小于 0")

    if open_price <= 0:
        raise ValueError("开盘价必须大于 0")

    if trade_value is not None and trade_value < 0:
        raise ValueError("卖出金额不能小于 0")

    if lot_size <= 0:
        raise ValueError("交易单位必须大于 0")

    # 1. 卖出滑点
    execution_price = open_price * (1 - slippage_rate)

    available_shares = int(shares)

    # 2. 判断是否全部清仓
    if (
        trade_value is None
        or trade_value >= available_shares * execution_price
    ):
        # 全部卖出，允许处理剩余不足一手的份额
        sell_shares = available_shares

    else:
        # 3. 部分卖出，按照整手向下取整
        theoretical_shares = trade_value / execution_price

        sell_shares = (
            math.floor(theoretical_shares / lot_size) * lot_size
        )

        sell_shares = min(sell_shares, available_shares)

    # 4. 计算成交金额
    trade_amount = sell_shares * execution_price

    # 5. 计算手续费
    commission = trade_amount * commission_rate

    # 6. 实际到账金额
    net_amount = trade_amount - commission

    return {
        "shares": sell_shares,
        "execution_price": execution_price,
        "trade_amount": trade_amount,
        "commission": commission,
        "net_amount": net_amount,
    }

def calculate_position_delta(
    cash,
    shares,
    price,
    target_position,
):
    """
    计算当前仓位与目标仓位之间的差额
    """

    # 1. 计算当前持仓市值
    market_value = shares * price

    # 2. 计算账户总资产
    equity = cash + market_value

    # 3. 计算当前仓位
    current_position = market_value / equity

    # 4. 计算目标仓位差额
    position_delta = target_position - current_position

    # 5. 判断交易方向
    if position_delta > 0:
        action = "BUY"
    elif position_delta < 0:
        action = "SELL"
    else:
        action = "HOLD"

    return {
        "equity": equity,
        "current_position": current_position,
        "target_position": target_position,
        "position_delta": position_delta,
        "action": action,
    }

def calculate_step_position(
    current_position,
    target_position,
    max_position_change=0.1,
):
    """
    计算本次应该调整到的目标仓位。
    但实际投资中，我们可能不希望一次性买入这么多，而是分几次逐步建仓。
    max_position_change:
        每次最大调整幅度，例如 0.1 = 10 个百分点
    """

    # 1. 检查仓位范围
    if not 0 <= current_position <= 1:
        raise ValueError("当前仓位必须在 0 到 1 之间")

    if not 0 <= target_position <= 1:
        raise ValueError("目标仓位必须在 0 到 1 之间")

    if not 0 < max_position_change <= 1:
        raise ValueError("最大调整幅度必须大于 0 且不超过 1")

    # 2. 计算仓位差额
    position_delta = target_position - current_position

    # 3. 限制本次调整幅度
    if position_delta > max_position_change:
        position_delta = max_position_change

    elif position_delta < -max_position_change:
        position_delta = -max_position_change

    # 4. 计算本次调整后的目标仓位
    next_position = current_position + position_delta

    return {
        "current_position": current_position,
        "target_position": target_position,
        "position_delta": position_delta,
        "next_position": next_position,
    }


def calculate_trade_value(
    cash,
    shares,
    open_price,
    target_position,
):
    """
    根据目标仓位计算需要买入或卖出的金额。
    先计算应该交易多少钱，再计算具体交易多少份ETF。
    """
    if cash < 0 or shares < 0:
        raise ValueError("现金和持仓不能小于 0")

    if open_price <= 0:
        raise ValueError("开盘价必须大于 0")

    if not 0 <= target_position <= 1:
        raise ValueError("目标仓位必须在 0 到 1 之间")

    # 1. 计算开盘时账户总资产
    equity = cash + shares * open_price

    # 2. 当前持仓市值
    current_market_value = shares * open_price

    # 3. 目标持仓市值
    target_market_value = equity * target_position

    # 4. 计算交易金额
    trade_value = target_market_value - current_market_value

    return {
        "equity": equity,
        "current_market_value": current_market_value,
        "target_market_value": target_market_value,
        "trade_value": trade_value,
    }

if __name__ == '__main__':
    result = calculate_buy_shares(
        cash=100_000,
        trade_value=30_000,
        open_price=4.0,
    )
    print(result)

    result = calculate_buy_shares(
        cash=70_000,
        trade_value=10_000,
        open_price=4.0,
    )

    print(result)

    result = calculate_sell_shares(
        shares=7_500,
        open_price=4.0,
        trade_value=10_000,
    )

    print(result)