#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 22:04
# @Author  : daniel
# @File    : benchmark.py
# @Project : daniel_quant

"""
Description: 基准对比（Benchmark）
             我们的策略主要投资沪深300 ETF，那么就可以把沪深300作为基准。
             就是我们投资的股票对应的基准
"""

import pandas as pd

# 根据收盘价计算涨跌情况
def calculate_benchmark_nav(
    benchmark_close: pd.Series
) -> pd.Series:
    """
    根据基准收盘价计算基准净值
    """
    # 计算相邻两个值的百分比变化，公式是 (今天 - 昨天) / 昨天, 根据收盘价计算: 涨跌变化
    benchmark_returns = benchmark_close.pct_change()
    benchmark_nav = (
        1 + benchmark_returns.fillna(0)
    ).cumprod()

    # 最终的涨跌情况
    return benchmark_nav

# 根据calculate_benchmark_nav可以计算策略净值和参考净值, 放入这里计算相对净值
def calculate_relative_nav(
    strategy_nav: pd.Series,
    benchmark_nav: pd.Series
) -> pd.Series:
    """
    计算策略相对基准的净值
    """
    aligned = pd.concat(
        [strategy_nav, benchmark_nav],
        axis=1,
        join="inner"
    ).dropna()

    if aligned.empty:
        return pd.Series(dtype=float)

    relative_nav = (
        aligned.iloc[:, 0] / aligned.iloc[:, 1]
    )

    # 统一从 1 开始
    return relative_nav / relative_nav.iloc[0]

def calculate_excess_return(
    strategy_nav: pd.Series,
    benchmark_nav: pd.Series
) -> float:
    """
    计算累计超额收益
    """
    # 对齐日期
    aligned = pd.concat(
        [strategy_nav, benchmark_nav],
        axis=1,
        join="inner"
    ).dropna()

    if len(aligned) < 2:
        return float("nan")

    strategy_return =  (aligned.iloc[-1, 0] / aligned.iloc[0, 0] - 1)
    benchmark_return = (aligned.iloc[-1, 1] / aligned.iloc[0, 1] - 1)

    return float(strategy_return - benchmark_return)


