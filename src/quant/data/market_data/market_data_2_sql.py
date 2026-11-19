#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/19 22:03
# @Author  : daniel
# @File    : market_data_2_sql.py
# @Project : daniel_quant

"""
Description: 
"""
import pandas as pd

from data.processed.processed_data_config import processed_data_path
from quant.data.mysql.database import get_connection


BATCH_SIZE = 1000
# 目前支持的证券类型
SUPPORTED_TYPES = ("stock", "etf")

# ============================================================
# 写入 MySQL
# ============================================================
def save_market_data(
    df: pd.DataFrame,
) -> int:
    """
    批量保存行情数据。
    如果 symbol + trade_date 已经存在，
    则更新已有行情。
    """
    if df.empty:
        return 0

    sql = """
        INSERT INTO market_daily (symbol, date, open, high, low, close, volume, amount, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            open = VALUES(open),
            high = VALUES(high),
            low = VALUES(low),
            close = VALUES(close),
            volume = VALUES(volume),
            amount = VALUES(amount)
    """

    records = []
    for row in df.itertuples(index=False):
        records.append((
            row.symbol,
            row.date,
            float(row.open),
            float(row.high),
            float(row.low),
            float(row.close),
            int(row.volume),
            float(row.amount),
            row.source,
        ))
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            for start in range(0, len(records), BATCH_SIZE):
                batch = records[start:start + BATCH_SIZE]
                cursor.executemany(sql, batch)
        connection.commit()
        return len(records)
    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == '__main__':
    data_path = processed_data_path / "sina_601600.csv"
    df = pd.read_csv(data_path)
    print(df.head())
    save_market_data(df)