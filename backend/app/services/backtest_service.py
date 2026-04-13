"""
Three-factor momentum backtest engine.
Fee logic and strategy ported from C:/PrivateProjects/TradingStrategy/backtest.py.
"""
import pandas as pd
import numpy as np
from app.core.three_factors import compute_three_factors, BIAS_N, MOMENTUM_DAY, SLOPE_N, EFFICIENCY_N, ZSCORE_WINDOW
from app.core.indicators import calc_ma, calc_supertrend
from app.services.data_service import load_stock_data


# ── Fee helpers ──────────────────────────────────────────────

def _buy_fees(amount: float) -> dict:
    transfer = round(amount * 0.00001, 2)
    commission = round(amount * 0.000075, 2)
    return {"transfer_fee": transfer, "commission": commission,
            "stamp_tax": None, "total_fee": round(transfer + commission, 2)}


def _sell_fees(amount: float) -> dict:
    transfer = round(amount * 0.00001, 2)
    stamp = round(amount * 0.0005, 2)
    commission = round(amount * 0.000075, 2)
    return {"transfer_fee": transfer, "commission": commission,
            "stamp_tax": stamp, "total_fee": round(transfer + stamp + commission, 2)}


# ── Strategy ─────────────────────────────────────────────────

def _run_strategy(df: pd.DataFrame, initial_cash: float, params: dict) -> tuple:
    score_rising_days = params.get("score_rising_days", 3)
    oversold_mult = params.get("oversold_std_mult", 2.0)
    tp_pct = params.get("take_profit_pct", 0.15)
    tp_mult = params.get("take_profit_std_mult", 1.5)
    sl_pct = params.get("stop_loss_pct", 0.05)
    add_pct = params.get("add_position_pct", 0.05)
    half_ratio = params.get("half_position_ratio", 0.5)

    trades = []
    cash = initial_cash
    shares = 0
    entry_price = 0.0
    position = "none"   # none | half | full

    def sell_all(row, reason):
        nonlocal cash, shares, entry_price, position
        price = float(row["收盘"])
        amount = shares * price
        fees = _sell_fees(amount)
        cash += amount - fees["total_fee"]
        trades.append({
            "date": row["日期"], "direction": "卖出", "reason": reason,
            "price": round(price, 2), "shares": shares,
            "amount": round(amount, 2), **fees,
            "pnl": round((price - entry_price) * shares - fees["total_fee"], 2),
            "remaining_cash": round(cash, 2),
        })
        shares = 0; entry_price = 0.0; position = "none"

    def buy(row, budget, reason):
        nonlocal cash, shares, entry_price, position
        price = float(row["收盘"])
        n = int(budget // (price * 100)) * 100
        if n == 0:
            return 0
        amount = n * price
        fees = _buy_fees(amount)
        while n > 0 and (amount + fees["total_fee"]) > budget:
            n -= 100; amount = n * price; fees = _buy_fees(amount)
        if n == 0:
            return 0
        entry_price = (shares * entry_price + n * price) / (shares + n)
        cash -= amount + fees["total_fee"]
        shares += n
        trades.append({
            "date": row["日期"], "direction": "买入", "reason": reason,
            "price": round(price, 2), "shares": n,
            "amount": round(amount, 2), **fees,
            "pnl": None, "remaining_cash": round(cash, 2),
        })
        return n

    for i in range(score_rising_days - 1, len(df)):
        row = df.iloc[i]
        price = float(row["收盘"])
        score = row.get("score", float("nan"))
        smean = row.get("score_mean", float("nan"))
        sstd = row.get("score_std", float("nan"))
        acted = False

        # Full position: stop-loss check (priority)
        if position == "full" and (price - entry_price) / entry_price <= -sl_pct:
            sell_all(row, f"全仓亏损{int(sl_pct*100)}%止损")
            acted = True

        # Half/Full: take-profit check
        if not acted and shares > 0:
            valid = pd.notna(smean) and pd.notna(sstd) and sstd > 0
            tp1 = (price - entry_price) / entry_price >= tp_pct
            tp2 = valid and pd.notna(score) and score > smean + tp_mult * sstd
            if tp1 or tp2:
                sell_all(row, f"盈利{int(tp_pct*100)}%止盈" if tp1 else "score超上轨止盈")
                acted = True

        # Half position: add position on dip
        if not acted and position == "half" and (price - entry_price) / entry_price <= -add_pct:
            if buy(row, cash, f"下跌{int(add_pct*100)}%加仓") > 0:
                position = "full"
            acted = True

        # No position: three-factor buy signal
        if not acted and position == "none":
            scores_window = [df.iloc[i - k]["score"] for k in range(score_rising_days - 1, -1, -1)]
            if any(pd.isna(s) for s in scores_window):
                continue
            if pd.isna(smean) or pd.isna(sstd) or sstd == 0:
                continue
            rising = all(scores_window[j] < scores_window[j + 1] for j in range(len(scores_window) - 1))

            def below_lower(r):
                sm, ss = r["score_mean"], r["score_std"]
                return pd.notna(sm) and pd.notna(ss) and ss > 0 and r["score"] < sm - oversold_mult * ss

            oversold = any(below_lower(df.iloc[i - k]) for k in range(score_rising_days))
            if rising and oversold:
                if buy(row, cash * half_ratio, "三因子信号") > 0:
                    position = "half"

    return trades, cash, shares


# ── Buy-and-hold strategy ────────────────────────────────────

def _run_buy_and_hold(df: pd.DataFrame, initial_cash: float) -> tuple:
    """Buy full position on first day and hold."""
    trades = []
    cash = initial_cash
    shares = 0

    row = df.iloc[0]
    price = float(row["收盘"])
    n = int(cash // (price * 100)) * 100
    if n > 0:
        amount = n * price
        fees = _buy_fees(amount)
        while n > 0 and (amount + fees["total_fee"]) > cash:
            n -= 100
            amount = n * price
            fees = _buy_fees(amount)
        if n > 0:
            cash -= amount + fees["total_fee"]
            shares = n
            trades.append({
                "date": row["日期"], "direction": "买入", "reason": "买入持有",
                "price": round(price, 2), "shares": n,
                "amount": round(amount, 2), **fees,
                "pnl": None, "remaining_cash": round(cash, 2),
            })

    return trades, cash, shares


# ── Public API ───────────────────────────────────────────────

def _to_list(s: pd.Series) -> list:
    return [None if pd.isna(v) else round(float(v), 4) for v in s]


def run_backtest(stock_code: str, start_date: str, end_date: str,
                 initial_cash: float, strategy_params: dict,
                 strategy_name: str = "three_factors") -> dict:
    df_all = load_stock_data(stock_code)
    df_all = df_all[df_all["日期"] <= end_date].reset_index(drop=True)

    if strategy_name == "three_factors":
        factors = compute_three_factors(
            df_all,
            bias_n=strategy_params.get("bias_n", BIAS_N),
            momentum_day=strategy_params.get("momentum_day", MOMENTUM_DAY),
            slope_n=strategy_params.get("slope_n", SLOPE_N),
            efficiency_n=strategy_params.get("efficiency_n", EFFICIENCY_N),
            zscore_window=strategy_params.get("zscore_window", ZSCORE_WINDOW),
        )
        df_all = df_all.merge(factors, on="日期", how="left")

    df = df_all[df_all["日期"] >= start_date].reset_index(drop=True)
    if df.empty:
        raise ValueError(f"{start_date} ~ {end_date} 期间无交易数据")

    if strategy_name == "buy_and_hold":
        trades, final_cash, final_shares = _run_buy_and_hold(df, initial_cash)
    else:
        trades, final_cash, final_shares = _run_strategy(df, initial_cash, strategy_params)

    # Indicators for chart
    close = df["收盘"]; high = df["最高"]; low = df["最低"]; open_ = df["开盘"]
    ma5 = calc_ma(close, 5); ma20 = calc_ma(close, 20); ma60 = calc_ma(close, 60)
    st_vals, st_dir = calc_supertrend(high, low, close, period=10, multiplier=3.0)

    # Summary
    last_price = float(close.iloc[-1])
    total_assets = final_shares * last_price + final_cash
    total_return = (total_assets - initial_cash) / initial_cash
    total_fees = sum(t["total_fee"] for t in trades)

    first_price = float(close.iloc[0])
    bh_shares = int(initial_cash // (first_price * 100)) * 100
    bh_cost = _buy_fees(bh_shares * first_price)["total_fee"]
    bh_assets = bh_shares * last_price + (initial_cash - bh_shares * first_price - bh_cost)
    bh_return = (bh_assets - initial_cash) / initial_cash

    def score_list(col):
        if col not in df.columns:
            return [None] * len(df)
        return [None if pd.isna(v) else round(float(v), 6) for v in df[col]]

    return {
        "success": True,
        "dates": df["日期"].tolist(),
        "open": _to_list(open_), "high": _to_list(high),
        "low": _to_list(low), "close": _to_list(close),
        "ma5": _to_list(ma5), "ma20": _to_list(ma20), "ma60": _to_list(ma60),
        "supertrend": _to_list(st_vals),
        "supertrend_direction": [None if pd.isna(v) else int(v) for v in st_dir],
        "score": score_list("score"),
        "score_mean": score_list("score_mean"),
        "score_std": score_list("score_std"),
        "trades": trades,
        "summary": {
            "initial_cash": initial_cash,
            "final_assets": round(total_assets, 2),
            "total_return": round(total_return, 4),
            "total_fees": round(total_fees, 2),
            "benchmark_return": round(bh_return, 4),
            "excess_return": round(total_return - bh_return, 4),
            "final_shares": final_shares,
            "final_cash": round(final_cash, 2),
        },
    }
