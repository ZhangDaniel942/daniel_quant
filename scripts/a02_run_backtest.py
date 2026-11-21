#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 23:25
# @Author  : daniel
# @File    : a02_run_backtest_bak01.py
# @Project : daniel_quant

"""
Description: 完整策略回测流程
"""
import pandas as pd
import matplotlib.pyplot as plt

from data.processed.processed_data_config import processed_data_path
from quant.backtest.benchmark import calculate_benchmark_nav, calculate_relative_nav, calculate_excess_return
from quant.backtest.comparison import compare_strategies
from quant.backtest.optimization import run_parameter_experiments, print_risk_events, plot_risk_analysis, \
    run_ma_parameter_experiments
from quant.backtest.trade_ledger import generate_trade_ledger
from quant.risk.risk_management import check_drawdown_warning, calculate_risk_status, print_risk_summary
from quant.strategies.dual_ma import generate_signals
from quant.backtest.engine import run_backtest
from quant.backtest.performance import calculate_performance
from quant.utils.print_utils import pf
from quant.validation.validation_performance import combine_oos_returns, calculate_oos_performance
from quant.validation.walk_forward import generate_walk_forward_splits, run_walk_forward, build_oos_results, \
    calculate_annual_position
from reports.report_data_config import report_data_path


# ============================================================
# 主程序
# ============================================================
def main():

    # 0, 初始化参数
    symbol = "510300"
    initial_capital = 100_000
    commission_rate = 0.0003
    slippage_rate = 0.0002
    from_path = processed_data_path / f"sina_{symbol}.csv"
    # 因为我们有最长120天的长线均线计算, 所以需要预留120作为预热, 从第121天才开始正式的进行训练和测试
    WARMUP_PERIOD = 120

    pf("1. 读取全部行情数据")
    row_df = pd.read_csv(from_path, parse_dates=["date"])
    field_filtered_df = row_df[["date", "open", "close"]].set_index("date").sort_index()
    print(f"过滤字段统计结果如下: \n{field_filtered_df.count()}, \n开始时间: {field_filtered_df.index.min()}, 结束时间: {field_filtered_df.index.max()}")
    # 正式研究起点：第 121 个交易日
    research_start = field_filtered_df.index[WARMUP_PERIOD]
    print(f"原始数据起点：{field_filtered_df.index[0].date()}")
    print(f"正式研究起点：{research_start.date()}")
    print(f"预热交易日数量：{WARMUP_PERIOD}")

    pf("3, 开始 Walk-Forward 滚动前向回测")
    wf_results, wf_summary = run_walk_forward(
        df=field_filtered_df,
        train_years=5,
        test_years=1,
        step_years=1,
        initial_capital=100_000,
    )

    # 查看第一轮测试结果
    print("\n第一轮测试结果字段：")
    print(wf_results[1].columns.tolist())

    print("\n第一轮测试结果前5行：")
    print(wf_results[1].head())

    print("\n第一轮测试结果后5行：")
    print(wf_results[1].tail())

    # 检查每日收益率
    print("\n第一轮每日收益率：")
    print(wf_results[1]["return"].head())

    # 构建 OOS 连续净值
    oos_df = build_oos_results(wf_results)

    print("\n" + "=" * 60)
    print("OOS 连续净值结果")
    print("=" * 60)

    print(oos_df.head())
    print(oos_df.tail())

    print(f"\nOOS 开始日期：{oos_df.index.min().date()}")
    print(f"OOS 结束日期：{oos_df.index.max().date()}")
    print(f"OOS 总交易日：{len(oos_df)}")

    print(f"最终 OOS 净值：{oos_df['strategy_nav'].iloc[-1]:.4f}")

    print(
        f"累计收益率："
        f"{oos_df['strategy_nav'].iloc[-1] - 1:.2%}"
    )

    # ==================================================
    # 计算 510300 Buy & Hold 基准净值
    # ==================================================
    print("\n" + "=" * 60)
    print("计算 510300 Buy & Hold 基准")
    print("=" * 60)

    # 1. 获取与策略 OOS 完全相同的行情日期
    benchmark_df = field_filtered_df.loc[
        oos_df.index.min():oos_df.index.max(),
        ["open", "close"]
    ].copy()

    # 2. 计算买入并持有基准净值
    benchmark_nav = calculate_benchmark_nav(
        df=benchmark_df,
        initial_capital=100_000,
        commission_rate=0.0003,
        slippage_rate=0.0002,
    )

    # 3. 保存到 OOS 结果中
    oos_df["benchmark_nav"] = benchmark_nav

    # 4. 输出结果
    benchmark_return = benchmark_nav.iloc[-1] - 1
    print(f"基准开始日期：{benchmark_nav.index.min().date()}")
    print(f"基准结束日期：{benchmark_nav.index.max().date()}")
    print(f"基准交易日数量：{len(benchmark_nav)}")
    print(f"基准最终净值：{benchmark_nav.iloc[-1]:.4f}")
    print(f"基准累计收益率：{benchmark_return:.2%}")

    print("\n策略与基准对比：")
    print(oos_df[["strategy_nav", "benchmark_nav"]].head())
    print(oos_df[["strategy_nav", "benchmark_nav"]].tail())

    # 1. 计算相对净值
    relative_nav = calculate_relative_nav(
        strategy_nav=oos_df["strategy_nav"],
        benchmark_nav=benchmark_nav,
    )

    # 2. 计算累计超额收益
    excess_return = calculate_excess_return(
        strategy_nav=oos_df["strategy_nav"],
        benchmark_nav=benchmark_nav,
    )

    print("\n策略相对基准表现")
    print("-" * 50)

    print(f"最终相对净值：{relative_nav.iloc[-1]:.4f}")
    print(f"累计超额收益：{excess_return:.2%}")

    import matplotlib.pyplot as plt

    plt.figure(figsize=(14, 6))

    plt.plot(
        oos_df.index,
        oos_df["strategy_nav"],
        label="Walk-Forward Strategy",
    )

    plt.plot(
        benchmark_nav.index,
        benchmark_nav,
        label="510300 Buy & Hold",
    )

    plt.title("Walk-Forward Strategy vs Buy & Hold")
    plt.xlabel("Date")
    plt.ylabel("Net Asset Value")

    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()

    # ============================================================
    # 计算策略与基准绩效指标
    # ============================================================

    # 1. 构造策略净值序列
    # 在第一天实际净值之前，增加初始净值 1.0
    strategy_nav = pd.concat([
        pd.Series(
            [1.0],
            index=[oos_df.index[0] - pd.Timedelta(days=1)]
        ),
        oos_df["strategy_nav"]
    ])

    # 策略每日收益率
    strategy_returns = oos_df["strategy_return"]

    # 2. 构造基准净值序列
    benchmark_nav_full = pd.concat([
        pd.Series(
            [1.0],
            index=[benchmark_nav.index[0] - pd.Timedelta(days=1)]
        ),
        benchmark_nav
    ])

    # 基准每日收益率
    benchmark_returns = benchmark_nav_full.pct_change().dropna()

    # 3. 计算策略绩效
    strategy_performance = calculate_performance(
        nav=strategy_nav,
        returns=strategy_returns,
        periods_per_year=252,
        risk_free_rate=0.02,
    )

    # 4. 计算基准绩效
    benchmark_performance = calculate_performance(
        nav=benchmark_nav_full,
        returns=benchmark_returns,
        periods_per_year=252,
        risk_free_rate=0.02,
    )

    # 5. 输出结果
    print("\n" + "=" * 60)
    print("策略与 Buy & Hold 绩效指标对比")
    print("=" * 60)

    comparison = pd.DataFrame({
        "Walk-Forward Strategy": strategy_performance,
        "510300 Buy & Hold": benchmark_performance,
    })

    print(comparison)

    # ============================================================
    # 按自然年度统计策略与基准收益
    # ============================================================

    annual_returns = pd.DataFrame({
        "strategy": oos_df["strategy_return"],
        "benchmark": benchmark_returns,
    })

    annual_returns["year"] = annual_returns.index.year

    annual_performance = annual_returns.groupby("year").agg(
        strategy_return=("strategy", lambda x: (1 + x).prod() - 1),
        benchmark_return=("benchmark", lambda x: (1 + x).prod() - 1),
    )

    annual_performance["excess_return"] = (
            annual_performance["strategy_return"]
            - annual_performance["benchmark_return"]
    )

    print("\n年度收益对比")
    print("=" * 70)
    print(annual_performance.to_string(
        formatters={
            "strategy_return": "{:.2%}".format,
            "benchmark_return": "{:.2%}".format,
            "excess_return": "{:.2%}".format,
        }
    ))

    annual_position = calculate_annual_position(wf_results)

    print("\n年度仓位统计")
    print("=" * 70)

    print(
        annual_position.to_string(
            formatters={
                "average_position": "{:.2%}".format,
                "holding_ratio": "{:.2%}".format,
                "empty_ratio": "{:.2%}".format,
            }
        )
    )
    # # 检查 510300 原始收盘价的单日涨跌幅
    # close_return = row_df["close"].pct_change(fill_method=None)
    #
    # print("\n收盘价单日涨跌幅最大的日期：")
    # print(
    #     close_return.abs()
    #     .sort_values(ascending=False)
    #     .head(10)
    # )
    #
    # print("\n对应的原始收盘价：")
    # print(
    #     pd.DataFrame({
    #         "close": row_df["close"],
    #         "daily_return": close_return,
    #     })
    #     .loc[close_return.abs().nlargest(10).index]
    #     .sort_index()
    # )
    #
    # # 找出绝对涨跌幅最大的10个交易日
    # top_positions = (
    #     close_return.abs()
    #     .to_numpy()
    #     .argsort()[::-1][:10]
    # )
    #
    # print("行情数据索引类型：", type(row_df.index))
    # print("行情数据索引名称：", row_df.index.name)
    # print("行情数据字段：", row_df.columns.tolist())
    #
    # for pos in top_positions:
    #     start = max(0, pos - 1)
    #     end = min(len(row_df), pos + 2)
    #
    #     print("\n" + "=" * 60)
    #     print(f"异常波动位置：第 {pos} 行")
    #     print(f"单日涨跌幅：{close_return.iloc[pos]:.2%}")
    #
    #     print(
    #         row_df.iloc[start:end]
    #     )
    #
    # # 统一日期索引
    # check_df = row_df.copy()
    #
    # check_df["date"] = pd.to_datetime(check_df["date"])
    #
    # check_df = (
    #     check_df
    #     .sort_values("date")
    #     .set_index("date")
    # )
    #
    # # 计算收盘价涨跌幅
    # check_df["daily_return"] = (
    #     check_df["close"].pct_change(fill_method=None)
    # )
    #
    # # 排除 NaN，取绝对涨跌幅最大的10个交易日
    # top_dates = (
    #     check_df["daily_return"]
    #     .abs()
    #     .nlargest(10)
    #     .index
    # )
    #
    # print("最大涨跌幅对应的行情：")
    #
    # for date in top_dates:
    #     print("\n", "=" * 50)
    #     print(check_df.loc[date - pd.offsets.BDay(1):date + pd.offsets.BDay(1)])
    #
    # # 检查价格关系是否合理
    # invalid_ohlc = check_df[
    #     (check_df["low"] > check_df["open"]) |
    #     (check_df["low"] > check_df["close"]) |
    #     (check_df["high"] < check_df["open"]) |
    #     (check_df["high"] < check_df["close"]) |
    #     (check_df["high"] < check_df["low"])
    #     ]
    #
    # print("OHLC 异常数据数量：", len(invalid_ohlc))
    # print(invalid_ohlc.head(20))
    #
    # oos_check = check_df.loc["2017-11-20":"2026-11-19"]
    #
    # print("OOS 最大单日涨跌幅：")
    #
    # print(
    #     oos_check["daily_return"]
    #     .abs()
    #     .nlargest(10)
    # )



    # # # 第一轮训练区间：2012-11-20 - 2017-11-17
    # ma_results, ma_comparison = run_ma_parameter_experiments(
    #     df=field_filtered_df,
    #     train_start=research_start,
    #     train_end=research_start + pd.DateOffset(years=5)
    # )
    # print("\n第一轮参数优化结果：")
    # print(ma_comparison.to_string())


    # pf("2, 运行双均线策略生成信号")
    # # 测试参数组合 A
    # df_a = generate_signals(
    #     field_filtered_df,
    #     short_window=5,
    #     long_window=20,
    # )
    #
    # # 测试参数组合 B
    # df_b = generate_signals(
    #     field_filtered_df,
    #     short_window=10,
    #     long_window=30,
    # )
    #
    # print("参数组合 A：MA5 / MA20")
    # print(df_a[["close", "ma_short", "ma_long", "signal"]].tail())
    #
    # print("\n参数组合 B：MA10 / MA30")
    # print(df_b[["close", "ma_short", "ma_long", "signal"]].tail())


    # signal_df = generate_signals(
    #     field_filtered_df,
    #     short_window=5,
    #     long_window=20,
    # )
    # print("策略信号生成完成")
    # print("信号统计：")
    # print(signal_df["signal"].value_counts())
    #
    # pf("3, 生成训练周期")
    # splits = generate_walk_forward_splits(
    #     df=field_filtered_df,
    #     train_years=5,
    #     test_years=1,
    #     step_years=1,
    # )
    # for item in splits:
    #     print(f"第 {item['round']} 轮")
    #     print(f"训练：{item['train_start'].date()} "f"至 {item['train_end'].date()}")
    #     print(f"测试：{item['test_start'].date()} "f"至 {item['test_end'].date()}")
    #     print(f"训练交易日：{len(item['train'])}，"f"测试交易日：{len(item['test'])}")
    #
    # pf("3, 开始 Walk-Forward 滚动前向回测")
    # wf_results, wf_summary = run_walk_forward(
    #     df=signal_df,
    #     train_years=5,
    #     test_years=1,
    #     step_years=1,
    #     initial_capital=100_000,
    # )
    #
    # # ==========================================
    # # 2. 拼接所有样本外每日收益
    # # ==========================================
    # oos_returns = combine_oos_returns(wf_results)
    # print("\n" + "=" * 50)
    # print("OOS 每日收益拼接完成")
    # print("=" * 50)
    #
    # print(f"数据起始日期：{oos_returns.index.min().date()}")
    # print(f"数据结束日期：{oos_returns.index.max().date()}")
    # print(f"OOS 交易日数量：{len(oos_returns)}")
    #
    # # ==========================================
    # # 3. 构建连续 OOS 净值
    # # ==========================================
    # oos_nav, oos_performance = calculate_oos_performance(oos_returns)
    # print("\n" + "=" * 50)
    # print("整体样本外绩效")
    # print("=" * 50)
    # for key, value in oos_performance.items():
    #     if isinstance(value, (int, float)):
    #         print(f"{key:<20}: {value:.4f}")
    #     else:
    #         print(f"{key:<20}: {value}")
    #
    # # ==========================================
    # # 4. 输出净值序列
    # # ==========================================
    # print("\nOOS 净值最后 10 行：")
    # print(oos_nav.tail(10))
    #
    #
    #
    #
    #
    # import matplotlib.pyplot as plt
    #
    # # 计算整体回撤
    # running_max = oos_nav.cummax()
    # oos_drawdown = oos_nav / running_max - 1
    #
    # # 创建画布
    # fig, axes = plt.subplots(
    #     2,
    #     1,
    #     figsize=(14, 9),
    #     sharex=True,
    # )
    #
    # # 净值曲线
    # axes[0].plot(
    #     oos_nav.index,
    #     oos_nav.values,
    #     label="OOS NAV",
    # )
    #
    # axes[0].set_title("Walk-Forward Out-of-Sample NAV")
    # axes[0].set_ylabel("NAV")
    # axes[0].grid(True)
    # axes[0].legend()
    #
    # # 回撤曲线
    # axes[1].plot(
    #     oos_drawdown.index,
    #     oos_drawdown.values,
    #     label="OOS Drawdown",
    # )
    #
    # axes[1].set_title("OOS Drawdown")
    # axes[1].set_ylabel("Drawdown")
    # axes[1].grid(True)
    # axes[1].legend()
    #
    # plt.tight_layout()
    # plt.show()
    #
    # # ==========================================
    # # OOS 数据完整性检查
    # # ==========================================
    #
    # print("\n" + "=" * 50)
    # print("OOS 数据完整性检查")
    # print("=" * 50)
    #
    # # 1. 每轮测试数据量
    # for round_number, result in wf_results.items():
    #     print(
    #         f"第 {round_number:2d} 轮："
    #         f"{len(result):4d} 行 | "
    #         f"{result.index.min().date()} 至 "
    #         f"{result.index.max().date()} | "
    #         f"收益率：{(1 + result['return']).prod() - 1:.4%}"
    #     )
    #
    # # 2. 所有轮次的测试行数
    # total_test_days = sum(
    #     len(result) for result in wf_results.values()
    # )
    #
    # print(f"\n各轮测试行数合计：{total_test_days}")
    # print(f"OOS 收益行数：{len(oos_returns)}")
    #
    # # 3. 检查拼接前后行数是否一致
    # assert total_test_days == len(oos_returns)
    #
    # # 4. 检查最终净值是否等于每日收益复利结果
    # expected_final_nav = (1 + oos_returns).prod()
    #
    # print(f"\n复利计算最终净值：{expected_final_nav:.8f}")
    # print(f"OOS 净值最终值：{oos_nav.iloc[-1]:.8f}")
    #
    # assert abs(
    #     expected_final_nav - oos_nav.iloc[-1]
    # ) < 1e-10
    #
    # # 5. 检查最后 10 天的收益
    # print("\n最后 10 天每日收益：")
    # print(oos_returns.tail(10))
    #
    # print("\nOOS 数据完整性检查通过")
    #
    # last_result = wf_results[10]
    #
    # print("\n最后 10 个交易日的交易状态：")
    #
    # print(
    #     last_result[
    #         ["signal", "action", "position", "return"]
    #     ].tail(10)
    # )

if __name__ == "__main__":
    main()
