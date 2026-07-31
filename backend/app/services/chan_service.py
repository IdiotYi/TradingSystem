"""
缠论 analysis orchestration.
"""
import re
from typing import Optional
import pandas as pd
from app.core.chan import Bar, merge_kbars, detect_fractals, detect_pens
from app.services.data_service import load_stock_data
from app.services.minute_data_service import load_minute_data


VALID_CHAN_PERIODS = {"daily", "30", "5"}
MAX_CHAN_BARS = 20_000


def _load_chan_frame(stock_code: str, period: str) -> tuple[pd.DataFrame, dict]:
    if period not in VALID_CHAN_PERIODS:
        raise ValueError(f"缠论周期必须为 {sorted(VALID_CHAN_PERIODS)}")

    if period == "daily":
        frame = load_stock_data(stock_code).rename(columns={"日期": "时间"})
        return frame, {
            "coverage_from": frame["时间"].iloc[0],
            "coverage_to": frame["时间"].iloc[-1],
            "data_source": "stock_daily_cache",
            "target_coverage_met": True,
        }

    return load_minute_data(stock_code, period)


def analyze_chan(
    stock_code: str,
    start_date: str = "2023-01-01",
    end_date: Optional[str] = None,
    period: str = "daily",
) -> dict:
    if end_date is None:
        end_date = str(pd.Timestamp.today())

    frame, metadata = _load_chan_frame(stock_code, period)
    timestamps = pd.to_datetime(frame["时间"], errors="raise")
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    if period != "daily" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(end_date).strip()):
        end_ts += pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
    df = frame.loc[(timestamps >= start_ts) & (timestamps <= end_ts)].reset_index(drop=True)
    if len(df) < 10:
        raise ValueError(f"数据不足，仅 {len(df)} 行（需至少 10 行）")
    if len(df) > MAX_CHAN_BARS:
        raise ValueError(f"返回K线数量超过 {MAX_CHAN_BARS}，请缩小日期范围")

    bars = [
        Bar(idx=i, date=row["时间"], high=float(row["最高"]), low=float(row["最低"]))
        for i, row in df.iterrows()
    ]
    merged = merge_kbars(bars)
    fractals = detect_fractals(merged)
    pens = detect_pens(merged, fractals, raw_bars=bars)

    dates_list = df["时间"].tolist()
    pen_points = [
        {
            "start_idx": p.start_src_idx,
            "start_date": dates_list[p.start_src_idx],
            "start_price": round(p.start_price, 4),
            "end_idx": p.end_src_idx,
            "end_date": dates_list[p.end_src_idx],
            "end_price": round(p.end_price, 4),
            "direction": p.direction,
        }
        for p in pens
    ]

    return {
        "success": True,
        "stock_code": stock_code,
        "period": period,
        "coverage_from": metadata["coverage_from"],
        "coverage_to": metadata["coverage_to"],
        "response_from": dates_list[0],
        "response_to": dates_list[-1],
        "data_source": metadata["data_source"],
        "target_coverage_met": metadata["target_coverage_met"],
        "dates": dates_list,
        "open":  [round(float(v), 4) for v in df["开盘"]],
        "close": [round(float(v), 4) for v in df["收盘"]],
        "high":  [round(float(v), 4) for v in df["最高"]],
        "low":   [round(float(v), 4) for v in df["最低"]],
        "pens":  pen_points,
    }
