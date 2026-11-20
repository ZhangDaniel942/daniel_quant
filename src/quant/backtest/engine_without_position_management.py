#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 22:24
# @Author  : daniel
# @File    : engine.py
# @Project : daniel_quant

"""
Description: 回测引擎: 这是早期版本, 没有仓位管理概念
    概念: equity = cash + shares * close
    字段	        中文名称	    含义
    date	    交易日期	    当前交易日
    open	    开盘价	    当天开盘价格
    close	    收盘价	    当天收盘价格
    signal	    策略信号	    策略希望持有还是空仓
    position	实际持仓	    当前是否持有ETF, 只有0和1, 0代表0%持有, 1代表100%持有, 我们目前不管理仓位, 只有全仓和空仓, 后续可以有小数, 代表仓位管理
    action	    交易动作	    BUY / SELL / HOLD
    cash	    现金	        当前可用现金
    shares	    持仓份额	    当前持有多少份ETF
    commission	手续费	    当天发生的交易手续费
    equity	    总资产	    现金加持仓市值
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
            # 前一天有信号, 比如1, 今天就全仓买入, 如果是0, 就清仓
            # 1. 使用前一天的信号
            target_position = int(data["signal"].iloc[i - 1])

        open_price = float(row["open"])
        close_price = float(row["close"])
        ma_short = float(row["ma_short"])
        ma_long = float(row["ma_long"])

        # 目标持仓与当前持仓不同，执行买卖
        # current_position其实是交易前的仓位.
        current_position = 1 if shares > 0 else 0  # shares就是当前份额, 因为我们只有空仓和全仓, 所以
        if target_position != current_position:
            if target_position == 1:
                # 考虑买入滑点
                execution_price = open_price * (1 + slippage_rate)
                # 留出手续费，计算可购买份额
                shares = cash / ( execution_price * (1 + commission_rate) )
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
            "ma_short": ma_short,
            "ma_long": ma_long,
            "signal": int(row["signal"]), # signal是在策略中生成的, 所以原先的数据中就有
            "position": int(shares > 0),
            "action": action,
            "cash": cash,
            "shares": shares,
            "commission": commission,
            "equity": equity,
        })


    # 建议再读取数据的时候, 直接设置日期索引, 这里就不需要设置了
    # 错了, 这是一个新的df, 需要设置哈
    result = pd.DataFrame(records).set_index("date").sort_index()
    # result["date"] = result.index

    # 回测的时候, 已经计算了: nav和return了
    result["nav"] = result["equity"] / initial_capital
    # 这里使用收盘价计算收益比
    result["return"] = result["nav"].pct_change().fillna(0)

    return result