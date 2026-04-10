from typing import Tuple
import numpy as np
import pandas as pd


def calc_ma(close: pd.Series, period: int) -> pd.Series:
    """Simple moving average."""
    return close.rolling(window=period).mean()


def calc_supertrend(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 10,
    multiplier: float = 3.0,
) -> Tuple[pd.Series, pd.Series]:
    """
    SuperTrend indicator.
    Returns (supertrend_values, direction) where direction=1 is uptrend, -1 is downtrend.
    """
    n = len(close)
    index = close.index
    close_arr = close.values.astype(float)
    high_arr = high.values.astype(float)
    low_arr = low.values.astype(float)

    # True Range
    prev_close = np.empty(n)
    prev_close[0] = close_arr[0]
    prev_close[1:] = close_arr[:-1]

    tr = np.maximum(
        high_arr - low_arr,
        np.maximum(np.abs(high_arr - prev_close), np.abs(low_arr - prev_close)),
    )

    # Wilder's smoothed ATR (EMA with alpha = 1/period)
    atr = np.empty(n)
    atr[0] = tr[0]
    alpha = 1.0 / period
    for i in range(1, n):
        atr[i] = alpha * tr[i] + (1 - alpha) * atr[i - 1]

    hl2 = (high_arr + low_arr) / 2.0
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr

    final_upper = np.empty(n)
    final_lower = np.empty(n)
    supertrend = np.full(n, np.nan)
    direction = np.ones(n, dtype=int)

    final_upper[0] = basic_upper[0]
    final_lower[0] = basic_lower[0]

    for i in range(1, n):
        # Final upper: only move down, unless price broke above it last bar
        final_upper[i] = (
            basic_upper[i]
            if basic_upper[i] < final_upper[i - 1] or close_arr[i - 1] > final_upper[i - 1]
            else final_upper[i - 1]
        )
        # Final lower: only move up, unless price broke below it last bar
        final_lower[i] = (
            basic_lower[i]
            if basic_lower[i] > final_lower[i - 1] or close_arr[i - 1] < final_lower[i - 1]
            else final_lower[i - 1]
        )

        prev_st = supertrend[i - 1]
        if np.isnan(prev_st):
            if close_arr[i] > final_upper[i]:
                direction[i] = 1
                supertrend[i] = final_lower[i]
            else:
                direction[i] = -1
                supertrend[i] = final_upper[i]
        elif prev_st == final_upper[i - 1]:
            # Was downtrend — switch to uptrend if price closes above upper band
            if close_arr[i] > final_upper[i]:
                direction[i] = 1
                supertrend[i] = final_lower[i]
            else:
                direction[i] = -1
                supertrend[i] = final_upper[i]
        else:
            # Was uptrend — switch to downtrend if price closes below lower band
            if close_arr[i] < final_lower[i]:
                direction[i] = -1
                supertrend[i] = final_upper[i]
            else:
                direction[i] = 1
                supertrend[i] = final_lower[i]

    return pd.Series(supertrend, index=index), pd.Series(direction, index=index)
