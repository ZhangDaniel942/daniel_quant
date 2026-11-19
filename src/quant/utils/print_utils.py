#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/14 14:52
# @Author  : daniel
# @File    : print_utils.py
# @Project : daniel_learning_code

"""
Description: 
"""
def pf(msg, line_no=40):
    print(f"-" * line_no + f"{msg}" + "-" * line_no)


if __name__ == '__main__':
    pf("NIhao")