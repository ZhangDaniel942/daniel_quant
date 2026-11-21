#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/18 22:24
# @Author  : daniel
# @File    : engine.py
# @Project : daniel_quant

"""
Description: 回测引擎, 模拟交易和账户变化
    概念: equity = cash + shares * close
    字段	                中文名称	        含义
    date	            交易日期	        当前交易日
    open	            开盘价	        当天开盘价格
    close	            收盘价	        当天收盘价格
    signal	            策略信号	        策略希望持有还是空仓

    current_position	开盘前持仓	    今天开盘时、交易执行前的实际仓位，按今天开盘价重新估值
    target_position	    最终目标仓位	    根据上一交易日的策略信号，确定最终希望达到的仓位
    next_position	    预计调整后持仓	根据每日最大调整幅度，计算今天计划调整到的仓位
    position	        收盘后实际持仓	今天交易完成后，按收盘价重新估值的实际仓位

    action	            交易动作	        BUY / SELL / HOLD
    cash	            现金	            当前可用现金
    shares	            持仓份额	        当前持有多少份ETF
    commission	        手续费	        当天发生的交易手续费
    equity	            总资产	        现金加持仓市值
"""

import pandas as pd

from quant.backtest.performance import calculate_max_drawdown
from quant.backtest.position_sizing import calculate_step_position, calculate_trade_value, calculate_buy_shares, calculate_sell_shares


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = 100_000,
    commission_rate: float = 0.0003,
    slippage_rate: float = 0.0002,
    max_position: float = 1.0,        # 最大满仓
    max_position_change: float = 0.1, # 每次仓位调整不能大于总资产的10%
    lot_size: int = 100,                   # 每手100份
    enable_risk_control = True,
    stop_drawdown: float = 0.10,   # 触发风控的回撤阈值
    resume_drawdown: float = 0.05, # 解除风控的回撤阈值
) -> pd.DataFrame:
    """
    最小版日频回测引擎。
    约定：
    1. 当日收盘生成 signal。
    2. 下一交易日开盘执行。
    3. 当日收盘计算账户资产。
    4. 模拟ETF整手交易、手续费和滑点。
    5. 暂不模拟涨跌停、流动性限制和部分成交。
    """
    required_columns = {"open", "close", "signal", "ma_short", "ma_long",}

    if not required_columns.issubset(df.columns):
        raise ValueError(f"缺少必要字段：{required_columns - set(df.columns)}")
    if df.empty:
        raise ValueError("行情数据不能为空")
    if initial_capital <= 0:
        raise ValueError("初始资金必须大于 0")
    if not 0 <= commission_rate < 1:
        raise ValueError("手续费率不合法")
    if not 0 <= slippage_rate < 1:
        raise ValueError("滑点率不合法")

    if not 0 < max_position <= 1:
        raise ValueError("最大仓位必须在 0 到 1 之间")

    if not 0 < max_position_change <= 1:
        raise ValueError("每日最大仓位调整幅度必须在 0 到 1 之间")

    if lot_size <= 0:
        raise ValueError("交易单位必须大于 0")

    if not 0 < resume_drawdown < stop_drawdown < 1:
        raise ValueError("回撤参数必须满足：0 < resume_drawdown < stop_drawdown < 1")

    data = df.copy().sort_index()
    if data.index.has_duplicates:
        raise ValueError("行情日期不能重复")

    if data[["open", "close", "signal"]].isna().any().any():
        raise ValueError("open、close、signal 不能包含空值")
    if (data[["open", "close"]] <= 0).any().any():
        raise ValueError("价格必须大于 0")
    if not data["signal"].isin([0, 1]).all():
        raise ValueError("signal 只能为 0 或 1")

    cash = float(initial_capital)
    shares = 0.0

    # ==========================================
    # 风控初始化
    # ==========================================
    # 是否处于风控状态
    risk_stopped = False
    # 历史最高净值
    # 初始资金对应的净值为1.0
    running_max_nav = 1.0

    records = []
    for i, (index, row) in enumerate(data.iterrows()):
        # print(index)
        if "date" in data.columns:
            date = row["date"]
        else:
            date = index

        # 第一天没有上一交易日信号，因此不交易
        if i == 0:
            execution_signal = 0
        else:
            # 使用前一个交易日的信号，避免未来函数
            # signal = int(data["signal"].iloc[i - 1])
            execution_signal = int(data["signal"].iloc[i - 1])

        # 策略信号转换成最终目标仓位
        # target_position 是最终目标仓位，不是今天实际要达到的仓位
        # 例如：
        # - 昨日 signal=1，最终目标仓位100%。
        # - 昨日 signal=0，最终目标仓位0%。
        # 但我们每天最多只调整10个百分点。
        target_position = execution_signal * max_position

        open_price = float(row["open"])
        close_price = float(row["close"])
        ma_short = float(row["ma_short"])
        ma_long = float(row["ma_long"])

        # ==========================================
        # 1. 计算开盘时的账户状态
        # ==========================================
        equity_at_open = cash + shares * open_price
        current_position = (
            shares * open_price / equity_at_open
            if equity_at_open > 0
            else 0.0
        )
        # ==========================================
        # 风控判断
        # ==========================================
        # 记录今天开盘交易时的风控状态
        risk_status = risk_stopped

        # 默认情况下，风控后的目标仓位等于策略目标仓位
        risk_target_position = target_position

        # 如果已经触发风控，并且策略希望继续持有
        if enable_risk_control and risk_status and execution_signal == 1:
            # 禁止新增买入，保持当前实际仓位
            risk_target_position = current_position

        # ==========================================
        # 2. 计算今天允许调整到的仓位
        # ==========================================
        step_result = calculate_step_position(
            current_position=current_position,
            target_position=risk_target_position, # 这里需要使用风控的仓位
            max_position_change=max_position_change,
        )
        next_position = step_result["next_position"]

        # ==========================================
        # 3. 计算本次需要交易的金额
        # ==========================================
        trade_result = calculate_trade_value(
            cash=cash,
            shares=shares,
            open_price=open_price,
            target_position=next_position,
        )
        desired_trade_value = trade_result["trade_value"]

        # ==========================================
        # 4. 初始化交易记录
        # ==========================================
        execution_price = None
        trade_amount = 0.0
        commission = 0.0
        action = "HOLD"

        # ==========================================
        # 5. 执行买入
        # ==========================================
        if desired_trade_value > 0.000001:
            buy_result = calculate_buy_shares(
                cash=cash,
                trade_value=desired_trade_value,
                open_price=open_price,
                commission_rate=commission_rate,
                slippage_rate=slippage_rate,
                lot_size=lot_size,
            )

            buy_shares = buy_result["shares"]
            if buy_shares > 0:
                shares += buy_shares
                cash -= buy_result["total_cost"]

                execution_price = buy_result["execution_price"]
                trade_amount = buy_result["trade_amount"]
                commission = buy_result["commission"]
                action = "BUY"

        # ==========================================
        # 6. 执行卖出
        # ==========================================
        elif desired_trade_value < -0.000001:
            sell_result = calculate_sell_shares(
                shares=shares,
                open_price=open_price,
                trade_value=abs(desired_trade_value),
                commission_rate=commission_rate,
                slippage_rate=slippage_rate,
                lot_size=lot_size,
            )
            sell_shares = sell_result["shares"]
            if sell_shares > 0:
                shares -= sell_shares
                cash += sell_result["net_amount"]

                execution_price = sell_result["execution_price"]
                trade_amount = sell_result["trade_amount"]
                commission = sell_result["commission"]

                action = "SELL"

        # 收盘估值
        equity = cash + shares * close_price
        # 收盘时的实际仓位
        position = shares * close_price / equity if equity > 0 else 0.0


        # ==========================================
        # 收盘后计算回撤
        # ==========================================
        nav = equity / initial_capital
        # 更新历史最高净值
        running_max_nav = max(running_max_nav, nav)
        # 计算当天收盘回撤
        drawdown = nav / running_max_nav - 1

        # ==========================================
        # 交易完之后再更新下一交易日的风控状态
        # ==========================================
        if enable_risk_control:
            if not risk_stopped and drawdown <= -stop_drawdown:
                # 达到风控阈值，进入风控状态
                risk_stopped = True
            elif risk_stopped and drawdown >= -resume_drawdown:
                # 回撤恢复到解除阈值，退出风控状态
                risk_stopped = False
        # 记录收盘后更新的状态
        risk_status_next = risk_stopped if enable_risk_control else False

        records.append({
            "date": date,
            "open": open_price,
            "close": close_price,
            "ma_short": ma_short,
            "ma_long": ma_long,
            "signal": int(row["signal"]), # signal是在策略中生成的, 所以原先的数据中就有
            "execution_signal": execution_signal,

            # 风控信息
            "risk_status": risk_status,
            "risk_status_next": risk_status_next,
            "drawdown": drawdown,

            # 仓位信息
            # 注意，position 是收盘后的实际仓位，所以它可能与 next_position 略有差异。这是正常的：成交整手限制、手续费、滑点和收盘价格变化都会造成差异。
            # "position": int(shares > 0),
            "position": position,
            "current_position": current_position,
            "target_position": target_position,
            "risk_target_position": risk_target_position,
            "next_position": next_position,

            # 交易信息
            "action": action,
            "execution_price": execution_price,
            "trade_amount": trade_amount,
            "commission": commission,

            # 账户信息
            # 账户信息
            "cash": cash,
            "shares": shares,
            "equity": equity,
        })


    # 建议再读取数据的时候, 直接设置日期索引, 这里就不需要设置了
    # 错了, 这是一个新的df, 需要设置哈
    result = pd.DataFrame(records).set_index("date").sort_index()
    # result["date"] = result.index

    # 回测的时候, 已经计算了: nav和return了
    result["nav"] = result["equity"] / initial_capital
    # 这里使用收盘价计算收益比
    result["return"] = result["nav"].pct_change().fillna(0)

    # # 同时直接计算回撤
    # # 上面已经计算过了
    # result["drawdown"] = calculate_max_drawdown(result["nav"])[1]

    return result