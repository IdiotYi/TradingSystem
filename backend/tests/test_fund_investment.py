from decimal import Decimal

import pandas as pd
import pytest

from app.core import fund_investment
from app.core.fund_investment import (
    run_smart_dip_investment,
    run_weekly_investment,
    select_weekly_investment_dates,
)


def make_fund_df(rows):
    frame = pd.DataFrame(rows)
    frame["基金代码"] = "000001"
    frame["基金名称"] = "示例基金"
    frame["基金类型"] = "混合型"
    frame["日增长率"] = 0.0
    frame["每份分红"] = [row.get("每份分红", 0.0) for row in rows]
    frame["拆分类型"] = [row.get("拆分类型", "") for row in rows]
    frame["拆分折算比例"] = [
        row.get("拆分折算比例", 1.0) for row in rows
    ]
    return frame


def test_missing_friday_moves_to_thursday_in_same_week():
    df = make_fund_df([
        {"日期": "2024-01-08", "单位净值": 1.0},
        {"日期": "2024-01-11", "单位净值": 1.1},
        {"日期": "2024-01-15", "单位净值": 1.2},
    ])

    events = select_weekly_investment_dates(df, "2024-01-01", weekday=5)

    assert events[0] == {
        "scheduled_date": "2024-01-12",
        "execution_date": "2024-01-11",
        "advanced": True,
    }


def test_incomplete_current_week_does_not_schedule_future_friday():
    df = make_fund_df([
        {"日期": "2024-01-08", "单位净值": 1.0},
        {"日期": "2024-01-11", "单位净值": 1.1},
    ])

    events = select_weekly_investment_dates(df, "2024-01-01", weekday=5)

    assert events == []


def test_missing_monday_does_not_cross_into_previous_week():
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 1.0},
        {"日期": "2024-01-09", "单位净值": 1.1},
    ])

    events = select_weekly_investment_dates(df, "2024-01-08", weekday=1)

    assert events == []


def test_same_day_order_is_split_then_dividend_then_investment():
    df = make_fund_df([
        {
            "日期": "2024-01-05",
            "单位净值": 1.0,
            "每份分红": 0.0,
            "拆分类型": "",
            "拆分折算比例": 1.0,
        },
        {
            "日期": "2024-01-12",
            "单位净值": 1.0,
            "每份分红": 0.1,
            "拆分类型": "份额折算",
            "拆分折算比例": 2.0,
        },
    ])

    result = run_weekly_investment(
        df, start_date="2024-01-01", weekday=5, amount=100.0
    )

    assert result["events"] == [
        {
            "event_type": "investment",
            "date": "2024-01-05",
            "scheduled_date": "2024-01-05",
            "advanced": False,
            "nav": 1.0,
            "amount": 100.0,
            "acquired_shares": 100.0,
            "shares_after": 100.0,
        },
        {
            "event_type": "split",
            "date": "2024-01-12",
            "split_type": "份额折算",
            "split_ratio": 2.0,
            "shares_before": 100.0,
            "shares_after": 200.0,
        },
        {
            "event_type": "dividend",
            "date": "2024-01-12",
            "dividend_per_share": 0.1,
            "dividend_cash": 20.0,
            "acquired_shares": 20.0,
            "shares_after": 220.0,
        },
        {
            "event_type": "investment",
            "date": "2024-01-12",
            "scheduled_date": "2024-01-12",
            "advanced": False,
            "nav": 1.0,
            "amount": 100.0,
            "acquired_shares": 100.0,
            "shares_after": 320.0,
        },
    ]
    assert result["summary"]["final_shares"] == pytest.approx(320.0)
    assert result["summary"]["total_invested"] == 200.0
    assert [event["event_type"] for event in result["events"]] == [
        "investment", "split", "dividend", "investment"
    ]


def test_summary_uses_fractional_shares_and_latest_nav():
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 3.0},
        {"日期": "2024-01-12", "单位净值": 4.0},
    ])

    result = run_weekly_investment(
        df, start_date="2024-01-01", weekday=5, amount=100.0
    )

    summary = result["summary"]
    assert result["dates"] == ["2024-01-05", "2024-01-12"]
    assert result["asset_value_series"] == [
        pytest.approx(100.0),
        pytest.approx(233.33333333333334),
    ]
    assert result["return_series"] == [
        pytest.approx(0.0),
        pytest.approx(1 / 6),
    ]
    assert summary["investment_count"] == 2
    assert summary["total_invested"] == 200.0
    assert summary["final_shares"] == pytest.approx(100 / 3 + 25)
    assert summary["current_value"] == pytest.approx(
        summary["final_shares"] * 4.0
    )
    assert summary["total_profit"] == pytest.approx(
        summary["current_value"] - 200.0
    )
    assert summary["total_return"] == pytest.approx(
        summary["total_profit"] / 200.0
    )


def test_start_after_latest_nav_is_rejected():
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 1.0},
    ])

    with pytest.raises(ValueError, match="晚于最新净值日"):
        run_weekly_investment(
            df, start_date="2024-02-01", weekday=5, amount=100.0
        )


def test_split_and_dividend_do_not_increase_user_contributions():
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 1.0},
        {
            "日期": "2024-01-12",
            "单位净值": 1.0,
            "每份分红": 0.1,
            "拆分类型": "份额折算",
            "拆分折算比例": 2.0,
        },
    ])

    result = run_weekly_investment(
        df, start_date="2024-01-01", weekday=5, amount=100.0
    )

    assert result["summary"]["total_invested"] == 200.0
    assert result["total_invested_series"][-1] == 200.0


def test_zero_position_days_do_not_emit_split_or_dividend_events():
    df = make_fund_df([
        {
            "日期": "2024-01-04",
            "单位净值": 1.0,
            "每份分红": 0.1,
            "拆分类型": "份额折算",
            "拆分折算比例": 2.0,
        },
        {"日期": "2024-01-05", "单位净值": 1.0},
    ])

    result = run_weekly_investment(
        df, start_date="2024-01-01", weekday=5, amount=100.0
    )

    assert result["events"] == [
        {
            "event_type": "investment",
            "date": "2024-01-05",
            "scheduled_date": "2024-01-05",
            "advanced": False,
            "nav": 1.0,
            "amount": 100.0,
            "acquired_shares": 100.0,
            "shares_after": 100.0,
        }
    ]


def test_empty_data_is_rejected():
    empty = make_fund_df([]).reindex(columns=[
        "日期", "单位净值", "基金代码", "基金名称", "基金类型",
        "日增长率", "每份分红", "拆分类型", "拆分折算比例",
    ])

    with pytest.raises(ValueError, match="不能为空"):
        run_weekly_investment(
            empty, start_date="2024-01-01", weekday=5, amount=100.0
        )


def test_empty_data_is_rejected_before_amount_validation():
    empty = make_fund_df([]).reindex(columns=[
        "日期", "单位净值", "基金代码", "基金名称", "基金类型",
        "日增长率", "每份分红", "拆分类型", "拆分折算比例",
    ])

    with pytest.raises(ValueError, match="不能为空"):
        run_weekly_investment(
            empty, start_date="2024-01-01", weekday=5, amount=0.0
        )


def test_non_positive_amount_is_rejected():
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 1.0},
    ])

    with pytest.raises(ValueError, match="amount"):
        run_weekly_investment(
            df, start_date="2024-01-01", weekday=5, amount=0.0
        )


def test_invalid_start_date_is_rejected():
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 1.0},
    ])

    with pytest.raises(ValueError):
        run_weekly_investment(
            df, start_date="not-a-date", weekday=5, amount=100.0
        )


def test_invalid_weekday_is_rejected():
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 1.0},
    ])

    with pytest.raises(ValueError, match="weekday"):
        run_weekly_investment(
            df, start_date="2024-01-01", weekday=0, amount=100.0
        )


def test_smart_signal_index_adjusts_dividend_and_split():
    df = make_fund_df([
        {
            "日期": "2024-01-05",
            "单位净值": 1.0,
            "每份分红": 0.0,
            "拆分折算比例": 1.0,
        },
        {
            "日期": "2024-01-12",
            "单位净值": 0.45,
            "每份分红": 0.05,
            "拆分折算比例": 2.0,
        },
    ])

    result = run_smart_dip_investment(
        df, start_date="2024-01-01", weekday=5, amount=1000
    )

    assert result["signal_index_series"] == pytest.approx([1.0, 1.0])


@pytest.mark.parametrize(
    ("drawdown", "multiplier", "reuse_cash"),
    [
        ("-0.5000", "5.0", True),
        ("-0.4999", "3.0", True),
        ("-0.4500", "3.0", True),
        ("-0.4499", "0.5", False),
        ("-0.4000", "0.5", False),
        ("-0.3999", "0", False),
    ],
)
def test_smart_buy_tiers_are_exact(drawdown, multiplier, reuse_cash):
    actual_multiplier, actual_reuse = fund_investment._smart_buy_rule(
        Decimal(drawdown)
    )
    assert actual_multiplier == Decimal(multiplier)
    assert actual_reuse is reuse_cash


def test_weekly_wilder_rsi_uses_only_available_values():
    result = fund_investment._weekly_wilder_rsi(
        [Decimal(value) for value in ("1", "2", "3", "2")],
        period=3,
    )

    assert result == pytest.approx(Decimal("66.66666666666666666666666667"))


def test_smart_strategy_uses_previous_week_signal_not_execution_nav():
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 1.00},
        {"日期": "2024-01-12", "单位净值": 0.95},
        {"日期": "2024-01-19", "单位净值": 0.55},
        {"日期": "2024-01-26", "单位净值": 0.56},
    ])

    result = run_smart_dip_investment(
        df, start_date="2024-01-01", weekday=5, amount=1000
    )

    buys = [e for e in result["events"] if e["event_type"] == "smart_buy"]
    assert [event["date"] for event in buys] == ["2024-01-26"]
    assert buys[0]["signal_date"] == "2024-01-19"


def test_smart_strategy_reuses_sale_cash_without_recounting_it(monkeypatch):
    monkeypatch.setattr(
        fund_investment,
        "_weekly_wilder_rsi",
        lambda values, period=14: Decimal("100"),
    )
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 1.0},
        {"日期": "2024-01-12", "单位净值": 0.5},
        {"日期": "2024-01-19", "单位净值": 1.0},
        {"日期": "2024-01-26", "单位净值": 2.0},
        {"日期": "2024-02-02", "单位净值": 2.0},
        {"日期": "2024-02-09", "单位净值": 1.1},
        {"日期": "2024-02-16", "单位净值": 1.1},
    ])

    result = run_smart_dip_investment(
        df, start_date="2024-01-01", weekday=5, amount=1000
    )

    buys = [e for e in result["events"] if e["event_type"] == "smart_buy"]
    sells = [e for e in result["events"] if e["event_type"] == "smart_sell"]
    first_sell = sells[0]
    second_buy = buys[1]
    sale_index = result["dates"].index(first_sell["date"])

    assert result["summary"]["total_invested"] == 8000.0
    assert result["summary"]["total_sale_proceeds"] > 0
    assert result["summary"]["cash_balance"] == 0.0
    assert result["asset_value_series"][sale_index] == pytest.approx(
        first_sell["proceeds"]
    )
    assert second_buy["reused_cash"] == first_sell["proceeds"]
    assert second_buy["contribution_amount"] == 3000.0
    assert second_buy["purchase_amount"] == pytest.approx(
        second_buy["contribution_amount"] + second_buy["reused_cash"]
    )


def test_smart_sell_has_priority_and_fully_liquidates(monkeypatch):
    monkeypatch.setattr(
        fund_investment,
        "_weekly_wilder_rsi",
        lambda values, period=14: Decimal("100"),
    )
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 100.0},
        {"日期": "2024-01-12", "单位净值": 40.0},
        {"日期": "2024-01-19", "单位净值": 1.0},
        {"日期": "2024-01-26", "单位净值": 40.0},
        {"日期": "2024-02-02", "单位净值": 40.0},
    ])

    result = run_smart_dip_investment(
        df, start_date="2024-01-01", weekday=5, amount=1000
    )

    sell_event = next(
        event
        for event in result["events"]
        if event["event_type"] == "smart_sell"
    )
    assert sell_event["sold_shares"] == pytest.approx(
        sell_event["shares_before"]
    )
    assert sell_event["shares_after"] == 0.0
    assert not any(
        event["event_type"] == "smart_buy"
        and event["date"] == sell_event["date"]
        for event in result["events"]
    )


def test_smart_strategy_returns_zero_result_when_drawdown_never_reaches_40_percent():
    rows = [
        {
            "日期": timestamp.strftime("%Y-%m-%d"),
            "单位净值": 1.0 + index * 0.01,
        }
        for index, timestamp in enumerate(
            pd.date_range("2024-01-05", periods=16, freq="7D")
        )
    ]
    result = run_smart_dip_investment(
        make_fund_df(rows),
        start_date="2024-01-01",
        weekday=5,
        amount=1000,
    )
    assert result["summary"]["total_invested"] == 0.0
    assert result["summary"]["total_return"] == 0.0
    assert result["summary"]["buy_count"] == 0
    assert result["summary"]["sell_count"] == 0


@pytest.mark.parametrize("bad_nav", [0, -1, float("nan"), float("inf")])
def test_smart_strategy_rejects_invalid_nav(bad_nav):
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 1.0},
        {"日期": "2024-01-12", "单位净值": bad_nav},
    ])
    with pytest.raises(ValueError, match="单位净值"):
        run_smart_dip_investment(
            df,
            start_date="2024-01-01",
            weekday=5,
            amount=1000,
        )


@pytest.mark.parametrize("bad_split", [0, -1, float("nan"), float("inf")])
def test_smart_strategy_rejects_invalid_split_ratio(bad_split):
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 1.0},
        {
            "日期": "2024-01-12",
            "单位净值": 1.0,
            "拆分折算比例": bad_split,
        },
    ])
    with pytest.raises(ValueError, match="拆分折算比例"):
        run_smart_dip_investment(
            df,
            start_date="2024-01-01",
            weekday=5,
            amount=1000,
        )


@pytest.mark.parametrize(
    "bad_amount",
    [0, -1, float("nan"), float("inf")],
)
def test_smart_strategy_rejects_invalid_base_amount(bad_amount):
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 1.0},
    ])
    with pytest.raises(ValueError, match="amount"):
        run_smart_dip_investment(
            df,
            start_date="2024-01-01",
            weekday=5,
            amount=bad_amount,
        )


def test_weekly_strategy_adds_compatible_unified_fields():
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 1.0},
        {"日期": "2024-01-12", "单位净值": 1.1},
    ])

    result = run_weekly_investment(
        df, start_date="2024-01-01", weekday=5, amount=100.0
    )

    summary = result["summary"]
    assert summary["decision_count"] == summary["investment_count"] == 2
    assert summary["buy_count"] == summary["investment_count"]
    assert summary["sell_count"] == 0
    assert summary["fund_value"] == summary["current_value"]
    assert summary["cash_balance"] == 0.0
    assert summary["total_sale_proceeds"] == 0.0
    assert summary["realized_profit"] == 0.0
    assert result["cash_balance_series"] == [0.0, 0.0]
    assert result["signal_index_series"] == pytest.approx([1.0, 1.1])
