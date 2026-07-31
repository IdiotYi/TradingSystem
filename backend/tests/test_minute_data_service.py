import importlib
import importlib.util
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
