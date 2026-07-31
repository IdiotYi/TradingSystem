import math
import re
from pathlib import Path

import akshare as ak
import pandas as pd
from app.config import DATA_DIR


FUND_COLUMNS = [
    "日期",
    "基金代码",
    "基金名称",
    "基金类型",
    "单位净值",
    "日增长率",
    "每份分红",
    "拆分类型",
    "拆分折算比例",
]

UNSUPPORTED_FUND_TYPE_KEYWORDS = (
    "货币",
    "ETF",
    "场内",
    "交易型开放式",
    "上市开放式",
)


class FundNotFoundError(ValueError):
    pass


def normalize_fund_code(fund_code: str) -> str:
    code = str(fund_code).strip()
    if len(code) != 6 or not code.isdigit():
        raise ValueError("基金代码必须为6位数字")
    return code


def _parse_dividend_per_share(value: object) -> float:
    match = re.search(r"每10份派现金([0-9.]+)元", str(value))
    if not match:
        raise ValueError(f"无法解析基金分红: {value}")
    return float(match.group(1)) / 10


def _parse_split_ratio(value: object) -> float:
    match = re.fullmatch(r"\s*([0-9.]+)\s*:\s*([0-9.]+)\s*", str(value))
    if not match or float(match.group(1)) == 0:
        raise ValueError(f"无法解析基金拆分比例: {value}")
    return float(match.group(2)) / float(match.group(1))


def _normalize_dates(series: pd.Series) -> pd.Series:
    dates = pd.to_datetime(series, errors="raise")
    return dates.dt.strftime("%Y-%m-%d")


def _normalize_dividends(dividend_df: pd.DataFrame) -> pd.DataFrame:
    if dividend_df is None or dividend_df.empty:
        return pd.DataFrame(columns=["日期", "每份分红"])
    result = dividend_df.loc[:, ["除息日", "每10份分红"]].copy()
    result["日期"] = _normalize_dates(result["除息日"])
    result["每份分红"] = result["每10份分红"].map(_parse_dividend_per_share)
    return result.loc[:, ["日期", "每份分红"]]


def _normalize_splits(split_df: pd.DataFrame) -> pd.DataFrame:
    if split_df is None or split_df.empty:
        return pd.DataFrame(columns=["日期", "拆分类型", "拆分折算比例"])
    result = split_df.loc[:, ["拆分折算日", "拆分类型", "拆分折算比例"]].copy()
    result["日期"] = _normalize_dates(result["拆分折算日"])
    result["拆分类型"] = result["拆分类型"].fillna("").astype(str)
    result["拆分折算比例"] = result["拆分折算比例"].map(_parse_split_ratio)
    return result.loc[:, ["日期", "拆分类型", "拆分折算比例"]]


def _require_history_rows(df: pd.DataFrame) -> None:
    if df is None or df.empty:
        raise ValueError("基金净值数据不能为空")


def normalize_fund_history(
    nav_df: pd.DataFrame,
    dividend_df: pd.DataFrame,
    split_df: pd.DataFrame,
    fund_code: str,
    fund_name: str,
    fund_type: str,
) -> pd.DataFrame:
    _require_history_rows(nav_df)
    result = nav_df.rename(columns={"净值日期": "日期"}).loc[:, ["日期", "单位净值", "日增长率"]].copy()
    result["日期"] = _normalize_dates(result["日期"])
    result["基金代码"] = normalize_fund_code(fund_code)
    result["基金名称"] = str(fund_name)
    result["基金类型"] = str(fund_type)

    if result["日期"].duplicated().any():
        raise ValueError("基金净值数据存在重复日期")

    result["单位净值"] = pd.to_numeric(result["单位净值"], errors="raise")
    result["日增长率"] = pd.to_numeric(result["日增长率"], errors="raise")
    if not result["单位净值"].map(math.isfinite).all():
        raise ValueError("基金单位净值必须为有限数值")
    if not result["单位净值"].gt(0).all():
        raise ValueError("基金单位净值必须大于0")

    result = result.merge(_normalize_dividends(dividend_df), on="日期", how="left")
    result = result.merge(_normalize_splits(split_df), on="日期", how="left")
    result["每份分红"] = result["每份分红"].fillna(0.0)
    result["拆分类型"] = result["拆分类型"].fillna("")
    result["拆分折算比例"] = result["拆分折算比例"].fillna(1.0)

    result = result.sort_values("日期").reset_index(drop=True)
    return result.loc[:, FUND_COLUMNS]


def _validate_supported_type(fund_type: str) -> None:
    normalized_type = str(fund_type).strip()
    upper_type = normalized_type.upper()
    for keyword in UNSUPPORTED_FUND_TYPE_KEYWORDS:
        if keyword == "ETF":
            if keyword in upper_type:
                raise ValueError(f"不支持基金类型: {normalized_type}")
        elif keyword in normalized_type:
            raise ValueError(f"不支持基金类型: {normalized_type}")


def _fetch_exchange_listed_fund_codes() -> set[str]:
    funds = ak.fund_etf_fund_daily_em()
    if funds is None or funds.empty:
        raise ValueError("场内ETF列表不能为空")
    if "基金代码" not in funds.columns:
        raise ValueError("场内ETF列表缺少基金代码")

    codes = (
        funds["基金代码"]
        .astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(6)
    )
    valid_codes = set(codes[codes.str.fullmatch(r"\d{6}", na=False)].tolist())
    if not valid_codes:
        raise ValueError("场内ETF列表未包含有效基金代码")
    return valid_codes


def _fetch_fund_metadata(code: str) -> dict:
    funds = ak.fund_name_em().copy()
    funds["基金代码"] = funds["基金代码"].astype(str).str.zfill(6)
    match = funds.loc[funds["基金代码"] == code]
    if match.empty:
        raise FundNotFoundError(f"基金代码不存在: {code}")
    row = match.iloc[0]
    return {
        "基金代码": code,
        "基金简称": str(row["基金简称"]),
        "基金类型": str(row["基金类型"]),
    }


def _download_normalized_fund_data(code: str) -> pd.DataFrame:
    metadata = _fetch_fund_metadata(code)
    _validate_supported_type(metadata["基金类型"])
    if code in _fetch_exchange_listed_fund_codes():
        raise ValueError(f"不支持场内ETF基金: {code}")
    nav = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
    dividends = ak.fund_open_fund_info_em(symbol=code, indicator="分红送配详情")
    splits = ak.fund_open_fund_info_em(symbol=code, indicator="拆分详情")
    return normalize_fund_history(
        nav_df=nav,
        dividend_df=dividends,
        split_df=splits,
        fund_code=code,
        fund_name=metadata["基金简称"],
        fund_type=metadata["基金类型"],
    )


def _cache_path(code: str) -> Path:
    return DATA_DIR / f"Fund_{code}.csv"


def _atomic_write_csv(df: pd.DataFrame, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    try:
        df.to_csv(temp, index=False, encoding="utf-8-sig")
        pd.read_csv(temp, encoding="utf-8-sig")
        temp.replace(target)
    finally:
        if temp.exists():
            temp.unlink()


def _read_fund_csv(target: Path) -> pd.DataFrame:
    df = pd.read_csv(
        target,
        encoding="utf-8-sig",
        dtype={"基金代码": "string"},
    )
    df["基金代码"] = (
        df["基金代码"]
        .str.strip()
        .str.zfill(6)
        .map(normalize_fund_code)
    )
    df["日期"] = pd.to_datetime(df["日期"], errors="raise").dt.strftime("%Y-%m-%d")
    return df.sort_values("日期").reset_index(drop=True).loc[:, FUND_COLUMNS]


def refresh_fund_data(fund_code: str) -> dict:
    code = normalize_fund_code(fund_code)
    target = _cache_path(code)
    df = _download_normalized_fund_data(code)
    _require_history_rows(df)
    _atomic_write_csv(df, target)
    cached = _read_fund_csv(target)
    return {
        "fund_code": code,
        "fund_name": cached["基金名称"].iloc[0],
        "fund_type": cached["基金类型"].iloc[0],
        "rows": len(cached),
        "date_from": cached["日期"].iloc[0],
        "date_to": cached["日期"].iloc[-1],
    }


def load_fund_data(fund_code: str) -> pd.DataFrame:
    code = normalize_fund_code(fund_code)
    target = _cache_path(code)
    if not target.exists():
        df = _download_normalized_fund_data(code)
        _require_history_rows(df)
        _atomic_write_csv(df, target)
    return _read_fund_csv(target)
