#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 20:07
# @Author  : daniel
# @File    : moving_average.py
# @Project : daniel_quant

"""
Description: 
"""
import pandas as pd

from data.processed.processed_data_config import processed_data_path

def add_moving_averages(
    df: pd.DataFrame,
    windows: tuple[int, ...] = (5, 20, 60),
) -> pd.DataFrame:
    """
    双均线交叉策略, 添加移动平均线.
    :param df:
    :param windows:
    :return:
    """
    df = df.copy()

    for window in windows:
        column_name = f"ma{window}"
        df[column_name] = (
            df["close"]
            .rolling(window=window)
            .mean()
        )
    return df


if __name__ == '__main__':
    data_path = processed_data_path / "sina_510300.csv"
    df = pd.read_csv(data_path)
    df = add_moving_averages(df)
    print(
        df[
            ["date", "close", "ma5", "ma20", "ma60"]
        ].tail(20)
    )