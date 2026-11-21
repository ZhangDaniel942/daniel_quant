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
from quant.backtest.optimization import run_parameter_experiments, print_risk_events, plot_risk_analysis
from quant.backtest.trade_ledger import generate_trade_ledger
from quant.risk.risk_management import check_drawdown_warning, calculate_risk_status, print_risk_summary
from quant.strategies.dual_ma import generate_signals
from quant.backtest.engine import run_backtest
from quant.backtest.performance import calculate_performance
from quant.utils.print_utils import pf
from reports.report_data_config import report_data_path

# ============================================================
# 1. 路径配置
# ============================================================

# 输出
REPORT_DIR = report_data_path

# ============================================================
# 2. 加载行情数据
# ============================================================
def load_data(symbol):
    # 输入
    DATA_PATH = processed_data_path / f"sina_{symbol}.csv"
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"行情文件不存在：{DATA_PATH}")
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    required_columns = {"open", "close"}

    if not required_columns.issubset(df.columns):
        raise ValueError(f"缺少行情字段：{required_columns - set(df.columns)}")

    df = df[["date", "open", "close"]].copy()
    # 建议统一使用日期索引并排序
    # 不要删除日期, 后续还需要用
    df = df.set_index("date", drop=False).sort_index()
    print("=" * 50)
    print("行情数据加载成功")
    print("=" * 50)

    print(f"数据起始日期：{df.index.min()}")
    print(f"数据结束日期：{df.index.max()}")
    print(f"数据总行数：{len(df)}")

    return df

# ============================================================
# 3. 生成策略信号
# ============================================================
def generate_strategy(df):
    df = generate_signals(
        df,
        short_window=5,
        long_window=20,
    )
    print("\n策略信号生成完成")
    print("信号统计：")
    print(df["signal"].value_counts())

    return df

# ============================================================
# 4. 执行回测
# ============================================================
def execute_backtest(df, initial_capital, commission_rate, slippage_rate, max_position=1.0, max_position_change=0.1, lot_size=100, enable_risk_control = True, stop_drawdown=0.10,  resume_drawdown=0.05,):
    result = run_backtest(
        df,
        initial_capital=initial_capital,
        commission_rate=commission_rate,
        slippage_rate=slippage_rate,
        max_position=max_position,
        max_position_change=max_position_change,
        lot_size=lot_size,
        enable_risk_control=enable_risk_control,
        stop_drawdown=stop_drawdown,   # 临时改为 9%
        resume_drawdown=resume_drawdown,
    )

    print("\n回测执行完成")
    print("交易统计：")
    print(result["action"].value_counts())
    return result

# ============================================================
# 5. 绩效分析
# ============================================================
def analyze_performance(result):
    metrics = calculate_performance(
        result["nav"],
        returns=result["return"],
    )
    return metrics

# ============================================================
# 6. 绘制净值和回撤曲线
# ============================================================
def plot_result(result):

    nav = result["nav"]
    drawdown = nav / nav.cummax() - 1

    fig, axes = plt.subplots(3,1,figsize=(20, 15),sharex=True,)

    # 净值曲线
    axes[0].plot(result.index,nav,label="Dual MA Strategy", color="r")
    axes[0].plot(result.index,result["benchmark_nav"],label="直接买入策略",)
    axes[0].axhline(1.0,linestyle="--",label="Initial NAV",)
    axes[0].set_title("策略净值曲线")
    axes[0].set_ylabel("NAV")
    axes[0].legend()
    axes[0].grid(True)

    # 回撤曲线
    axes[1].plot(drawdown.index,drawdown,label="Drawdown",)
    axes[1].set_title("Strategy Drawdown策略回测曲线")
    axes[1].set_ylabel("Drawdown")
    axes[1].legend()
    axes[1].grid(True)

    # 双均线策略曲线
    axes[2].plot(result.index, result["ma_short"], label="ma5", color="r")
    axes[2].plot(result.index, result["ma_long"], label="ma20", )
    axes[2].set_title("双均线策略曲线")
    axes[2].set_ylabel("ma")
    axes[2].legend()
    axes[2].grid(True)

    plt.tight_layout()
    image_path = REPORT_DIR / "sina_510300_dual_ma.png"

    plt.savefig(image_path,dpi=150,bbox_inches="tight",)
    print(f"\n图表已保存：{image_path}")

    plt.show()


# ============================================================
# 7. 保存回测结果
# ============================================================
def save_result(result):
    output_path = REPORT_DIR / "510300_dual_ma.parquet"
    result.to_parquet(output_path)
    print(f"\n回测数据已保存：{output_path}")

# ============================================================
# 8. 主程序
# ============================================================
def main():

    # 0, 初始化参数
    initial_capital = 100_000
    commission_rate = 0.0003
    slippage_rate = 0.0002
    # test_year = '2021'


    # 1. 读取全部行情数据
    raw_df = load_data("510300")

    # 2. 运行双均线策略生成信号
    # 2.1, 使用完整的数据生成信号
    signal_df = generate_strategy(raw_df)

    # 2.2.1, 取出2021年行情
    filtered_df = signal_df[signal_df.index > "2025-01-01"].copy()
    # 2.2.2, 找到2021年之前的最后一个交易日
    previous_df = signal_df.loc[signal_df.index < filtered_df.index[0]].tail(1)

    # 2.3, 回测数据保留前一个交易日
    backtest_df = pd.concat([previous_df, filtered_df]) # 某一年的数据 + 前一天的数据
    print("=" * 50)
    print("回测数据处理完毕")
    print("=" * 50)
    print(f"数据起始日期：{backtest_df.index.min()}")
    print(f"数据结束日期：{backtest_df.index.max()}")
    print(f"数据总行数：{len(backtest_df)}")

    # 3, 根据策略信号进行回测
    # 内部会计算nav和return哈
    # 注意哈: 这里的返回结果result不是在原先的df上增加字段, 而是一个新的.
    # 因为后续可能会在df上同时跑多个策略, 尽量保证结果数据独立化
    max_position_change = 0.1
    # result = execute_backtest(backtest_df, initial_capital, commission_rate, slippage_rate,
    #                           max_position=1.0,
    #                           max_position_change=max_position_change,
    #                           lot_size=100,
    #                           enable_risk_control = False,
    #                           stop_drawdown=0.09,   # 临时改为 9%
    #                           resume_drawdown=0.05,
    #                           )


    # 批量运行风控参数实验
    results, comparison = run_parameter_experiments(
        df=backtest_df,
    )

    print("\n")
    print("=" * 100)
    print("风控参数批量回测结果")
    print("=" * 100)

    print(comparison.round(4).to_string())

    # 绘制 6% / 3% 风控方案
    plot_risk_analysis(results["触发6%_解除3%"], title="Risk Control: 6% / 3%",)

    # 绘制 8% / 5% 风控方案
    plot_risk_analysis(results["触发8%_解除5%"], title="Risk Control: 8% / 5%",)

    # print_risk_events(results)

    # # A：关闭风控
    # result_without_risk = run_backtest(
    #     df=backtest_df,
    #     enable_risk_control=False,
    # )
    #
    # # B：启用风控
    # result_with_risk = run_backtest(
    #     df=backtest_df,
    #     enable_risk_control=True,
    #     stop_drawdown=0.08,
    #     resume_drawdown=0.05,
    # )
    #
    # # 策略绩效对比
    # comparison = compare_strategies(
    #     {
    #         "关闭风控": result_without_risk,
    #         "启用风控": result_with_risk,
    #     }
    # )
    #
    # print("\n" + "=" * 60)
    # print("策略绩效对比")
    # print("=" * 60)
    #
    # print(comparison.round(4))
    #
    # print_risk_summary(result_without_risk, "关闭风控")
    # print_risk_summary(result_with_risk, "开启风控")


    # risk_result = check_drawdown_warning(result["drawdown"])
    # print("=" * 50)
    # print("风险数据查看")
    # print("=" * 50)
    # print(risk_result.head(20))
    #
    #
    # # 4, 根据基准进行基准回测测试
    # # 4.1, 计算基准净值（买入并持有）
    # benchmark_nav = calculate_benchmark_nav(
    #     df=backtest_df,
    #     initial_capital=initial_capital,
    #     commission_rate=commission_rate,
    #     slippage_rate=slippage_rate,
    # )
    # result["benchmark_nav"] = benchmark_nav
    #
    # # 4.2, 计算相对净值
    # relative_nav = calculate_relative_nav(
    #     strategy_nav=result["nav"],
    #     benchmark_nav=benchmark_nav,
    # )
    # result["relative_nav"] = relative_nav
    #
    # # 4.3, 计算累计超额收益
    # excess_return = calculate_excess_return(
    #     strategy_nav=result["nav"],
    #     benchmark_nav=benchmark_nav,
    # )
    # print("\n===== 基准测试状态 =====")
    # print(f"累计超额收益：{excess_return:.2%}")
    #
    #
    # # 4, 查看资金变化
    # print("\n===== 账户状态 =====")
    # print("初始资产：", result["equity"].iloc[0])
    # print("最低资产：", result["equity"].min())
    # print("最高资产：", result["equity"].max())
    # print("最终资产：", result["equity"].iloc[-1])
    #
    # # 5, 绩效分析
    # print("\n===== 绩效分析 =====")
    # # 绩效分析, 内部会打印几个分析后的指标, 所以这里就不再打印
    # metrics = analyze_performance(result)
    # print("=" * 50)
    # for name, value in metrics.items():
    #     print(f"{name}: {value}")
    #
    #
    # # 6, 绘制图像分析
    # plot_result(result)



    # # 生成交易账本
    # trade_ledger = generate_trade_ledger(result)
    # print("\n交易账本：")
    # print(trade_ledger)

    # # 保存交易账本
    # trade_ledger_path = report_data_path / "trade_ledger.csv"
    # trade_ledger.to_csv(
    #     trade_ledger_path,
    #     index=False,
    # )


    # 保存数据
    # save_result(result)


if __name__ == "__main__":
    main()
