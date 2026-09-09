"""Fixed-window local-cache strategy evaluation; this module never tunes parameters."""
from __future__ import annotations

import argparse
import re
import json
from pathlib import Path
from statistics import mean, median

import pandas as pd

from app.services.backtest_service import run_backtest

PERIODS = {
    "development_historical": {"start": "2021-01-01", "end": "2023-12-31"},
    "later_holdout": {"start": "2024-01-01", "end": "2025-12-31"},
}
STRATEGIES = ["buy_and_hold", "three_factors", "supertrend_ma", "trend_pullback_maw_macd", "trend_following_maw_macd"]
REQUIRED_FIELDS = {"日期", "开盘", "最高", "最低", "收盘", "成交量"}
MAW_FIELDS = {"成交额", "成交量", "换手率"}
NUMERIC_FIELDS = {"开盘", "最高", "最低", "收盘", "成交量", "成交额", "换手率"}
COVERAGE_START = pd.Timestamp("2021-01-01")
COVERAGE_END = pd.Timestamp("2025-12-31")


def _max_drawdown(values: list[float]) -> float:
    if not values:
        return 0.0
    peak = float(values[0])
    worst = 0.0
    for value in values:
        value = float(value)
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, (value - peak) / peak)
    return worst


def _validate_frame(frame: pd.DataFrame) -> str | None:
    missing = sorted(REQUIRED_FIELDS.difference(frame.columns))
    if missing:
        return f"missing required fields: {', '.join(missing)}"
    missing_maw = sorted(MAW_FIELDS.difference(frame.columns))
    if missing_maw:
        return f"missing MAW fields: {', '.join(missing_maw)}"
    dates = pd.to_datetime(frame["日期"], errors="coerce")
    if dates.isna().any():
        return "invalid dates"
    for column in sorted(NUMERIC_FIELDS):
        numeric = pd.to_numeric(frame[column], errors="coerce")
        if numeric.isna().any():
            return f"invalid numeric field: {column}"
        frame[column] = numeric
    if dates.min() > COVERAGE_START or dates.max() < COVERAGE_END:
        return "insufficient fixed boundary coverage: 2021-01-01 ~ 2025-12-31"
    return None


def evaluate_cached_strategies(data_dir: Path, codes: list[str] | None = None) -> dict:
    data_dir = Path(data_dir)
    if codes is None:
        codes = sorted(p.stem for p in data_dir.glob("[0-9][0-9][0-9][0-9][0-9][0-9].csv"))
    results = []
    skipped = []
    failures = []
    for supplied_code in codes:
        code = str(supplied_code)
        if re.fullmatch(r"\d{6}", code) is None:
            skipped.append({"code": code, "reason": "invalid code: expected exactly 6 digits"})
            continue
        path = data_dir / f"{code}.csv"
        if not path.exists():
            skipped.append({"code": code, "reason": "cache file not found"})
            continue
        frame = pd.read_csv(path, encoding="utf-8-sig")
        reason = _validate_frame(frame)
        if reason:
            skipped.append({"code": code, "reason": reason})
            continue
        frame["日期"] = pd.to_datetime(frame["日期"]).dt.strftime("%Y-%m-%d")
        for period_name, period in PERIODS.items():
            for strategy in STRATEGIES:
                try:
                    response = run_backtest(
                        stock_code=code,
                        start_date=period["start"],
                        end_date=period["end"],
                        initial_cash=100000.0,
                        strategy_params={},
                        strategy_name=strategy,
                        market_data=frame,
                    )
                    curve = response["portfolio_value"]
                    if len(curve) != len(response["dates"]):
                        raise ValueError("portfolio curve length does not match dates")
                    if curve and abs(float(curve[-1]) - float(response["summary"]["final_assets"])) > 0.011:
                        raise ValueError("portfolio curve final value does not match final assets")
                    results.append({
                        "code": code, "period": period_name, "strategy": strategy,
                        "total_return": float(response["summary"]["total_return"]),
                        "max_drawdown": _max_drawdown(curve),
                        "trade_count": len(response["trades"]),
                    })
                except Exception as exc:
                    failures.append({"code": code, "period": period_name, "strategy": strategy, "reason": str(exc)})
    summary = {}
    holdout = [r for r in results if r["period"] == "later_holdout"]
    bh = {r["code"]: r["total_return"] for r in holdout if r["strategy"] == "buy_and_hold"}
    for strategy in STRATEGIES:
        rows = [r for r in holdout if r["strategy"] == strategy]
        returns = [r["total_return"] for r in rows]
        drawdowns = [r["max_drawdown"] for r in rows]
        comparable = [r for r in rows if r["code"] in bh]
        summary[strategy] = {
            "mean_return": mean(returns) if returns else None,
            "median_return": median(returns) if returns else None,
            "mean_max_drawdown": mean(drawdowns) if drawdowns else None,
            "beat_buy_and_hold_ratio": (sum(r["total_return"] > bh[r["code"]] for r in comparable) / len(comparable)) if comparable else None,
        }
    return {
        "evaluation_kind": "fixed_historical_comparison",
        "parameter_selection_performed": False,
        "periods": PERIODS,
        "strategies": STRATEGIES,
        "results": results,
        "skipped": skipped,
        "failures": failures,
        "later_holdout_summary": summary,
        "code_universe": sorted({row["code"] for row in results}),
        "code_universe_size": len({row["code"] for row in results}),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate_cached_strategies(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
