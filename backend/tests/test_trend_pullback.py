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

# Review regression helpers/tests: patch deterministic indicator sequences directly.
def install_sequences(monkeypatch, maw20, maw60, maw120, histogram, dif=None, dea=None):
    n = len(maw20)
    lookup = {20: maw20, 60: maw60, 120: maw120}
    monkeypatch.setattr("app.core.trend_pullback.calc_maw", lambda df, period: pd.Series(lookup[period], index=df.index))
    dif_values = np.ones(n) if dif is None else np.asarray(dif, dtype=float)
    dea_values = np.zeros(n) if dea is None else np.asarray(dea, dtype=float)
    monkeypatch.setattr(
        "app.core.trend_pullback.calc_macd",
        lambda close: (pd.Series(dif_values, index=close.index), pd.Series(dea_values, index=close.index), pd.Series(histogram, index=close.index)),
    )


def deterministic_frame(close):
    close = np.asarray(close, dtype=float)
    n = len(close)
    volume = np.full(n, 10_000.0)
    return pd.DataFrame({
        "日期": pd.date_range("2025-01-01", periods=n, freq="B").strftime("%Y-%m-%d"),
        "收盘": close, "成交量": volume, "成交额": close * volume, "换手率": np.ones(n),
    })


def test_exact_target_mapping_40_60_80(monkeypatch):
    n = 145
    close = np.full(n, 130.0); close[-3:] = [123.0, 115.0, 105.0]
    m20 = np.linspace(90, 120, n); m60 = np.linspace(85, 105, n); m120 = np.linspace(70, 90, n)
    hist = np.arange(n, dtype=float)
    install_sequences(monkeypatch, m20, m60, m120, hist)
    *_, series = run_trend_pullback(deterministic_frame(close), 100_000, no_fee, no_fee)
    assert series["target_position"][-3:] == [0.4, 0.6, 0.8]


def test_add_requires_five_bars_and_price_or_recovery_gate(monkeypatch):
    n = 150
    close = np.full(n, 130.0); close[120] = 113.0; close[124] = 108.0; close[125] = 107.0
    m20 = np.linspace(90, 120, n); m60 = np.linspace(80, 104, n); m120 = np.linspace(70, 90, n)
    m20[120] = 112.0; m20[124:126] = [110.0, 110.0]
    m60[120] = 105.0; m60[124:126] = [106.0, 106.0]
    install_sequences(monkeypatch, m20, m60, m120, np.arange(n, dtype=float))
    trades, *_ = run_trend_pullback(deterministic_frame(close), 100_000, no_fee, no_fee)
    buys = [t for t in trades if t["action"] == "buy"]
    assert buys[0]["date"] == deterministic_frame(close).at[120, "日期"]
    assert buys[1]["date"] == deterministic_frame(close).at[125, "日期"]
    assert buys[1]["reason"] == "趋势回撤加仓"


def test_matched_exit_suppresses_same_bar_buy_when_rounding_needs_no_sale(monkeypatch):
    n = 130
    close = np.full(n, 100.0)
    close[120] = 50.0
    close[-2:] = [100.0, 90.0]
    m20 = np.full(n, 75.0)
    m60 = np.full(n, 70.0)
    m120 = np.full(n, 40.0)
    m60[100] = 45.0
    m60[120] = 50.0
    m60[-1] = 90.0
    hist = np.arange(n, dtype=float)
    install_sequences(monkeypatch, m20, m60, m120, hist)

    # The opening buy leaves exactly 100 shares. On the final bar, the high-MAW20
    # momentum exit matches a 70% target, but that target permits 100 shares, so
    # sell_to_ratio rounds the required sale to zero. The bar also satisfies all
    # add gates and targets 80%, proving acted suppression prevents the addition.
    frame = deterministic_frame(close)
    trades, *_ = run_trend_pullback(frame, 9_000, no_fee, no_fee)
    final_date = frame.at[n - 1, "日期"]
    buys = [trade for trade in trades if trade["action"] == "buy"]

    assert [(trade["date"], trade["shares"]) for trade in buys] == [
        (frame.at[120, "日期"], 100)
    ]
    assert not any(trade["action"] == "sell" and trade["date"] == final_date for trade in trades)
    assert not any(trade["action"] == "buy" and trade["date"] == final_date for trade in trades)


def test_fee_inclusive_exposure_never_exceeds_eighty_percent(monkeypatch):
    n = 140; close = np.full(n, 10.0)
    m20 = np.linspace(8, 11, n); m60 = np.linspace(7, 9.9, n); m120 = np.linspace(5, 8, n)
    install_sequences(monkeypatch, m20, m60, m120, np.arange(n, dtype=float))
    def fee(amount): return {"total_fee": amount * 0.10}
    trades, cash, shares, series = run_trend_pullback(deterministic_frame(close), 100_000, fee, no_fee)
    assert trades
    assert max(series["position_ratio"]) <= 0.8 + 1e-12
    assert shares * close[-1] / (cash + shares * close[-1]) <= 0.8 + 1e-12


def test_risk_reduction_prefers_lower_cost_loss_target(monkeypatch):
    n = 145; close = np.full(n, 130.0); close[120] = 105.0; close[-2:] = [89.0, 88.0]
    m20 = np.linspace(90, 120, n); m60 = np.linspace(80, 100, n); m120 = np.linspace(65, 85, n)
    m60[-2:] = [100.0, 100.0]
    install_sequences(monkeypatch, m20, m60, m120, np.arange(n, dtype=float))
    trades, *_ = run_trend_pullback(deterministic_frame(close), 100_000, no_fee, no_fee)
    assert any(t["reason"] == "成本亏损12%减仓" for t in trades)


def test_profit_rules_choose_lowest_target(monkeypatch):
    n = 145; close = np.full(n, 130.0); close[120] = 105.0; close[-2:] = [130.0, 145.0]
    m20 = np.linspace(90, 115, n); m60 = np.linspace(80, 100, n); m120 = np.linspace(65, 90, n)
    hist = np.arange(n, dtype=float); hist[-3:] = [3.0, 2.0, 1.0]
    dif = np.ones(n); dea = np.zeros(n); dif[-2:] = [1.0, -1.0]; dea[-2:] = [0.0, 0.0]
    install_sequences(monkeypatch, m20, m60, m120, hist, dif, dea)
    trades, *_ = run_trend_pullback(deterministic_frame(close), 100_000, no_fee, no_fee)
    assert trades[-1]["reason"] == "高位死叉止盈"

def test_trade_records_lossless_fee_cash_and_sell_pnl(monkeypatch):
    n = 145
    close = np.full(n, 130.0); close[120] = 100.0; close[-1] = 80.0
    m20 = np.linspace(90, 120, n); m60 = np.linspace(80, 105, n); m120 = np.linspace(60, 90, n)
    install_sequences(monkeypatch, m20, m60, m120, np.arange(n, dtype=float))
    def buy_fee(amount): return {"transfer_fee": 1.0, "commission": 2.0, "stamp_tax": None, "total_fee": 3.0}
    def sell_fee(amount): return {"transfer_fee": 1.0, "commission": 2.0, "stamp_tax": 4.0, "total_fee": 7.0}
    trades, cash, _, _ = run_trend_pullback(deterministic_frame(close), 100_000, buy_fee, sell_fee)
    assert trades[0]["remaining_cash"] == pytest.approx(100_000 - trades[0]["amount"] - 3.0)
    assert trades[-1]["transfer_fee"] == 1.0
    assert trades[-1]["commission"] == 2.0
    assert trades[-1]["stamp_tax"] == 4.0
    assert trades[-1]["total_fee"] == 7.0
    assert trades[-1]["pnl"] is not None
    assert trades[-1]["remaining_cash"] == pytest.approx(cash)


def test_configurable_periods_and_buy_interval_are_honored(monkeypatch):
    n = 40; close = np.full(n, 100.0)
    periods = []
    def fake_maw(df, period):
        periods.append(period)
        base = {3: 100.0, 5: 90.0, 8: 70.0}[period]
        return pd.Series(np.linspace(base - 10, base, n), index=df.index)
    monkeypatch.setattr("app.core.trend_pullback.calc_maw", fake_maw)
    monkeypatch.setattr("app.core.trend_pullback.calc_macd", lambda c: (pd.Series(np.ones(n)), pd.Series(np.zeros(n)), pd.Series(np.arange(n, dtype=float))))
    run_trend_pullback(deterministic_frame(close), 100_000, no_fee, no_fee, params={"maw_short_period":3,"maw_medium_period":5,"maw_long_period":8,"maw_slope_days":2,"min_rebalance_delta":0.15,"min_buy_interval_days":2})
    assert periods == [3, 5, 8]


def test_partial_sell_respects_configured_minimum_rebalance_delta(monkeypatch):
    n = 130; close = np.full(n, 100.0); close[120] = 50.0; close[-1] = 90.0
    m20 = np.full(n, 75.0); m60 = np.full(n, 70.0); m120 = np.full(n, 40.0)
    m60[100] = 45.0; m60[120] = 50.0; m60[-1] = 90.0
    hist = np.arange(n, dtype=float)
    install_sequences(monkeypatch, m20, m60, m120, hist)
    trades, *_ = run_trend_pullback(deterministic_frame(close), 9_000, no_fee, no_fee, params={"min_rebalance_delta":0.25})
    assert not any(t["reason"] == "高位动能减仓" for t in trades)
