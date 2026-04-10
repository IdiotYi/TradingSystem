import numpy as np
import pandas as pd
import pytest
from app.core.three_factors import compute_three_factors


def make_ohlc(n=400):
    np.random.seed(42)
    close = pd.Series(np.cumprod(1 + np.random.normal(0.0005, 0.01, n)) * 100)
    high = close * (1 + np.random.uniform(0, 0.02, n))
    low = close * (1 - np.random.uniform(0, 0.02, n))
    open_ = close.shift(1).fillna(close.iloc[0])
    dates = pd.date_range("2020-01-01", periods=n, freq="B").strftime("%Y-%m-%d").tolist()
    return pd.DataFrame({
        "日期": dates,
        "开盘": open_.values,
        "最高": high.values,
        "最低": low.values,
        "收盘": close.values,
    })


class TestComputeThreeFactors:
    def test_returns_required_columns(self):
        df = make_ohlc(400)
        result = compute_three_factors(df)
        assert set(["日期", "score", "score_mean", "score_std"]).issubset(result.columns)

    def test_output_length_less_than_input(self):
        df = make_ohlc(400)
        result = compute_three_factors(df)
        assert len(result) < len(df)

    def test_score_is_numeric(self):
        df = make_ohlc(400)
        result = compute_three_factors(df)
        valid = result["score"].dropna()
        assert len(valid) > 0
        assert valid.dtype == float

    def test_score_mean_lags_by_one(self):
        """score_mean at position i must equal expanding mean of score up to i-1."""
        df = make_ohlc(500)
        result = compute_three_factors(df).reset_index(drop=True)
        valid_idx = result["score_mean"].first_valid_index()
        if valid_idx is not None and valid_idx > 0:
            expected = result["score"].iloc[:valid_idx].mean()
            actual = result["score_mean"].iloc[valid_idx]
            assert abs(actual - expected) < 1e-6
