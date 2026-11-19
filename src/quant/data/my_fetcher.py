#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/19 17:30
# @Author  : daniel
# @File    : my_fetcher.py
# @Project : daniel_quant

"""
Description: 自己用来写的草稿
"""

import akshare as ak

from data.raw.raw_data_config import raw_data_path
from quant.utils.flush_env import flush_env_done

stock_id = "601899"
data_source = "sina"
save_name = stock_id + "_" + data_source + ".csv"
save_path = raw_data_path / save_name

sina_stock_id = "sh" + stock_id
df = ak.stock_zh_a_hist_sina(
    symbol = sina_stock_id,
    period = "daily",
    start_date = "19700101",
    end_date = "20500101",
    adjust = "qfq",
)

print(df.head())
df.to_csv(save_path)


# # flush_env_done()
# stock_id = "601899"
# data_source = "em"
# save_name = stock_id + "_" + data_source + ".csv"
# save_path = raw_data_path / save_name
#
# em_stock_id = stock_id
# df = ak.stock_zh_a_hist_em(
#     symbol = em_stock_id,
#     period = "daily",
#     start_date = "19700101",
#     end_date = "20500101",
#     adjust = "qfq",
# )
#
# print(df.head())
# df.to_csv(save_path)