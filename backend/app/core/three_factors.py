"""
Three-factor momentum score calculation.
Ported directly from C:/PrivateProjects/TradingStrategy/analysis.py.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

BIAS_N = 60
MOMENTUM_DAY = 60
SLOPE_N = 60
EFFICIENCY_N = 60
ZSCORE_WINDOW = 250


def _bias_momentum(close: pd.Series) -> float:
    if close.empty:
        return np.nan
    bias = close / close.rolling(window=BIAS_N, min_periods=1).mean()
    if len(bias) < MOMENTUM_DAY or bias.iloc[-MOMENTUM_DAY] == 0:
        return np.nan
    bias_recent = bias.iloc[-MOMENTUM_DAY:]
    base = bias_recent.iloc[0]
    if base == 0:
        return np.nan
    x = np.arange(MOMENTUM_DAY).reshape(-1, 1)
    y = (bias_recent / base).values.reshape(-1, 1)
    lr = LinearRegression()
    lr.fit(x, y)
    return float(lr.coef_[0, 0]) * 10000


def _slope_momentum(close: pd.Series) -> float:
    if len(close) < SLOPE_N:
        return np.nan
    base = close.iloc[-SLOPE_N]
    if base == 0 or np.isnan(base):
        return np.nan
    normalized = close.iloc[-SLOPE_N:] / base
    if normalized.isna().any():
        return np.nan
    x = np.arange(1, SLOPE_N + 1).reshape(-1, 1)
    y = normalized.values.reshape(-1, 1)
    lr = LinearRegression()
    lr.fit(x, y)
    return 10000 * float(lr.coef_[0, 0]) * float(lr.score(x, y))


def _efficiency_momentum(df_window: pd.DataFrame) -> float:
    if len(df_window) < EFFICIENCY_N:
        return np.nan
    window = df_window.iloc[-EFFICIENCY_N:]
    pivot = (window["open"] + window["high"] + window["low"] + window["close"]) / 4.0
    pivot = pivot.ffill()
    if pivot.iloc[0] <= 0 or pivot.iloc[-1] <= 0:
        return np.nan
    momentum = 100 * np.log(pivot.iloc[-1] / pivot.iloc[0])
    direction = abs(np.log(pivot.iloc[-1]) - np.log(pivot.iloc[0]))
    volatility = np.log(pivot).diff().abs().sum()
    efficiency_ratio = direction / volatility if volatility > 0 else 0
    return momentum * efficiency_ratio


def compute_three_factors(df_all: pd.DataFrame) -> pd.DataFrame:
    """
    Compute three-factor scores on full historical data with no lookahead.

    Args:
        df_all: DataFrame with columns 日期, 开盘, 最高, 最低, 收盘

    Returns:
        DataFrame with columns: 日期, score, score_mean, score_std
    """
    df_ohlc = df_all.rename(columns={
        "开盘": "open", "最高": "high", "最低": "low", "收盘": "close",
    })
    close_full = df_all["收盘"]
    dates_full = df_all["日期"]

    min_history = max(BIAS_N, MOMENTUM_DAY, SLOPE_N, EFFICIENCY_N)
    results = []
    for i in range(min_history, len(df_all)):
        close_slice = close_full.iloc[: i + 1]
        ohlc_slice = df_ohlc.iloc[: i + 1]
        results.append({
            "日期": dates_full.iloc[i],
            "乖离动量": _bias_momentum(close_slice),
            "斜率动量": _slope_momentum(close_slice),
            "效率动量": _efficiency_momentum(ohlc_slice),
        })

    fdf = pd.DataFrame(results)
    for col, z_col in [("乖离动量", "z_bias"), ("斜率动量", "z_slope"), ("效率动量", "z_eff")]:
        rm = fdf[col].rolling(ZSCORE_WINDOW).mean()
        rs = fdf[col].rolling(ZSCORE_WINDOW).std()
        fdf[z_col] = (fdf[col] - rm) / rs

    fdf["score"] = (2 * fdf["z_bias"] + 2 * fdf["z_slope"] + 6 * fdf["z_eff"]) / 10
    fdf["score_mean"] = fdf["score"].expanding().mean().shift(1)
    fdf["score_std"] = fdf["score"].expanding().std().shift(1)

    return fdf[["日期", "score", "score_mean", "score_std"]]
