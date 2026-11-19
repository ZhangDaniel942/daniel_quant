#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 22:35
# @Author  : daniel
# @File    : a01_strategy_test.py
# @Project : daniel_quant

"""
Description: 策略测试
             给定清洗后数据, 加上策略, 计算signal, 然后回测计算最终收益等
             再根据回测结果, 进行benchmark测试以及最大回撤等计算
"""
from pathlib import Path

import pandas as pd

from data.processed.processed_data_config import processed_data_path
from quant.utils.print_utils import pf
from src.quant.backtest.engine import run_backtest
from src.quant.strategies.dual_ma import generate_signals

# 获取数据路径
data_path = processed_data_path / "sina_601600.csv"

# 加载行情数据
df = pd.read_csv(data_path, parse_dates=["date"])
pf("打印一下数据核对一下")
print(df["date"].count())
print(df[['open', 'high', 'low', 'close']].sum())
pf("核对原始数据done")

# 生成策略信号, 买入卖出信号
df = generate_signals(df)

# 执行回测
result = run_backtest(df,initial_capital=100_000)

print(result.tail())
print("最终净值：", result["nav"].iloc[-1])
print("最终资产：", result["equity"].iloc[-1])

# 1. 查看所有列，避免 pandas 省略字段
print("\n===== 最后10行 =====")
print(result.tail(10).to_string())

# 2. 查看交易次数
print("\n===== 交易统计 =====")
print("买入次数：", (result["action"] == "BUY").sum())
print("卖出次数：", (result["action"] == "SELL").sum())

# 3. 查看信号和持仓
print("\n===== 信号统计 =====")
print(result["signal"].value_counts(dropna=False))

if "position" in result.columns:
    print("\n===== 持仓统计 =====")
    print(result["position"].value_counts(dropna=False))

# 4. 查看资金变化
print("\n===== 账户状态 =====")
print("初始资产：", result["equity"].iloc[0])
print("最低资产：", result["equity"].min())
print("最高资产：", result["equity"].max())
print("最终资产：", result["equity"].iloc[-1])

# 5. 查看买卖发生时的情况
print("\n===== 交易记录 =====")
print(
    result[result["action"].isin(["BUY", "SELL"])][
        ["open", "close", "signal", "action", "cash", "shares", "equity", "nav"]
    ].to_string()
)
