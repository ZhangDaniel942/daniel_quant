#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/19 21:03
# @Author  : daniel
# @File    : database.py
# @Project : daniel_quant

"""
Description: 建立和管理 MySQL 连接
"""

import pymysql
from pymysql.connections import Connection

from config.settings import MYSQL_CONFIG


def get_connection() -> Connection:
    """
    创建 MySQL 数据库连接
    """
    connection = pymysql.connect(
        **MYSQL_CONFIG,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    return connection

if __name__ == '__main__':
    connection = get_connection()
    with connection.cursor() as cursor:
        cursor.execute("select version() as version")
        result = cursor.fetchone()
        print("MySQL连接成功！")
        print("MySQL版本：", result["version"])

