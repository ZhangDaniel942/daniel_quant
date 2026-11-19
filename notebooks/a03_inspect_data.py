#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/19 20:08
# @Author  : daniel
# @File    : a03_inspect_data.py
# @Project : daniel_quant

"""
Description: 数据挖掘和查看
"""
from cProfile import label

import matplotlib.pyplot as plt
import pandas as pd

from data.processed.processed_data_config import processed_data_path
from quant.indicators.moving_average import add_moving_averages

data_path = processed_data_path / "sina_510300.csv"

data = pd.read_csv(data_path, parse_dates=["date"])
df = add_moving_averages(data, windows=[5, 20, 60, 120])
# print(df)
# df.to_csv(data_path)

print(df)

df = df[(df["date"] > "2024-01-01") & (df["date"] < "2025-01-01")]

plt.title("510300 ETF - Moving Average Analysis")
# 双均线策略: 短期均线上穿长期均线买入, 短期均线下穿长期均线卖出
plt.plot(df["date"], df["close"], label="close")
plt.plot(df["date"], df["ma5"], label="ma5")
plt.plot(df["date"], df["ma20"], label="ma20")
# plt.plot(df["date"], df["ma60"], label="ma60")
# plt.plot(df["date"], df["ma120"], label="ma120")
plt.legend()  # 显示图例


import matplotlib.dates as mdates
ax = plt.gca()
ax.xaxis.set_major_locator(mdates.DayLocator(interval=15))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()


print(df["date"].dtype)   # 应该是 datetime64[ns]






