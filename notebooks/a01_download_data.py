#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 20:01
# @Author  : daniel
# @File    : a01_download_data.py
# @Project : daniel_quant

"""
Description: 下载需要的数据
"""
from data.raw.raw_data_config import raw_data_path
from quant.data.market_data.market_data_fetcher import get_sina_stock_daily_hist
from quant.utils.print_utils import pf


def download_data(symbol):
    # 获取基金原始信息并保存
    # data = get_sina_fund_daily_hist("510300")
    # print(data.head())
    # data_path = raw_data_path / "sina_510300.csv"
    # data.to_csv(data_path)

    # 获取股票原始信息并保存
    data = get_sina_stock_daily_hist(symbol)
    print(data.head())
    pf("数据获取成功")
    data_path = raw_data_path / f"sina_{symbol}.csv"
    data.to_csv(data_path, index=False)
    pf("数据保存成功")


if __name__ == "__main__":
    download_data(symbol="601600")
    pf("数据下载成功")