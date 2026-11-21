#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/21 14:46
# @Author  : daniel
# @File    : walk_forward.py
# @Project : daniel_quant

"""
Description: walk_forward.py 将负责：
                    1. 按时间切分训练集和测试集。
                    2. 在训练集上研究策略参数。
                    3. 使用训练阶段选出的参数运行后续测试集。
                    4. 汇总多轮测试结果。
                    5. 比较各个时间窗口的收益、回撤、夏普和交易次数。

                    第一轮 2012—2016 训练 -> 2017 测试
                    第二轮 2012—2017 训练 -> 2018 测试
                    第三轮 2012—2018 训练 -> 2019 测试
                    每一轮只使用当时已经发生的历史数据来研究策略，再测试后面的时间段。
"""
import pandas as pd

from quant.backtest.optimization import run_ma_parameter_experiments, run_backtest_pipeline
from quant.strategies.dual_ma import generate_signals

def generate_walk_forward_splits(
    df: pd.DataFrame,
    train_years: int = 5,
    test_years: int = 1,
    step_years: int = 1,
    warmup_period: int = 120,
) -> list[dict]:
    """
        按时间顺序生成 Walk-Forward 训练集和测试集。
        前 warmup_period 个交易日只用于指标预热，
        不参与正式训练和测试。
        """
    if df.empty:
        raise ValueError("行情数据为空")

    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("df.index 必须是 DatetimeIndex")

    if train_years <= 0 or test_years <= 0 or step_years <= 0:
        raise ValueError("时间窗口参数必须大于 0")

    if warmup_period < 0:
        raise ValueError("warmup_period 不能小于 0")

    df = df.sort_index().copy()

    if df.index.has_duplicates:
        raise ValueError("行情数据存在重复日期")

    if len(df) <= warmup_period:
        raise ValueError("行情数据不足，无法完成预热")

    # 正式研究起点：跳过前 warmup_period 个交易日
    first_date = df.index[warmup_period]
    last_date = df.index.max()
    print(f"原始数据起点：{df.index[0].date()}")
    print(f"正式研究起点：{first_date.date()}")
    print(f"预热交易日数量：{warmup_period}")

    splits = []
    round_number = 1
    while True:
        # 训练窗口起点
        train_start = (first_date + pd.DateOffset(years=(round_number - 1) * step_years))
        # 测试窗口起点
        test_start = train_start + pd.DateOffset(years=train_years)
        # 测试窗口终点
        test_end = test_start + pd.DateOffset(years=test_years)

        if test_start > last_date:
            break

        # 训练数据：[train_start, test_start)
        train_df = df.loc[(df.index >= train_start) & (df.index < test_start)].copy()
        # 测试数据：[test_start, test_end)
        test_df = df.loc[(df.index >= test_start)& (df.index < test_end)].copy()

        if train_df.empty or test_df.empty:
            break

        splits.append({
            "round": round_number,
            "train": train_df,
            "test": test_df,
            "train_start": train_df.index.min(),
            "train_end": train_df.index.max(),  # 这个是包含的
            "test_start": test_df.index.min(),
            "test_end": test_df.index.max(),
        })

        round_number += 1

    return splits


# 现在训练集上跑不同的参数, 选出结果最好的一组
# 然后用这组在测试集上跑, 看看结果
def run_walk_forward(
    df: pd.DataFrame,
    train_years: int = 5,
    test_years: int = 1,
    step_years: int = 1,
    initial_capital: float = 100_000,
    warmup_period: int = 120,
) -> tuple[dict, pd.DataFrame]:

    """
    固定策略的 Walk-Forward 滚动前向回测。
    每轮：
    1. 使用训练集比较不同 MA 参数
    2. 选择训练表现最好的参数
    3. 使用选出的参数测试未来一年
    4. 测试期间不再调整参数
    """
    splits = generate_walk_forward_splits(
        df=df,
        train_years=train_years,
        test_years=test_years,
        step_years=step_years,
        warmup_period=warmup_period,
    )

    if not splits:
        raise ValueError("没有生成有效的训练/测试窗口")

    # 检查数据
    df = df.sort_index().copy()

    if df.index.has_duplicates:
        raise ValueError("行情数据存在重复日期")


    results = {}
    summary_rows = []
    for round_item in splits:
        round_number = round_item["round"]

        # 后续会用到统计训练天数和测试天数
        train_df = round_item["train"]
        test_df = round_item["test"]

        print("\n" + "=" * 60)
        print(f"开始第 {round_number} 轮滚动参数优化")
        print("=" * 60)

        # --------------------------------------------------
        # 第一步：训练集参数优化
        # --------------------------------------------------
        print("\n第一步：训练集参数优化")
        # 执行训练集回测, 里面会在不同的参数上进行训练集回测, 选出最好的一个
        _, comparison = run_ma_parameter_experiments(
            df=df,
            train_start=round_item["train_start"],
            train_end=round_item["test_start"],
        )
        if comparison.empty:
            raise ValueError(f"第 {round_number} 轮没有有效的参数优化结果")

        # 选择训练集表现最好的参数
        best_name = comparison.index[0]
        best_row = comparison.iloc[0]

        best_short = int(best_row["short_window"])
        best_long = int(best_row["long_window"])

        print(f"\n第 {round_number} 轮选出的参数：{best_name}")
        print(f"训练期 CAGR：{best_row['cagr']:.2%}")
        print(f"训练期最大回撤：{best_row['max_drawdown']:.2%}")
        print(f"训练期 Sharpe：{best_row['sharpe']:.4f}")

        # --------------------------------------------------
        # 第二步：使用选出的参数生成完整历史信号
        # --------------------------------------------------
        print("\n第二步：生成测试期信号")
        # 前面是训练, 这里就是在测试数据上重新再验证
        signal_df = generate_signals(
            df,
            short_window=best_short,
            long_window=best_long,
        )

        # 执行测试集回测
        period_result, performance = run_backtest_pipeline(signal_df=signal_df,
                                                           start_date=round_item["test_start"],
                                                           end_date=round_item["test_end"] + pd.Timedelta(days=1),
                                                           initial_capital=100_000)

        # --------------------------------------------------
        # 第六步：统计测试期交易
        # --------------------------------------------------
        buy_count = int((period_result["action"] == "BUY").sum())

        sell_count = int((period_result["action"] == "SELL").sum())

        # --------------------------------------------------
        # 第七步：整理本轮结果
        # --------------------------------------------------
        performance.update({

            "round": round_number,

            # 训练窗口
            "train_start": round_item["train_start"],
            "train_end": round_item["train_end"],

            # 测试窗口
            "test_start": round_item["test_start"],
            "test_end": round_item["test_end"],

            "train_days": len(train_df),
            "test_days": len(test_df),

            # 本轮训练选出的参数
            "best_parameter": best_name,
            "short_window": best_short,
            "long_window": best_long,

            # 训练期表现
            "train_cagr": best_row["cagr"],
            "train_max_drawdown": best_row["max_drawdown"],
            "train_sharpe": best_row["sharpe"],

            # 测试期交易次数
            "buy_count": buy_count,
            "sell_count": sell_count,
            "action_days": buy_count + sell_count,
        })

        # 保存正式测试期结果
        results[round_number] = period_result.copy()
        summary_rows.append(performance)

        print(
            f"\n第 {round_number} 轮完成 | "
            f"参数：{best_name} | "
            f"OOS收益率：{performance['total_return']:.2%} | "
            f"OOS CAGR：{performance['cagr']:.2%} | "
            f"OOS最大回撤：{performance['max_drawdown']:.2%}"
        )

        # --------------------------------------------------
        # 第八步：汇总所有轮次
        # --------------------------------------------------

    summary = pd.DataFrame(summary_rows)
    return results, summary



def build_oos_results(results: dict) -> pd.DataFrame:
    """
    拼接每轮样本外收益率，构建分段 OOS 净值。
    Parameters
    ----------
    results : dict
        Walk-Forward 每轮测试期的回测结果。
    Returns
    -------
    pd.DataFrame
        包含每日策略收益率和连续复利净值。
    """
    if not results:
        raise ValueError("Walk-Forward 测试结果为空")

    # 1. 提取每轮测试期的每日收益率
    return_list = []
    for round_number, period_result in results.items():
        if "return" not in period_result.columns:
            raise ValueError(f"第 {round_number} 轮缺少 return 字段")
        daily_return = period_result["return"].copy()
        return_list.append(daily_return)

    # 2. 拼接所有轮次的每日收益率
    # 这里不是已经是dataframe了吗
    oos_return = pd.concat(return_list).sort_index()

    # 3. 检查日期是否重复
    if oos_return.index.has_duplicates:
        raise ValueError("OOS 收益率存在重复日期")

    # 4. 检查收益率是否存在空值
    if oos_return.isna().any():
        raise ValueError("OOS 收益率存在 NaN")

    # 5. 构建 OOS 结果
    oos_df = pd.DataFrame(index=oos_return.index)

    oos_df["strategy_return"] = oos_return

    # 6. 根据每日收益率计算连续复利净值
    oos_df["strategy_nav"] = (1 + oos_df["strategy_return"]).cumprod()

    return oos_df


def calculate_annual_position(results: dict) -> pd.DataFrame:
    """
    统计 Walk-Forward 测试期间每年的持仓情况。
    """
    if not results:
        raise ValueError("Walk-Forward 测试结果为空")

    position_list = []
    for round_number, period_result in results.items():

        if "position" not in period_result.columns:
            raise ValueError(
                f"第 {round_number} 轮缺少 position 字段"
            )

        position = period_result["position"].copy()
        position_list.append(position)

    position_series = pd.concat(position_list).sort_index()

    if position_series.index.has_duplicates:
        raise ValueError("持仓数据存在重复日期")

    position_df = pd.DataFrame({
        "position": position_series
    })

    position_df["year"] = position_df.index.year

    annual_position = position_df.groupby("year").agg(
        average_position=("position", "mean"),
        full_position_days=(
            "position",
            lambda x: (x >= 0.99).sum()
        ),
        empty_position_days=(
            "position",
            lambda x: (x <= 0.01).sum()
        ),
        trading_days=("position", "count"),
    )

    annual_position["holding_ratio"] = (
        annual_position["average_position"]
    )

    annual_position["empty_ratio"] = (
        annual_position["empty_position_days"]
        / annual_position["trading_days"]
    )

    return annual_position