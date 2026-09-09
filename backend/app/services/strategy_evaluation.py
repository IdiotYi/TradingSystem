"""Fixed-window local-cache strategy evaluation; this module never tunes parameters."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, median

import pandas as pd

from app.services import backtest_service
from app.services.backtest_service import run_backtest

PERIODS = {
    "train": {"start": "2021-01-01", "end": "2023-12-31"},
    "out_of_sample": {"start": "2024-01-01", "end": "2025-12-31"},
}
STRATEGIES = ["buy_and_hold", "three_factors", "supertrend_ma", "trend_pullback_maw_macd", "trend_following_maw_macd"]
MAW_FIELDS = {"成交额", "成交量", "换手率"}

def _max_drawdown(values: list[float]) -> float:
    if not values:
        return 0.0
    peak = float(values[0]); worst = 0.0
    for value in values:
        value = float(value); peak = max(peak, value)
        if peak > 0: worst = min(worst, (value - peak) / peak)
    return worst

def _portfolio_curve(result: dict, initial_cash: float = 100000.0) -> list[float]:
    explicit = result.get("portfolio_value")
    if explicit is not None:
        return [float(v) for v in explicit]
    # Existing backtest response has no daily equity curve. Use the exact endpoints;
    # maximum drawdown is therefore conservative/limited for legacy strategies.
    return [initial_cash, float(result["summary"]["final_assets"])]

def evaluate_cached_strategies(data_dir: Path, codes: list[str] | None = None) -> dict:
    data_dir = Path(data_dir)
    if codes is None:
        codes = sorted(p.stem for p in data_dir.glob("[0-9][0-9][0-9][0-9][0-9][0-9].csv"))
    results=[]; skipped=[]
    original_loader = backtest_service.load_stock_data
    try:
        for code in codes:
            path=data_dir / f"{code}.csv"
            if not path.exists():
                skipped.append({"code": code, "reason": "cache file not found"}); continue
            frame=pd.read_csv(path, encoding="utf-8-sig")
            missing=sorted(MAW_FIELDS.difference(frame.columns))
            if missing:
                skipped.append({"code": code, "reason": f"missing MAW fields: {', '.join(missing)}"}); continue
            frame["日期"]=pd.to_datetime(frame["日期"]).dt.strftime("%Y-%m-%d")
            backtest_service.load_stock_data=lambda _code, frame=frame: frame.copy()
            for period_name, period in PERIODS.items():
                for strategy in STRATEGIES:
                    try:
                        response=run_backtest(code, period["start"], period["end"], 100000.0, {}, strategy)
                        curve=_portfolio_curve(response)
                        results.append({"code":code,"period":period_name,"strategy":strategy,
                            "total_return":float(response["summary"]["total_return"]),
                            "max_drawdown":_max_drawdown(curve),"trade_count":len(response["trades"])})
                    except Exception as exc:
                        results.append({"code":code,"period":period_name,"strategy":strategy,"error":str(exc)})
    finally:
        backtest_service.load_stock_data=original_loader
    summary={}
    oos=[r for r in results if r["period"]=="out_of_sample" and "error" not in r]
    bh={r["code"]:r["total_return"] for r in oos if r["strategy"]=="buy_and_hold"}
    for strategy in STRATEGIES:
        rows=[r for r in oos if r["strategy"]==strategy]
        returns=[r["total_return"] for r in rows]; drawdowns=[r["max_drawdown"] for r in rows]
        summary[strategy]={"mean_return":mean(returns) if returns else None,"median_return":median(returns) if returns else None,
            "mean_max_drawdown":mean(drawdowns) if drawdowns else None,
            "beat_buy_and_hold_ratio":(sum(r["total_return"]>bh[r["code"]] for r in rows if r["code"] in bh)/sum(r["code"] in bh for r in rows)) if any(r["code"] in bh for r in rows) else None}
    return {"periods":PERIODS,"strategies":STRATEGIES,"results":results,"skipped":skipped,"out_of_sample_summary":summary,"tuning_performed":False}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--data-dir", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    args=parser.parse_args(); result=evaluate_cached_strategies(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")

if __name__ == "__main__": main()
