import numpy as np
import pandas as pd
from app.core.indicators import calc_ma, calc_supertrend
from app.services.data_service import load_stock_data


def _to_list(s: pd.Series) -> list:
    return [None if pd.isna(v) else round(float(v), 4) for v in s]


def get_analysis_data(stock_code: str) -> dict:
    df = load_stock_data(stock_code)

    close = df["收盘"]
    high = df["最高"]
    low = df["最低"]
    open_ = df["开盘"]
    volume = df["成交量"]
    dates = df["日期"]

    ma5 = calc_ma(close, 5)
    ma20 = calc_ma(close, 20)
    ma60 = calc_ma(close, 60)
    supertrend, direction = calc_supertrend(high, low, close, period=10, multiplier=3.0)

    # Price percentiles over full history
    close_valid = close.dropna().values
    p20, p50, p80 = np.percentile(close_valid, [20, 50, 80])

    # Max drawdown over full history
    close_arr = close.values
    dates_arr = dates.values
    cummax = np.maximum.accumulate(close_arr)
    drawdown = (close_arr - cummax) / cummax
    trough_idx = int(np.argmin(drawdown))
    peak_idx = int(np.argmax(close_arr[: trough_idx + 1]))

    return {
        "success": True,
        "stock_code": stock_code.strip(),
        "dates": dates.tolist(),
        "open": _to_list(open_),
        "high": _to_list(high),
        "low": _to_list(low),
        "close": _to_list(close),
        "volume": _to_list(volume),
        "ma5": _to_list(ma5),
        "ma20": _to_list(ma20),
        "ma60": _to_list(ma60),
        "supertrend": _to_list(supertrend),
        "supertrend_direction": [
            None if pd.isna(v) else int(v) for v in direction
        ],
        "current_price": round(float(close.iloc[-1]), 2),
        "p20": round(float(p20), 2),
        "p50": round(float(p50), 2),
        "p80": round(float(p80), 2),
        "max_drawdown": round(float(drawdown[trough_idx]), 4),
        "drawdown_peak_date": str(dates_arr[peak_idx]),
        "drawdown_trough_date": str(dates_arr[trough_idx]),
        "drawdown_peak_price": round(float(close_arr[peak_idx]), 2),
        "drawdown_trough_price": round(float(close_arr[trough_idx]), 2),
    }
