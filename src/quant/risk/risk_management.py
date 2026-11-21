#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/21 12:39
# @Author  : daniel
# @File    : risk_management.py
# @Project : daniel_quant

"""
Description: 风险控制
"""


import pandas as pd


def calculate_max_drawdown(
    nav: pd.Series,
) -> tuple[float, pd.Series]:
    """
    Calculate maximum drawdown and drawdown series.
    最大回撤函数
    """

    # 1. Calculate historical running maximum
    running_max = nav.cummax()

    # 2. Calculate drawdown from historical peak
    drawdown = nav / running_max - 1

    # 3. Get maximum drawdown magnitude
    max_drawdown = -drawdown.min()

    return max_drawdown, drawdown


def check_drawdown_warning(
    drawdown: pd.Series,
    warning_level: float = 0.05,
    danger_level: float = 0.08,
    stop_level: float = 0.10,
) -> pd.DataFrame:
    """
    根据每日回撤判断风险等级。
    drawdown 使用负数表示回撤。
    """

    result = pd.DataFrame(index=drawdown.index)
    result["drawdown"] = drawdown
    result["risk_level"] = "NORMAL"

    result.loc[
        drawdown <= -warning_level,
        "risk_level"
    ] = "WARNING"

    result.loc[
        drawdown <= -danger_level,
        "risk_level"
    ] = "DANGER"

    result.loc[
        drawdown <= -stop_level,
        "risk_level"
    ] = "STOP"

    return result



def calculate_risk_status(
    drawdown: pd.Series,
    stop_level: float = 0.10,
    resume_level: float = 0.05,
) -> pd.Series:
    """
    根据回撤计算风控状态。
    实际量化系统中，可以使用滞回机制（Hysteresis）：
        - 回撤达到 10%：进入风控状态。
        - 回撤恢复到 5% 以内：解除风控状态。
    True  = 禁止新增买入
    False = 允许正常交易
    """
    risk_status = []
    stopped = False

    for dd in drawdown:

        # 触发风控
        if not stopped and dd <= -stop_level:
            stopped = True

        # 解除风控
        elif stopped and dd >= -resume_level:
            stopped = False

        risk_status.append(stopped)

    return pd.Series(
        risk_status,
        index=drawdown.index,
        name="risk_status",
    )


def print_risk_summary(result, name):
    print(f"\n{name}")
    print("-" * 40)

    if "risk_status_next" not in result.columns:
        print("结果中没有 risk_status_next 字段")
        return

    trigger_count = (
        (result["risk_status"] == False)
        & (result["risk_status_next"] == True)
    ).sum()

    resume_count = (
        (result["risk_status"] == True)
        & (result["risk_status_next"] == False)
    ).sum()

    risk_days = result["risk_status"].sum()

    print(f"风控触发次数：{trigger_count}")
    print(f"风控解除次数：{resume_count}")
    print(f"风控持续天数：{risk_days}")
