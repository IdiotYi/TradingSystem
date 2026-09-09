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
    def fake_run(*, stock_code, start_date, end_date, initial_cash, strategy_params, strategy_name, market_data):
        calls.append((stock_code, start_date, end_date, strategy_name))
        value = {"buy_and_hold": .1, "three_factors": .2, "supertrend_ma": .3,
                 "trend_pullback_maw_macd": .4, "trend_following_maw_macd": .5}[strategy_name]
        return {"dates": [start_date, end_date], "trades": [{}, {}], "summary": {"total_return": value, "final_assets": initial_cash * (1 + value)},
                "portfolio_value": [initial_cash, initial_cash * (1 + value)]}
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
    def fake_run(*, stock_code, start_date, end_date, initial_cash, strategy_params, strategy_name, market_data):
        ret = returns.get((stock_code, strategy_name), 0.0)
        curve = [initial_cash, initial_cash * .8, initial_cash * (1 + ret)]
        return {"dates": [start_date, "2025-01-01", end_date], "trades": [{}],
                "summary": {"total_return": ret, "final_assets": curve[-1]}, "portfolio_value": curve}
    monkeypatch.setattr("app.services.strategy_evaluation.run_backtest", fake_run)
    result = evaluate_cached_strategies(tmp_path, ["600001", "600002"])
    agg = result["out_of_sample_summary"]["trend_following_maw_macd"]
    assert agg["mean_return"] == pytest.approx(.25)
    assert agg["median_return"] == pytest.approx(.25)
    assert agg["mean_max_drawdown"] == pytest.approx(-.20)
    assert agg["beat_buy_and_hold_ratio"] == pytest.approx(.5)

def test_evaluator_success_rows_have_exact_metrics_and_real_curve_drawdown(tmp_path, monkeypatch):
    _write_csv(tmp_path / "600001.csv")
    def fake_runner(*, stock_code, start_date, end_date, initial_cash, strategy_params, strategy_name, market_data):
        assert market_data is not None
        return {"dates": [start_date, "2025-01-01", end_date], "trades": [{}],
                "summary": {"total_return": .1, "final_assets": 110.0}, "portfolio_value": [100.0, 50.0, 110.0]}
    monkeypatch.setattr("app.services.strategy_evaluation.run_backtest", fake_runner)
    result = evaluate_cached_strategies(tmp_path, ["600001"])
    assert result["failures"] == []
    assert set(result["results"][0]) == {"code", "period", "strategy", "total_return", "max_drawdown", "trade_count"}
    assert result["results"][0]["max_drawdown"] == pytest.approx(-.5)


def test_evaluator_never_calls_normal_loader_and_segregates_failures(tmp_path, monkeypatch):
    _write_csv(tmp_path / "600001.csv")
    def fake_runner(*, strategy_name, market_data, **kwargs):
        assert market_data is not None
        if strategy_name == "three_factors":
            raise RuntimeError("strategy failed")
        return {"dates": ["2024-01-01"], "trades": [], "summary": {"total_return": 0.0, "final_assets": 100000.0}, "portfolio_value": [100000.0]}
    monkeypatch.setattr("app.services.strategy_evaluation.run_backtest", fake_runner)
    result = evaluate_cached_strategies(tmp_path, ["600001"])
    assert all("error" not in row for row in result["results"])
    assert result["failures"] == [
        {"code": "600001", "period": "train", "strategy": "three_factors", "reason": "strategy failed"},
        {"code": "600001", "period": "out_of_sample", "strategy": "three_factors", "reason": "strategy failed"},
    ]


def test_evaluator_skips_invalid_dates_ohlc_and_period_coverage(tmp_path):
    _write_csv(tmp_path / "600001.csv")
    broken = pd.read_csv(tmp_path / "600001.csv", encoding="utf-8-sig").drop(columns=["最高"])
    broken.to_csv(tmp_path / "600001.csv", index=False, encoding="utf-8-sig")
    result = evaluate_cached_strategies(tmp_path, ["600001"])
    assert result["results"] == []
    assert "missing required fields" in result["skipped"][0]["reason"]


def test_portfolio_curve_replays_each_strategy_daily(monkeypatch):
    from app.services.backtest_service import run_backtest
    frame = pd.DataFrame({
        "日期": ["2025-01-01", "2025-01-02", "2025-01-03"],
        "开盘": [10.0, 8.0, 11.0], "最高": [10.0, 8.0, 11.0],
        "最低": [10.0, 8.0, 11.0], "收盘": [10.0, 8.0, 11.0],
        "成交量": [100000.0] * 3, "成交额": [1e6, 8e5, 1.1e6], "换手率": [.02] * 3,
    })
    result = run_backtest("600001", "2025-01-01", "2025-01-03", 100000, {}, "buy_and_hold", market_data=frame)
    assert len(result["portfolio_value"]) == len(result["dates"])
    assert result["portfolio_value"][1] < result["portfolio_value"][0]


@pytest.mark.parametrize("bad_code", ["60001", "6000000", "ABC001", "../001"])
def test_evaluator_rejects_invalid_code_before_file_access(tmp_path, bad_code):
    result = evaluate_cached_strategies(tmp_path, [bad_code])
    assert result["results"] == []
    assert result["skipped"] == [{"code": bad_code, "reason": "invalid code: expected exactly 6 digits"}]


def test_evaluator_skips_invalid_numeric_cache_and_requires_exact_boundary_coverage(tmp_path):
    _write_csv(tmp_path / "600001.csv")
    invalid = pd.read_csv(tmp_path / "600001.csv", encoding="utf-8-sig")
    invalid.loc[0, "收盘"] = "not-a-number"
    invalid.to_csv(tmp_path / "600001.csv", index=False, encoding="utf-8-sig")
    result = evaluate_cached_strategies(tmp_path, ["600001"])
    assert result["results"] == []
    assert "invalid numeric field: 收盘" in result["skipped"][0]["reason"]

    short_dates = pd.date_range("2021-01-04", "2025-12-30", freq="B")
    close = pd.Series(range(len(short_dates)), dtype=float) / 20 + 10
    pd.DataFrame({
        "日期": short_dates.strftime("%Y-%m-%d"), "开盘": close, "最高": close,
        "最低": close, "收盘": close, "成交量": 100000.0,
        "成交额": close * 100000.0, "换手率": .02,
    }).to_csv(tmp_path / "600002.csv", index=False, encoding="utf-8-sig")
    result = evaluate_cached_strategies(tmp_path, ["600002"])
    assert result["results"] == []
    assert result["skipped"] == [{"code": "600002", "reason": "insufficient fixed boundary coverage: 2021-01-01 ~ 2025-12-31"}]


def test_evaluator_with_real_runner_never_calls_normal_loader(tmp_path, monkeypatch):
    _write_csv(tmp_path / "600001.csv")
    monkeypatch.setattr(
        "app.services.backtest_service.load_stock_data",
        lambda _code: (_ for _ in ()).throw(AssertionError("normal loader must not run")),
    )
    result = evaluate_cached_strategies(tmp_path, ["600001"])
    assert result["skipped"] == []
    assert not any("normal loader" in failure["reason"] for failure in result["failures"])
    assert len(result["results"]) == 10


def test_native_strategy_portfolio_curve_matches_summary_final_assets():
    from app.services.backtest_service import run_backtest
    dates = pd.date_range("2020-01-01", "2025-12-31", freq="B")
    close = pd.Series(range(len(dates)), dtype=float) / 50 + 10
    frame = pd.DataFrame({
        "日期": dates.strftime("%Y-%m-%d"), "开盘": close, "最高": close * 1.01,
        "最低": close * .99, "收盘": close, "成交量": 100000.0,
        "成交额": close * 100000.0, "换手率": .02,
    })
    for strategy in ("buy_and_hold", "three_factors", "supertrend_ma", "trend_pullback_maw_macd", "trend_following_maw_macd"):
        response = run_backtest(
            stock_code="600001", start_date="2024-01-01", end_date="2025-12-31",
            initial_cash=100000.0, strategy_params={}, strategy_name=strategy,
            market_data=frame,
        )
        assert len(response["portfolio_value"]) == len(response["dates"])
        assert response["portfolio_value"][-1] == pytest.approx(response["summary"]["final_assets"], abs=.01)
