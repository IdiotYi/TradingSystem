"""Return-focused MAW + MACD trend-following state machine."""
from collections.abc import Callable
import math

import pandas as pd

from app.core.indicators import calc_macd, calc_maw

_REQUIRED = {"日期", "收盘", "成交量", "成交额", "换手率"}
_LOT = 100


def _value(value):
    return None if pd.isna(value) else float(value)


def prepare_trend_following_indicators(df, short_period=20, medium_period=60, long_period=120, slope_days=20):
    missing = _REQUIRED.difference(df.columns)
    if missing:
        raise ValueError(f"MAW 必需字段缺失: {', '.join(sorted(missing))}")
    data = df.reset_index(drop=True).copy()
    data["_maw20"] = calc_maw(data, short_period)
    data["_maw60"] = calc_maw(data, medium_period)
    data["_maw120"] = calc_maw(data, long_period)
    data["_macd_dif"], data["_macd_dea"], data["_macd_histogram"] = calc_macd(data["收盘"])
    data["_maw60_lag"] = data["_maw60"].shift(slope_days)
    data["_maw120_lag"] = data["_maw120"].shift(slope_days)
    if len(data) and any(data[c].notna().sum() == 0 for c in ("_maw20", "_maw60", "_maw120")):
        raise ValueError("MAW required fields produced no valid values")
    return data


def run_trend_following(df, initial_cash, buy_fee: Callable[[float], dict], sell_fee: Callable[[float], dict], prepared=None, params=None):
    params = params or {}
    short = int(params.get("maw_short_period", 20))
    medium = int(params.get("maw_medium_period", 60))
    long = int(params.get("maw_long_period", 120))
    slope = int(params.get("maw_slope_days", 20))
    interval = int(params.get("min_buy_interval_days", 5))
    delta = float(params.get("min_rebalance_delta", 0.10))
    if min(short, medium, long, slope, interval) <= 0 or not 0 < delta <= 1:
        raise ValueError("趋势策略参数必须为正数且最小调仓差值不超过1")
    if prepared is None:
        data = prepare_trend_following_indicators(df, short, medium, long, slope)
    else:
        attrs = dict(prepared.attrs)
        data = prepared.reset_index(drop=True).copy()
        data.attrs.update(attrs)
    missing = _REQUIRED.difference(data.columns)
    if missing:
        raise ValueError(f"MAW 必需字段缺失: {', '.join(sorted(missing))}")
    required_indicators = ("_maw20", "_maw60", "_maw120", "_macd_dif", "_macd_dea", "_macd_histogram", "_maw60_lag", "_maw120_lag")
    if any(c not in data for c in required_indicators):
        raise ValueError("Prepared trend-following data is missing indicator columns")

    trades, targets, ratios = [], [], []
    cash, shares, average_cost = float(initial_cash), 0, 0.0
    last_buy = None

    def record(action, qty, price, fee, i, reason, pnl=None):
        trades.append({"date": str(data.at[i, "日期"]), "signal_date": str(data.at[i, "日期"]), "action": action,
            "price": price, "shares": qty, "amount": qty * price,
            "transfer_fee": float(fee.get("transfer_fee", 0.0)), "commission": float(fee.get("commission", 0.0)),
            "stamp_tax": fee.get("stamp_tax"), "total_fee": float(fee.get("total_fee", 0.0)),
            "pnl": pnl, "remaining_cash": round(cash, 2), "reason": reason})

    def buy_to(i, target, reason):
        nonlocal cash, shares, average_cost, last_buy
        price = float(data.at[i, "收盘"]); assets = cash + shares * price
        desired = math.floor(assets * target / price / _LOT) * _LOT
        if target >= 1.0:
            desired = shares + math.floor(cash / price / _LOT) * _LOT
        qty = max(0, desired - shares)
        while qty > 0:
            amount = qty * price; fee = buy_fee(amount); total_fee = float(fee.get("total_fee", 0.0))
            if amount + total_fee <= cash + 1e-9: break
            qty -= _LOT
        if qty <= 0: return False
        amount = qty * price; fee = buy_fee(amount); total_fee = float(fee.get("total_fee", 0.0))
        old = average_cost * shares; cash -= amount + total_fee; shares += qty
        average_cost = (old + amount + total_fee) / shares; last_buy = i
        record("buy", qty, price, fee, i, reason); return True

    def sell_to(i, target, reason):
        nonlocal cash, shares, average_cost, last_buy
        price = float(data.at[i, "收盘"]); assets = cash + shares * price
        allowed = math.floor(assets * target / price / _LOT) * _LOT
        qty = shares if target == 0 else max(0, math.ceil((shares - allowed) / _LOT) * _LOT)
        qty = min(qty, shares)
        if qty <= 0: return False
        amount = qty * price; fee = sell_fee(amount); total_fee = float(fee.get("total_fee", 0.0))
        pnl = (price - average_cost) * qty - total_fee
        cash += amount - total_fee; shares -= qty
        record("sell", qty, price, fee, i, reason, pnl)
        if shares == 0: average_cost = 0.0; last_buy = None
        return True

    h = data["_macd_histogram"]; dif = data["_macd_dif"]; dea = data["_macd_dea"]
    for i in range(len(data)):
        close = float(data.at[i, "收盘"]); m20 = data.at[i, "_maw20"]; m60 = data.at[i, "_maw60"]; m120 = data.at[i, "_maw120"]
        valid = not any(pd.isna(x) for x in (m20, m60, m120, data.at[i, "_maw60_lag"], data.at[i, "_maw120_lag"]))
        improving = i > 0 and h.iloc[i] > h.iloc[i - 1]
        cross = i > 0 and dif.iloc[i] > dea.iloc[i] and dif.iloc[i - 1] <= dea.iloc[i - 1]
        strong = valid and close > m20 > m60 > m120 and m60 > data.at[i, "_maw60_lag"] and m120 > data.at[i, "_maw120_lag"]
        normal = valid and close > m60 > m120 and m60 > data.at[i, "_maw60_lag"]
        recovery = i > 0 and normal and close >= m20 and data.at[i - 1, "收盘"] < data.at[i - 1, "_maw20"] and improving
        target = 0.85 if recovery else 1.0 if strong else 0.7 if normal else 0.0
        targets.append(target)
        assets = cash + shares * close; ratio = shares * close / assets if assets > 0 else 0.0; acted = False
        if shares:
            loss = (close - average_cost) / average_cost
            lookback = range(i - 2, i + 1)
            below120 = (
                i >= 2
                and all(pd.notna(data.at[j, "收盘"]) and pd.notna(data.at[j, "_maw120"]) for j in lookback)
                and all(data.at[j, "收盘"] < data.at[j, "_maw120"] for j in lookback)
            )
            lookback = range(i - 2, i + 1)
            below60 = (
                i >= 2
                and all(pd.notna(data.at[j, "收盘"]) and pd.notna(data.at[j, "_maw60"]) for j in lookback)
                and all(data.at[j, "收盘"] < data.at[j, "_maw60"] for j in lookback)
            )
            lookback = range(i - 2, i + 1)
            weak = (
                i >= 2
                and pd.notna(m60)
                and close < m60
                and all(pd.notna(dif.iloc[j]) and pd.notna(dea.iloc[j]) for j in lookback)
                and all(dif.iloc[j] < dea.iloc[j] for j in lookback)
            )
            if loss <= -0.25: sell_to(i, 0, "成本亏损25%清仓"); acted = True
            elif valid and m60 < m120: sell_to(i, 0, "MAW60跌破MAW120清仓"); acted = True
            elif below120: sell_to(i, 0, "跌破MAW120三日清仓"); acted = True
            elif below60:
                if ratio - 0.30 >= delta: sell_to(i, 0.30, "跌破MAW60三日减仓")
                acted = True
            elif weak:
                if ratio - 0.50 >= delta: sell_to(i, 0.50, "MAW60下方MACD弱势减仓")
                acted = True
        if not acted and target and (last_buy is None or i - last_buy >= interval):
            assets = cash + shares * close; ratio = shares * close / assets if assets > 0 else 0.0
            if shares == 0 and (improving or cross): buy_to(i, target, "强趋势开仓" if strong else "上升趋势开仓")
            elif target - ratio >= delta:
                reason = "回撤恢复加仓" if recovery else "强趋势加仓" if strong else "上升趋势加仓"
                buy_to(i, target, reason)
        assets = cash + shares * close; ratios.append(shares * close / assets if assets > 0 else 0.0)

    series = {"maw20": [_value(v) for v in data["_maw20"]], "maw60": [_value(v) for v in data["_maw60"]],
        "maw120": [_value(v) for v in data["_maw120"]], "macd_dif": [_value(v) for v in dif],
        "macd_dea": [_value(v) for v in dea], "macd_histogram": [_value(v) for v in h],
        "target_position": targets, "position_ratio": ratios}
    return trades, cash, shares, series
