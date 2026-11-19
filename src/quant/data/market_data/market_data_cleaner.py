#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 20:04
# @Author  : daniel
# @File    : market_data_cleaner.py
# @Project : daniel_quant

"""
Description: 
"""
import pandas as pd

from data.processed.processed_data_config import processed_data_path
from data.raw.raw_data_config import raw_data_path

# 统一字段名称
column_mapping = {
    # 东方财富返回的是中文名字
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
    "振幅": "amplitude",
    "涨跌幅": "pct_change",
    "涨跌额": "change",
    "换手率": "turnover",

    # 新浪等数据源可能直接返回英文列名
    "date": "date",
    "open": "open",
    "close": "close",
    "high": "high",
    "low": "low",
    "volume": "volume",
    "amount": "amount",

    # 我们后续自己添加的一些字段
    "source": "source" # 数据来源, sina, em
}

def clean_etf_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗和标准化 ETF 行情数据。
    """
    if df is None or df.empty:
        raise ValueError("数据源返回了空数据, 请检查")

    df = df.copy()

    # 1, 统一字段名称
    df = df.rename(columns=column_mapping)

    # 2. 检查必要字段
    required_columns = [
        "date", "open", "high", "low", "close", "volume", "source", "symbol"
    ]

    missing_columns = [
        col for col in required_columns if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(f"缺少必要字段: {missing_columns}")

    # 3. 日期转换
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # 4. 数值类型转换
    numeric_columns = [
        "open", "high", "low", "close", "volume", "amount"
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 5. 删除无效日期
    df = df.dropna(subset=["date"])

    # 6. 删除重复日期，保留最后一条
    df = df.drop_duplicates(subset=["date"], keep="last")

    # 7. 按日期升序排列
    df = df.sort_values("date").reset_index(drop=True)

    # 8. 检查关键行情字段是否缺失
    df = df.dropna(subset=["open", "high", "low", "close", "volume", "amount"])

    # 9. 检查价格是否有效
    price_columns = ["open", "high", "low", "close"]

    for col in price_columns:
        df = df[df[col] > 0]

    # 10. 检查最高价、最低价逻辑
    df = df[
        (df["high"] >= df["low"])
        & (df["high"] >= df["open"])
        & (df["high"] >= df["close"])
        & (df["low"] <= df["open"])
        & (df["low"] <= df["close"])
    ]

    # 11. 检查成交量
    df = df[df["volume"] >= 0]

    return df.reset_index(drop=True)

if __name__ == '__main__':
    from_data = raw_data_path / "sina_510300.csv"
    df = pd.read_csv(from_data)
    print(df)
    processed_data = clean_etf_data(df)
    to_data = processed_data_path / "sina_510300.csv"
    processed_data.to_csv(to_data, index=False)

    # to_data = processed_data_path / "sina_510300.csv"
    # df = pd.read_csv(to_data)
    # print(df)

