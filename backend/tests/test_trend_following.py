import numpy as np
import pandas as pd
import pytest

from app.core.trend_following import run_trend_following


def no_fee(_amount: float) -> dict:
    return {"transfer_fee": 0.0, "commission": 0.0, "stamp_tax": None, "total_fee": 0.0}


def fees(amount: float) -> dict:
    return {"transfer_fee": 1.0, "commission": 2.0, "stamp_tax": None, "total_fee": 3.0}


def frame(close, m20, m60, m120, hist=None, dif=None, dea=None, slope=20):
    close = np.asarray(close, dtype=float)
    n = len(close)
    volume = np.full(n, 10000.0)
    result = pd.DataFrame({
        "日期": pd.date_range("2024-01-01", periods=n, freq="B").strftime("%Y-%m-%d"),
        "收盘": close,
        "成交量": volume,
        "成交额": close * volume,
        "换手率": np.ones(n),
        "_maw20": np.asarray(m20, dtype=float),
        "_maw60": np.asarray(m60, dtype=float),
        "_maw120": np.asarray(m120, dtype=float),
        "_macd_histogram": np.arange(n, dtype=float) if hist is None else np.asarray(hist, dtype=float),
        "_macd_dif": np.ones(n) if dif is None else np.asarray(dif, dtype=float),
        "_macd_dea": np.zeros(n) if dea is None else np.asarray(dea, dtype=float),
    })
    result["_maw60_lag"] = result["_maw60"].shift(slope)
    result["_maw120_lag"] = result["_maw120"].shift(slope)
    return result


def base(n=150):
    close = np.full(n, 130.0)
    m20 = np.linspace(90.0, 120.0, n)
    m60 = np.linspace(80.0, 105.0, n)
    m120 = np.linspace(60.0, 90.0, n)
    return close, m20, m60, m120


def run(prepared, cash=100000, buy=no_fee, sell=no_fee, params=None):
    raw = prepared[["日期", "收盘", "成交量", "成交额", "换手率"]]
    return run_trend_following(raw, cash, buy, sell, prepared=prepared, params=params)


def seed_normal_entry(n=150):
    close, m20, m60, m120 = base(n)
    close[:120] = 80.0
    close[120] = 115.0
    m20[120], m60[120], m120[120] = 120.0, 110.0, 90.0
    return close, m20, m60, m120


def test_strong_trend_reaches_full_position_and_ignores_short_macd_weakness():
    close, m20, m60, m120 = base()
    close[:120] = 80.0
    close[120:] = 130.0
    hist = np.arange(150, dtype=float)
    hist[-4:] = [4.0, 3.0, 2.0, 1.0]
    trades, _, _, series = run(frame(close, m20, m60, m120, hist), cash=1_000_000)
    assert max(series["position_ratio"]) > 0.98
    assert not any("MACD" in t["reason"] and t["action"] == "sell" for t in trades)


def test_normal_trend_opens_to_seventy_percent_same_day():
    close, m20, m60, m120 = seed_normal_entry()
    prepared = frame(close, m20, m60, m120)
    trades, cash, shares, series = run(prepared)
    trade = next(t for t in trades if t["action"] == "buy")
    idx = prepared.index[prepared["日期"] == trade["date"]][0]
    assert trade["reason"] == "上升趋势开仓"
    assert trade["signal_date"] == trade["date"]
    assert trade["price"] == prepared.at[idx, "收盘"]
    assert 0.60 < series["position_ratio"][idx] <= 0.70
    assert cash >= 0 and shares % 100 == 0


def test_recovery_over_maw20_targets_eighty_five_percent_after_buy_interval():
    close, m20, m60, m120 = seed_normal_entry()
    close[121:124] = 130.0
    close[124], close[125] = 118.0, 121.0
    m20[124:126] = [120.0, 120.0]
    m60[124:126], m120[124:126] = [110.0, 110.0], [90.0, 90.0]
    close[126:] = 100.0
    prepared = frame(close, m20, m60, m120)
    trades, *_ = run(prepared)
    buys = [t for t in trades if t["action"] == "buy"]
    assert buys[-1]["date"] == prepared.at[125, "日期"]
    assert buys[-1]["reason"] == "回撤恢复加仓"


def test_twenty_five_percent_cost_loss_liquidates_with_accounting():
    close, m20, m60, m120 = seed_normal_entry()
    close[-1] = 115.0 * 0.75
    prepared = frame(close, m20, m60, m120)
    trades, cash, shares, _ = run(prepared, cash=1000000, buy=fees, sell=lambda a: {"transfer_fee": 1.0, "commission": 2.0, "stamp_tax": 4.0, "total_fee": 7.0})
    assert trades[-1]["reason"] == "成本亏损25%清仓"
    assert trades[-1]["stamp_tax"] == 4.0
    assert trades[-1]["pnl"] is not None
    assert trades[-1]["remaining_cash"] == pytest.approx(cash)
    assert shares == 0


def test_maw60_below_maw120_liquidates():
    close, m20, m60, m120 = seed_normal_entry()
    m60[-1], m120[-1], close[-1] = 90.0, 91.0, 100.0
    trades, _, shares, _ = run(frame(close, m20, m60, m120))
    assert trades[-1]["reason"] == "MAW60跌破MAW120清仓"
    assert shares == 0


def test_three_days_below_maw120_liquidates():
    close, m20, m60, m120 = seed_normal_entry()
    close[-3:] = 99.0
    m60[-3:], m120[-3:] = 105.0, 100.0
    trades, _, shares, _ = run(frame(close, m20, m60, m120))
    assert trades[-1]["reason"] == "跌破MAW120三日清仓"
    assert shares == 0


def test_three_days_below_maw60_reduces_to_thirty_percent():
    close, m20, m60, m120 = seed_normal_entry()
    close[-3:] = 99.0
    m60[-3:], m120[-3:] = 100.0, 90.0
    trades, _, _, series = run(frame(close, m20, m60, m120))
    assert trades[-1]["reason"] == "跌破MAW60三日减仓"
    assert series["position_ratio"][-1] <= 0.30


def test_three_days_weak_macd_below_maw60_reduces_to_fifty_percent():
    close, m20, m60, m120 = seed_normal_entry()
    close[-1] = 99.0
    m60[-3:], m120[-3:] = 100.0, 90.0
    dif, dea = np.ones(150), np.zeros(150)
    dif[-3:] = -1.0
    trades, _, _, series = run(frame(close, m20, m60, m120, dif=dif, dea=dea))
    assert trades[-1]["reason"] == "MAW60下方MACD弱势减仓"
    assert series["position_ratio"][-1] <= 0.50


def test_future_truncation_keeps_prior_trades_and_series_identical():
    close, m20, m60, m120 = base(210)
    prepared = frame(close, m20, m60, m120)
    full = run(prepared)
    cut = run(prepared.iloc[:180].copy())
    assert [t for t in full[0] if t["date"] <= prepared.at[179, "日期"]] == cut[0]
    for key in cut[3]:
        assert full[3][key][:180] == cut[3][key]

@pytest.mark.parametrize(
    ("column", "reason"),
    [
        ("_maw120", "跌破MAW120三日清仓"),
        ("_maw60", "跌破MAW60三日减仓"),
    ],
)
def test_three_day_price_guards_ignore_windows_with_prior_non_numeric(column, reason):
    close, m20, m60, m120 = seed_normal_entry()
    close[-3:] = 99.0
    m60[-3:], m120[-3:] = 100.0, 90.0
    prepared = frame(close, m20, m60, m120)
    prepared.loc[prepared.index[-2], column] = pd.NA

    trades, *_ = run(prepared)

    assert not any(trade["reason"] == reason for trade in trades)


def test_three_day_macd_weak_guard_ignores_prior_non_numeric():
    close, m20, m60, m120 = seed_normal_entry()
    close[-1] = 99.0
    m60[-3:], m120[-3:] = 100.0, 90.0
    dif, dea = np.ones(150), np.zeros(150)
    dif[-3:] = -1.0
    prepared = frame(close, m20, m60, m120, dif=dif, dea=dea)
    prepared.loc[prepared.index[-2], "_macd_dif"] = pd.NA

    trades, *_ = run(prepared)

    assert not any(trade["reason"] == "MAW60下方MACD弱势减仓" for trade in trades)
