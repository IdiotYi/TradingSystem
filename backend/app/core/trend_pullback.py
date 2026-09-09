"""MAW + MACD trend-pullback backtest state machine."""
from collections.abc import Callable
import math

import pandas as pd

from app.core.indicators import calc_macd, calc_maw

_REQUIRED_FIELDS = {"日期", "收盘", "成交量", "成交额", "换手率"}
_LOT = 100


def _value(value):
    return None if pd.isna(value) else float(value)


def _fee_total(fee_fn: Callable[[float], dict], amount: float) -> float:
    return float(fee_fn(float(amount)).get("total_fee", 0.0))


def run_trend_pullback(
    df: pd.DataFrame,
    initial_cash: float,
    buy_fee: Callable[[float], dict],
    sell_fee: Callable[[float], dict],
) -> tuple[list[dict], float, int, dict]:
    """Run the strategy sequentially, executing at each bar's closing price."""
    missing = _REQUIRED_FIELDS.difference(df.columns)
    if missing:
        raise ValueError(f"MAW 必需字段缺失: {', '.join(sorted(missing))}")

    data = df.reset_index(drop=True).copy()
    maw20 = calc_maw(data, 20)
    maw60 = calc_maw(data, 60)
    maw120 = calc_maw(data, 120)
    dif, dea, histogram = calc_macd(data["收盘"])
    if len(data) and any(series.notna().sum() == 0 for series in (maw20, maw60, maw120)):
        raise ValueError("MAW required fields produced no valid values")

    target_positions: list[float] = []
    position_ratios: list[float] = []
    trades: list[dict] = []
    cash = float(initial_cash)
    shares = 0
    average_cost = 0.0
    last_buy_price: float | None = None
    last_buy_index: int | None = None

    def record(action: str, quantity: int, price: float, fee: float, date, reason: str) -> None:
        trades.append({
            "date": str(date),
            "signal_date": str(date),
            "action": action,
            "price": float(price),
            "shares": int(quantity),
            "amount": float(quantity * price),
            "fee": float(fee),
            "reason": reason,
        })

    def sell_to_ratio(i: int, target: float, reason: str) -> bool:
        nonlocal cash, shares, average_cost, last_buy_price, last_buy_index
        price = float(data.at[i, "收盘"])
        total_assets = cash + shares * price
        maximum_shares = math.floor((total_assets * target) / price / _LOT) * _LOT
        quantity = shares if target == 0 else max(0, math.ceil((shares - maximum_shares) / _LOT) * _LOT)
        quantity = min(shares, quantity)
        if quantity <= 0:
            return False
        amount = quantity * price
        fee = _fee_total(sell_fee, amount)
        cash += amount - fee
        shares -= quantity
        record("sell", quantity, price, fee, data.at[i, "日期"], reason)
        if shares == 0:
            average_cost = 0.0
            last_buy_price = None
            last_buy_index = None
        return True

    def buy_to_ratio(i: int, target: float, reason: str) -> bool:
        nonlocal cash, shares, average_cost, last_buy_price, last_buy_index
        price = float(data.at[i, "收盘"])
        total_assets = cash + shares * price
        desired = math.floor((total_assets * min(target, 0.8)) / price / _LOT) * _LOT
        quantity = max(0, desired - shares)
        while quantity > 0:
            amount = quantity * price
            fee = _fee_total(buy_fee, amount)
            if amount + fee <= cash + 1e-9:
                break
            quantity -= _LOT
        if quantity <= 0:
            return False
        amount = quantity * price
        fee = _fee_total(buy_fee, amount)
        old_cost = average_cost * shares
        cash -= amount + fee
        shares += quantity
        average_cost = (old_cost + amount + fee) / shares
        last_buy_price = price
        last_buy_index = i
        record("buy", quantity, price, fee, data.at[i, "日期"], reason)
        return True

    for i in range(len(data)):
        close = float(data.at[i, "收盘"])
        m20, m60, m120 = maw20.iloc[i], maw60.iloc[i], maw120.iloc[i]
        valid = not any(pd.isna(value) for value in (m20, m60, m120))
        hist_improving = i > 0 and histogram.iloc[i] > histogram.iloc[i - 1]
        bullish_cross = i > 0 and dif.iloc[i] > dea.iloc[i] and dif.iloc[i - 1] <= dea.iloc[i - 1]
        confirmation = hist_improving or bullish_cross
        healthy = (
            valid and i >= 20 and close > m120 and m60 > m120
            and not pd.isna(maw60.iloc[i - 20]) and m60 > maw60.iloc[i - 20]
        )

        target = 0.0
        if healthy and confirmation:
            if close <= m60 * 1.02:
                target = 0.8
            elif close < m20 and close > m60 * 1.02:
                target = 0.6
            elif close <= m20 * 1.03:
                target = 0.4
        target_positions.append(target)

        total_assets = cash + shares * close
        current_ratio = shares * close / total_assets if total_assets > 0 else 0.0
        acted = False
        if shares > 0:
            loss = (close - average_cost) / average_cost
            below120_two = i > 0 and close < m120 and data.at[i - 1, "收盘"] < maw120.iloc[i - 1]
            below60_two = i > 0 and close < m60 and data.at[i - 1, "收盘"] < maw60.iloc[i - 1]
            bearish_cross = i > 0 and dif.iloc[i] < dea.iloc[i] and dif.iloc[i - 1] >= dea.iloc[i - 1]
            shrinking_three = i >= 2 and histogram.iloc[i] < histogram.iloc[i - 1] < histogram.iloc[i - 2]
            cross_below20 = (
                i > 0 and close < m20 and data.at[i - 1, "收盘"] >= maw20.iloc[i - 1]
                and m20 <= maw20.iloc[i - 1]
            )
            if loss <= -0.18:
                acted = sell_to_ratio(i, 0.0, "成本亏损18%清仓")
            elif valid and m60 < m120:
                acted = sell_to_ratio(i, 0.0, "MAW60跌破MAW120清仓")
            elif valid and below120_two:
                acted = sell_to_ratio(i, 0.0, "跌破MAW120两日清仓")
            else:
                risk_target = 1.0
                risk_reason = ""
                if below60_two:
                    risk_target, risk_reason = 0.4, "跌破MAW60减仓"
                if loss <= -0.12 and 0.3 < risk_target:
                    risk_target, risk_reason = 0.3, "成本亏损12%减仓"
                if risk_target < current_ratio:
                    acted = sell_to_ratio(i, risk_target, risk_reason)
                else:
                    profit_targets: list[tuple[float, str]] = []
                    if valid and close >= m20 * 1.12 and shrinking_three:
                        profit_targets.append((0.7, "高位动能减仓"))
                    if valid and close >= m20 * 1.20 and bearish_cross:
                        profit_targets.append((0.4, "高位死叉止盈"))
                    if loss > 0 and valid and cross_below20:
                        profit_targets.append((0.2, "跌破MAW20止盈"))
                    if profit_targets:
                        profit_target, profit_reason = min(profit_targets, key=lambda item: item[0])
                        if profit_target < current_ratio:
                            acted = sell_to_ratio(i, profit_target, profit_reason)

        if not acted and target >= 0.4:
            total_assets = cash + shares * close
            current_ratio = shares * close / total_assets if total_assets > 0 else 0.0
            if shares == 0:
                buy_to_ratio(i, target, "趋势回撤开仓")
            elif target - current_ratio >= 0.10:
                recovered_m20 = (
                    i > 0 and close >= m20 and data.at[i - 1, "收盘"] < maw20.iloc[i - 1]
                )
                can_add = (
                    last_buy_index is not None and i - last_buy_index >= 5
                    and (close < last_buy_price or recovered_m20)
                    and i > 0 and histogram.iloc[i] >= histogram.iloc[i - 1]
                    and valid and close > m120
                )
                if can_add:
                    buy_to_ratio(i, target, "趋势回撤加仓")

        total_assets = cash + shares * close
        position_ratios.append(shares * close / total_assets if total_assets > 0 else 0.0)

    series = {
        "maw20": [_value(v) for v in maw20],
        "maw60": [_value(v) for v in maw60],
        "maw120": [_value(v) for v in maw120],
        "macd_dif": [_value(v) for v in dif],
        "macd_dea": [_value(v) for v in dea],
        "macd_histogram": [_value(v) for v in histogram],
        "target_position": target_positions,
        "position_ratio": position_ratios,
    }
    return trades, cash, shares, series
