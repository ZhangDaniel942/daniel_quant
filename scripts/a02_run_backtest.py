#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 23:25
# @Author  : daniel
# @File    : a02_run_backtest.py
# @Project : daniel_quant

"""
Description: 完整策略回测流程
"""
import pandas as pd
import matplotlib.pyplot as plt

from data.processed.processed_data_config import processed_data_path
from quant.backtest.benchmark import calculate_benchmark_nav, calculate_relative_nav, calculate_excess_return
from quant.backtest.trade_ledger import generate_trade_ledger
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
def execute_backtest(df, initial_capital, commission_rate, slippage_rate):
    result = run_backtest(
        df,
        initial_capital=initial_capital,
        commission_rate=commission_rate,
        slippage_rate=slippage_rate,
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

    print("\n绩效分析")
    print("=" * 50)

    for name, value in metrics.items():
        print(f"{name}: {value}")

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

    initial_capital = 100_000
    commission_rate = 0.0003
    slippage_rate = 0.0002

    # 1. 读取行情数据
    df = load_data("510300")
    df = df.loc["2021"]
    pf(f"读取行情数据df的索引: {df.index}")

    # 2. 运行双均线策略回测
    # 2.1, 生成信号
    df = generate_strategy(df)
    pf(f"运行双均线策略回测df的索引: {df.index}")

    # groupby是df的, 不是series的方法哈
    # print(df.groupby(["signal"])['signal'].count())

    # print(df[["ma_short", "ma_long"]].dtypes)
    # print(df.loc[200, "ma_short"] - df.loc[200, "ma_long"])
    # df.to_csv("test.csv")

    # 2.2, 执行回测
    # 内部会计算nav和return哈
    # 注意哈: 这里的返回结果result不是在原先的df上增加字段, 而是一个新的.
    # 因为后续可能会在df上同时跑多个策略, 尽量保证结果数据独立化
    result = execute_backtest(df, initial_capital, commission_rate, slippage_rate)
    pf(f"执行回测: {df.index}")

    print(result.iloc[-1])

    # 3. 查看资金变化
    print("\n===== 账户状态 =====")
    print("初始资产：", result["equity"].iloc[0])
    print("最低资产：", result["equity"].min())
    print("最高资产：", result["equity"].max())
    print("最终资产：", result["equity"].iloc[-1])

    # 绩效分析, 内部会打印几个分析后的指标, 所以这里就不再打印
    metrics = analyze_performance(result)
    pf(f"绩效分析,: {df.index}")

    # 4, 基准测试
    # 4.1, 计算基准净值（买入并持有）
    benchmark_nav = calculate_benchmark_nav(
        df=df,
        initial_capital=initial_capital,
        commission_rate=commission_rate,
        slippage_rate=slippage_rate,
    )
    pf(f"基准测试,: {df.index}")

    print("benchmark_nav的数据")
    print(benchmark_nav.index)
    print(benchmark_nav.head())
    result["benchmark_nav"] = benchmark_nav

    # 4.2, 计算相对净值
    relative_nav = calculate_relative_nav(
        strategy_nav=result["nav"],
        benchmark_nav=benchmark_nav,
    )
    result["relative_nav"] = relative_nav

    # 4.3, 计算累计超额收益
    excess_return = calculate_excess_return(
        strategy_nav=result["nav"],
        benchmark_nav=benchmark_nav,
    )
    print(f"累计超额收益：{excess_return:.2%}")




    # 生成交易账本
    trade_ledger = generate_trade_ledger(result)
    print("\n交易账本：")
    print(trade_ledger)

    # 保存交易账本
    trade_ledger_path = report_data_path / "trade_ledger.csv"
    trade_ledger.to_csv(
        trade_ledger_path,
        index=False,
    )



    # 绘制图表
    plot_result(result)

    # 保存数据
    # save_result(result)


if __name__ == "__main__":
    main()
