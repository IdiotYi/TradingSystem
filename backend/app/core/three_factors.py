"""
Three-factor momentum score calculation.
Ported directly from C:/PrivateProjects/TradingStrategy/analysis.py.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from app.core.indicators import calc_maw

BIAS_N = 20          # 乖离率计算窗口：收盘价相对移动均线偏离度的均线周期（交易日）
MOMENTUM_DAY = 20    # 乖离动量回看窗口：对乖离率序列做线性拟合时使用的历史天数
SLOPE_N = 20         # 斜率动量回看窗口：对价格归一化序列做线性拟合时使用的历史天数
EFFICIENCY_N = 20    # 效率动量回看窗口：计算价格路径效率比时使用的历史天数
ZSCORE_WINDOW = 60   # Z-score 滚动窗口：对各因子做滚动标准化时的窗口大小（约1季度交易日）


def _bias_momentum(close: pd.Series, bias_n: int, momentum_day: int) -> float:
    if close.empty:
        return np.nan
    bias = close / close.rolling(window=bias_n, min_periods=1).mean()
    if len(bias) < momentum_day or bias.iloc[-momentum_day] == 0:
        return np.nan
    bias_recent = bias.iloc[-momentum_day:]
    base = bias_recent.iloc[0]
    if base == 0:
        return np.nan
    x = np.arange(momentum_day).reshape(-1, 1)
    y = (bias_recent / base).values.reshape(-1, 1)
    lr = LinearRegression()
    lr.fit(x, y)
    return float(lr.coef_[0, 0]) * 10000


def _bias_momentum_maw(df_window: pd.DataFrame, bias_n: int, momentum_day: int) -> float:
    """与 _bias_momentum 一致，但乖离率 = 收盘 / MAW(N) 而非 / MA(N)。
    df_window 需包含 calc_maw 所需的列（收盘/成交量/成交额/换手率，可选收盘_未复权）。"""
    if df_window.empty:
        return np.nan
    close = df_window["收盘"]
    maw = calc_maw(df_window, bias_n)
    bias = close / maw
    if len(bias) < momentum_day:
        return np.nan
    bias_recent = bias.iloc[-momentum_day:]
    if bias_recent.isna().any():
        return np.nan
    base = bias_recent.iloc[0]
    if base == 0 or pd.isna(base):
        return np.nan
    x = np.arange(momentum_day).reshape(-1, 1)
    y = (bias_recent / base).values.reshape(-1, 1)
    lr = LinearRegression()
    lr.fit(x, y)
    return float(lr.coef_[0, 0]) * 10000


def _slope_momentum(close: pd.Series, slope_n: int) -> float:
    if len(close) < slope_n:
        return np.nan
    base = close.iloc[-slope_n]
    if base == 0 or np.isnan(base):
        return np.nan
    normalized = close.iloc[-slope_n:] / base
    if normalized.isna().any():
        return np.nan
    x = np.arange(1, slope_n + 1).reshape(-1, 1)
    y = normalized.values.reshape(-1, 1)
    lr = LinearRegression()
    lr.fit(x, y)
    return 10000 * float(lr.coef_[0, 0]) * float(lr.score(x, y))


def _efficiency_momentum(df_window: pd.DataFrame, efficiency_n: int) -> float:
    if len(df_window) < efficiency_n:
        return np.nan
    window = df_window.iloc[-efficiency_n:]
    pivot = (window["open"] + window["high"] + window["low"] + window["close"]) / 4.0
    pivot = pivot.ffill()
    if pivot.iloc[0] <= 0 or pivot.iloc[-1] <= 0:
        return np.nan
    momentum = 100 * np.log(pivot.iloc[-1] / pivot.iloc[0])
    direction = abs(np.log(pivot.iloc[-1]) - np.log(pivot.iloc[0]))
    volatility = np.log(pivot).diff().abs().sum()
    efficiency_ratio = direction / volatility if volatility > 0 else 0
    return momentum * efficiency_ratio


def _compute(
    df_all: pd.DataFrame,
    bias_n: int,
    momentum_day: int,
    slope_n: int,
    efficiency_n: int,
    zscore_window: int,
    use_maw: bool,
) -> pd.DataFrame:
    df_ohlc = df_all.rename(columns={
        "开盘": "open", "最高": "high", "最低": "low", "收盘": "close",
    })
    close_full = df_all["收盘"]
    dates_full = df_all["日期"]

    min_history = max(bias_n, momentum_day, slope_n, efficiency_n)
    results = []
    for i in range(min_history, len(df_all)):
        close_slice = close_full.iloc[: i + 1]
        ohlc_slice = df_ohlc.iloc[: i + 1]
        if use_maw:
            bias_val = _bias_momentum_maw(df_all.iloc[: i + 1], bias_n, momentum_day)
        else:
            bias_val = _bias_momentum(close_slice, bias_n, momentum_day)
        results.append({
            "日期": dates_full.iloc[i],
            "乖离动量": bias_val,
            "斜率动量": _slope_momentum(close_slice, slope_n),
            "效率动量": _efficiency_momentum(ohlc_slice, efficiency_n),
        })

    fdf = pd.DataFrame(results)
    for col, z_col in [("乖离动量", "z_bias"), ("斜率动量", "z_slope"), ("效率动量", "z_eff")]:
        rm = fdf[col].rolling(zscore_window).mean()
        rs = fdf[col].rolling(zscore_window).std()
        fdf[z_col] = (fdf[col] - rm) / rs

    fdf["score"] = (2 * fdf["z_bias"] + 2 * fdf["z_slope"] + 6 * fdf["z_eff"]) / 10
    fdf["score_mean"] = fdf["score"].expanding().mean().shift(1)
    fdf["score_std"] = fdf["score"].expanding().std().shift(1)

    return fdf[["日期", "score", "score_mean", "score_std"]]


def compute_three_factors(
    df_all: pd.DataFrame,
    bias_n: int = BIAS_N,
    momentum_day: int = MOMENTUM_DAY,
    slope_n: int = SLOPE_N,
    efficiency_n: int = EFFICIENCY_N,
    zscore_window: int = ZSCORE_WINDOW,
) -> pd.DataFrame:
    """Three-factor score with bias computed against MA(bias_n)."""
    return _compute(df_all, bias_n, momentum_day, slope_n, efficiency_n, zscore_window, use_maw=False)


def compute_three_factors_v2(
    df_all: pd.DataFrame,
    bias_n: int = BIAS_N,
    momentum_day: int = MOMENTUM_DAY,
    slope_n: int = SLOPE_N,
    efficiency_n: int = EFFICIENCY_N,
    zscore_window: int = ZSCORE_WINDOW,
) -> pd.DataFrame:
    """Three-factor score with bias computed against MAW(bias_n) — 偏离成本线."""
    return _compute(df_all, bias_n, momentum_day, slope_n, efficiency_n, zscore_window, use_maw=True)
