#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/19 21:26
# @Author  : daniel
# @File    : security_info_2_sql.py
# @Project : daniel_quant

"""
Description: 
"""
from quant.data.mysql.database import get_connection
from quant.data.security.security_fetcher import fetch_all_securities, fetch_etfs_from_ths


def save_securities(df):
    sql = """
        INSERT INTO security_info (symbol, name, security_type, exchange, source)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE name = VALUES(name), source = VALUES(source)
    """
    records = [(row.symbol, row.name, row.security_type, row.exchange, row.source,) for row in df.itertuples(index=False)]
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.executemany(sql, records)
        connection.commit()
        print(f"成功处理 {len(records)} 条证券信息")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def main():
    df = fetch_all_securities()
    # df = fetch_etfs_from_ths()
    print("\n证券分类统计：")
    print(df.groupby("security_type").size())

    print("\n前20条数据：")
    print(df.head(20))

    save_securities(df)
    print(f"证券信息保存mysql完成:{df.count()}")

if __name__ == "__main__":
    main()