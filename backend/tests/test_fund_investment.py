import pandas as pd
import pytest

from app.core.fund_investment import (
    run_weekly_investment,
    select_weekly_investment_dates,
)


def make_fund_df(rows):
    frame = pd.DataFrame(rows)
    frame["基金代码"] = "000001"
    frame["基金名称"] = "示例基金"
    frame["基金类型"] = "混合型"
    frame["日增长率"] = 0.0
    frame["每份分红"] = frame.get("每份分红", 0.0)
    frame["拆分类型"] = frame.get("拆分类型", "")
    frame["拆分折算比例"] = frame.get("拆分折算比例", 1.0)
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
