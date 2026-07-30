import pandas as pd
import pytest

from app.services.fund_data_service import (
    FundNotFoundError,
    load_fund_data,
    normalize_fund_code,
    normalize_fund_history,
    refresh_fund_data,
)


def test_normalize_fund_code_requires_six_digits():
    assert normalize_fund_code(" 000001 ") == "000001"
    with pytest.raises(ValueError, match="6位"):
        normalize_fund_code("abc")


def test_normalize_history_merges_dividend_and_split_events():
    nav = pd.DataFrame({
        "净值日期": ["2024-01-04", "2024-01-05"],
        "单位净值": [1.0, 0.8],
        "日增长率": [0.0, -20.0],
    })
    dividends = pd.DataFrame({
        "除息日": ["2024-01-05"],
        "每10份分红": ["每10份派现金1.0000元"],
    })
    splits = pd.DataFrame({
        "拆分折算日": ["2024-01-05"],
        "拆分类型": ["份额折算"],
        "拆分折算比例": ["1:1.2500"],
    })

    result = normalize_fund_history(
        nav, dividends, splits, "000001", "示例基金", "混合型"
    )

    assert result["每份分红"].tolist() == [0.0, 0.1]
    assert result["拆分折算比例"].tolist() == [1.0, 1.25]
    assert result["日期"].tolist() == ["2024-01-04", "2024-01-05"]


def test_normalize_history_rejects_duplicate_dates():
    nav = pd.DataFrame({
        "净值日期": ["2024-01-05", "2024-01-05"],
        "单位净值": [1.0, 1.1],
        "日增长率": [0.0, 10.0],
    })

    with pytest.raises(ValueError, match="重复日期"):
        normalize_fund_history(nav, pd.DataFrame(), pd.DataFrame(), "000001", "示例基金", "混合型")


def test_normalize_history_rejects_non_finite_nav():
    nav = pd.DataFrame({
        "净值日期": ["2024-01-05"],
        "单位净值": [float("inf")],
        "日增长率": [0.0],
    })

    with pytest.raises(ValueError, match="有限"):
        normalize_fund_history(nav, pd.DataFrame(), pd.DataFrame(), "000001", "示例基金", "混合型")


def test_refresh_rejects_money_fund(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.fund_data_service.DATA_DIR", tmp_path)
    monkeypatch.setattr(
        "app.services.fund_data_service._fetch_fund_metadata",
        lambda code: {"基金代码": code, "基金简称": "货币A", "基金类型": "货币型"},
    )
    with pytest.raises(ValueError, match="不支持"):
        refresh_fund_data("000009")


def test_atomic_write_preserves_old_cache_on_failure(monkeypatch, tmp_path):
    target = tmp_path / "Fund_000001.csv"
    target.write_text("old-cache", encoding="utf-8")
    monkeypatch.setattr("app.services.fund_data_service.DATA_DIR", tmp_path)
    monkeypatch.setattr(
        "app.services.fund_data_service._download_normalized_fund_data",
        lambda code: (_ for _ in ()).throw(ValueError("upstream failed")),
    )
    with pytest.raises(ValueError, match="upstream failed"):
        refresh_fund_data("000001")
    assert target.read_text(encoding="utf-8") == "old-cache"


def test_refresh_raises_fund_not_found_when_code_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.fund_data_service.DATA_DIR", tmp_path)
    monkeypatch.setattr(
        "app.services.fund_data_service.ak.fund_name_em",
        lambda: pd.DataFrame({
            "基金代码": ["000002"],
            "基金简称": ["示例基金"],
            "基金类型": ["混合型"],
        }),
    )

    with pytest.raises(FundNotFoundError, match="基金代码不存在: 000001"):
        refresh_fund_data("000001")


def test_load_fund_data_downloads_when_cache_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.fund_data_service.DATA_DIR", tmp_path)
    expected = pd.DataFrame({
        "日期": ["2024-01-05", "2024-01-04"],
        "基金代码": ["000001", "000001"],
        "基金名称": ["示例基金", "示例基金"],
        "基金类型": ["混合型", "混合型"],
        "单位净值": [1.1, 1.0],
        "日增长率": [10.0, 0.0],
        "每份分红": [0.0, 0.0],
        "拆分类型": ["", ""],
        "拆分折算比例": [1.0, 1.0],
    })
    monkeypatch.setattr(
        "app.services.fund_data_service._download_normalized_fund_data",
        lambda code: expected.copy(),
    )

    result = load_fund_data("000001")

    assert (tmp_path / "Fund_000001.csv").exists()
    assert result["日期"].tolist() == ["2024-01-04", "2024-01-05"]
