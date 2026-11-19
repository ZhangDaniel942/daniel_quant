#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/19 21:23
# @Author  : daniel
# @File    : security_fetcher.py
# @Project : daniel_quant

"""
Description: 
"""
import akshare as ak
import pandas as pd

def fetch_stocks_info_from_sina():
    """获取A股股票列表"""
    df = ak.stock_info_a_code_name()
    return pd.DataFrame({
        "symbol": df["code"].astype(str).str.zfill(6),
        "name": df["name"],
        "security_type": "stock",
        "exchange": df["code"].apply(get_exchange),
        "source": "sina",
    })


def fetch_etfs_from_ths():
    """获取场内ETF列表"""
    # 这里使用东方财富老是被封, 改为同花顺
    # df = ak.fund_etf_spot_em()
    # print(df.columns.tolist())
    # return pd.DataFrame({
    #     "symbol": df["代码"].astype(str).str.zfill(6),
    #     "name": df["名称"],
    #     "security_type": "etf",
    #     "exchange": df["代码"].apply(get_exchange),
    #     "source": "em",
    # })
    """获取场内ETF列表, 这里使用东方财富老是被封, 改为同花顺"""
    df = ak.fund_etf_spot_ths()
    return pd.DataFrame({
        "symbol": df["基金代码"].astype(str).str.zfill(6),
        "name": df["基金名称"],
        "security_type": "etf",
        "exchange": df["基金代码"].astype(str).apply(get_exchange),
        "source": "ths",
    })


# 暂时不需要这个
def fetch_lofs():
    """获取场内LOF列表"""
    df = ak.fund_lof_spot_em()
    return pd.DataFrame({
        "symbol": df["代码"].astype(str).str.zfill(6),
        "name": df["名称"],
        "security_type": "lof",
        "exchange": df["代码"].apply(get_exchange),
        "source": "AKShare",
    })


def get_exchange(code):
    """根据代码前缀初步判断交易市场"""
    code = str(code).zfill(6)
    if code.startswith(("6", "5")):
        return "sse"
    if code.startswith(("0", "1", "2", "3")):
        return "szse"
    if code.startswith(("4", "8")):
        return "bse"
    return "unknown"


def fetch_all_securities():
    """获取第一批证券基础信息"""
    results = []

    # 这里还能这样啊, 直接方法就能执行啊, 牛牛牛
    fetchers = [
        ("股票", fetch_stocks_info_from_sina),
        ("ETF", fetch_etfs_from_ths),
        # ("LOF", fetch_lofs),
    ]

    for name, fetcher in fetchers:
        try:
            df = fetcher()
            results.append(df)
            print(f"{name}获取成功：{len(df)} 条")

        except Exception as e:
            print(f"{name}获取失败：{e}")

    if not results:
        raise RuntimeError("所有证券数据接口均获取失败")
    result = pd.concat(results, ignore_index=True)
    result = result.drop_duplicates(
        subset=["symbol", "exchange", "security_type"]
    )
    return result

if __name__ == '__main__':
    # df = fetch_all_securities()
    # print(df.head())

    df = fetch_etfs_from_ths()
    print(df.head())