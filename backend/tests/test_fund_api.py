import asyncio

import httpx
import pandas as pd
import pytest

from app.main import app
from app.services.fund_data_service import FundNotFoundError


async def _post(path: str, body: dict) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.post(path, json=body)


def post_json(path: str, body: dict) -> httpx.Response:
    return asyncio.run(_post(path, body))


def make_fund_df() -> pd.DataFrame:
    return pd.DataFrame({
        "日期": ["2024-01-04", "2024-01-05"],
        "基金代码": ["000001", "000001"],
        "基金名称": ["示例基金", "示例基金"],
        "基金类型": ["混合型", "混合型"],
        "单位净值": [1.0, 1.1234567],
        "日增长率": [0.0, 12.35],
        "每份分红": [0.0, 0.0],
        "拆分类型": ["", ""],
        "拆分折算比例": [1.0, 1.0],
    })


def test_fund_analysis_returns_service_payload(monkeypatch):
    payload = {
        "success": True,
        "fund_code": "000001",
        "fund_name": "示例基金",
        "fund_type": "混合型",
        "date_from": "2024-01-04",
        "date_to": "2024-01-05",
        "rows": 2,
        "latest_nav": 1.123457,
    }
    monkeypatch.setattr("app.api.fund.get_fund_analysis", lambda code: payload)

    response = post_json("/api/fund/analysis", {"fund_code": "000001"})

    assert response.status_code == 200
    assert response.json() == payload


def test_fund_refresh_returns_service_payload(monkeypatch):
    payload = {
        "fund_code": "000001",
        "fund_name": "示例基金",
        "fund_type": "混合型",
        "rows": 120,
        "date_from": "2020-01-02",
        "date_to": "2024-01-05",
    }
    monkeypatch.setattr("app.api.fund.refresh_fund", lambda code: payload)

    response = post_json("/api/fund/refresh", {"fund_code": "000001"})

    assert response.status_code == 200
    assert response.json() == payload


def test_fund_backtest_rejects_invalid_weekday():
    response = post_json("/api/fund/backtest", {
        "fund_code": "000001",
        "strategy_name": "weekly_investment",
        "start_date": "2020-01-01",
        "weekday": 0,
        "amount": 1000,
    })

    assert response.status_code == 422


def test_fund_backtest_invalid_strategy_maps_to_400():
    response = post_json("/api/fund/backtest", {
        "fund_code": "000001",
        "strategy_name": "monthly_investment",
        "start_date": "2020-01-01",
        "weekday": 5,
        "amount": 1000,
    })

    assert response.status_code == 400
    assert response.json()["detail"] == "不支持的基金定投策略: monthly_investment"


@pytest.mark.parametrize(
    ("target", "endpoint", "body"),
    [
        ("app.api.fund.get_fund_analysis", "/api/fund/analysis", {"fund_code": "999999"}),
        ("app.api.fund.refresh_fund", "/api/fund/refresh", {"fund_code": "999999"}),
        (
            "app.api.fund.run_fund_backtest",
            "/api/fund/backtest",
            {
                "fund_code": "999999",
                "strategy_name": "weekly_investment",
                "start_date": "2020-01-01",
                "weekday": 5,
                "amount": 1000,
            },
        ),
    ],
)
def test_missing_fund_maps_to_404(monkeypatch, target, endpoint, body):
    monkeypatch.setattr(
        target,
        lambda *args, **kwargs: (_ for _ in ()).throw(
            FundNotFoundError("基金代码不存在: 999999")
        ),
    )

    response = post_json(endpoint, body)

    assert response.status_code == 404
    assert response.json()["detail"] == "基金代码不存在: 999999"


def test_fund_analysis_maps_value_error_to_400(monkeypatch):
    monkeypatch.setattr(
        "app.api.fund.get_fund_analysis",
        lambda code: (_ for _ in ()).throw(ValueError("基金类型不支持")),
    )

    response = post_json("/api/fund/analysis", {"fund_code": "000009"})

    assert response.status_code == 400
    assert response.json()["detail"] == "基金类型不支持"


def test_fund_backtest_maps_unexpected_errors_to_500(monkeypatch):
    monkeypatch.setattr(
        "app.api.fund.run_fund_backtest",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    response = post_json("/api/fund/backtest", {
        "fund_code": "000001",
        "strategy_name": "weekly_investment",
        "start_date": "2020-01-01",
        "weekday": 5,
        "amount": 1000,
    })

    assert response.status_code == 500
    assert response.json()["detail"] == "基金定投回测失败: boom"


def test_get_fund_analysis_returns_latest_nav_and_range(monkeypatch):
    from app.services.fund_investment_service import get_fund_analysis

    monkeypatch.setattr(
        "app.services.fund_investment_service.load_fund_data",
        lambda code: make_fund_df(),
    )

    result = get_fund_analysis("000001")

    assert result == {
        "success": True,
        "fund_code": "000001",
        "fund_name": "示例基金",
        "fund_type": "混合型",
        "date_from": "2024-01-04",
        "date_to": "2024-01-05",
        "rows": 2,
        "latest_nav": 1.123457,
    }


def test_run_fund_backtest_wraps_core_result(monkeypatch):
    from app.services.fund_investment_service import run_fund_backtest

    monkeypatch.setattr(
        "app.services.fund_investment_service.load_fund_data",
        lambda code: make_fund_df(),
    )
    monkeypatch.setattr(
        "app.services.fund_investment_service.run_weekly_investment",
        lambda df, start_date, weekday, amount: {
            "summary": {"investment_count": 1, "total_invested": amount},
            "dates": ["2024-01-05"],
            "total_invested_series": [amount],
            "asset_value_series": [1100.0],
            "return_series": [0.1],
            "events": [],
        },
    )

    result = run_fund_backtest("000001", "weekly_investment", "2024-01-01", 5, 1000.0)

    assert result == {
        "success": True,
        "fund_code": "000001",
        "summary": {"investment_count": 1, "total_invested": 1000.0},
        "dates": ["2024-01-05"],
        "total_invested_series": [1000.0],
        "asset_value_series": [1100.0],
        "return_series": [0.1],
        "events": [],
    }


def test_run_fund_backtest_rejects_unsupported_strategy():
    from app.services.fund_investment_service import run_fund_backtest

    with pytest.raises(ValueError, match="不支持的基金定投策略: monthly_investment"):
        run_fund_backtest("000001", "monthly_investment", "2024-01-01", 5, 1000.0)
