#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 22:24
# @Author  : daniel
# @File    : engine.py
# @Project : daniel_quant

"""
Description: 回测引擎

"""

import pandas as pd

def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = 100_000,
    commission_rate: float = 0.0003,
    slippage_rate: float = 0.0002,
) -> pd.DataFrame:
    """
    最小版日频回测引擎。
    约定：
    1. 当日收盘生成 signal。
    2. 下一交易日开盘执行。
    3. 当日收盘计算账户资产。
    4. 暂不模拟整手、税费、涨跌停和部分成交。
    """
    required_columns = {"open", "close", "signal"}

    if not required_columns.issubset(df.columns):
        raise ValueError(f"缺少必要字段：{required_columns - set(df.columns)}")

    if df.empty:
        raise ValueError("行情数据不能为空")

    if initial_capital <= 0:
        raise ValueError("初始资金必须大于 0")

    if not 0 <= commission_rate < 1:
        raise ValueError("手续费率不合法")

    if not 0 <= slippage_rate < 1:
        raise ValueError("滑点率不合法")

    data = df.copy().sort_index()

    if data.index.has_duplicates:
        raise ValueError("行情日期不能重复")

    if data[["open", "close", "signal"]].isna().any().any():
        raise ValueError("open、close、signal 不能包含空值")

    if (data[["open", "close"]] <= 0).any().any():
        raise ValueError("价格必须大于 0")

    if not data["signal"].isin([0, 1]).all():
        raise ValueError("signal 只能为 0 或 1")

    cash = float(initial_capital)
    shares = 0.0

    records = []

    for i, (index, row) in enumerate(data.iterrows()):
        # print(index)
        if "date" in data.columns:
            date = row["date"]
        else:
            date = index
        # 第一天没有上一交易日信号，因此不交易
        if i == 0:
            target_position = 0
        else:
            target_position = int(data["signal"].iloc[i - 1])

        open_price = float(row["open"])
        close_price = float(row["close"])

        # 目标持仓与当前持仓不同，执行买卖
        current_position = 1 if shares > 0 else 0

        if target_position != current_position:

            if target_position == 1:
                # 考虑买入滑点
                execution_price = open_price * (1 + slippage_rate)

                # 留出手续费，计算可购买份额
                shares = cash / (
                    execution_price * (1 + commission_rate)
                )

                trade_value = shares * execution_price
                commission = trade_value * commission_rate

                cash -= trade_value + commission

                action = "BUY"

            else:
                # 考虑卖出滑点
                execution_price = open_price * (1 - slippage_rate)

                trade_value = shares * execution_price
                commission = trade_value * commission_rate

                cash += trade_value - commission
                shares = 0.0

                action = "SELL"

        else:
            execution_price = None
            trade_value = 0.0
            commission = 0.0
            action = "HOLD"

        # 收盘估值
        equity = cash + shares * close_price

        records.append({
            "date": date,
            "open": open_price,
            "close": close_price,
            "signal": int(row["signal"]), # signal是在策略中生成的, 所以原先的数据中就有
            "position": int(shares > 0),
            "action": action,
            "cash": cash,
            "shares": shares,
            "commission": commission,
            "equity": equity,
        })


    result = pd.DataFrame(records).set_index("date")
    # result["date"] = result.index

    result["nav"] = result["equity"] / initial_capital
    # 这里使用收盘价计算收益
    result["return"] = result["nav"].pct_change().fillna(0)

    return result