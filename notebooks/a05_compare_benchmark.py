#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 22:11
# @Author  : daniel
# @File    : a05_compare_benchmark.py
# @Project : daniel_quant

"""
Description: 模拟数据查看一下基准测试
             这里应该使用真实数据写一下看看
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from src.quant.backtest.benchmark import (
    calculate_benchmark_nav,
    calculate_relative_nav,
)

# 生成模拟数据
np.random.seed(42)
dates = pd.bdate_range(
    start="2025-01-01",
    periods=252
)

strategy_returns = np.random.normal(
    loc=0.0007,
    scale=0.012,
    size=252
)

benchmark_returns = np.random.normal(
    loc=0.0004,
    scale=0.01,
    size=252
)

strategy_nav = pd.Series(
    (1 + strategy_returns).cumprod(),
    index=dates
)

benchmark_close = pd.Series(
    (1 + benchmark_returns).cumprod() * 100,
    index=dates
)

benchmark_nav = calculate_benchmark_nav(
    benchmark_close
)

relative_nav = calculate_relative_nav(
    strategy_nav,
    benchmark_nav
)


# 打印结果
strategy_total_return = strategy_nav.iloc[-1] - 1
benchmark_total_return = benchmark_nav.iloc[-1] - 1

print(f"策略累计收益：{strategy_total_return:.2%}")
print(f"基准累计收益：{benchmark_total_return:.2%}")
print(
    f"累计超额收益："
    f"{strategy_total_return - benchmark_total_return:.2%}"
)


# 绘制净值对比图
fig, axes = plt.subplots(
    2,
    1,
    figsize=(12, 8),
    sharex=True
)

axes[0].plot(
    strategy_nav,
    label="Strategy NAV"
)

axes[0].plot(
    benchmark_nav,
    label="Benchmark NAV"
)

axes[0].set_title("Strategy vs Benchmark")
axes[0].legend()
axes[0].grid(True)


# 绘制相对净值
axes[1].plot(
    relative_nav,
    label="Relative NAV"
)

axes[1].axhline(
    y=1,
    linestyle="--"
)

axes[1].set_title("Relative NAV")
axes[1].legend()
axes[1].grid(True)

plt.tight_layout()
plt.show()