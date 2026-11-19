#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/19 18:58
# @Author  : daniel
# @File    : stock_symbol_utils.py
# @Project : daniel_quant

"""
Description: 常用的股票小工具
"""

def get_sina_symbol(symbol: str) -> str:
    """
    将沪深证券代码转换为新浪行情代码。
    支持常见股票、ETF、基金、可转债等。

    159915 -> sz159915
    123001 -> sz123001
    300750 -> sz300750

    510300 -> sh510300
    600000 -> sh600000
    """
    symbol = str(symbol).strip()
    if len(symbol) != 6 or not symbol.isdigit():
        raise ValueError(f"无效的证券代码: {symbol}")

    # 上海证券交易所
    sh_prefixes = (
        "50", "51", "52", "56", "58",
        "60", "68"
    )
    # 深圳证券交易所
    sz_prefixes = (
        "00",
        "12", "13", "15", "16", "18",
        "20",
        "30"
    )

    if symbol.startswith(sh_prefixes):
        return f"sh{symbol}"
    if symbol.startswith(sz_prefixes):
        return f"sz{symbol}"

    raise ValueError(f"无法判断证券所属市场: {symbol}")



if __name__ == '__main__':
    result_symbol = get_sina_symbol("500300")
    print(result_symbol)