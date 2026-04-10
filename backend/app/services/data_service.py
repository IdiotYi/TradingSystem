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


def _download(code: str, csv_path: Path) -> None:
    """Download stock/ETF data via akshare with fallback chain. Raises ValueError if all fail."""
    df = None

    # 1. stock_zh_a_hist (preferred for A-shares)
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        if df is None or df.empty:
            df = None
    except Exception:
        df = None

    # 2. stock_zh_a_daily (fallback)
    if df is None or df.empty:
        try:
            if code.startswith("6"):
                sym = f"sh{code}"
            elif code.startswith(("0", "3")):
                sym = f"sz{code}"
            elif code.startswith(("8", "4")):
                sym = f"bj{code}"
            else:
                sym = f"sz{code}"
            df = ak.stock_zh_a_daily(symbol=sym, adjust="qfq")
            if df is not None and not df.empty:
                df.rename(columns={
                    "date": "日期", "open": "开盘", "high": "最高",
                    "low": "最低", "close": "收盘", "volume": "成交量",
                    "amount": "成交额", "outstanding_share": "流通股本",
                    "turnover": "换手率",
                }, inplace=True)
                df.insert(1, "股票代码", code)
        except Exception:
            df = None

    # 3. fund_etf_hist_sina (ETF fallback)
    if df is None or df.empty:
        try:
            sym = f"sh{code}" if code.startswith("6") else f"sz{code}"
            df = ak.fund_etf_hist_sina(symbol=sym)
            if df is not None and not df.empty:
                df.rename(columns={
                    "date": "日期", "open": "开盘", "high": "最高",
                    "low": "最低", "close": "收盘", "volume": "成交量",
                }, inplace=True)
                df.insert(1, "股票代码", code)
            else:
                df = None
        except Exception:
            df = None

    if df is None or df.empty:
        raise ValueError(f"无法获取股票 {code} 的数据，请确认代码正确（已尝试股票/ETF接口）。")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")


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
    return df
