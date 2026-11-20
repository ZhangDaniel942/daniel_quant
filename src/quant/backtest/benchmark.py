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

# 根据开盘价、收盘价计算考虑手续费和滑点的买入持有基准净值
def calculate_benchmark_nav(
    df: pd.DataFrame,
    initial_capital: float = 100_000,
    commission_rate: float = 0.0003,
    slippage_rate: float = 0.0002,
) -> pd.Series:
    """
    计算买入并持有（Buy & Hold）基准净值。
    交易规则：
    1. 第一个交易日开盘时买入。
    2. 买入价格考虑滑点。
    3. 买入手续费从初始资金中扣除。
    4. 后续一直持有，不进行主动交易。
    5. 每个交易日收盘时计算账户权益。
    """
    required_columns = {"open", "close"}
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

    if data[["open", "close"]].isna().any().any():
        raise ValueError("open、close 不能包含空值")

    if (data[["open", "close"]] <= 0).any().any():
        raise ValueError("价格必须大于 0")

    # 获取第一个交易日的开盘价
    open_price = float(data["open"].iloc[0])

    # 买入成交价：开盘价 + 买入滑点
    execution_price = open_price * (1 + slippage_rate)

    # 买入股数：确保手续费也包含在初始资金内
    shares = initial_capital / (
        execution_price * (1 + commission_rate)
    )

    # 实际买入金额
    trade_value = shares * execution_price

    # 买入手续费
    commission = trade_value * commission_rate

    # 买入后剩余现金
    cash = initial_capital - trade_value - commission

    # 每日收盘计算账户权益
    # 这里shares是一个常量, 就是第一天买入的份额, 但是close是每天的收盘价, 计算出当前份额对应的总金额
    equity = cash + shares * data["close"]

    # 基准净值
    # 再根据每天的equity计算净值
    benchmark_nav = equity / initial_capital
    benchmark_nav.name = "benchmark_nav"

    return benchmark_nav


# 计算策略相对基准的净值
def calculate_relative_nav(
    strategy_nav: pd.Series,
    benchmark_nav: pd.Series
) -> pd.Series:
    """计算策略相对基准的净值"""
    aligned = pd.concat(
        [strategy_nav, benchmark_nav],
        axis=1,
        join="inner"
    ).dropna()

    if aligned.empty:
        return pd.Series(dtype=float, name="relative_nav")

    if (aligned == 0).any().any():
        raise ValueError("净值不能为 0")

    relative_nav = (
        aligned.iloc[:, 0] / aligned.iloc[:, 1]
    )

    # 统一从 1 开始
    relative_nav = relative_nav / relative_nav.iloc[0]
    relative_nav.name = "relative_nav"

    return relative_nav

# 计算累计超额收益
def calculate_excess_return(
    strategy_nav: pd.Series,
    benchmark_nav: pd.Series
) -> float:
    """计算策略相对基准的累计超额收益（算术差值）"""
    aligned = pd.concat(
        [strategy_nav, benchmark_nav],
        axis=1,
        join="inner"
    ).dropna()

    if len(aligned) < 2:
        return float("nan")

    strategy_return = (
        aligned.iloc[-1, 0] / aligned.iloc[0, 0] - 1
    )

    benchmark_return = (
        aligned.iloc[-1, 1] / aligned.iloc[0, 1] - 1
    )

    return float(strategy_return - benchmark_return)


