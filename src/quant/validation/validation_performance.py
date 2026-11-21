#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/21 18:00
# @Author  : daniel
# @File    : validation_performance.py
# @Project : daniel_quant

"""
Description: 这个模块先实现两个功能：
1. 拼接所有测试期的每日收益。
2. 根据每日收益构造连续 OOS 净值，并计算整体绩效。
"""

import pandas as pd

from quant.backtest.performance import calculate_performance


# 注意，这里合并的是每日收益率，不是每轮的 NAV。
# OOS: Out-Of-Sample
def combine_oos_returns(
    test_results: dict[int, pd.DataFrame],
) -> pd.Series:
    """
    拼接所有 Walk-Forward 测试期的每日收益率。
    test_results:
        {
            1: 第1轮测试结果,
            2: 第2轮测试结果,
            ...
        }

    返回:
        按日期排序的 OOS 每日收益率 Series
    """
    if not test_results:
        raise ValueError("测试结果为空")

    return_list = []
    for round_number, result in sorted(test_results.items()):
        if "return" not in result.columns:
            raise ValueError(f"第 {round_number} 轮缺少 return 字段")

        # 只提取测试期每日收益率
        daily_returns = result["return"].copy()

        # 标记数据来自哪一轮，方便排查
        daily_returns.name = f"round_{round_number}"

        return_list.append(daily_returns)

    # 按时间顺序拼接
    oos_returns = pd.concat(return_list).sort_index()

    # 检查是否有重复日期
    if oos_returns.index.has_duplicates:
        duplicate_dates = oos_returns.index[oos_returns.index.duplicated()]
        raise ValueError(f"OOS 收益存在重复日期：{duplicate_dates.tolist()}")

    # 检查是否存在空值
    if oos_returns.isna().any():
        raise ValueError("OOS 每日收益存在 NaN，请检查回测结果")

    # 确保收益率是数值类型
    oos_returns = pd.to_numeric(oos_returns)

    # 检查收益率是否合法
    if (oos_returns < -1).any():
        raise ValueError("发现小于 -100% 的每日收益率")

    oos_returns.name = "return"
    return oos_returns


def calculate_oos_performance(
    oos_returns: pd.Series,
) -> tuple[pd.Series, dict]:
    """
    根据 OOS 每日收益率构建连续净值，并计算整体绩效。
    """
    if oos_returns.empty:
        raise ValueError("OOS 收益数据为空")
    if oos_returns.isna().any():
        raise ValueError("OOS 收益存在 NaN")

    # 初始净值
    initial_nav = pd.Series(
        [1.0],
        index=[oos_returns.index[0] - pd.Timedelta(days=1)],
        name="nav",
    )

    # 根据每日收益率计算净值
    daily_nav = (1 + oos_returns).cumprod()
    daily_nav.name = "nav"

    # 拼接初始净值和每日净值
    oos_nav = pd.concat([
        initial_nav, # 之前的收益是从第一天投入开始算的, 这里需要拼接个预热数据
        daily_nav,
    ])

    # 计算整体样本外绩效
    performance = calculate_performance(
        nav=oos_nav,
        returns=oos_returns,
        periods_per_year=252,
        risk_free_rate=0.02,
    )

    return oos_nav, performance
