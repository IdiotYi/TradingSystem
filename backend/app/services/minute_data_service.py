import math
from typing import Literal, cast

import pandas as pd

from app.services.data_service import normalize_code


MinutePeriod = Literal["5", "30"]

MINUTE_COLUMNS = [
    "时间", "股票代码", "周期",
    "开盘", "最高", "最低", "收盘",
    "成交量", "成交额", "复权", "数据源",
]
VALID_PERIODS = {"5", "30"}

_BAOSTOCK_COLUMNS = [
    "date", "time", "code", "open", "high",
    "low", "close", "volume", "amount", "adjustflag",
]
_SINA_COLUMNS = {"day", "open", "high", "low", "close", "volume", "amount"}
_EASTMONEY_COLUMNS = {"时间", "开盘", "最高", "最低", "收盘", "成交量", "成交额"}
_PRICE_COLUMNS = ["开盘", "最高", "最低", "收盘"]
_NUMERIC_COLUMNS = _PRICE_COLUMNS + ["成交量", "成交额"]


def normalize_minute_code(stock_code: str) -> str:
    code = str(stock_code).strip()
    for prefix in ("sh.", "sz.", "bj.", "SH.", "SZ.", "BJ."):
        if code.startswith(prefix):
            code = code[len(prefix):]
            break
    code = normalize_code(code).strip()
    if len(code) != 6 or not code.isdigit():
        raise ValueError("股票代码必须为6位数字")
    return code


def to_baostock_code(code: str) -> str:
    normalized = normalize_minute_code(code)
    if normalized.startswith("6"):
        return f"sh.{normalized}"
    if normalized.startswith(("0", "3")):
        return f"sz.{normalized}"
    raise ValueError(f"暂不支持分钟数据代码: {normalized}")


def _normalize_period(period: str) -> MinutePeriod:
    normalized = str(period).strip()
    if normalized not in VALID_PERIODS:
        raise ValueError(f"分钟周期必须为 {sorted(VALID_PERIODS)}")
    return cast(MinutePeriod, normalized)


def _empty_minute_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=MINUTE_COLUMNS)


def _validate_price_rows(df: pd.DataFrame) -> None:
    finite_mask = df.loc[:, _PRICE_COLUMNS].apply(lambda column: column.map(math.isfinite))
    if not finite_mask.all().all():
        raise ValueError("分钟数据OHLC必须为有限数值")
    if (df["最高"] < df["最低"]).any():
        raise ValueError("分钟数据最高价不能低于最低价")


def _finalize_minute_frame(
    df: pd.DataFrame,
    code: str,
    period: str,
    source: str,
) -> pd.DataFrame:
    if df is None or df.empty:
        return _empty_minute_frame()

    result = df.copy()
    result["时间"] = pd.to_datetime(result["时间"], errors="raise").dt.strftime("%Y-%m-%d %H:%M:%S")
    for column in _NUMERIC_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="raise")

    _validate_price_rows(result)

    result["股票代码"] = normalize_minute_code(code)
    result["周期"] = _normalize_period(period)
    result["复权"] = "qfq"
    result["数据源"] = str(source).strip()

    result = (
        result.sort_values("时间", kind="mergesort")
        .drop_duplicates(subset=["时间"], keep="last")
        .reset_index(drop=True)
    )
    return result.loc[:, MINUTE_COLUMNS]


def normalize_baostock_minutes(rows: list[list[str]], code: str, period: str) -> pd.DataFrame:
    if not rows:
        return _empty_minute_frame()

    raw = pd.DataFrame(rows, columns=_BAOSTOCK_COLUMNS)
    result = raw.rename(columns={
        "open": "开盘",
        "high": "最高",
        "low": "最低",
        "close": "收盘",
        "volume": "成交量",
        "amount": "成交额",
    })
    result["时间"] = pd.to_datetime(
        raw["time"],
        format="%Y%m%d%H%M%S%f",
        errors="raise",
    )
    return _finalize_minute_frame(
        result.loc[:, ["时间", "开盘", "最高", "最低", "收盘", "成交量", "成交额"]],
        code=code,
        period=period,
        source="baostock",
    )


def normalize_akshare_minutes(
    df: pd.DataFrame,
    code: str,
    period: str,
    source: str,
) -> pd.DataFrame:
    if df is None or df.empty:
        return _empty_minute_frame()

    columns = set(df.columns)
    if _SINA_COLUMNS.issubset(columns):
        result = df.rename(columns={
            "day": "时间",
            "open": "开盘",
            "high": "最高",
            "low": "最低",
            "close": "收盘",
            "volume": "成交量",
            "amount": "成交额",
        })
    elif _EASTMONEY_COLUMNS.issubset(columns):
        result = df.copy()
    else:
        raise ValueError("不支持的分钟数据列")

    return _finalize_minute_frame(
        result.loc[:, ["时间", "开盘", "最高", "最低", "收盘", "成交量", "成交额"]],
        code=code,
        period=period,
        source=source,
    )
