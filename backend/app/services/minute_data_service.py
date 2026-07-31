import math
from datetime import date
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

import akshare as ak
import baostock as bs
import pandas as pd

from app.config import DATA_DIR
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


def _validate_baostock_metadata(raw: pd.DataFrame, requested_code: str) -> None:
    expected_code = normalize_minute_code(requested_code)

    def normalize_provider_code(value: object) -> str:
        try:
            return normalize_minute_code(str(value).strip())
        except ValueError as exc:
            raise ValueError(f"BaoStock分钟数据代码无效: {value!r}") from exc

    provider_codes = raw["code"].map(normalize_provider_code)
    mismatched_codes = raw.loc[provider_codes != expected_code, "code"].drop_duplicates().tolist()
    if mismatched_codes:
        raise ValueError(
            f"BaoStock分钟数据代码与请求代码不一致: 期望 {expected_code}, 实际 {mismatched_codes}"
        )

    adjustflags = raw["adjustflag"].fillna("").map(lambda value: str(value).strip())
    invalid_adjustflags = raw.loc[adjustflags != "2", "adjustflag"].fillna("").drop_duplicates().tolist()
    if invalid_adjustflags:
        raise ValueError(
            f"BaoStock分钟数据复权标记必须全部为前复权(2): 实际 {invalid_adjustflags}"
        )


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
    _validate_baostock_metadata(raw, requested_code=code)
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


def _today() -> date:
    return date.today()


def is_etf_code(code: str) -> bool:
    normalized = normalize_minute_code(code)
    return normalized.startswith(("1", "5"))


def _to_akshare_symbol(code: str) -> str:
    normalized = normalize_minute_code(code)
    if normalized.startswith(("5", "6")):
        return f"sh{normalized}"
    if normalized.startswith(("0", "1", "3")):
        return f"sz{normalized}"
    if normalized.startswith(("4", "8")):
        return f"bj{normalized}"
    return f"sz{normalized}"


def _requested_window() -> tuple[date, date]:
    end_date = _today()
    start_date = (pd.Timestamp(end_date) - pd.DateOffset(years=2)).date()
    return start_date, end_date


def _require_history_rows(frame: pd.DataFrame, provider_name: str) -> pd.DataFrame:
    if frame is None or frame.empty:
        raise ValueError(f"{provider_name} 未返回分钟数据")
    return frame


def _download_baostock(
    code: str,
    period: MinutePeriod,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    login = bs.login()
    if login.error_code != "0":
        raise ValueError(f"BaoStock 登录失败: {login.error_msg}")
    try:
        rs = bs.query_history_k_data_plus(
            to_baostock_code(code),
            "date,time,code,open,high,low,close,volume,amount,adjustflag",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            frequency=period,
            adjustflag="2",
        )
        if rs.error_code != "0":
            raise ValueError(f"BaoStock 下载失败: {rs.error_msg}")
        rows: list[list[str]] = []
        while rs.next():
            rows.append(rs.get_row_data())
        return _require_history_rows(
            normalize_baostock_minutes(rows, code, period),
            "BaoStock",
        )
    finally:
        bs.logout()


def _download_akshare(
    code: str,
    period: MinutePeriod,
    start_date: date,
    end_date: date,
) -> tuple[pd.DataFrame, str]:
    provider_errors: list[str] = []

    try:
        eastmoney = ak.stock_zh_a_hist_min_em(
            symbol=code,
            start_date=f"{start_date} 09:30:00",
            end_date=f"{end_date} 15:00:00",
            period=period,
            adjust="qfq",
        )
        normalized = _require_history_rows(
            normalize_akshare_minutes(
                eastmoney,
                code=code,
                period=period,
                source="akshare_eastmoney",
            ),
            "AKShare Eastmoney",
        )
        return normalized, "akshare_eastmoney"
    except Exception as exc:
        provider_errors.append(f"AKShare Eastmoney: {exc}")

    try:
        sina = ak.stock_zh_a_minute(
            symbol=_to_akshare_symbol(code),
            period=period,
            adjust="qfq",
        )
        normalized = _require_history_rows(
            normalize_akshare_minutes(
                sina,
                code=code,
                period=period,
                source="akshare_sina",
            ),
            "AKShare Sina",
        )
        return normalized, "akshare_sina"
    except Exception as exc:
        provider_errors.append(f"AKShare Sina: {exc}")

    raise ValueError("; ".join(provider_errors))


def _minute_cache_path(code: str, period: MinutePeriod) -> Path:
    return DATA_DIR / f"Minute_{code}_{period}.csv"


def _crop_minute_frame(
    frame: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    if frame is None or frame.empty:
        return _empty_minute_frame()

    result = frame.copy()
    timestamps = pd.to_datetime(result["时间"], errors="raise")
    window_end = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    in_window = (timestamps >= pd.Timestamp(start_date)) & (timestamps <= window_end)
    result = result.loc[in_window].reset_index(drop=True)
    if result.empty:
        return _empty_minute_frame()

    return (
        result.sort_values("时间", kind="mergesort")
        .drop_duplicates(subset=["时间"], keep="last")
        .reset_index(drop=True)
        .loc[:, MINUTE_COLUMNS]
    )


def _coerce_download_frame(
    frame: pd.DataFrame,
    code: str,
    period: MinutePeriod,
    source: str,
) -> pd.DataFrame:
    _require_history_rows(frame, source)
    if set(MINUTE_COLUMNS).issubset(frame.columns):
        return frame.loc[:, MINUTE_COLUMNS].copy()
    return normalize_akshare_minutes(frame, code=code, period=period, source=source)


def _atomic_write_minute_csv(df: pd.DataFrame, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(f"{target.name}.{uuid4().hex}.tmp")
    try:
        df.to_csv(temp, index=False, encoding="utf-8-sig")
        pd.read_csv(temp, encoding="utf-8-sig")
        temp.replace(target)
    finally:
        if temp.exists():
            temp.unlink()


def _read_minute_csv(
    target: Path,
    expected_code: str,
    expected_period: MinutePeriod,
) -> pd.DataFrame:
    frame = pd.read_csv(
        target,
        encoding="utf-8-sig",
        dtype={
            "股票代码": "string",
            "周期": "string",
            "复权": "string",
            "数据源": "string",
        },
    )
    frame["时间"] = pd.to_datetime(frame["时间"], errors="raise").dt.strftime("%Y-%m-%d %H:%M:%S")
    for column in _NUMERIC_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    _validate_price_rows(frame)
    frame["股票代码"] = frame["股票代码"].map(lambda value: normalize_minute_code(str(value).strip()))
    frame["周期"] = frame["周期"].map(lambda value: _normalize_period(str(value).strip()))
    if not frame["股票代码"].eq(expected_code).all():
        raise ValueError(f"分钟数据缓存股票代码与请求不一致: 期望 {expected_code}")
    if not frame["周期"].eq(expected_period).all():
        raise ValueError(f"分钟数据缓存周期与请求不一致: 期望 {expected_period}")
    frame["复权"] = frame["复权"].map(lambda value: str(value).strip())
    if not frame["复权"].eq("qfq").all():
        raise ValueError("分钟数据缓存复权标记必须为qfq")
    frame["数据源"] = frame["数据源"].map(lambda value: str(value).strip())
    return (
        frame.sort_values("时间", kind="mergesort")
        .drop_duplicates(subset=["时间"], keep="last")
        .reset_index(drop=True)
        .loc[:, MINUTE_COLUMNS]
    )


def _build_minute_metadata(frame: pd.DataFrame, start_date: date) -> dict:
    coverage_from = frame["时间"].iloc[0]
    coverage_to = frame["时间"].iloc[-1]
    return {
        "coverage_from": coverage_from,
        "coverage_to": coverage_to,
        "data_source": str(frame["数据源"].iloc[-1]).strip(),
        "target_coverage_met": (
            pd.Timestamp(coverage_from)
            <= pd.Timestamp(start_date) + pd.Timedelta(days=7)
        ),
    }


def _load_cached_minute_data(
    target: Path,
    code: str,
    period: MinutePeriod,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    cached = _read_minute_csv(target, code, period)
    cropped = _crop_minute_frame(cached, start_date, end_date)
    if not cropped.equals(cached):
        _atomic_write_minute_csv(cropped, target)
        cached = _read_minute_csv(target, code, period)
    else:
        cached = cropped
    if cached.empty:
        raise ValueError("分钟数据缓存在当前两年窗口内无可用数据，请显式刷新")
    return cached


def download_minute_data(
    stock_code: str,
    period: MinutePeriod,
) -> tuple[pd.DataFrame, dict]:
    code = normalize_minute_code(stock_code)
    normalized_period = _normalize_period(period)
    start_date, end_date = _requested_window()
    provider_errors: list[str] = []

    if not is_etf_code(code):
        try:
            frame = _download_baostock(code, normalized_period, start_date, end_date)
            return frame, _build_minute_metadata(frame, start_date)
        except Exception as exc:
            provider_errors.append(f"BaoStock: {exc}")

    try:
        frame, source = _download_akshare(code, normalized_period, start_date, end_date)
        frame = _coerce_download_frame(frame, code, normalized_period, source)
        metadata = _build_minute_metadata(frame, start_date)
        metadata["data_source"] = source
        return frame, metadata
    except Exception as exc:
        provider_errors.append(str(exc))

    raise ValueError(f"分钟数据下载失败: {'; '.join(provider_errors)}")


def refresh_minute_data(stock_code: str, period: MinutePeriod) -> dict:
    code = normalize_minute_code(stock_code)
    normalized_period = _normalize_period(period)
    start_date, end_date = _requested_window()
    target = _minute_cache_path(code, normalized_period)
    frame, metadata = download_minute_data(code, normalized_period)
    cropped = _crop_minute_frame(frame, start_date, end_date)
    _require_history_rows(cropped, "分钟数据")
    _atomic_write_minute_csv(cropped, target)
    cached = _read_minute_csv(target, code, normalized_period)
    result = _build_minute_metadata(cached, start_date)
    result.update({
        "stock_code": code,
        "period": normalized_period,
        "rows": len(cached),
        "data_source": metadata["data_source"],
    })
    return result


def load_minute_data(
    stock_code: str,
    period: MinutePeriod,
) -> tuple[pd.DataFrame, dict]:
    code = normalize_minute_code(stock_code)
    normalized_period = _normalize_period(period)
    start_date, end_date = _requested_window()
    target = _minute_cache_path(code, normalized_period)
    if not target.exists():
        refresh_minute_data(code, normalized_period)
    cached = _load_cached_minute_data(
        target,
        code,
        normalized_period,
        start_date,
        end_date,
    )
    return cached, _build_minute_metadata(cached, start_date)
