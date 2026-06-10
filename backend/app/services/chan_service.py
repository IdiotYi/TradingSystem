"""
缠论 analysis orchestration.
"""
from typing import Optional
import pandas as pd
from app.core.chan import Bar, merge_kbars, detect_fractals, detect_pens
from app.services.data_service import load_stock_data


def analyze_chan(
    stock_code: str,
    start_date: str = "2023-01-01",
    end_date: Optional[str] = None,
) -> dict:
    df = load_stock_data(stock_code)
    if end_date is None:
        end_date = pd.Timestamp.today().strftime("%Y-%m-%d")

    df = df[(df["日期"] >= start_date) & (df["日期"] <= end_date)].reset_index(drop=True)
    if len(df) < 10:
        raise ValueError(f"数据不足，仅 {len(df)} 行（需至少 10 行）")

    bars = [
        Bar(idx=i, date=row["日期"], high=float(row["最高"]), low=float(row["最低"]))
        for i, row in df.iterrows()
    ]
    merged = merge_kbars(bars)
    fractals = detect_fractals(merged)
    pens = detect_pens(merged, fractals, raw_bars=bars)

    dates_list = df["日期"].tolist()
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
        "dates": dates_list,
        "open":  [round(float(v), 4) for v in df["开盘"]],
        "close": [round(float(v), 4) for v in df["收盘"]],
        "high":  [round(float(v), 4) for v in df["最高"]],
        "low":   [round(float(v), 4) for v in df["最低"]],
        "pens":  pen_points,
    }
