#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 20:00
# @Author  : daniel
# @File    : market_data_fetcher.py
# @Project : daniel_quant

"""
market_data data fetcher.
    510300: 沪深300
    601899: 紫金矿业
"""
import akshare as ak

from data.raw.raw_data_config import raw_data_path
from quant.utils.stock_symbol_utils import get_sina_symbol

# 新浪财经-股票历史信息
def get_sina_stock_daily_hist(symbol,
                      data_source="sina",
                      start_date = "19700101",
                      end_date = "21000101",
                      adjust = "qfq"
                      ):
    """
    通过sina财经接口获取**股票**相关数据
    :param symbol:
    :param data_source:
    :param start_date:
    :param end_date:
    :param adjust:
    :return:
    """
    sina_symbol = get_sina_symbol(symbol)
    df = ak.stock_zh_a_hist_sina(
        symbol=sina_symbol,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust=adjust,
    )
    df["source"] = data_source
    df.insert(0, "symbol", symbol)
    return df

# 新浪财经-基金历史信息
def get_sina_fund_daily_hist(symbol,
                      data_source="sina"
                      ):
    """
    通过sina财经接口获取**基金**相关数据
    :param stock_id:
    :param data_source:
    :return:
    """
    sina_symbol = get_sina_symbol(symbol)
    df = ak.fund_etf_hist_sina(
        symbol=sina_symbol
    )
    df["source"] = data_source
    df.insert(0, "symbol", symbol)
    return df


if __name__ == "__main__":

    # 获取基金原始信息并保存
    data = get_sina_fund_daily_hist("510300")
    print(data.head())
    data_path = raw_data_path / "sina_510300.csv"
    data.to_csv(data_path, index=False)

    # # 获取股票原始信息并保存
    # data = get_sina_stock_daily_hist("601899")
    # print(data.head())
    # data_path = raw_data_path / "sina_601899.csv"
    # data.to_csv(data_path, index=False)



