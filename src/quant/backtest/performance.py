#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 21:24
# @Author  : daniel
# @File    : performance.py
# @Project : daniel_quant

"""
Description: 收益表现及各种指标
             不要只看收益率。
             一个策略年化收益 30%，但最大回撤 40%，可能并不适合我们；
             另一个策略年化收益 15%，最大回撤 8%，反而可能更有实际投资价值。
             我们未来的目标不是寻找收益最高的单一策略，而是构建一个收益、回撤、波动率都比较合理的多策略组合。
"""
import numpy as np
import pandas as pd

from quant.risk.risk_management import calculate_max_drawdown


# 使用收盘价和使用净值计算结果是一样的哈
def calculate_returns(close: pd.Series) -> pd.Series:
    """
    计算标的资产每日简单收益率。
    returns = 今日收盘价 / 昨日收盘价 - 1
    """
    return close.pct_change(fill_method=None)

def calculate_nav(
    returns: pd.Series,
    initial_nav: float = 1.0,
) -> pd.Series:
    """
    Calculate cumulative net asset value.
    净值计算函数
    """

    returns = returns.fillna(0)
    nav = (1 + returns).cumprod() * initial_nav

    return nav


def calculate_cagr(
    nav: pd.Series,
    periods_per_year: int = 252, # 因为A股一年大约有252个交易日，而不是365个自然日。
) -> float:
    """
    Calculate annualized compound growth rate.
    年化收益率函数
    """
    if len(nav) < 2:
        return 0.0

    # 净值最开始的一个数据
    initial_value = nav.iloc[0]
    # 净值最后一个数据
    final_value = nav.iloc[-1]

    # 总天数减去1, 因为三棵树, 只能有两个区间. net也是一样
    periods = len(nav) - 1

    years = periods / periods_per_year

    if initial_value <= 0 or final_value < 0:
        raise ValueError("NAV must be non-negative and initial NAV positive")

    if final_value == 0:
        return -1.0

    # 年化收益率就是: (最终的净值-开始的净值)/(总天数/每年的天数)
    cagr = (final_value / initial_value) ** (1 / years) - 1

    return cagr



def calculate_volatility(
    returns: pd.Series,
    periods_per_year: int = 252
) -> float:
    """
    计算年化波动率
    日波动率(returns的标准差)： [sigma_{daily}=std(r_1,r_2,ldots,r_n)],
    但量化分析通常使用年化波动率(returns的标准差*sqrt(252))： [sigma_{annual}=sigma_{daily} \times sqrt{252}]
    这里的 252 是 A 股一年大约的交易日数量。
    为什么乘以平方根 252？
    因为在假设每日收益相互独立、方差稳定的情况下，多个交易日收益的方差可以累加，所以标准差按时间长度的平方根扩大。
    """
    returns = returns.dropna()

    if len(returns) < 2:
        return float("nan")

    daily_volatility = returns.std(ddof=1)

    annual_volatility = daily_volatility * np.sqrt(periods_per_year)

    return float(annual_volatility)


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252
) -> float:
    """
    计算年化夏普比率
    夏普比率	一般理解
    小于 0	风险调整后表现较差
    0～1	一般
    1～2	较好
    2～3	很好
    大于 3	非常突出，需检查是否过拟合
    """
    returns = returns.dropna()

    if len(returns) < 2:
        return float("nan")

    # 将年化无风险利率转换为日化利率
    daily_rf = (1 + risk_free_rate) ** (
        1 / periods_per_year
    ) - 1

    # 每日超额收益
    excess_returns = returns - daily_rf

    # 超额收益的标准差
    volatility = excess_returns.std(ddof=1)

    if volatility == 0:
        return float("nan")

    sharpe = (
        excess_returns.mean()
        / volatility
        * np.sqrt(periods_per_year)
    )

    return float(sharpe)

def calculate_win_rate(
    trade_returns: pd.Series
) -> float:
    """
    计算已完成交易的胜率
    WinRate=\frac{盈利交易次数}{总交易次数}

    不能直接用每日正收益天数计算交易胜率。
    例如，你买入一只 ETF，持有了 20 天，中间有 12 天上涨、8 天下跌，最后卖出时赚了 5%。
    这应该算一笔盈利交易，而不是 12 笔盈利交易。
    所以，胜率需要基于完整的买卖交易记录。我们目前的 trade_log.py 还只是记录买卖动作，并没有完整的交易配对和单笔盈亏核算。
    今天先把胜率函数写好，等后面升级交易账本再接入真实交易数据。#todo
    """
    trade_returns = pd.Series(trade_returns).dropna()

    if len(trade_returns) == 0:
        return float("nan")

    return float((trade_returns > 0).mean())


def calculate_performance(
    nav: pd.Series,                  # nav是收益率, 用它计算总回报率. 所以需要真实数据前一天的数据作为基准. nav会比returns多一条数据
    returns: pd.Series = None,       # 这个是每日收益
    trade_returns: pd.Series = None, # 这个是单笔的收益
    periods_per_year: int = 252,
    risk_free_rate: float = 0.02
) -> dict:
    """
    Calculate overall strategy performance.
    综合计算策略表现指标
    净值计算, 年化收益率, 最大回撤
    年化波动率
    年化夏普比率
    已完成交易的胜率
    """
    cagr = calculate_cagr(nav, periods_per_year)
    max_drawdown, drawdown = calculate_max_drawdown(nav)

    total_return = nav.iloc[-1] / nav.iloc[0] - 1 # 注意: nav要多拿一个预热最后一个作为nav0, 这样才能计算出准确的return

    # 先把: 净值计算, 年化收益率, 最大回撤
    result = {
        "total_return": total_return, # 总回报率
        "cagr": cagr,                 # 年化收益率
        "max_drawdown": max_drawdown, # 最大回撤
        "final_nav": nav.iloc[-1],    # 最终净值
    }

    if returns is not None:
        # 年化波动率
        result["volatility"] = calculate_volatility(
            returns,
            periods_per_year
        )
        # 年化夏普比率
        result["sharpe"] = calculate_sharpe_ratio(
            returns,
            risk_free_rate,
            periods_per_year
        )

    if trade_returns is not None:
        # 已完成交易的胜率
        result["win_rate"] = calculate_win_rate(
            trade_returns
        )

    return result

if __name__ == '__main__':
    nav = pd.Series([
        1.00,
        1.10,
        1.20,
        1.05,
        0.95,
        1.05,
        1.25,
    ])
    print(calculate_max_drawdown(nav))

