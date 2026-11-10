import numpy as np
import pandas as pd
from app.core.indicators import calc_ma, calc_supertrend, calc_kama
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

    nan_series = pd.Series(np.nan, index=df.index)
    vwap = nan_series
    indicator_warnings = []
    # Daily average price only needs amount and volume; turnover is needed
    # separately for MAW. A partial provider must not hide available VWAP.
    if "成交额" in df.columns:
        amount = pd.to_numeric(df["成交额"], errors="coerce")
        vol_num = pd.to_numeric(volume, errors="coerce")
        vwap_raw = amount / vol_num.where(vol_num > 0)

        # Apply qfq adjustment factor when raw close is available; amount/volume are
        # unadjusted, but close is qfq-adjusted, so factor = close / close_raw.
        if "收盘_未复权" in df.columns:
            close_raw = pd.to_numeric(df["收盘_未复权"], errors="coerce")
            factor = close / close_raw.where(close_raw > 0)
            vwap = vwap_raw * factor
        else:
            vwap = vwap_raw

    if "成交额" in df.columns and "换手率" in df.columns:
        turnover = pd.to_numeric(df["换手率"], errors="coerce")
        weighted = (vwap * turnover).where(turnover.notna() & vwap.notna())

        def _maw(n: int) -> pd.Series:
            num = weighted.rolling(window=n, min_periods=n).sum()
            den = turnover.where(vwap.notna()).rolling(window=n, min_periods=n).sum()
            return num / den.where(den > 0)

        maw5   = _maw(5)
        maw10  = _maw(10)
        maw20  = _maw(20)
        maw60  = _maw(60)
        maw120 = _maw(120)
        maw243 = _maw(243)
    else:
        maw5 = maw10 = maw20 = maw60 = maw120 = maw243 = nan_series
        if "成交额" not in df.columns:
            indicator_warnings.append("当前行情缺少成交额，无法计算均价和MAW；请点击顶部「刷新数据」重试。")
        else:
            indicator_warnings.append("当前行情缺少换手率，MAW及其上下轨暂不可用，均价仍可显示；请点击顶部「刷新数据」重试。")

    ma5 = calc_ma(close, 5)
    ma20 = calc_ma(close, 20)
    ma60 = calc_ma(close, 60)
    kama = calc_kama(close, period=10, fast=2, slow=30)
    supertrend, direction = calc_supertrend(high, low, close, period=10, multiplier=1.0)
    supertrend2, direction2 = calc_supertrend(high, low, close, period=11, multiplier=2.0)
    supertrend3, direction3 = calc_supertrend(high, low, close, period=12, multiplier=3.0)

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
        "indicator_warnings": indicator_warnings,
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
        "maw5": _to_list(maw5),
        "maw10": _to_list(maw10),
        "maw20": _to_list(maw20),
        "maw60": _to_list(maw60),
        "maw120": _to_list(maw120),
        "maw243": _to_list(maw243),
        "vwap": _to_list(vwap),
        "kama": _to_list(kama),
        "supertrend": _to_list(supertrend),
        "supertrend_direction": [None if pd.isna(v) else int(v) for v in direction],
        "supertrend2": _to_list(supertrend2),
        "supertrend2_direction": [None if pd.isna(v) else int(v) for v in direction2],
        "supertrend3": _to_list(supertrend3),
        "supertrend3_direction": [None if pd.isna(v) else int(v) for v in direction3],
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
