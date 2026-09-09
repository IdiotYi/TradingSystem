from pathlib import Path

import pandas as pd
import pytest

from app.services.strategy_evaluation import evaluate_cached_strategies


def _write_csv(path: Path, with_maw: bool = True):
    dates = pd.date_range("2020-01-01", "2025-12-31", freq="B")
    close = pd.Series(range(len(dates)), dtype=float) / 20 + 10
    data = {
        "日期": dates.strftime("%Y-%m-%d"), "开盘": close, "最高": close * 1.01,
        "最低": close * .99, "收盘": close, "成交量": 100000.0,
    }
    if with_maw:
        data.update({"成交额": close * 100000, "换手率": 0.02})
    pd.DataFrame(data).to_csv(path, index=False, encoding="utf-8-sig")


def test_evaluator_uses_fixed_windows_and_all_strategies(tmp_path, monkeypatch):
    _write_csv(tmp_path / "600001.csv")
    calls = []
    def fake_run(code, start, end, cash, params, strategy):
        calls.append((code, start, end, strategy))
        value = {"buy_and_hold": .1, "three_factors": .2, "supertrend_ma": .3,
                 "trend_pullback_maw_macd": .4, "trend_following_maw_macd": .5}[strategy]
        return {"dates": [start, end], "trades": [{}, {}], "summary": {"total_return": value},
                "portfolio_value": [100.0, 100.0 * (1 + value)]}
    monkeypatch.setattr("app.services.strategy_evaluation.run_backtest", fake_run)
    result = evaluate_cached_strategies(tmp_path, ["600001"])
    assert result["periods"] == {
        "train": {"start": "2021-01-01", "end": "2023-12-31"},
        "out_of_sample": {"start": "2024-01-01", "end": "2025-12-31"},
    }
    assert {call[3] for call in calls} == {"buy_and_hold", "three_factors", "supertrend_ma", "trend_pullback_maw_macd", "trend_following_maw_macd"}
    assert len(result["results"]) == 10


def test_evaluator_skips_non_maw_instrument_with_reason(tmp_path):
    _write_csv(tmp_path / "159999.csv", with_maw=False)
    result = evaluate_cached_strategies(tmp_path, ["159999"])
    assert result["results"] == []
    assert result["skipped"] == [{"code": "159999", "reason": "missing MAW fields: 成交额, 换手率"}]


def test_evaluator_aggregates_oos_metrics(tmp_path, monkeypatch):
    for code in ("600001", "600002"):
        _write_csv(tmp_path / f"{code}.csv")
    returns = {
        ("600001", "buy_and_hold"): .10, ("600001", "trend_following_maw_macd"): .30,
        ("600002", "buy_and_hold"): .40, ("600002", "trend_following_maw_macd"): .20,
    }
    def fake_run(code, start, end, cash, params, strategy):
        ret = returns.get((code, strategy), 0.0)
        curve = [100.0, 80.0, 100.0 * (1 + ret)]
        return {"dates": [start, "2025-01-01", end], "trades": [{}],
                "summary": {"total_return": ret}, "portfolio_value": curve}
    monkeypatch.setattr("app.services.strategy_evaluation.run_backtest", fake_run)
    result = evaluate_cached_strategies(tmp_path, ["600001", "600002"])
    agg = result["out_of_sample_summary"]["trend_following_maw_macd"]
    assert agg["mean_return"] == pytest.approx(.25)
    assert agg["median_return"] == pytest.approx(.25)
    assert agg["mean_max_drawdown"] == pytest.approx(-.20)
    assert agg["beat_buy_and_hold_ratio"] == pytest.approx(.5)
