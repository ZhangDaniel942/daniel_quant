#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/21 13:42
# @Author  : daniel
# @File    : comparison.py
# @Project : daniel_quant

"""
Description: 专门负责策略结果比较，不负责执行交易。
"""
import pandas as pd

from quant.backtest.performance import calculate_performance

def calculate_strategy_metrics(
    result: pd.DataFrame,
    periods_per_year: int = 252,
    risk_free_rate: float = 0.02,
) -> dict:
    """
    计算单个策略的绩效指标。
    具体指标计算交给 performance.py。
    """
    if result.empty:
        raise ValueError("回测结果不能为空")

    required_columns = {"nav", "return", "action"}
    missing_columns = required_columns - set(result.columns)

    if missing_columns:
        raise ValueError(f"回测结果缺少字段：{missing_columns}")

    performance = calculate_performance(
        nav=result["nav"],
        returns=result["return"],
        periods_per_year=periods_per_year,
        risk_free_rate=risk_free_rate,
    )

    # 补充交易统计
    buy_count = int((result["action"] == "BUY").sum())
    sell_count = int((result["action"] == "SELL").sum())

    performance.update({
        "buy_count": buy_count,
        "sell_count": sell_count,
        "action_days": buy_count + sell_count,
    })

    return performance


def compare_strategies(
    results: dict[str, pd.DataFrame],
    periods_per_year: int = 252,
    risk_free_rate: float = 0.02,
) -> pd.DataFrame:
    """
    比较多组策略的绩效。
    """

    if not results:
        raise ValueError("至少需要提供一组回测结果")

    metrics = {}

    for strategy_name, result in results.items():
        metrics[strategy_name] = calculate_strategy_metrics(
            result=result,
            periods_per_year=periods_per_year,
            risk_free_rate=risk_free_rate,
        )

    comparison = pd.DataFrame(metrics)

    return comparison
