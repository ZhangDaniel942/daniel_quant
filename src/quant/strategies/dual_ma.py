#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 22:29
# @Author  : daniel
# @File    : dual_ma.py
# @Project : daniel_quant

"""
Description: 双均线策略（Dual Moving Average Strategy）
它的核心思想很简单：
短期均线上穿长期均线时买入，短期均线下穿长期均线时卖出。

# ============================================================
# 金叉 / 死叉信号生成
#
# 金叉（Golden Cross）—— 买入信号：
#   MA5_t > MA20_t  且  MA5_{t-1} <= MA20_{t-1}
#   即短期均线从下向上穿过长期均线的“那一天”
#
# 死叉（Death Cross）—— 卖出信号：
#   MA5_t < MA20_t  且  MA5_{t-1} >= MA20_{t-1}
#   即短期均线从上向下穿过长期均线的“那一天”
#
# 注意：不是 MA5 > MA20 的每一天都算买入信号，
#       只在两条均线发生交叉的那一天产生信号。
# ============================================================

"""
import pandas as pd

def generate_signals(
    df: pd.DataFrame,
    short_window: int = 5,
    long_window: int = 20
) -> pd.DataFrame:
    """
    MA5 在 MA20 上方：近期价格相对强势。
    MA5 在 MA20 下方：近期价格相对弱势。
    :param df:
    :param short_window: 短期窗口长度
    :param long_window:  长期窗口长度
    :return:
    """
    if short_window <= 0 or long_window <= 0:
        raise ValueError("均线周期必须大于 0")

    if short_window >= long_window:
        raise ValueError("短均线周期必须小于长均线周期")

    df = df.copy()

    df["ma_short"] = df["close"].rolling(short_window).mean()
    df["ma_long"] = df["close"].rolling(long_window).mean()

    # 短期均线在长期均线上方时持有
    # 🔥注意: 这里的ma_short, ma_long都是float64, 跟mysql的decimal不一样, 这里可能会存在精度差异. 所以要减去一个微小差值避免出现微小的精度差异
    # 比如: date	         open	close	ma_short	       ma_long	signal
    #       2025/6/4	6.17	6.17	6.098000000000001	6.098	1
    # 这里ma_short-ma_long = 0, 信号应该为0, 但还因为精度的差异, 就会导致信号变为1.
    epsilon = 1e-8
    df["signal"] = (df["ma_short"] - df["ma_long"] > epsilon).astype(int)

    return df