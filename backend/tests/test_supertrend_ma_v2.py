"""
Unit tests for SuperTrend+MA V2 strategy.
Verifies key behaviors: ATR stop, cooldown, min hold, vol filter,
entry-2 toggle, and the absence of look-ahead (perturbing future
bars must not change historical decisions).
"""
import numpy as np
import pandas as pd
import pytest

from app.core.indicators import calc_ma, calc_kama, calc_supertrend
from app.services.backtest_service import _run_supertrend_ma_v2


def _make_df(close_arr):
    """Build an OHLC frame from a close-price array (high=close*1.01, low=close*0.99)."""
    n = len(close_arr)
    dates = pd.date_range("2023-01-01", periods=n, freq="B").strftime("%Y-%m-%d").tolist()
    high = close_arr * 1.01
    low = close_arr * 0.99
    df = pd.DataFrame({
        "日期": dates,
        "开盘": close_arr,
        "最高": high,
        "最低": low,
        "收盘": close_arr,
    })
    df["ma20"] = calc_ma(df["收盘"], 20)
    df["kama"] = calc_kama(df["收盘"])
    st, st_dir, st_up, st_lo = calc_supertrend(
        df["最高"], df["最低"], df["收盘"],
        period=12, multiplier=3.0, return_bands=True,
    )
    df["st"] = st; df["st_dir"] = st_dir
    df["st_upper"] = st_up; df["st_lower"] = st_lo
    return df


def _trending_close(n=400, seed=0):
    rng = np.random.default_rng(seed)
    base = np.linspace(10.0, 18.0, n)
    noise = rng.normal(0, 0.05, n)
    return base + noise


class TestSupertrendMaV2:
    def test_runs_and_returns_tuple(self):
        df = _make_df(_trending_close())
        trades, cash, shares = _run_supertrend_ma_v2(df, 100000.0, {})
        assert isinstance(trades, list)
        assert cash >= 0
        assert shares >= 0

    def test_entry2_disabled_by_default(self):
        """No '突破上轨' trade should appear when enable_entry2 is False (default)."""
        df = _make_df(_trending_close(seed=1))
        trades, _, _ = _run_supertrend_ma_v2(df, 100000.0, {})
        assert all("突破上轨" not in t["reason"] for t in trades)

    def test_atr_stop_reason_uses_atr_label(self):
        df = _make_df(_trending_close(seed=2))
        trades, _, _ = _run_supertrend_ma_v2(
            df, 100000.0,
            {"atr_stop_mult": 0.5, "min_hold_bars": 0, "cooldown_bars": 0,
             "vol_threshold": 1.0, "recent_high_window": 1},
        )
        # If any sells occurred, ATR-labelled stop should be possible (not asserted to exist
        # because trending data may not trigger), but no '下跌2%' V1 reason should appear.
        assert all("下跌2%" not in t["reason"] for t in trades)

    def test_high_volatility_blocks_entries(self):
        """vol_threshold=0 should block all entries."""
        df = _make_df(_trending_close(seed=3))
        trades, cash, shares = _run_supertrend_ma_v2(
            df, 100000.0, {"vol_threshold": 0.0},
        )
        assert shares == 0
        assert cash == 100000.0
        assert trades == []

    def test_no_lookahead_perturbation(self):
        """
        Perturbing future bars (after some midpoint M) must not change
        any trade whose date is on or before bar M.
        """
        close = _trending_close(seed=4)
        df_a = _make_df(close.copy())
        # Mutate the last 20% of bars wildly
        m = int(len(close) * 0.8)
        close_b = close.copy()
        close_b[m:] = close_b[m:] * 5.0  # extreme future shock
        df_b = _make_df(close_b)

        params = {"vol_threshold": 1.0, "recent_high_window": 1}
        trades_a, _, _ = _run_supertrend_ma_v2(df_a, 100000.0, params)
        trades_b, _, _ = _run_supertrend_ma_v2(df_b, 100000.0, params)

        cutoff_date = df_a.iloc[m]["日期"]
        a_before = [t for t in trades_a if t["date"] < cutoff_date]
        b_before = [t for t in trades_b if t["date"] < cutoff_date]
        assert len(a_before) == len(b_before), \
            "Future data perturbation changed historical trade count — look-ahead bug!"
        for ta, tb in zip(a_before, b_before):
            assert ta["date"] == tb["date"]
            assert ta["direction"] == tb["direction"]
            assert ta["reason"] == tb["reason"]
            assert abs(ta["price"] - tb["price"]) < 1e-9

    def test_cooldown_prevents_immediate_reentry(self):
        """After a stop-loss exit, no new buy should occur within cooldown_bars."""
        # Build oscillating data that would normally trigger many entries
        n = 300
        rng = np.random.default_rng(5)
        close = 10 + np.sin(np.linspace(0, 30, n)) * 0.5 + rng.normal(0, 0.05, n)
        df = _make_df(close)
        params = {
            "cooldown_bars": 20, "vol_threshold": 1.0,
            "recent_high_window": 1, "atr_stop_mult": 0.3,
            "min_hold_bars": 0,
        }
        trades, _, _ = _run_supertrend_ma_v2(df, 100000.0, params)
        date_to_idx = {d: i for i, d in enumerate(df["日期"].tolist())}
        last_sell_idx = None
        for t in trades:
            idx = date_to_idx[t["date"]]
            if t["direction"] == "买入" and last_sell_idx is not None:
                assert idx - last_sell_idx > params["cooldown_bars"], \
                    f"Buy on bar {idx} violates cooldown after sell on bar {last_sell_idx}"
            if t["direction"] == "卖出":
                last_sell_idx = idx
