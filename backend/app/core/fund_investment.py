from decimal import Decimal

import pandas as pd


def _to_decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _to_decimal_or_default(value: object, default: str) -> Decimal:
    if pd.isna(value):
        return Decimal(default)
    return _to_decimal(value)


def _to_float(value: Decimal) -> float:
    return float(value)


def select_weekly_investment_dates(
    df: pd.DataFrame,
    start_date: str,
    weekday: int,
) -> list[dict]:
    if weekday not in range(1, 6):
        raise ValueError("weekday 必须为 1 到 5")

    start = pd.Timestamp(start_date).normalize()
    dates = pd.to_datetime(df["日期"], errors="raise").sort_values()
    result = []

    iso = dates.dt.isocalendar()
    for (iso_year, iso_week), week_dates in dates.groupby([iso.year, iso.week]):
        monday = pd.Timestamp.fromisocalendar(int(iso_year), int(iso_week), 1)
        target = monday + pd.Timedelta(days=weekday - 1)
        eligible = week_dates[(week_dates <= target) & (week_dates >= start)]
        if eligible.empty:
            continue
        execution = eligible.max()
        result.append({
            "scheduled_date": target.strftime("%Y-%m-%d"),
            "execution_date": execution.strftime("%Y-%m-%d"),
            "advanced": execution != target,
        })

    return result


def run_weekly_investment(
    df: pd.DataFrame,
    start_date: str,
    weekday: int,
    amount: float,
) -> dict:
    if df is None or df.empty:
        raise ValueError("基金净值数据不能为空")
    if amount <= 0:
        raise ValueError("amount 必须大于 0")

    start = pd.Timestamp(start_date).normalize()
    working = df.copy()
    working["_date"] = pd.to_datetime(working["日期"], errors="raise")
    working = working.sort_values("_date").reset_index(drop=True)

    latest_date = working["_date"].iloc[-1].normalize()
    if start > latest_date:
        raise ValueError("开始日期晚于最新净值日")

    selected_dates = {
        item["execution_date"]: item
        for item in select_weekly_investment_dates(working, start_date, weekday)
    }

    active_rows = working.loc[working["_date"] >= start].reset_index(drop=True)
    amount_decimal = _to_decimal(amount)
    shares = Decimal("0")
    total_invested = Decimal("0")
    investment_count = 0
    dates = []
    total_invested_series = []
    asset_value_series = []
    return_series = []
    events = []

    for _, row in active_rows.iterrows():
        date = row["日期"]
        nav = _to_decimal(row["单位净值"])

        split_ratio = _to_decimal_or_default(row["拆分折算比例"], "1")
        if split_ratio != Decimal("1"):
            shares_before = shares
            shares = shares * split_ratio
            if shares_before != Decimal("0"):
                events.append({
                    "event_type": "split",
                    "date": date,
                    "split_type": "" if pd.isna(row["拆分类型"]) else str(row["拆分类型"]),
                    "split_ratio": _to_float(split_ratio),
                    "shares_before": _to_float(shares_before),
                    "shares_after": _to_float(shares),
                })

        dividend_per_share = _to_decimal_or_default(row["每份分红"], "0")
        if dividend_per_share != Decimal("0"):
            dividend_cash = shares * dividend_per_share
            acquired_shares = dividend_cash / nav
            shares = shares + acquired_shares
            if dividend_cash != Decimal("0"):
                events.append({
                    "event_type": "dividend",
                    "date": date,
                    "dividend_per_share": _to_float(dividend_per_share),
                    "dividend_cash": _to_float(dividend_cash),
                    "acquired_shares": _to_float(acquired_shares),
                    "shares_after": _to_float(shares),
                })

        scheduled = selected_dates.get(date)
        if scheduled is not None:
            acquired_shares = amount_decimal / nav
            shares = shares + acquired_shares
            total_invested = total_invested + amount_decimal
            investment_count += 1
            events.append({
                "event_type": "investment",
                "date": date,
                "scheduled_date": scheduled["scheduled_date"],
                "advanced": scheduled["advanced"],
                "nav": _to_float(nav),
                "amount": _to_float(amount_decimal),
                "acquired_shares": _to_float(acquired_shares),
                "shares_after": _to_float(shares),
            })

        asset_value = shares * nav
        total_profit = asset_value - total_invested
        total_return = (
            Decimal("0")
            if total_invested == Decimal("0")
            else total_profit / total_invested
        )

        dates.append(date)
        total_invested_series.append(_to_float(total_invested))
        asset_value_series.append(_to_float(asset_value))
        return_series.append(_to_float(total_return))

    latest_nav = _to_decimal(active_rows.iloc[-1]["单位净值"])
    current_value = shares * latest_nav
    total_profit = current_value - total_invested
    total_return = (
        Decimal("0")
        if total_invested == Decimal("0")
        else total_profit / total_invested
    )

    return {
        "summary": {
            "investment_count": investment_count,
            "total_invested": _to_float(total_invested),
            "final_shares": _to_float(shares),
            "latest_nav": _to_float(latest_nav),
            "current_value": _to_float(current_value),
            "total_profit": _to_float(total_profit),
            "total_return": _to_float(total_return),
        },
        "dates": dates,
        "total_invested_series": total_invested_series,
        "asset_value_series": asset_value_series,
        "return_series": return_series,
        "events": events,
    }
