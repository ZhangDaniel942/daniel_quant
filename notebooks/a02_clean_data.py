#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 23:11
# @Author  : daniel
# @File    : a02_clean_data.py
# @Project : daniel_quant

"""
Description: 
"""
import pandas as pd

from data.processed.processed_data_config import processed_data_path
from data.raw.raw_data_config import raw_data_path
from quant.data.market_data.market_data_cleaner import clean_etf_data


def clean_data(file_name):
    from_data = raw_data_path / file_name
    df = pd.read_csv(from_data)
    print(df)
    print("数据读取成功")

    processed_data = clean_etf_data(df)
    to_data = processed_data_path / file_name
    processed_data.to_csv(to_data, index=False)
    print("数据保存成功")



if __name__ == '__main__':
    clean_data("sina_510300.csv")
    print("数据清晰成功")