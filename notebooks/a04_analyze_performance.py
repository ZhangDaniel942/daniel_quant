#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 21:33
# @Author  : daniel
# @File    : a04_analyze_performance.py
# @Project : daniel_quant

"""
Description: 收益表现分析
"""
import os

import pandas as pd
from matplotlib import pyplot as plt

from data.processed.processed_data_config import processed_data_path
from src.quant.backtest.performance import (
    calculate_nav,
    calculate_performance,
    calculate_max_drawdown,
)

data_path = processed_data_path / "sina_510300.csv"
df = pd.read_csv(data_path, parse_dates=["date"])

# Simulated daily strategy returns
returns = pd.Series([
    0.00,
    0.02,
    0.03,
    -0.02,
    -0.04,
    0.01,
    0.03,
    -0.01,
    0.02,
    0.04,
    -0.03,
    0.02,
])

# 1. Calculate NAV
nav = calculate_nav(returns)

# 2. Calculate performance
performance = calculate_performance(nav)

# 3. Calculate drawdown
max_dd, drawdown = calculate_max_drawdown(nav)

print("===== Strategy Performance =====")
for name, value in performance.items():
    print(f"{name}: {value:.4%}" if isinstance(value, float) else value)

print("\n===== NAV =====")
print(nav.round(4))

print("\n===== Drawdown =====")
print(drawdown.round(4))


# 量化研究不能只看数字，还需要可视化。
fig, axes = plt.subplots(
    2,
    1,
    figsize=(12, 8),
    sharex=True,
)

# NAV curve
axes[0].plot(nav.index, nav.values)

axes[0].set_title("Strategy NAV")
axes[0].set_ylabel("NAV")
axes[0].grid(alpha=0.3)

# Drawdown curve
axes[1].fill_between(
    drawdown.index,
    drawdown.values,
    0,
    alpha=0.3,
)

axes[1].set_title("Strategy Drawdown")
axes[1].set_ylabel("Drawdown")
axes[1].grid(alpha=0.3)

plt.tight_layout()

os.makedirs("reports", exist_ok=True)
plt.savefig(
    "../reports/performance_analysis.png",
    dpi=150,
)

plt.show()