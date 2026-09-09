import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _frame(rows: int = 180) -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=rows, freq="B")
    close = np.linspace(80.0, 130.0, rows)
    close[-4:] = [118.0, 116.0, 117.0, 119.0]
    volume = np.full(rows, 1_000_000.0)
    return pd.DataFrame({
        "日期": dates.strftime("%Y-%m-%d"),
        "开盘": close,
        "最高": close * 1.01,
        "最低": close * 0.99,
        "收盘": close,
        "成交量": volume,
        "成交额": close * volume,
        "换手率": np.full(rows, 0.02),
    })


def _request(strategy_name="trend_pullback_maw_macd"):
    return {
        "stock_code": "600000",
        "start_date": "2025-06-01",
        "end_date": "2025-12-31",
        "initial_cash": 100000,
        "strategy_name": strategy_name,
        "strategy_params": {},
    }


def test_invalid_stock_strategy_is_rejected():
    response = client.post("/api/backtest/run", json=_request("typo"))
    assert response.status_code == 422


def test_trend_strategy_returns_aligned_series_and_signal_dates(monkeypatch):
    monkeypatch.setattr("app.services.backtest_service.load_stock_data", lambda _: _frame())
    response = client.post("/api/backtest/run", json=_request())
    assert response.status_code == 200, response.text
    data = response.json()
    for name in (
        "maw20", "maw60", "maw120", "macd_dif", "macd_dea",
        "macd_histogram", "target_position", "position_ratio",
    ):
        assert len(data[name]) == len(data["dates"])
    assert all(trade["signal_date"] == trade["date"] for trade in data["trades"])
    assert data["summary"]["rebalance_count"] == len(data["trades"])


def test_trend_warmup_carries_indicators_without_portfolio_state_leakage(monkeypatch):
    frame = _frame(180)
    frame.loc[150:, "收盘"] = 100.0
    frame.loc[150:, "开盘"] = 100.0
    frame.loc[150:, "最高"] = 101.0
    frame.loc[150:, "最低"] = 99.0
    frame.loc[150:, "成交额"] = frame.loc[150:, "收盘"] * frame.loc[150:, "成交量"]
    requested_start = frame.at[150, "日期"]
    request = _request()
    request["start_date"] = requested_start
    request["end_date"] = frame.at[179, "日期"]

    def fake_maw(df, period):
        starts = {20: 100.0, 60: 90.0, 120: 70.0}
        ends = {20: 110.0, 60: 100.0, 120: 80.0}
        return pd.Series(np.linspace(starts[period], ends[period], len(df)), index=df.index)

    def fake_macd(close):
        n = len(close)
        return (
            pd.Series(np.ones(n), index=close.index),
            pd.Series(np.zeros(n), index=close.index),
            pd.Series(np.arange(n, dtype=float), index=close.index),
        )

    monkeypatch.setattr("app.services.backtest_service.load_stock_data", lambda _: frame)
    monkeypatch.setattr("app.core.trend_pullback.calc_maw", fake_maw)
    monkeypatch.setattr("app.core.trend_pullback.calc_macd", fake_macd)

    response = client.post("/api/backtest/run", json=request)
    assert response.status_code == 200, response.text
    data = response.json()

    # Warmup bars satisfy the mocked buy rules, but requested execution must start
    # with fresh cash/shares/cost/last-buy/trade state on the first requested bar.
    assert data["trades"][0]["date"] == requested_start
    assert data["trades"][0]["direction"] == "买入"
    assert data["trades"][0]["reason"] == "趋势回撤开仓"
    assert data["summary"]["total_fees"] == data["trades"][0]["total_fee"]
    assert data["summary"]["final_cash"] == data["trades"][0]["remaining_cash"]
    assert data["summary"]["final_shares"] == data["trades"][0]["shares"]
    assert data["summary"]["rebalance_count"] == 1

    # Indicator values on requested bars still come from the full-history index.
    assert data["maw60"][0] == np.linspace(90.0, 100.0, len(frame))[150]
    assert data["macd_histogram"][0] == 150.0


def test_existing_strategy_returns_null_trend_series(monkeypatch):
    monkeypatch.setattr("app.services.backtest_service.load_stock_data", lambda _: _frame())
    response = client.post("/api/backtest/run", json=_request("buy_and_hold"))
    assert response.status_code == 200, response.text
    data = response.json()
    nulls = [None] * len(data["dates"])
    for name in (
        "maw60", "maw120", "macd_dif", "macd_dea", "macd_histogram",
        "target_position", "position_ratio",
    ):
        assert data[name] == nulls
    assert data["summary"]["max_position_ratio"] == 0.0
    assert data["summary"]["average_position_ratio"] == 0.0
    assert data["summary"]["rebalance_count"] == 0


def test_trend_strategy_missing_maw_columns_returns_400(monkeypatch):
    monkeypatch.setattr(
        "app.services.backtest_service.load_stock_data",
        lambda _: _frame().drop(columns=["成交额", "换手率"]),
    )
    response = client.post("/api/backtest/run", json=_request())
    assert response.status_code == 400
    assert "MAW" in response.json()["detail"]

def test_return_focused_trend_strategy_is_registered_and_aligned(monkeypatch):
    monkeypatch.setattr("app.services.backtest_service.load_stock_data", lambda _: _frame())
    response = client.post("/api/backtest/run", json=_request("trend_following_maw_macd"))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["strategy_name"] == "trend_following_maw_macd"
    assert all(len(data[name]) == len(data["dates"]) for name in (
        "maw20", "maw60", "maw120", "macd_dif", "macd_dea",
        "macd_histogram", "target_position", "position_ratio",
    ))
    assert all(trade["signal_date"] == trade["date"] for trade in data["trades"])

