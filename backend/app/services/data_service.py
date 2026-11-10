"""
Load stock/ETF historical data from local CSV, downloading via akshare if absent.
Mirrors logic from C:/PrivateProjects/TradingStrategy/stock_data_retriever.py.
"""
from pathlib import Path
import pandas as pd
import akshare as ak
from app.config import DATA_DIR


def normalize_code(stock_code: str) -> str:
    """Strip exchange prefixes (sh/sz/bj) from stock code."""
    code = stock_code.strip()
    for prefix in ("sh", "sz", "bj", "SH", "SZ", "BJ"):
        if code.startswith(prefix):
            return code[len(prefix):]
    return code


def _exchange_prefix(code: str) -> str:
    if code.startswith(("5", "6")):
        return f"sh{code}"
    elif code.startswith(("0", "3")):
        return f"sz{code}"
    elif code.startswith(("8", "4")):
        return f"bj{code}"
    return f"sz{code}"


def _download(code: str, csv_path: Path) -> None:
    """Download stock/ETF data via akshare with fallback chain. Raises ValueError if all fail."""
    df = None

    # 1. stock_zh_a_daily 新浪财经（与参考项目 backtest.py 数据源一致）
    try:
        sym = _exchange_prefix(code)
        df = ak.stock_zh_a_daily(symbol=sym, adjust="qfq")
        if df is not None and not df.empty:
            # Also fetch raw close to compute adjustment factor for amount-based VWAP
            try:
                df_raw = ak.stock_zh_a_daily(symbol=sym)
                if df_raw is not None and not df_raw.empty:
                    df = df.merge(
                        df_raw[["date", "close"]].rename(columns={"close": "close_raw"}),
                        on="date", how="left",
                    )
            except Exception:
                pass
            df.rename(columns={
                "date": "日期", "open": "开盘", "high": "最高",
                "low": "最低", "close": "收盘", "volume": "成交量",
                "amount": "成交额", "outstanding_share": "流通股本",
                "turnover": "换手率", "close_raw": "收盘_未复权",
            }, inplace=True)
            df.insert(1, "股票代码", code)
        else:
            df = None
    except Exception:
        df = None

    # 2. stock_zh_a_hist 东方财富（fallback）
    if df is None or df.empty:
        try:
            history = ak.fund_etf_hist_em if code.startswith(("1", "5")) else ak.stock_zh_a_hist
            df = history(symbol=code, period="daily", adjust="qfq")
            if df is None or df.empty:
                df = None
            else:
                # Eastmoney reports lots (100 shares/ETF units), while Sina
                # and our VWAP/MAW calculations use individual shares/units.
                df["成交量"] = pd.to_numeric(df["成交量"], errors="raise") * 100
                if code.startswith(("1", "5")):
                    # ETF distributions/splits can make raw transaction prices
                    # differ from adjusted candles. Carry the adjustment factor.
                    raw = history(symbol=code, period="daily", adjust="")
                    if raw is None or raw.empty:
                        raise ValueError("ETF未复权行情不可用")
                    df = df.merge(
                        raw[["日期", "收盘"]].rename(columns={"收盘": "收盘_未复权"}),
                        on="日期", how="left", validate="one_to_one",
                    )
        except Exception:
            df = None

    # 3. fund_etf_hist_sina 新浪ETF（ETF fallback）
    if df is None or df.empty:
        try:
            sym = _exchange_prefix(code)
            df = ak.fund_etf_hist_sina(symbol=sym)
            if df is not None and not df.empty:
                df.rename(columns={
                    "date": "日期", "open": "开盘", "high": "最高",
                    "low": "最低", "close": "收盘", "volume": "成交量",
                    "amount": "成交额",
                }, inplace=True)
                df.insert(1, "股票代码", code)
            else:
                df = None
        except Exception:
            df = None

    if df is None or df.empty:
        raise ValueError(f"暂时无法获取股票/ETF {code} 的行情（已尝试多个数据源），请稍后重试或检查代码是否受支持。")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if "股票代码" not in df.columns:
        df.insert(1, "股票代码", code)
    df["volume_unit"] = "shares"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")


def refresh_stock_data(stock_code: str) -> dict:
    """Force-download latest data, overwriting any existing CSV."""
    code = normalize_code(stock_code)
    csv_path = DATA_DIR / f"{code}.csv"
    _download(code, csv_path)  # always downloads, ignores existing file
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
    df = df.sort_values("日期").reset_index(drop=True)
    return {
        "stock_code": code,
        "rows": len(df),
        "date_from": df["日期"].iloc[0],
        "date_to": df["日期"].iloc[-1],
    }


def load_stock_data(stock_code: str) -> pd.DataFrame:
    """
    Load OHLCV data for stock_code. Downloads and caches to data/<code>.csv if not present.
    Returns DataFrame with columns: 日期, 开盘, 最高, 最低, 收盘, 成交量 (+ possible extras).
    Rows sorted by 日期 ascending.
    """
    code = normalize_code(stock_code)
    csv_path = DATA_DIR / f"{code}.csv"

    if not csv_path.exists():
        _download(code, csv_path)

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
    df = df.sort_values("日期").reset_index(drop=True)
    # Older unmarked Eastmoney caches were written in the provider's lot
    # units. Recognize that provider's schema, not price-based heuristics.
    # Normalize only in memory to preserve the original cache on disk.
    eastmoney_fields = {"成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"}
    if "volume_unit" not in df.columns and eastmoney_fields.issubset(df.columns):
        df["成交量"] = pd.to_numeric(df["成交量"], errors="raise") * 100
        df["volume_unit"] = "shares"
    if "成交额" not in df.columns and "amount" in df.columns:
        df = df.rename(columns={"amount": "成交额"})
    return df
