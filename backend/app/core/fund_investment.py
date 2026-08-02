import math
from decimal import Decimal

import pandas as pd


SMART_RSI_PERIOD = 14
SMART_SELL_POSITION_RETURN = Decimal("0.90")
SMART_SELL_RSI = Decimal("70")


def _to_decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _validated_decimal(
    value: object,
    label: str,
    *,
    positive: bool = False,
) -> Decimal:
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label}必须为有限数值") from exc
    if not math.isfinite(numeric):
        raise ValueError(f"{label}必须为有限数值")
    if positive and numeric <= 0:
        raise ValueError(f"{label}必须大于 0")
    return _to_decimal(value)


def _validated_decimal_or_default(
    value: object,
    default: str,
    label: str,
) -> Decimal:
    if pd.isna(value):
        return Decimal(default)
    return _validated_decimal(value, label)


def _to_float(value: Decimal) -> float:
    return float(value)


def _prepare_fund_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        raise ValueError("基金净值数据不能为空")

    working = df.copy()
    working["_date"] = pd.to_datetime(working["日期"], errors="raise")
    working = working.sort_values("_date").reset_index(drop=True)

    navs = []
    split_ratios = []
    dividends = []
    signal_indexes = []
    previous_nav = None
    signal_index = Decimal("1")

    for _, row in working.iterrows():
        nav = _validated_decimal(
            row["单位净值"],
            "单位净值",
            positive=True,
        )
        split_ratio = _validated_decimal(
            row["拆分折算比例"],
            "拆分折算比例",
            positive=True,
        )
        dividend = _validated_decimal_or_default(
            row["每份分红"],
            "0",
            "每份分红",
        )

        if previous_nav is not None:
            adjusted_value = nav + dividend
            if adjusted_value <= Decimal("0"):
                raise ValueError("单位净值与每份分红之和必须大于 0")
            signal_index = (
                signal_index
                * split_ratio
                * adjusted_value
                / previous_nav
            )

        navs.append(nav)
        split_ratios.append(split_ratio)
        dividends.append(dividend)
        signal_indexes.append(signal_index)
        previous_nav = nav

    working["_nav"] = navs
    working["_split_ratio"] = split_ratios
    working["_dividend_per_share"] = dividends
    working["_signal_index"] = signal_indexes
    return working


def _smart_buy_rule(drawdown: Decimal) -> tuple[Decimal, bool]:
    if drawdown <= Decimal("-0.50"):
        return Decimal("5.0"), True
    if drawdown <= Decimal("-0.45"):
        return Decimal("3.0"), True
    if drawdown <= Decimal("-0.40"):
        return Decimal("0.5"), False
    return Decimal("0"), False


def _weekly_wilder_rsi(
    values: list[Decimal],
    period: int = SMART_RSI_PERIOD,
) -> Decimal | None:
    if len(values) <= period:
        return None
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(change, Decimal("0")) for change in changes]
    losses = [max(-change, Decimal("0")) for change in changes]
    average_gain = sum(gains[:period]) / Decimal(period)
    average_loss = sum(losses[:period]) / Decimal(period)
    for gain, loss in zip(gains[period:], losses[period:]):
        average_gain = (
            average_gain * Decimal(period - 1) + gain
        ) / Decimal(period)
        average_loss = (
            average_loss * Decimal(period - 1) + loss
        ) / Decimal(period)
    if average_loss == 0:
        return Decimal("100")
    relative_strength = average_gain / average_loss
    return Decimal("100") - Decimal("100") / (
        Decimal("1") + relative_strength
    )


def select_weekly_investment_dates(
    df: pd.DataFrame,
    start_date: str,
    weekday: int,
) -> list[dict]:
    if weekday not in range(1, 6):
        raise ValueError("weekday 必须为 1 到 5")

    start = pd.Timestamp(start_date).normalize()
    dates = pd.to_datetime(df["日期"], errors="raise").sort_values()
    latest_date = dates.max().normalize()
    result = []

    iso = dates.dt.isocalendar()
    for (iso_year, iso_week), week_dates in dates.groupby([iso.year, iso.week]):
        monday = pd.Timestamp.fromisocalendar(int(iso_year), int(iso_week), 1)
        target = monday + pd.Timedelta(days=weekday - 1)
        if target > latest_date:
            continue
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


def _apply_corporate_actions(
    row: pd.Series,
    date: str,
    shares: Decimal,
    events: list[dict],
) -> Decimal:
    split_ratio = row["_split_ratio"]
    if split_ratio != Decimal("1"):
        shares_before = shares
        shares = shares * split_ratio
        if shares_before != Decimal("0"):
            events.append({
                "event_type": "split",
                "date": date,
                "split_type": (
                    ""
                    if pd.isna(row["拆分类型"])
                    else str(row["拆分类型"])
                ),
                "split_ratio": _to_float(split_ratio),
                "shares_before": _to_float(shares_before),
                "shares_after": _to_float(shares),
            })

    dividend_per_share = row["_dividend_per_share"]
    if dividend_per_share != Decimal("0"):
        dividend_cash = shares * dividend_per_share
        acquired_shares = dividend_cash / row["_nav"]
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

    return shares


def run_weekly_investment(
    df: pd.DataFrame,
    start_date: str,
    weekday: int,
    amount: float,
) -> dict:
    if df is None or df.empty:
        raise ValueError("基金净值数据不能为空")
    amount_decimal = _validated_decimal(amount, "amount", positive=True)
    start = pd.Timestamp(start_date).normalize()
    working = _prepare_fund_rows(df)
    latest_date = working["_date"].iloc[-1].normalize()
    if start > latest_date:
        raise ValueError("开始日期晚于最新净值日")

    selected_dates = {
        item["execution_date"]: item
        for item in select_weekly_investment_dates(working, start_date, weekday)
    }

    active_rows = working.loc[working["_date"] >= start].reset_index(drop=True)
    shares = Decimal("0")
    total_invested = Decimal("0")
    investment_count = 0
    dates = []
    total_invested_series = []
    asset_value_series = []
    return_series = []
    cash_balance_series = []
    signal_index_series = []
    events = []

    for _, row in active_rows.iterrows():
        date = row["_date"].strftime("%Y-%m-%d")
        nav = row["_nav"]
        shares = _apply_corporate_actions(row, date, shares, events)

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
        cash_balance_series.append(0.0)
        signal_index_series.append(_to_float(row["_signal_index"]))

    latest_nav = active_rows.iloc[-1]["_nav"]
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
            "decision_count": investment_count,
            "buy_count": investment_count,
            "sell_count": 0,
            "total_invested": _to_float(total_invested),
            "final_shares": _to_float(shares),
            "latest_nav": _to_float(latest_nav),
            "fund_value": _to_float(current_value),
            "cash_balance": 0.0,
            "current_value": _to_float(current_value),
            "total_sale_proceeds": 0.0,
            "realized_profit": 0.0,
            "total_profit": _to_float(total_profit),
            "total_return": _to_float(total_return),
        },
        "dates": dates,
        "total_invested_series": total_invested_series,
        "asset_value_series": asset_value_series,
        "return_series": return_series,
        "cash_balance_series": cash_balance_series,
        "signal_index_series": signal_index_series,
        "events": events,
    }


def run_smart_dip_investment(
    df: pd.DataFrame,
    start_date: str,
    weekday: int,
    amount: float,
) -> dict:
    if df is None or df.empty:
        raise ValueError("基金净值数据不能为空")
    amount_decimal = _validated_decimal(amount, "amount", positive=True)
    start = pd.Timestamp(start_date).normalize()
    working = _prepare_fund_rows(df)
    latest_date = working["_date"].iloc[-1].normalize()
    if start > latest_date:
        raise ValueError("开始日期晚于最新净值日")

    history_start = working["_date"].iloc[0].strftime("%Y-%m-%d")
    selected_dates = {
        item["execution_date"]: item
        for item in select_weekly_investment_dates(
            working,
            history_start,
            weekday,
        )
    }

    shares = Decimal("0")
    cost_basis = Decimal("0")
    cash_balance = Decimal("0")
    total_invested = Decimal("0")
    total_sale_proceeds = Decimal("0")
    realized_profit = Decimal("0")
    running_peak = Decimal("0")
    previous_snapshot = None
    weekly_signal_history = []
    decision_count = 0
    buy_count = 0
    sell_count = 0
    dates = []
    total_invested_series = []
    asset_value_series = []
    return_series = []
    cash_balance_series = []
    signal_index_series = []
    events = []

    for _, row in working.iterrows():
        date_value = row["_date"].normalize()
        date = date_value.strftime("%Y-%m-%d")
        nav = row["_nav"]
        signal_index = row["_signal_index"]
        running_peak = max(running_peak, signal_index)

        shares = _apply_corporate_actions(row, date, shares, events)

        scheduled = selected_dates.get(date)
        if scheduled is not None:
            if date_value >= start and previous_snapshot is not None:
                decision_count += 1
                signal_rsi = previous_snapshot["rsi"]
                signal_position_return = previous_snapshot[
                    "position_return"
                ]
                qualifies_for_sale = (
                    shares > Decimal("0")
                    and signal_position_return is not None
                    and signal_position_return
                    >= SMART_SELL_POSITION_RETURN
                    and signal_rsi is not None
                    and signal_rsi >= SMART_SELL_RSI
                )

                if qualifies_for_sale:
                    shares_before = shares
                    sold_shares = shares
                    proceeds = sold_shares * nav
                    realized = proceeds - cost_basis
                    cash_balance += proceeds
                    total_sale_proceeds += proceeds
                    realized_profit += realized
                    shares = Decimal("0")
                    cost_basis = Decimal("0")
                    sell_count += 1
                    events.append({
                        "event_type": "smart_sell",
                        "date": date,
                        "scheduled_date": scheduled["scheduled_date"],
                        "advanced": scheduled["advanced"],
                        "signal_date": previous_snapshot["date"],
                        "nav": _to_float(nav),
                        "position_return": _to_float(
                            signal_position_return
                        ),
                        "rsi": _to_float(signal_rsi),
                        "shares_before": _to_float(shares_before),
                        "sold_shares": _to_float(sold_shares),
                        "proceeds": _to_float(proceeds),
                        "realized_profit": _to_float(realized),
                        "shares_after": _to_float(shares),
                        "cash_balance_after": _to_float(cash_balance),
                    })
                else:
                    multiplier, reuse_cash = _smart_buy_rule(
                        previous_snapshot["drawdown"]
                    )
                    if multiplier > Decimal("0"):
                        contribution = amount_decimal * multiplier
                        reused_cash = (
                            cash_balance
                            if reuse_cash
                            else Decimal("0")
                        )
                        purchase_amount = contribution + reused_cash
                        acquired_shares = purchase_amount / nav
                        shares += acquired_shares
                        cost_basis += purchase_amount
                        cash_balance -= reused_cash
                        total_invested += contribution
                        buy_count += 1
                        events.append({
                            "event_type": "smart_buy",
                            "date": date,
                            "scheduled_date": scheduled["scheduled_date"],
                            "advanced": scheduled["advanced"],
                            "signal_date": previous_snapshot["date"],
                            "nav": _to_float(nav),
                            "drawdown": _to_float(
                                previous_snapshot["drawdown"]
                            ),
                            "rsi": (
                                None
                                if signal_rsi is None
                                else _to_float(signal_rsi)
                            ),
                            "multiplier": _to_float(multiplier),
                            "contribution_amount": _to_float(contribution),
                            "reused_cash": _to_float(reused_cash),
                            "purchase_amount": _to_float(purchase_amount),
                            "acquired_shares": _to_float(acquired_shares),
                            "shares_after": _to_float(shares),
                            "cash_balance_after": _to_float(
                                cash_balance
                            ),
                        })

            weekly_signal_history.append(signal_index)
            current_rsi = _weekly_wilder_rsi(
                weekly_signal_history,
                SMART_RSI_PERIOD,
            )
            position_return = (
                None
                if cost_basis == Decimal("0")
                else shares * nav / cost_basis - Decimal("1")
            )
            previous_snapshot = {
                "date": date,
                "drawdown": signal_index / running_peak - Decimal("1"),
                "rsi": current_rsi,
                "position_return": position_return,
            }

        if date_value >= start:
            fund_value = shares * nav
            current_value = fund_value + cash_balance
            total_profit = current_value - total_invested
            total_return = (
                Decimal("0")
                if total_invested == Decimal("0")
                else total_profit / total_invested
            )

            dates.append(date)
            total_invested_series.append(_to_float(total_invested))
            asset_value_series.append(_to_float(current_value))
            return_series.append(_to_float(total_return))
            cash_balance_series.append(_to_float(cash_balance))
            signal_index_series.append(_to_float(signal_index))

    latest_nav = working.iloc[-1]["_nav"]
    fund_value = shares * latest_nav
    current_value = fund_value + cash_balance
    total_profit = current_value - total_invested
    total_return = (
        Decimal("0")
        if total_invested == Decimal("0")
        else total_profit / total_invested
    )

    return {
        "summary": {
            "investment_count": buy_count,
            "decision_count": decision_count,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "total_invested": _to_float(total_invested),
            "final_shares": _to_float(shares),
            "latest_nav": _to_float(latest_nav),
            "fund_value": _to_float(fund_value),
            "cash_balance": _to_float(cash_balance),
            "current_value": _to_float(current_value),
            "total_sale_proceeds": _to_float(total_sale_proceeds),
            "realized_profit": _to_float(realized_profit),
            "total_profit": _to_float(total_profit),
            "total_return": _to_float(total_return),
        },
        "dates": dates,
        "total_invested_series": total_invested_series,
        "asset_value_series": asset_value_series,
        "return_series": return_series,
        "cash_balance_series": cash_balance_series,
        "signal_index_series": signal_index_series,
        "events": events,
    }
