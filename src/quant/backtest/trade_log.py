#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 21:19
# @Author  : daniel
# @File    : trade_log.py
# @Project : daniel_quant

"""
Description: 量化系统不能只看最终赚了多少钱，还要知道每笔交易发生了什么
"""


import pandas as pd


def generate_trade_log(df: pd.DataFrame) -> pd.DataFrame:

    trades = df.loc[
        df["trade"] != 0,
        ["close", "trade", "cost", "equity"]
    ].copy()

    trades["action"] = trades["trade"].map({
        1: "BUY",
        -1: "SELL",
    })

    trades = trades.reset_index()

    trades = trades.rename(columns={
        "index": "date",
        "close": "price",
        "trade": "position_change",
    })

    return trades
