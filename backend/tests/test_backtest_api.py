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


def test_existing_strategy_returns_null_trend_series(monkeypatch):
    monkeypatch.setattr("app.services.backtest_service.load_stock_data", lambda _: _frame())
    response = client.post("/api/backtest/run", json=_request("buy_and_hold"))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["maw60"] == [None] * len(data["dates"])
    assert data["macd_dif"] == [None] * len(data["dates"])
    assert data["summary"]["max_position_ratio"] == 0.0


def test_trend_strategy_missing_maw_columns_returns_400(monkeypatch):
    monkeypatch.setattr(
        "app.services.backtest_service.load_stock_data",
        lambda _: _frame().drop(columns=["成交额", "换手率"]),
    )
    response = client.post("/api/backtest/run", json=_request())
    assert response.status_code == 400
    assert "MAW" in response.json()["detail"]
