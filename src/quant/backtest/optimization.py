#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/21 14:21
# @Author  : daniel
# @File    : optimization.py
# @Project : daniel_quant

"""
Description: 优化模块负责组织实验，
             回测引擎负责执行交易，
             绩效模块负责计算指标。
             批量传入参数，运行多组回测
             不应该自己计算收益率或最大回撤，也不应该复制交易逻辑。它只负责组织实验。
"""
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from quant.backtest.engine import run_backtest
from quant.backtest.comparison import compare_strategies
from quant.backtest.performance import calculate_performance
from quant.strategies.dual_ma import generate_signals

# 双均线参数候选组合
PARAMETER_CANDIDATES = [
    (5, 20),
    (5, 30),
    (10, 20),
    (10, 30),
    (10, 60),
    (20, 60),
    (20, 120),
]


# 组织一次完整回测, 它本身并不跑回测, 内部调用engine进行处理
def run_backtest_pipeline(
    signal_df: pd.DataFrame,
    start_date: str,
    end_date: str,
    initial_capital: float = 100_000,
) -> tuple[pd.DataFrame, dict]:
    """
    对指定时间区间执行策略回测。
    start_date: 正式回测开始日期，包含
    end_date: 正式回测结束日期，不包含
    """
    # 1. 选取正式回测区间
    mask = ((signal_df.index >= start_date) & (signal_df.index < end_date))
    period_df = signal_df.loc[mask].copy()

    if period_df.empty:
        raise ValueError("正式回测区间没有数据")

    # 2. 获取正式区间前一个交易日，作为预热行
    warmup_df = signal_df.loc[signal_df.index < period_df.index[0]].tail(1)
    if warmup_df.empty:
        raise ValueError("正式回测区间之前没有预热数据")

    # 3. 拼接预热行和正式回测数据
    backtest_df = pd.concat([warmup_df, period_df])

    # 4. 调用引擎: 执行回测
    result = run_backtest(
        df=backtest_df,
        initial_capital=initial_capital,
        enable_risk_control=False,
    )

    # 5. 只保留正式回测期间的数据
    period_result = result.loc[period_df.index].copy()

    if not period_result.index.equals(period_df.index):
        raise ValueError("回测结果日期与正式回测日期不一致")

    # 6. 计算正式区间绩效
    performance = calculate_performance(
        nav=result["nav"],
        returns=period_result["return"],
        periods_per_year=252,
        risk_free_rate=0.02,
    )

    return period_result, performance



def run_ma_parameter_experiments(
    df: pd.DataFrame,
    train_start: str, # 训练开始时间
    train_end: str,   # 训练结束时间
    initial_capital= 100_000,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """
    批量测试不同双均线参数在训练集上的表现。
    train_end 为不包含的结束日期。
    """
    if df.empty:
        raise ValueError("行情数据为空")

    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("行情数据必须使用 DatetimeIndex")

    if df.index.has_duplicates:
        raise ValueError("行情数据存在重复日期")

    df = df.sort_index().copy()

    # train_start = pd.Timestamp(train_start)
    # train_end = pd.Timestamp(train_end)

    if train_start > train_end:
        raise ValueError("训练开始日期必须早于结束日期")

    # # 找到训练区间
    # train_mask = ((df.index >= train_start) & (df.index <= train_end))
    #
    # if not train_mask.any():
    #     raise ValueError("训练区间没有行情数据")

    # 训练区间之前最后一个交易日，作为 warm-up
    # warmup_df = df.loc[df.index < train_start].tail(1)
    # # # todo: 第一个训练区间不就会报错吗
    # if warmup_df.empty:
    #     print("训练区间之前没有 warm-up 行情数据")

    # 训练开始前最后一个交易日
    # 作用：让正式训练第一天能够执行前一天收盘产生的信号
    warmup_index = df.index[df.index < train_start][-1:]
    if len(warmup_index) == 0:
        raise ValueError("训练区间之前没有历史数据，无法执行首日信号")

    results = {}
    metrics_list = []

    # 依次测试不同参数
    for short_window, long_window in PARAMETER_CANDIDATES:

        name = f"MA{short_window}/MA{long_window}"
        print(f"\n开始训练参数组合：{name}")

        # 在完整历史行情上计算均线和信号
        # rolling 只使用当前及过去的数据，不使用未来数据
        signal_df = generate_signals(
            df,
            short_window=short_window,
            long_window=long_window,
        )

        period_result, performance = run_backtest_pipeline(signal_df=signal_df,
                                                           start_date=train_start,
                                                           end_date=train_end,
                                                           initial_capital=initial_capital)


        # # 取训练区间
        # train_df = signal_df.loc[train_mask].copy()
        # # 取训练开始前最后一个交易日的信号
        # warmup_df = signal_df.loc[warmup_index].copy()
        #
        # # 拼接前一个交易日和正式训练数据
        # experiment_df = pd.concat([
        #     warmup_df,
        #     train_df,
        # ])
        #
        # # 独立运行回测，关闭风控
        # result = run_backtest(
        #     df=experiment_df,
        #     enable_risk_control=False,
        # )
        #
        # # 只保存正式训练期结果，不保存预热行
        # train_result = result.loc[train_df.index].copy()
        # results[name] = train_result
        #
        # # 绩效计算：
        # # NAV 包含预热行的初始净值 + 正式训练期所有净值
        # # Returns 只包含正式训练期收益
        # performance_nav = result["nav"]
        # performance_returns = train_result["return"]
        # performance = calculate_performance(
        #     nav=performance_nav,
        #     returns=performance_returns,
        #     periods_per_year=252,
        #     risk_free_rate=0.02,
        # )

        results[name] = period_result
        performance["short_window"] = short_window
        performance["long_window"] = long_window

        metrics_list.append({
            "name": name,
            **performance,
        })

        print(
            f"{name} | "
            f"CAGR: {performance['cagr']:.2%} | "
            f"最大回撤: {performance['max_drawdown']:.2%}"
        )

    # 整理绩效排名表
    comparison = pd.DataFrame(metrics_list)
    comparison = comparison.set_index("name")

    # 暂时按照 CAGR 从高到低排名
    comparison = comparison.sort_values(
        by="cagr",
        ascending=False,
    )

    return results, comparison




def calculate_risk_statistics(result: pd.DataFrame) -> dict:
    """
    统计风控触发次数、解除次数和持续天数。
    """
    required_columns = {
        "risk_status",
        "risk_status_next",
    }

    missing_columns = required_columns - set(result.columns)

    if missing_columns:
        raise ValueError(f"回测结果缺少风控字段：{missing_columns}")

    risk_status = result["risk_status"].astype(bool)
    risk_status_next = result["risk_status_next"].astype(bool)

    # 从未触发 -> 触发
    trigger_count = int(
        ((~risk_status) & risk_status_next).sum()
    )

    # 从已触发 -> 解除
    resume_count = int(
        (risk_status & (~risk_status_next)).sum()
    )

    # 实际处于风控状态的交易日
    risk_days = int(risk_status.sum())

    return {
        "risk_trigger_count": trigger_count,
        "risk_resume_count": resume_count,
        "risk_days": risk_days,
    }


def run_parameter_experiments(
    df: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """
    批量运行不同风控参数的回测实验。
    """
    # 不同的风控参数
    parameter_sets = [
        {
            "name": "触发6%_解除3%",
            "stop_drawdown": 0.06,
            "resume_drawdown": 0.03,
        },
        {
            "name": "触发8%_解除5%",
            "stop_drawdown": 0.08,
            "resume_drawdown": 0.05,
        },
        {
            "name": "触发10%_解除5%",
            "stop_drawdown": 0.10,
            "resume_drawdown": 0.05,
        },
        {
            "name": "触发12%_解除6%",
            "stop_drawdown": 0.12,
            "resume_drawdown": 0.06,
        },
    ]

    results = {}

    # 先运行无风控基准组
    print("\n开始运行：关闭风控")

    results["关闭风控"] = run_backtest(
        df=df,
        enable_risk_control=False,
    )

    # 依次运行不同风控参数
    for params in parameter_sets:

        name = params["name"]

        print(f"\n开始运行：{name}")

        result = run_backtest(
            df=df,
            enable_risk_control=True,
            stop_drawdown=params["stop_drawdown"],
            resume_drawdown=params["resume_drawdown"],
        )

        results[name] = result

    # 统一计算绩效指标
    comparison = compare_strategies(
        results=results,
        periods_per_year=252,
        risk_free_rate=0.02,
    )

    # 补充风控统计
    for name, result in results.items():

        risk_stats = calculate_risk_statistics(result)

        for metric_name, metric_value in risk_stats.items():
            comparison.loc[metric_name, name] = metric_value

    return results, comparison




def plot_risk_analysis(
    result: pd.DataFrame,
    title: str = "风控分析",
) -> None:
    """
    绘制风控分析图：
    1. ETF收盘价
    2. 策略净值
    3. 回撤曲线
    4. 实际仓位及风控状态
    """

    required_columns = {
        "close",
        "nav",
        "drawdown",
        "position",
        "risk_status",
        "risk_status_next",
    }

    missing_columns = required_columns - set(result.columns)

    if missing_columns:
        raise ValueError(f"回测结果缺少字段：{missing_columns}")

    if result.empty:
        raise ValueError("回测结果为空")

    # 日期索引
    dates = pd.to_datetime(result.index)

    # 风控状态：当天开盘时实际使用的风控状态
    risk_status = result["risk_status"].astype(bool)

    # 找到风控触发日期
    trigger_rows = result[
        (~result["risk_status"].astype(bool))
        & result["risk_status_next"].astype(bool)
    ]

    # 找到风控解除日期
    resume_rows = result[
        result["risk_status"].astype(bool)
        & (~result["risk_status_next"].astype(bool))
    ]

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(15, 12),
        sharex=True,
    )

    # ---------------------------------
    # 1. ETF收盘价
    # ---------------------------------
    axes[0].plot(
        dates,
        result["close"],
        label="ETF Close",
    )

    axes[0].set_title("ETF Price")
    axes[0].set_ylabel("Price")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    # ---------------------------------
    # 2. 策略净值
    # ---------------------------------
    axes[1].plot(
        dates,
        result["nav"],
        label="Strategy NAV",
    )

    axes[1].axhline(
        1.0,
        linestyle="--",
        alpha=0.6,
        label="Initial NAV",
    )

    axes[1].set_title("Strategy NAV")
    axes[1].set_ylabel("NAV")
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    # ---------------------------------
    # 3. 回撤曲线
    # ---------------------------------
    axes[2].plot(
        dates,
        result["drawdown"] * 100,
        label="Drawdown",
    )

    axes[2].axhline(
        -6,
        linestyle="--",
        alpha=0.6,
        label="-6%",
    )

    axes[2].axhline(
        -8,
        linestyle=":",
        alpha=0.6,
        label="-8%",
    )

    axes[2].set_title("Drawdown")
    axes[2].set_ylabel("Drawdown (%)")
    axes[2].legend()
    axes[2].grid(alpha=0.3)

    # 标记触发日期
    for date in trigger_rows.index:
        axes[2].axvline(
            pd.to_datetime(date),
            color="red",
            linestyle="--",
            alpha=0.7,
        )

    # 标记解除日期
    for date in resume_rows.index:
        axes[2].axvline(
            pd.to_datetime(date),
            color="green",
            linestyle="--",
            alpha=0.7,
        )

    # ---------------------------------
    # 4. 实际仓位 + 风控状态
    # ---------------------------------
    axes[3].plot(
        dates,
        result["position"] * 100,
        label="Actual Position",
    )

    # 风控期间背景标记
    risk_values = risk_status.to_numpy()

    if risk_values.any():
        starts = np.where(
            risk_values & ~np.r_[False, risk_values[:-1]]
        )[0]

        ends = np.where(
            risk_values & ~np.r_[risk_values[1:], False]
        )[0]

        for start, end in zip(starts, ends):
            axes[3].axvspan(
                dates[start],
                dates[end],
                color="red",
                alpha=0.12,
            )

    axes[3].set_title("Actual Position (Red = Risk Control)")
    axes[3].set_ylabel("Position (%)")
    axes[3].set_ylim(-5, 105)
    axes[3].legend()
    axes[3].grid(alpha=0.3)

    plt.suptitle(title, fontsize=15)
    plt.tight_layout()
    plt.show()



def print_risk_events(results: dict[str, pd.DataFrame]) -> None:
    """
    打印每组实验的风控触发和解除日期。
    """

    for name, result in results.items():

        risk_status = result["risk_status"].astype(bool)
        risk_status_next = result["risk_status_next"].astype(bool)

        trigger_rows = result[
            (~risk_status) & risk_status_next
        ]

        resume_rows = result[
            risk_status & (~risk_status_next)
        ]

        print(f"\n{name}")
        print("-" * 50)

        print("触发日期：")
        if trigger_rows.empty:
            print("无")
        else:
            print(trigger_rows[["nav", "drawdown"]].to_string())

        print("解除日期：")
        if resume_rows.empty:
            print("无")
        else:
            print(resume_rows[["nav", "drawdown"]].to_string())
