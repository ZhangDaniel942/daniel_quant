#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 23:25
# @Author  : daniel
# @File    : a02_run_backtest.py
# @Project : daniel_quant

"""
Description: 完整策略回测流程
"""
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

from data.processed.processed_data_config import processed_data_path
from quant.strategies.dual_ma import generate_signals
from quant.backtest.engine import run_backtest
from quant.backtest.performance import calculate_performance
from reports.report_data_config import report_data_path

# ============================================================
# 1. 路径配置
# ============================================================
# 输入
DATA_PATH = processed_data_path / "sina_510300.csv"
# 输出
REPORT_DIR = report_data_path

# ============================================================
# 2. 加载行情数据
# ============================================================
def load_data():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"行情文件不存在：{DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    required_columns = {"open", "close"}

    if not required_columns.issubset(df.columns):
        raise ValueError(f"缺少行情字段：{required_columns - set(df.columns)}")

    df = df[["date", "open", "close"]].copy()
    df = df.sort_index()

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
def execute_backtest(df):
    result = run_backtest(
        df,
        initial_capital=100_000,
        commission_rate=0.0003,
        slippage_rate=0.0002,
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

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(14, 9),
        sharex=True,
    )

    # 净值曲线
    axes[0].plot(
        nav.index,
        nav,
        label="Dual MA Strategy",
    )

    axes[0].axhline(
        1.0,
        linestyle="--",
        label="Initial NAV",
    )

    axes[0].set_title("Strategy NAV")
    axes[0].set_ylabel("NAV")
    axes[0].legend()
    axes[0].grid(True)

    # 回撤曲线
    axes[1].plot(
        drawdown.index,
        drawdown,
        label="Drawdown",
    )

    axes[1].set_title("Strategy Drawdown")
    axes[1].set_ylabel("Drawdown")
    axes[1].legend()
    axes[1].grid(True)

    plt.tight_layout()
    image_path = REPORT_DIR / "sina_510300_dual_ma.png"

    plt.savefig(
        image_path,
        dpi=150,
        bbox_inches="tight",
    )

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

    # 加载行情
    df = load_data()

    # 生成信号
    df = generate_strategy(df)

    # 执行回测
    result = execute_backtest(df)

    # 4. 查看资金变化
    print("\n===== 账户状态 =====")
    print("初始资产：", result["equity"].iloc[0])
    print("最低资产：", result["equity"].min())
    print("最高资产：", result["equity"].max())
    print("最终资产：", result["equity"].iloc[-1])

    # 绩效分析
    analyze_performance(result)

    # 绘制图表
    plot_result(result)

    # 保存数据
    save_result(result)


if __name__ == "__main__":
    main()
