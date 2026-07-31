import importlib
import importlib.util
from datetime import date
from pathlib import Path
from typing import get_args

import pandas as pd
import pytest


def load_service():
    if importlib.util.find_spec("app.services.minute_data_service") is None:
        pytest.fail("minute_data_service module missing")
    return importlib.import_module("app.services.minute_data_service")


def test_minute_schema_defines_exact_columns_and_periods():
    service = load_service()

    assert service.MINUTE_COLUMNS == [
        "时间", "股票代码", "周期",
        "开盘", "最高", "最低", "收盘",
        "成交量", "成交额", "复权", "数据源",
    ]
    assert service.VALID_PERIODS == {"5", "30"}
    assert set(get_args(service.MinutePeriod)) == {"5", "30"}


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("600519", "sh.600519"),
        ("000001", "sz.000001"),
    ],
)
def test_to_baostock_code_maps_supported_a_share_codes(code, expected):
    service = load_service()

    assert service.to_baostock_code(code) == expected


def test_to_baostock_code_rejects_unsupported_exchange():
    service = load_service()

    with pytest.raises(ValueError, match="暂不支持"):
        service.to_baostock_code("430047")


def test_normalize_baostock_minutes_normalizes_rows_to_exact_schema():
    service = load_service()
    rows = [[
        "2026-07-29", "20260729150000000", "sh.600519",
        "1319.8", "1325", "1319", "1321", "148791",
        "196561700", "2",
    ]]

    result = service.normalize_baostock_minutes(rows, code="600519", period="5")

    assert result.columns.tolist() == service.MINUTE_COLUMNS
    assert result.to_dict("records") == [{
        "时间": "2026-07-29 15:00:00",
        "股票代码": "600519",
        "周期": "5",
        "开盘": 1319.8,
        "最高": 1325.0,
        "最低": 1319.0,
        "收盘": 1321.0,
        "成交量": 148791.0,
        "成交额": 196561700.0,
        "复权": "qfq",
        "数据源": "baostock",
    }]


def test_normalize_baostock_minutes_sorts_and_deduplicates_by_timestamp():
    service = load_service()
    rows = [
        [
            "2026-07-29", "20260729150500000", "sh.600519",
            "1321", "1326", "1320", "1324", "100", "1000", "2",
        ],
        [
            "2026-07-29", "20260729150000000", "sh.600519",
            "1319.8", "1325", "1319", "1321", "148791", "196561700", "2",
        ],
        [
            "2026-07-29", "20260729150000000", "sh.600519",
            "1319.8", "1325", "1319", "1321", "148791", "196561700", "2",
        ],
    ]

    result = service.normalize_baostock_minutes(rows, code="600519", period="5")

    assert result["时间"].tolist() == [
        "2026-07-29 15:00:00",
        "2026-07-29 15:05:00",
    ]


def test_normalize_baostock_minutes_rejects_rows_for_a_different_code():
    service = load_service()
    rows = [[
        "2026-07-29", "20260729150000000", "sz.000001",
        "1319.8", "1325", "1319", "1321", "148791", "196561700", "2",
    ]]

    with pytest.raises(ValueError, match="代码.*不一致"):
        service.normalize_baostock_minutes(rows, code="600519", period="5")


@pytest.mark.parametrize("adjustflag", ["1", "3", ""])
def test_normalize_baostock_minutes_rejects_non_qfq_adjustflag(adjustflag):
    service = load_service()
    rows = [[
        "2026-07-29", "20260729150000000", "sh.600519",
        "1319.8", "1325", "1319", "1321", "148791", "196561700", adjustflag,
    ]]

    with pytest.raises(ValueError, match="复权.*2"):
        service.normalize_baostock_minutes(rows, code="600519", period="5")


@pytest.mark.parametrize(
    "rows",
    [
        [[
            "2026-07-29", "20260729150000000", "sh.600519",
            "nan", "1325", "1319", "1321", "148791", "196561700", "2",
        ]],
        [[
            "2026-07-29", "20260729150000000", "sh.600519",
            "1319.8", "1318", "1319", "1321", "148791", "196561700", "2",
        ]],
    ],
)
def test_normalize_baostock_minutes_rejects_invalid_price_rows(rows):
    service = load_service()

    with pytest.raises(ValueError):
        service.normalize_baostock_minutes(rows, code="600519", period="5")


def test_normalize_akshare_minutes_accepts_sina_columns():
    service = load_service()
    df = pd.DataFrame({
        "day": ["2026-07-29 15:05:00", "2026-07-29 15:00:00"],
        "open": ["1321", "1319.8"],
        "high": ["1326", "1325"],
        "low": ["1320", "1319"],
        "close": ["1324", "1321"],
        "volume": ["100", "148791"],
        "amount": ["1000", "196561700"],
    })

    result = service.normalize_akshare_minutes(df, code="600519", period="5", source="sina")

    assert result.columns.tolist() == service.MINUTE_COLUMNS
    assert result.to_dict("records") == [
        {
            "时间": "2026-07-29 15:00:00",
            "股票代码": "600519",
            "周期": "5",
            "开盘": 1319.8,
            "最高": 1325.0,
            "最低": 1319.0,
            "收盘": 1321.0,
            "成交量": 148791.0,
            "成交额": 196561700.0,
            "复权": "qfq",
            "数据源": "sina",
        },
        {
            "时间": "2026-07-29 15:05:00",
            "股票代码": "600519",
            "周期": "5",
            "开盘": 1321.0,
            "最高": 1326.0,
            "最低": 1320.0,
            "收盘": 1324.0,
            "成交量": 100.0,
            "成交额": 1000.0,
            "复权": "qfq",
            "数据源": "sina",
        },
    ]


def test_normalize_akshare_minutes_accepts_eastmoney_columns():
    service = load_service()
    df = pd.DataFrame({
        "时间": ["2026-07-29 15:00:00"],
        "开盘": ["1319.8"],
        "最高": ["1325"],
        "最低": ["1319"],
        "收盘": ["1321"],
        "成交量": ["148791"],
        "成交额": ["196561700"],
    })

    result = service.normalize_akshare_minutes(df, code="600519", period="30", source="eastmoney")

    assert result.to_dict("records") == [{
        "时间": "2026-07-29 15:00:00",
        "股票代码": "600519",
        "周期": "30",
        "开盘": 1319.8,
        "最高": 1325.0,
        "最低": 1319.0,
        "收盘": 1321.0,
        "成交量": 148791.0,
        "成交额": 196561700.0,
        "复权": "qfq",
        "数据源": "eastmoney",
    }]


def test_a_share_falls_back_to_akshare(monkeypatch):
    service = load_service()
    monkeypatch.setattr(
        "app.services.minute_data_service._download_baostock",
        lambda code, period, start, end: (_ for _ in ()).throw(
            ValueError("baostock unavailable")
        ),
    )
    fallback = pd.DataFrame({
        "day": ["2026-07-29 15:00:00"],
        "open": [10.0], "high": [11.0], "low": [9.0], "close": [10.5],
        "volume": [1000], "amount": [10500],
    })
    monkeypatch.setattr(
        "app.services.minute_data_service._download_akshare",
        lambda code, period, start, end: (fallback, "akshare_sina"),
    )

    frame, metadata = service.download_minute_data("600519", "5")

    assert metadata["data_source"] == "akshare_sina"
    assert len(frame) == 1


def test_etf_skips_baostock(monkeypatch):
    service = load_service()
    fallback = pd.DataFrame({
        "day": ["2026-07-29 15:00:00"],
        "open": [4.0], "high": [4.1], "low": [3.9], "close": [4.05],
        "volume": [2000], "amount": [8100],
    })
    monkeypatch.setattr(
        "app.services.minute_data_service._download_baostock",
        lambda *args: pytest.fail("ETF must not call BaoStock"),
    )
    monkeypatch.setattr(
        "app.services.minute_data_service._download_akshare",
        lambda code, period, start, end: (fallback, "akshare_sina"),
    )

    frame, metadata = service.download_minute_data("510300", "30")

    assert len(frame) == 1
    assert metadata["data_source"] == "akshare_sina"


def make_standard_minutes(times):
    return pd.DataFrame({
        "时间": times,
        "股票代码": ["600519"] * len(times),
        "周期": ["5"] * len(times),
        "开盘": [10.0] * len(times),
        "最高": [11.0] * len(times),
        "最低": [9.0] * len(times),
        "收盘": [10.5] * len(times),
        "成交量": [1000.0] * len(times),
        "成交额": [10500.0] * len(times),
        "复权": ["qfq"] * len(times),
        "数据源": ["baostock"] * len(times),
    })


def test_refresh_crops_two_years_and_deduplicates(monkeypatch, tmp_path):
    service = load_service()
    frame = make_standard_minutes([
        "2024-07-20 15:00:00",
        "2024-07-29 15:00:00",
        "2024-07-29 15:00:00",
        "2026-07-29 15:00:00",
    ])
    monkeypatch.setattr(
        "app.services.minute_data_service.DATA_DIR", tmp_path
    )
    monkeypatch.setattr(
        "app.services.minute_data_service._today",
        lambda: date(2026, 7, 29),
    )
    monkeypatch.setattr(
        "app.services.minute_data_service.download_minute_data",
        lambda code, period: (
            frame,
            {"data_source": "baostock"},
        ),
    )

    result = service.refresh_minute_data("600519", "5")
    cached = pd.read_csv(
        tmp_path / "Minute_600519_5.csv", encoding="utf-8-sig"
    )

    assert cached["时间"].tolist() == [
        "2024-07-29 15:00:00",
        "2026-07-29 15:00:00",
    ]
    assert result["coverage_from"] == "2024-07-29 15:00:00"
    assert result["coverage_to"] == "2026-07-29 15:00:00"
    assert result["target_coverage_met"] is True


def test_failed_refresh_preserves_existing_cache(monkeypatch, tmp_path):
    service = load_service()
    target = tmp_path / "Minute_600519_30.csv"
    target.write_text("existing-cache", encoding="utf-8")
    monkeypatch.setattr(
        "app.services.minute_data_service.DATA_DIR", tmp_path
    )
    monkeypatch.setattr(
        "app.services.minute_data_service.download_minute_data",
        lambda code, period: (_ for _ in ()).throw(
            ValueError("all providers failed")
        ),
    )

    with pytest.raises(ValueError, match="all providers failed"):
        service.refresh_minute_data("600519", "30")

    assert target.read_text(encoding="utf-8") == "existing-cache"


@pytest.mark.parametrize(
    ("column", "value", "pattern"),
    [
        ("股票代码", "000001", "股票代码"),
        ("周期", "30", "周期"),
    ],
)
def test_load_rejects_cache_metadata_mismatch(monkeypatch, tmp_path, column, value, pattern):
    service = load_service()
    cached = make_standard_minutes(["2026-07-29 15:00:00"])
    cached[column] = [value]
    target = tmp_path / "Minute_600519_5.csv"
    cached.to_csv(target, index=False, encoding="utf-8-sig")
    monkeypatch.setattr(
        "app.services.minute_data_service.DATA_DIR", tmp_path
    )

    with pytest.raises(ValueError, match=pattern):
        service.load_minute_data("600519", "5")


def test_atomic_write_uses_unique_temp_files_for_same_target(monkeypatch, tmp_path):
    service = load_service()
    target = tmp_path / "Minute_600519_5.csv"
    first = make_standard_minutes(["2026-07-29 15:00:00"])
    second = make_standard_minutes(["2026-07-29 15:05:00"])
    original_replace = Path.replace
    nested_write_started = False

    def replace_with_nested(self, other):
        nonlocal nested_write_started
        if not nested_write_started:
            nested_write_started = True
            service._atomic_write_minute_csv(second, target)
        return original_replace(self, other)

    monkeypatch.setattr(Path, "replace", replace_with_nested)

    service._atomic_write_minute_csv(first, target)
    cached = pd.read_csv(target, encoding="utf-8-sig")

    assert cached["时间"].tolist() == ["2026-07-29 15:00:00"]
    assert list(tmp_path.glob("*.tmp")) == []
