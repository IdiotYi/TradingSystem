import numpy as np
import pandas as pd
import pytest

from app.core.trend_pullback import run_trend_pullback


def no_fee(_amount: float) -> dict:
    return {"total_fee": 0.0}


def make_frame(n: int = 180) -> pd.DataFrame:
    close = np.linspace(80.0, 130.0, n)
    close[-3:] = [124.0, 121.0, 123.0]
    volume = np.full(n, 10_000.0)
    return pd.DataFrame({
        "日期": pd.date_range("2025-01-01", periods=n, freq="B").strftime("%Y-%m-%d"),
        "收盘": close,
        "成交量": volume,
        "成交额": close * volume,
        "换手率": np.full(n, 1.0),
    })


def test_requires_all_maw_fields():
    with pytest.raises(ValueError, match="MAW.*必需字段|MAW.*required fields"):
        run_trend_pullback(make_frame().drop(columns=["成交额"]), 100_000, no_fee, no_fee)


def install_buy_signal(monkeypatch, df):
    n = len(df)

    def fake_maw(_df, period):
        if period == 20:
            values = np.linspace(75.0, 125.0, n)
        elif period == 60:
            values = np.linspace(74.0, 122.0, n)
        else:
            values = np.linspace(70.0, 110.0, n)
        return pd.Series(values, index=_df.index)

    def fake_macd(close):
        dif = pd.Series(np.ones(n), index=close.index)
        dea = pd.Series(np.zeros(n), index=close.index)
        hist = pd.Series(np.arange(n, dtype=float), index=close.index)
        return dif, dea, hist

    monkeypatch.setattr("app.core.trend_pullback.calc_maw", fake_maw)
    monkeypatch.setattr("app.core.trend_pullback.calc_macd", fake_macd)


def test_same_day_signal_close_and_output_contract(monkeypatch):
    df = make_frame()
    install_buy_signal(monkeypatch, df)
    trades, cash, shares, series = run_trend_pullback(df, 100_000, no_fee, no_fee)

    assert trades
    first = trades[0]
    row = df.loc[df["日期"] == first["date"]].iloc[0]
    assert first["reason"] == "趋势回撤开仓"
    assert first["signal_date"] == first["date"]
    assert first["price"] == pytest.approx(row["收盘"])
    assert cash >= 0
    assert shares % 100 == 0
    expected = {"maw20", "maw60", "maw120", "macd_dif", "macd_dea", "macd_histogram", "target_position", "position_ratio"}
    assert set(series) == expected
    assert {len(values) for values in series.values()} == {len(df)}


def test_future_truncation_does_not_change_prior_results():
    df = make_frame(210)
    cutoff = 185
    short = run_trend_pullback(df.iloc[:cutoff].copy(), 100_000, no_fee, no_fee)
    full = run_trend_pullback(df, 100_000, no_fee, no_fee)

    assert full[0][: len(short[0])] == short[0]
    for key, values in short[3].items():
        pd.testing.assert_series_equal(
            pd.Series(full[3][key][:cutoff]), pd.Series(values), check_names=False
        )


def test_position_cash_and_lot_invariants_with_fees(monkeypatch):
    df = make_frame()
    install_buy_signal(monkeypatch, df)

    def fee(amount: float) -> dict:
        return {"total_fee": max(5.0, amount * 0.001)}

    trades, cash, shares, series = run_trend_pullback(df, 100_000, fee, fee)

    assert trades
    assert cash >= 0
    assert shares % 100 == 0
    assert max(series["position_ratio"]) <= 0.8 + 1e-12
    assert all(trade["shares"] % 100 == 0 for trade in trades)


def test_hard_stop_has_priority_over_other_exit_rules(monkeypatch):
    n = 150
    df = make_frame(n)
    df.loc[n - 1, "收盘"] = 80.0

    def fake_maw(_df, period):
        values = np.linspace(70.0, 100.0, n)
        if period == 20:
            values[-2:] = [125.0, 90.0]
        elif period == 60:
            values[-2:] = [122.0, 91.0]
        else:
            values[-2:] = [110.0, 89.0]
        return pd.Series(values, index=_df.index)

    def fake_macd(close):
        dif = pd.Series(np.ones(n), index=close.index)
        dea = pd.Series(np.zeros(n), index=close.index)
        hist = pd.Series(np.linspace(-1.0, 1.0, n), index=close.index)
        return dif, dea, hist

    monkeypatch.setattr("app.core.trend_pullback.calc_maw", fake_maw)
    monkeypatch.setattr("app.core.trend_pullback.calc_macd", fake_macd)
    trades, _, _, _ = run_trend_pullback(df, 100_000, no_fee, no_fee)

    assert trades[-1]["action"] == "sell"
    assert trades[-1]["reason"] == "成本亏损18%清仓"
