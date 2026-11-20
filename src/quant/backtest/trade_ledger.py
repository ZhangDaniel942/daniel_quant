#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/20 00:02
# @Author  : daniel
# @File    : trade_ledger.py
# @Project : daniel_quant

"""
Description: 把一次买入和对应的卖出配对，计算完整交易盈亏。
交易账本

将回测引擎产生的 BUY / SELL 动作配对，
统计每笔完整交易的盈亏、收益率和持有时间。
"""
import pandas as pd

def generate_trade_ledger(
    result: pd.DataFrame,
) -> pd.DataFrame:
    """
    根据回测结果生成交易账本。

    参数：
        result: engine.py 返回的回测结果。
                交易日期必须是 DataFrame 的 index。
    返回：
        每一行代表一笔完整交易。
    """

    # 1. 检查必要字段
    required_columns = {
        "action",
        "open",
        "shares",
        "equity",
    }

    missing_columns = required_columns - set(result.columns)

    if missing_columns:
        raise ValueError(
            f"缺少必要字段：{missing_columns}"
        )

    if result.empty:
        return pd.DataFrame()

    if result.index.has_duplicates:
        raise ValueError("交易日期不能重复")

    # 2. 初始化交易记录
    trades = []

    # 当前尚未完成的交易
    current_trade = None

    # 3. 遍历回测结果
    for date, row in result.iterrows():

        action = row["action"]

        # 买入
        if action == "BUY":

            if current_trade is not None:
                raise ValueError(
                    "发现连续 BUY，上一笔交易尚未完成"
                )

            current_trade = {
                "entry_date": date,
                "entry_price": float(row["open"]),
                "shares": float(row["shares"]),
            }

        # 卖出
        elif action == "SELL":

            if current_trade is None:
                raise ValueError(
                    "发现没有对应 BUY 的 SELL"
                )

            entry_date = current_trade["entry_date"]
            entry_price = current_trade["entry_price"]
            shares = current_trade["shares"]

            exit_date = date
            exit_price = float(row["open"])

            # 4. 计算交易盈亏
            profit = (
                exit_price - entry_price
            ) * shares

            # 价格收益率
            profit_rate = (
                exit_price / entry_price - 1
            )

            # 持有交易日数（按交易记录的行数计算）
            entry_index = result.index.get_loc(entry_date)
            exit_index = result.index.get_loc(exit_date)

            holding_days = exit_index - entry_index

            # 5. 保存完整交易记录
            trades.append({
                "entry_date": entry_date,
                "exit_date": exit_date,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "shares": shares,
                "profit": profit,
                "profit_rate": profit_rate,
                "holding_days": holding_days,
            })

            # 当前交易结束
            current_trade = None

    # 6. 转换成 DataFrame
    trade_ledger = pd.DataFrame(trades)

    return trade_ledger

