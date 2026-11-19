#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 23:17
# @Author  : daniel
# @File    : test_engine.py
# @Project : daniel_quant

"""
Description: uv run python -m pytest -v
"""

import pandas as pd
import pytest

from quant.backtest.engine import run_backtest


# ============================================================
# 1. 测试数据
# ============================================================

def make_test_data(
    open_prices=None,
    close_prices=None,
    signals=None,
):
    """构造测试行情数据"""

    if open_prices is None:
        open_prices = [10, 10, 11, 12, 10]

    if close_prices is None:
        close_prices = [10, 11, 12, 11, 10]

    if signals is None:
        signals = [1, 1, 1, 0, 0]

    return pd.DataFrame(
        {
            "open": open_prices,
            "close": close_prices,
            "signal": signals,
        },
        index=pd.date_range(
            "2026-01-01",
            periods=len(open_prices),
            freq="D",
        ),
    )


# ============================================================
# 2. 基础交易逻辑
# ============================================================

def test_buy_and_sell():
    """测试买入、持仓、卖出及资金计算"""

    df = make_test_data()

    initial_capital = 10_000
    commission_rate = 0.001
    slippage_rate = 0.001

    result = run_backtest(
        df,
        initial_capital=initial_capital,
        commission_rate=commission_rate,
        slippage_rate=slippage_rate,
    )

    # 检查交易时序
    assert result["action"].tolist() == [
        "HOLD",
        "BUY",
        "HOLD",
        "HOLD",
        "SELL",
    ]

    # 计算预期买入价格
    buy_price = 10 * (1 + slippage_rate)

    # 计算预期买入份额
    expected_shares = initial_capital / (
        buy_price * (1 + commission_rate)
    )

    assert result.iloc[1]["shares"] == pytest.approx(
        expected_shares
    )

    # 买入后收盘资产
    expected_equity = expected_shares * 11

    assert result.iloc[1]["equity"] == pytest.approx(
        expected_equity
    )

    # 第三天继续持仓
    assert result.iloc[2]["position"] == 1

    # 第四天产生卖出信号，但不立即卖出
    assert result.iloc[3]["action"] == "HOLD"
    assert result.iloc[3]["position"] == 1

    # 第五天开盘卖出
    sell_price = 10 * (1 - slippage_rate)

    expected_sell_value = expected_shares * sell_price
    expected_commission = expected_sell_value * commission_rate

    expected_final_cash = (
        expected_sell_value - expected_commission
    )

    assert result.iloc[4]["action"] == "SELL"
    assert result.iloc[4]["shares"] == pytest.approx(0)
    assert result.iloc[4]["cash"] == pytest.approx(
        expected_final_cash
    )

    # 最终资产与净值
    assert result.iloc[4]["equity"] == pytest.approx(
        expected_final_cash
    )

    assert result.iloc[4]["nav"] == pytest.approx(
        expected_final_cash / initial_capital
    )


def test_first_day_does_not_trade():
    """第一天没有前一日信号，不应该交易"""

    df = make_test_data()

    result = run_backtest(df)

    assert result.iloc[0]["action"] == "HOLD"
    assert result.iloc[0]["position"] == 0
    assert result.iloc[0]["cash"] == pytest.approx(100_000)


# ============================================================
# 3. 连续信号与持仓状态
# ============================================================

def test_continuous_buy_signal():
    """连续买入信号只应该买入一次"""

    df = make_test_data(
        open_prices=[10, 10, 11, 12],
        close_prices=[10, 11, 12, 13],
        signals=[1, 1, 1, 1],
    )

    result = run_backtest(df)

    assert result["action"].tolist() == [
        "HOLD",
        "BUY",
        "HOLD",
        "HOLD",
    ]

    assert result["action"].tolist().count("BUY") == 1


def test_continuous_empty_signal():
    """连续空仓信号不应该重复卖出"""

    df = make_test_data(
        open_prices=[10, 10, 11, 12],
        close_prices=[10, 11, 12, 13],
        signals=[0, 0, 0, 0],
    )

    result = run_backtest(df)

    assert result["action"].tolist() == [
        "HOLD",
        "HOLD",
        "HOLD",
        "HOLD",
    ]

    assert result["action"].tolist().count("SELL") == 0


def test_repeated_signal_transitions():
    """测试多次买入、卖出切换"""

    df = make_test_data(
        open_prices=[10, 10, 11, 12, 10, 9],
        close_prices=[10, 11, 12, 11, 9, 10],
        signals=[1, 1, 0, 0, 1, 1],
    )

    result = run_backtest(df)

    assert result["action"].tolist() == [
        "HOLD",
        "BUY",
        "HOLD",
        "SELL",
        "HOLD",
        "BUY",
    ]

    assert result["action"].tolist().count("BUY") == 2
    assert result["action"].tolist().count("SELL") == 1


# ============================================================
# 4. 手续费与滑点
# ============================================================

def test_zero_commission_and_slippage():
    """手续费和滑点为零时，按照开盘价成交"""

    df = make_test_data()

    result = run_backtest(
        df,
        initial_capital=10_000,
        commission_rate=0,
        slippage_rate=0,
    )

    # 第二天开盘价为10元
    expected_shares = 10_000 / 10

    assert result.iloc[1]["shares"] == pytest.approx(
        expected_shares
    )

    assert result.iloc[1]["commission"] == pytest.approx(0)

    # 第五天开盘价为10元
    assert result.iloc[4]["cash"] == pytest.approx(
        expected_shares * 10
    )


def test_commission_calculation():
    """验证手续费计算"""

    df = make_test_data()

    result = run_backtest(
        df,
        initial_capital=10_000,
        commission_rate=0.001,
        slippage_rate=0,
    )

    buy_value = result.iloc[1]["shares"] * 10
    expected_commission = buy_value * 0.001

    assert result.iloc[1]["commission"] == pytest.approx(
        expected_commission
    )

    sell_value = result.iloc[4]["shares"] * 10

    # 卖出后 shares 已清零，所以使用卖出前持仓计算
    shares_before_sell = result.iloc[3]["shares"]
    expected_sell_commission = shares_before_sell * 10 * 0.001

    assert result.iloc[4]["commission"] == pytest.approx(
        expected_sell_commission
    )


def test_slippage_affects_final_equity():
    """有滑点时，最终资产应该低于无滑点情况"""

    df = make_test_data()

    result_without_slippage = run_backtest(
        df,
        commission_rate=0,
        slippage_rate=0,
    )

    result_with_slippage = run_backtest(
        df,
        commission_rate=0,
        slippage_rate=0.01,
    )

    assert (
        result_with_slippage.iloc[-1]["equity"]
        < result_without_slippage.iloc[-1]["equity"]
    )


# ============================================================
# 5. 净值与收益率
# ============================================================

def test_nav_calculation():
    """验证净值计算"""

    df = make_test_data()

    result = run_backtest(
        df,
        initial_capital=10_000,
    )

    expected_nav = result["equity"] / 10_000

    pd.testing.assert_series_equal(
        result["nav"],
        expected_nav,
        check_names=False,
    )


def test_return_calculation():
    """验证每日收益率计算"""

    df = make_test_data()

    result = run_backtest(df)

    expected_return = (
        result["nav"].pct_change().fillna(0)
    )

    pd.testing.assert_series_equal(
        result["return"],
        expected_return,
        check_names=False,
    )


def test_cash_and_equity_consistency():
    """验证现金加持仓市值等于账户总资产"""

    df = make_test_data()

    result = run_backtest(df)

    expected_equity = (
        result["cash"]
        + result["shares"] * result["close"]
    )

    pd.testing.assert_series_equal(
        result["equity"],
        expected_equity,
        check_names=False,
    )


# ============================================================
# 6. 输入数据异常校验
# ============================================================

def test_empty_data():
    """空行情数据应该报错"""

    df = pd.DataFrame(
        columns=["open", "close", "signal"]
    )

    with pytest.raises(ValueError, match="不能为空"):
        run_backtest(df)


def test_missing_column():
    """缺少必要字段应该报错"""

    df = pd.DataFrame(
        {
            "open": [10, 11],
            "close": [10, 11],
        }
    )

    with pytest.raises(ValueError, match="缺少必要字段"):
        run_backtest(df)


def test_invalid_signal():
    """信号不允许出现0和1以外的值"""

    df = make_test_data(
        open_prices=[10, 11],
        close_prices=[10, 11],
        signals=[1, 2],
    )

    with pytest.raises(ValueError, match="signal"):
        run_backtest(df)


def test_nan_data():
    """行情数据不允许包含空值"""

    df = make_test_data(
        open_prices=[10, None],
        close_prices=[10, 11],
        signals=[1, 1],
    )

    with pytest.raises(ValueError, match="空值"):
        run_backtest(df)


def test_zero_price():
    """价格必须大于0"""

    df = make_test_data(
        open_prices=[10, 0],
        close_prices=[10, 11],
        signals=[1, 1],
    )

    with pytest.raises(ValueError, match="价格"):
        run_backtest(df)


def test_negative_capital():
    """初始资金必须大于0"""

    df = make_test_data()

    with pytest.raises(ValueError, match="初始资金"):
        run_backtest(df, initial_capital=-100)


def test_zero_capital():
    """初始资金不能为0"""

    df = make_test_data()

    with pytest.raises(ValueError, match="初始资金"):
        run_backtest(df, initial_capital=0)


def test_invalid_commission():
    """手续费率必须在0到1之间"""

    df = make_test_data()

    with pytest.raises(ValueError, match="手续费率"):
        run_backtest(df, commission_rate=1)


def test_invalid_slippage():
    """滑点率必须在0到1之间"""

    df = make_test_data()

    with pytest.raises(ValueError, match="滑点率"):
        run_backtest(df, slippage_rate=1)


def test_duplicate_dates():
    """不允许出现重复日期"""

    df = make_test_data()

    df.index = [
        pd.Timestamp("2026-01-01"),
        pd.Timestamp("2026-01-02"),
        pd.Timestamp("2026-01-02"),
        pd.Timestamp("2026-01-04"),
        pd.Timestamp("2026-01-05"),
    ]

    with pytest.raises(ValueError, match="不能重复"):
        run_backtest(df)


# ============================================================
# 7. 边界情况
# ============================================================

def test_single_day_data():
    """只有一天数据时不应该交易"""

    df = make_test_data(
        open_prices=[10],
        close_prices=[11],
        signals=[1],
    )

    result = run_backtest(df)

    assert len(result) == 1
    assert result.iloc[0]["action"] == "HOLD"
    assert result.iloc[0]["cash"] == pytest.approx(100_000)
    assert result.iloc[0]["nav"] == pytest.approx(1.0)

def test_all_buy_signals():
    """一直保持买入信号，最终仍然持仓"""

    df = make_test_data(
        open_prices=[10, 10, 11],
        close_prices=[10, 11, 12],
        signals=[1, 1, 1],
    )

    result = run_backtest(df)

    assert result.iloc[-1]["position"] == 1
    assert result.iloc[-1]["shares"] > 0


def test_all_sell_signals():
    """一直保持空仓信号，不应该产生交易"""

    df = make_test_data(
        open_prices=[10, 11, 12],
        close_prices=[10, 11, 12],
        signals=[0, 0, 0],
    )

    result = run_backtest(df)

    assert result["action"].tolist() == [
        "HOLD",
        "HOLD",
        "HOLD",
    ]

    assert (result["position"] == 0).all()


