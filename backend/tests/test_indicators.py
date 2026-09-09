import numpy as np
import pandas as pd
import pytest
from app.core.indicators import calc_ma, calc_macd, calc_supertrend


def make_series(values):
    return pd.Series(values, dtype=float)


class TestCalcMa:
    def test_ma5_simple(self):
        close = make_series([10, 11, 12, 13, 14, 15, 16])
        ma = calc_ma(close, 5)
        assert abs(ma.iloc[4] - 12.0) < 1e-6
        assert abs(ma.iloc[5] - 13.0) < 1e-6

    def test_ma_shorter_than_period_is_nan(self):
        close = make_series([10, 11, 12])
        ma = calc_ma(close, 5)
        assert ma.isna().all()

    def test_ma_length_matches_input(self):
        close = make_series(range(20))
        assert len(calc_ma(close, 5)) == 20


class TestCalcMacd:
    def test_uses_adjust_false_ema_formulas(self):
        close = pd.Series(
            [10.0, 11.0, 13.0, 12.0, 15.0],
            index=pd.date_range("2026-01-01", periods=5, freq="D"),
        )

        dif, dea, histogram = calc_macd(close, fast=2, slow=3, signal=2)

        expected_dif = (
            close.ewm(span=2, adjust=False).mean()
            - close.ewm(span=3, adjust=False).mean()
        )
        expected_dea = expected_dif.ewm(span=2, adjust=False).mean()
        pd.testing.assert_series_equal(dif, expected_dif)
        pd.testing.assert_series_equal(dea, expected_dea)
        pd.testing.assert_series_equal(histogram, dif - dea)


class TestCalcSupertrend:
    def test_returns_two_series(self):
        n = 50
        np.random.seed(1)
        high = make_series(np.random.uniform(105, 110, n))
        low = make_series(np.random.uniform(90, 95, n))
        close = make_series(np.random.uniform(95, 105, n))
        st, direction = calc_supertrend(high, low, close, period=10, multiplier=3.0)
        assert len(st) == n
        assert len(direction) == n

    def test_direction_is_1_or_minus_1(self):
        n = 100
        np.random.seed(2)
        high = make_series(np.linspace(100, 110, n) + np.random.uniform(0, 2, n))
        low = make_series(np.linspace(95, 105, n) - np.random.uniform(0, 2, n))
        close = make_series(np.linspace(97, 108, n))
        _, direction = calc_supertrend(high, low, close)
        valid = direction.dropna()
        assert set(valid.unique()).issubset({1, -1})

    def test_strong_uptrend_direction(self):
        n = 60
        prices = np.linspace(100, 200, n)
        high = make_series(prices + 2)
        low = make_series(prices - 2)
        close = make_series(prices)
        _, direction = calc_supertrend(high, low, close, period=10, multiplier=3.0)
        assert direction.iloc[-1] == 1
