# TradingSystem Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-stack A-share technical analysis and backtest platform with React frontend and FastAPI backend.

**Architecture:** FastAPI backend computes all indicators and backtest logic in Python; React frontend renders ECharts interactive candlestick charts with draggable time range; CSV data files live in a shared `data/` folder at the project root.

**Tech Stack:** Python 3.11 / FastAPI / pandas / numpy / akshare / scikit-learn; React 18 / TypeScript / Vite / ECharts 5 / Ant Design 5 / Axios

---

## File Map

```
TradingSystem/
├── data/                                      # auto-created, CSV per stock
├── backend/
│   ├── requirements.txt
│   ├── run.py
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── analysis.py
│       │   └── backtest.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── data_service.py
│       │   ├── indicator_service.py
│       │   └── backtest_service.py
│       └── core/
│           ├── __init__.py
│           ├── indicators.py
│           └── three_factors.py
│   └── tests/
│       ├── __init__.py
│       ├── test_indicators.py
│       ├── test_three_factors.py
│       └── test_api.py
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── App.css
│       ├── types/
│       │   ├── stock.ts
│       │   └── backtest.ts
│       ├── services/
│       │   └── api.ts
│       └── components/
│           ├── layout/
│           │   └── Header.tsx
│           ├── technical/
│           │   ├── TechnicalTab.tsx
│           │   ├── KLineChart.tsx
│           │   └── AnalysisCards.tsx
│           └── backtest/
│               ├── BacktestTab.tsx
│               ├── BacktestConfig.tsx
│               ├── BacktestChart.tsx
│               ├── BacktestSummary.tsx
│               └── TradeTable.tsx
```

---

## Task 1: Backend project scaffold

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/run.py`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/tests/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
cd C:/GithubProjects/TradingSystem
mkdir -p backend/app/api backend/app/services backend/app/core backend/tests data
touch backend/app/__init__.py backend/app/api/__init__.py
touch backend/app/services/__init__.py backend/app/core/__init__.py
touch backend/tests/__init__.py
```

- [ ] **Step 2: Write requirements.txt**

`backend/requirements.txt`:
```
fastapi==0.115.0
uvicorn[standard]==0.32.0
pandas==2.2.3
numpy==1.26.4
akshare
scikit-learn==1.5.2
pydantic==2.9.2
python-dotenv==1.0.1
pytest==8.3.3
httpx==0.27.2
```

- [ ] **Step 3: Write config.py**

`backend/app/config.py`:
```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

API_HOST = "0.0.0.0"
API_PORT = 8000
CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
```

- [ ] **Step 4: Write main.py**

`backend/app/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ORIGINS

app = FastAPI(title="TradingSystem API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Write run.py**

`backend/run.py`:
```python
import uvicorn
from app.config import API_HOST, API_PORT

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=API_HOST, port=API_PORT, reload=True)
```

- [ ] **Step 6: Install dependencies and verify**

```bash
cd C:/GithubProjects/TradingSystem/backend
pip install -r requirements.txt
python run.py
```

Expected: Server starts on http://0.0.0.0:8000. Visit http://localhost:8000/health → `{"status":"ok"}`. Stop with Ctrl+C.

- [ ] **Step 7: Commit**

```bash
cd C:/GithubProjects/TradingSystem
git init
git add backend/ data/
git commit -m "feat: backend project scaffold with FastAPI"
```

---

## Task 2: Core indicator functions (MA + SuperTrend) with tests

**Files:**
- Create: `backend/app/core/indicators.py`
- Create: `backend/tests/test_indicators.py`

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_indicators.py`:
```python
import numpy as np
import pandas as pd
import pytest
from app.core.indicators import calc_ma, calc_supertrend


def make_series(values):
    return pd.Series(values, dtype=float)


class TestCalcMa:
    def test_ma5_simple(self):
        close = make_series([10, 11, 12, 13, 14, 15, 16])
        ma = calc_ma(close, 5)
        assert abs(ma.iloc[4] - 12.0) < 1e-6
        assert abs(ma.iloc[5] - 13.0) < 1e-6

    def test_ma_shorter_than_period_is_nan(self):
        close = make_series([10, 11, 12])
        ma = calc_ma(close, 5)
        assert ma.isna().all()

    def test_ma_length_matches_input(self):
        close = make_series(range(20))
        assert len(calc_ma(close, 5)) == 20


class TestCalcSupertrend:
    def test_returns_two_series(self):
        n = 50
        high = make_series(np.random.uniform(105, 110, n))
        low = make_series(np.random.uniform(90, 95, n))
        close = make_series(np.random.uniform(95, 105, n))
        st, direction = calc_supertrend(high, low, close, period=10, multiplier=3.0)
        assert len(st) == n
        assert len(direction) == n

    def test_direction_is_1_or_minus_1(self):
        n = 100
        high = make_series(np.linspace(100, 110, n) + np.random.uniform(0, 2, n))
        low = make_series(np.linspace(95, 105, n) - np.random.uniform(0, 2, n))
        close = make_series(np.linspace(97, 108, n))
        _, direction = calc_supertrend(high, low, close)
        valid = direction.dropna()
        assert set(valid.unique()).issubset({1, -1})

    def test_strong_uptrend_direction(self):
        n = 60
        prices = np.linspace(100, 200, n)
        high = make_series(prices + 2)
        low = make_series(prices - 2)
        close = make_series(prices)
        _, direction = calc_supertrend(high, low, close, period=10, multiplier=3.0)
        # Last bar of a strong uptrend should be direction=1
        assert direction.iloc[-1] == 1
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
cd C:/GithubProjects/TradingSystem/backend
python -m pytest tests/test_indicators.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.core.indicators'`

- [ ] **Step 3: Implement indicators.py**

`backend/app/core/indicators.py`:
```python
from typing import Tuple
import numpy as np
import pandas as pd


def calc_ma(close: pd.Series, period: int) -> pd.Series:
    """Simple moving average."""
    return close.rolling(window=period).mean()


def calc_supertrend(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 10,
    multiplier: float = 3.0,
) -> Tuple[pd.Series, pd.Series]:
    """
    SuperTrend indicator.
    Returns (supertrend_values, direction) where direction=1 is uptrend, -1 is downtrend.
    """
    n = len(close)
    index = close.index
    close_arr = close.values.astype(float)
    high_arr = high.values.astype(float)
    low_arr = low.values.astype(float)

    # True Range
    prev_close = np.empty(n)
    prev_close[0] = close_arr[0]
    prev_close[1:] = close_arr[:-1]

    tr = np.maximum(
        high_arr - low_arr,
        np.maximum(np.abs(high_arr - prev_close), np.abs(low_arr - prev_close)),
    )

    # Wilder's smoothed ATR (EMA with alpha = 1/period)
    atr = np.empty(n)
    atr[0] = tr[0]
    alpha = 1.0 / period
    for i in range(1, n):
        atr[i] = alpha * tr[i] + (1 - alpha) * atr[i - 1]

    hl2 = (high_arr + low_arr) / 2.0
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr

    final_upper = np.empty(n)
    final_lower = np.empty(n)
    supertrend = np.full(n, np.nan)
    direction = np.ones(n, dtype=int)

    final_upper[0] = basic_upper[0]
    final_lower[0] = basic_lower[0]

    for i in range(1, n):
        # Final upper: only move down, unless price broke above it last bar
        final_upper[i] = (
            basic_upper[i]
            if basic_upper[i] < final_upper[i - 1] or close_arr[i - 1] > final_upper[i - 1]
            else final_upper[i - 1]
        )
        # Final lower: only move up, unless price broke below it last bar
        final_lower[i] = (
            basic_lower[i]
            if basic_lower[i] > final_lower[i - 1] or close_arr[i - 1] < final_lower[i - 1]
            else final_lower[i - 1]
        )

        prev_st = supertrend[i - 1]
        if np.isnan(prev_st):
            # Initialise based on first bar
            if close_arr[i] > final_upper[i]:
                direction[i] = 1
                supertrend[i] = final_lower[i]
            else:
                direction[i] = -1
                supertrend[i] = final_upper[i]
        elif prev_st == final_upper[i - 1]:
            # Was downtrend — switch to uptrend if price closes above upper band
            if close_arr[i] > final_upper[i]:
                direction[i] = 1
                supertrend[i] = final_lower[i]
            else:
                direction[i] = -1
                supertrend[i] = final_upper[i]
        else:
            # Was uptrend — switch to downtrend if price closes below lower band
            if close_arr[i] < final_lower[i]:
                direction[i] = -1
                supertrend[i] = final_upper[i]
            else:
                direction[i] = 1
                supertrend[i] = final_lower[i]

    return pd.Series(supertrend, index=index), pd.Series(direction, index=index)
```

- [ ] **Step 4: Run tests, confirm they pass**

```bash
cd C:/GithubProjects/TradingSystem/backend
python -m pytest tests/test_indicators.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/indicators.py backend/tests/test_indicators.py
git commit -m "feat: core indicator functions MA and SuperTrend with tests"
```

---

## Task 3: Three factors core computation with test

**Files:**
- Create: `backend/app/core/three_factors.py`
- Create: `backend/tests/test_three_factors.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_three_factors.py`:
```python
import numpy as np
import pandas as pd
import pytest
from app.core.three_factors import compute_three_factors


def make_ohlc(n=400):
    np.random.seed(42)
    close = pd.Series(np.cumprod(1 + np.random.normal(0.0005, 0.01, n)) * 100)
    high = close * (1 + np.random.uniform(0, 0.02, n))
    low = close * (1 - np.random.uniform(0, 0.02, n))
    open_ = close.shift(1).fillna(close.iloc[0])
    dates = pd.date_range("2020-01-01", periods=n, freq="B").strftime("%Y-%m-%d").tolist()
    return pd.DataFrame({
        "日期": dates,
        "开盘": open_.values,
        "最高": high.values,
        "最低": low.values,
        "收盘": close.values,
    })


class TestComputeThreeFactors:
    def test_returns_required_columns(self):
        df = make_ohlc(400)
        result = compute_three_factors(df)
        assert set(["日期", "score", "score_mean", "score_std"]).issubset(result.columns)

    def test_output_length_less_than_input(self):
        df = make_ohlc(400)
        result = compute_three_factors(df)
        assert len(result) < len(df)

    def test_score_is_numeric(self):
        df = make_ohlc(400)
        result = compute_three_factors(df)
        valid = result["score"].dropna()
        assert len(valid) > 0
        assert valid.dtype == float

    def test_score_mean_lags_by_one(self):
        """score_mean at position i must equal expanding mean of score up to i-1."""
        df = make_ohlc(500)
        result = compute_three_factors(df).reset_index(drop=True)
        # At index 5 (first non-NaN score_mean), score_mean[5] == mean(score[0:5])
        valid_idx = result["score_mean"].first_valid_index()
        if valid_idx is not None and valid_idx > 0:
            expected = result["score"].iloc[:valid_idx].mean()
            actual = result["score_mean"].iloc[valid_idx]
            assert abs(actual - expected) < 1e-6
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
cd C:/GithubProjects/TradingSystem/backend
python -m pytest tests/test_three_factors.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.core.three_factors'`

- [ ] **Step 3: Implement three_factors.py**

`backend/app/core/three_factors.py`:
```python
"""
Three-factor momentum score calculation.
Ported directly from C:/PrivateProjects/TradingStrategy/analysis.py.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

BIAS_N = 60
MOMENTUM_DAY = 60
SLOPE_N = 60
EFFICIENCY_N = 60
ZSCORE_WINDOW = 250


def _bias_momentum(close: pd.Series) -> float:
    if close.empty:
        return np.nan
    bias = close / close.rolling(window=BIAS_N, min_periods=1).mean()
    if len(bias) < MOMENTUM_DAY or bias.iloc[-MOMENTUM_DAY] == 0:
        return np.nan
    bias_recent = bias.iloc[-MOMENTUM_DAY:]
    base = bias_recent.iloc[0]
    if base == 0:
        return np.nan
    x = np.arange(MOMENTUM_DAY).reshape(-1, 1)
    y = (bias_recent / base).values.reshape(-1, 1)
    lr = LinearRegression()
    lr.fit(x, y)
    return float(lr.coef_[0, 0]) * 10000


def _slope_momentum(close: pd.Series) -> float:
    if len(close) < SLOPE_N:
        return np.nan
    base = close.iloc[-SLOPE_N]
    if base == 0 or np.isnan(base):
        return np.nan
    normalized = close.iloc[-SLOPE_N:] / base
    if normalized.isna().any():
        return np.nan
    x = np.arange(1, SLOPE_N + 1).reshape(-1, 1)
    y = normalized.values.reshape(-1, 1)
    lr = LinearRegression()
    lr.fit(x, y)
    return 10000 * float(lr.coef_[0, 0]) * float(lr.score(x, y))


def _efficiency_momentum(df_window: pd.DataFrame) -> float:
    if len(df_window) < EFFICIENCY_N:
        return np.nan
    window = df_window.iloc[-EFFICIENCY_N:]
    pivot = (window["open"] + window["high"] + window["low"] + window["close"]) / 4.0
    pivot = pivot.ffill()
    if pivot.iloc[0] <= 0 or pivot.iloc[-1] <= 0:
        return np.nan
    momentum = 100 * np.log(pivot.iloc[-1] / pivot.iloc[0])
    direction = abs(np.log(pivot.iloc[-1]) - np.log(pivot.iloc[0]))
    volatility = np.log(pivot).diff().abs().sum()
    efficiency_ratio = direction / volatility if volatility > 0 else 0
    return momentum * efficiency_ratio


def compute_three_factors(df_all: pd.DataFrame) -> pd.DataFrame:
    """
    Compute three-factor scores on full historical data with no lookahead.

    Args:
        df_all: DataFrame with columns 日期, 开盘, 最高, 最低, 收盘

    Returns:
        DataFrame with columns: 日期, score, score_mean, score_std
    """
    df_ohlc = df_all.rename(columns={
        "开盘": "open", "最高": "high", "最低": "low", "收盘": "close",
    })
    close_full = df_all["收盘"]
    dates_full = df_all["日期"]

    min_history = max(BIAS_N, MOMENTUM_DAY, SLOPE_N, EFFICIENCY_N)
    results = []
    for i in range(min_history, len(df_all)):
        close_slice = close_full.iloc[: i + 1]
        ohlc_slice = df_ohlc.iloc[: i + 1]
        results.append({
            "日期": dates_full.iloc[i],
            "乖离动量": _bias_momentum(close_slice),
            "斜率动量": _slope_momentum(close_slice),
            "效率动量": _efficiency_momentum(ohlc_slice),
        })

    fdf = pd.DataFrame(results)
    for col, z_col in [("乖离动量", "z_bias"), ("斜率动量", "z_slope"), ("效率动量", "z_eff")]:
        rm = fdf[col].rolling(ZSCORE_WINDOW).mean()
        rs = fdf[col].rolling(ZSCORE_WINDOW).std()
        fdf[z_col] = (fdf[col] - rm) / rs

    fdf["score"] = (2 * fdf["z_bias"] + 2 * fdf["z_slope"] + 6 * fdf["z_eff"]) / 10
    fdf["score_mean"] = fdf["score"].expanding().mean().shift(1)
    fdf["score_std"] = fdf["score"].expanding().std().shift(1)

    return fdf[["日期", "score", "score_mean", "score_std"]]
```

- [ ] **Step 4: Run tests, confirm they pass**

```bash
cd C:/GithubProjects/TradingSystem/backend
python -m pytest tests/test_three_factors.py -v
```

Expected: All 4 tests PASS. (Note: may take ~10s due to iterative computation on 400 rows.)

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/three_factors.py backend/tests/test_three_factors.py
git commit -m "feat: three-factor momentum score computation with tests"
```

---

## Task 4: Data service (load CSV / download via akshare)

**Files:**
- Create: `backend/app/services/data_service.py`

- [ ] **Step 1: Implement data_service.py**

`backend/app/services/data_service.py`:
```python
"""
Load stock/ETF historical data from local CSV, downloading via akshare if absent.
Mirrors logic from C:/PrivateProjects/TradingStrategy/stock_data_retriever.py.
"""
from pathlib import Path
import pandas as pd
import akshare as ak
from app.config import DATA_DIR


def normalize_code(stock_code: str) -> str:
    code = stock_code.strip()
    for prefix in ("sh", "sz", "bj", "SH", "SZ", "BJ"):
        if code.startswith(prefix):
            return code[len(prefix):]
    return code


def _download(code: str, csv_path: Path) -> None:
    df = None

    # 1. stock_zh_a_hist (preferred)
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
    Returns DataFrame with columns: 日期, 开盘, 最高, 最低, 收盘, 成交量 (+ extras).
    """
    code = normalize_code(stock_code)
    csv_path = DATA_DIR / f"{code}.csv"

    if not csv_path.exists():
        _download(code, csv_path)

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
    df = df.sort_values("日期").reset_index(drop=True)
    return df
```

- [ ] **Step 2: Smoke test manually (optional, skip if no network)**

```bash
cd C:/GithubProjects/TradingSystem/backend
python -c "from app.services.data_service import load_stock_data; df = load_stock_data('600519'); print(df.tail(3))"
```

Expected: Last 3 rows of 贵州茸台 OHLCV data printed. File `data/600519.csv` created.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/data_service.py
git commit -m "feat: data service with akshare download fallback chain"
```

---

## Task 5: Indicator service + analysis API endpoint

**Files:**
- Create: `backend/app/services/indicator_service.py`
- Create: `backend/app/api/analysis.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Implement indicator_service.py**

`backend/app/services/indicator_service.py`:
```python
import numpy as np
import pandas as pd
from app.core.indicators import calc_ma, calc_supertrend
from app.services.data_service import load_stock_data


def _to_list(s: pd.Series) -> list:
    return [None if pd.isna(v) else round(float(v), 4) for v in s]


def get_analysis_data(stock_code: str) -> dict:
    df = load_stock_data(stock_code)

    close = df["收盘"]
    high = df["最高"]
    low = df["最低"]
    open_ = df["开盘"]
    volume = df["成交量"]
    dates = df["日期"]

    ma5 = calc_ma(close, 5)
    ma20 = calc_ma(close, 20)
    ma60 = calc_ma(close, 60)
    supertrend, direction = calc_supertrend(high, low, close, period=10, multiplier=3.0)

    # Price percentiles over full history
    close_valid = close.dropna().values
    p20, p50, p80 = np.percentile(close_valid, [20, 50, 80])

    # Max drawdown over full history
    close_arr = close.values
    dates_arr = dates.values
    cummax = np.maximum.accumulate(close_arr)
    drawdown = (close_arr - cummax) / cummax
    trough_idx = int(np.argmin(drawdown))
    peak_idx = int(np.argmax(close_arr[: trough_idx + 1]))

    return {
        "success": True,
        "stock_code": stock_code.strip(),
        "dates": dates.tolist(),
        "open": _to_list(open_),
        "high": _to_list(high),
        "low": _to_list(low),
        "close": _to_list(close),
        "volume": _to_list(volume),
        "ma5": _to_list(ma5),
        "ma20": _to_list(ma20),
        "ma60": _to_list(ma60),
        "supertrend": _to_list(supertrend),
        "supertrend_direction": [
            None if pd.isna(v) else int(v) for v in direction
        ],
        "current_price": round(float(close.iloc[-1]), 2),
        "p20": round(float(p20), 2),
        "p50": round(float(p50), 2),
        "p80": round(float(p80), 2),
        "max_drawdown": round(float(drawdown[trough_idx]), 4),
        "drawdown_peak_date": str(dates_arr[peak_idx]),
        "drawdown_trough_date": str(dates_arr[trough_idx]),
        "drawdown_peak_price": round(float(close_arr[peak_idx]), 2),
        "drawdown_trough_price": round(float(close_arr[trough_idx]), 2),
    }
```

- [ ] **Step 2: Implement analysis API router**

`backend/app/api/analysis.py`:
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.indicator_service import get_analysis_data

router = APIRouter()


class AnalysisRequest(BaseModel):
    stock_code: str


@router.post("/run")
async def run_analysis(request: AnalysisRequest):
    try:
        return get_analysis_data(request.stock_code)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {e}")
```

- [ ] **Step 3: Register router in main.py**

`backend/app/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ORIGINS
from app.api import analysis, backtest

app = FastAPI(title="TradingSystem API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])

@app.get("/health")
async def health():
    return {"status": "ok"}
```

Note: backtest router doesn't exist yet — create a stub first.

- [ ] **Step 4: Create backtest router stub**

`backend/app/api/backtest.py`:
```python
from fastapi import APIRouter
router = APIRouter()
```

- [ ] **Step 5: Verify analysis endpoint**

```bash
cd C:/GithubProjects/TradingSystem/backend
python run.py &
curl -s -X POST http://localhost:8000/api/analysis/run \
  -H "Content-Type: application/json" \
  -d '{"stock_code":"600519"}' | python -c "import sys,json; d=json.load(sys.stdin); print(d['current_price'], d['p20'], d['max_drawdown'])"
```

Expected: Three numbers printed, e.g. `1768.0 1050.2 -0.5423`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/indicator_service.py backend/app/api/analysis.py \
        backend/app/api/backtest.py backend/app/main.py
git commit -m "feat: indicator service and /api/analysis/run endpoint"
```

---

## Task 6: Backtest service + backtest API endpoint

**Files:**
- Create: `backend/app/services/backtest_service.py`
- Modify: `backend/app/api/backtest.py`

- [ ] **Step 1: Implement backtest_service.py**

`backend/app/services/backtest_service.py`:
```python
"""
Three-factor momentum backtest engine.
Fee logic and strategy ported from C:/PrivateProjects/TradingStrategy/backtest.py.
"""
import pandas as pd
import numpy as np
from app.core.three_factors import compute_three_factors
from app.core.indicators import calc_ma, calc_supertrend
from app.services.data_service import load_stock_data


# ── Fee helpers ──────────────────────────────────────────────

def _buy_fees(amount: float) -> dict:
    transfer = round(amount * 0.00001, 2)
    commission = round(amount * 0.000075, 2)
    return {"transfer_fee": transfer, "commission": commission,
            "stamp_tax": None, "total_fee": round(transfer + commission, 2)}


def _sell_fees(amount: float) -> dict:
    transfer = round(amount * 0.00001, 2)
    stamp = round(amount * 0.0005, 2)
    commission = round(amount * 0.000075, 2)
    return {"transfer_fee": transfer, "commission": commission,
            "stamp_tax": stamp, "total_fee": round(transfer + stamp + commission, 2)}


# ── Strategy ─────────────────────────────────────────────────

def _run_strategy(df: pd.DataFrame, initial_cash: float, params: dict) -> list:
    score_rising_days = params.get("score_rising_days", 3)
    oversold_mult = params.get("oversold_std_mult", 2.0)
    tp_pct = params.get("take_profit_pct", 0.15)
    tp_mult = params.get("take_profit_std_mult", 1.5)
    sl_pct = params.get("stop_loss_pct", 0.05)
    add_pct = params.get("add_position_pct", 0.05)
    half_ratio = params.get("half_position_ratio", 0.5)

    trades = []
    cash = initial_cash
    shares = 0
    entry_price = 0.0
    position = "none"   # none | half | full

    def sell_all(row, reason):
        nonlocal cash, shares, entry_price, position
        price = float(row["收盘"])
        amount = shares * price
        fees = _sell_fees(amount)
        cash += amount - fees["total_fee"]
        trades.append({
            "date": row["日期"], "direction": "卖出", "reason": reason,
            "price": round(price, 2), "shares": shares,
            "amount": round(amount, 2), **fees,
            "pnl": round((price - entry_price) * shares - fees["total_fee"], 2),
            "remaining_cash": round(cash, 2),
        })
        shares = 0; entry_price = 0.0; position = "none"

    def buy(row, budget, reason):
        nonlocal cash, shares, entry_price, position
        price = float(row["收盘"])
        n = int(budget // (price * 100)) * 100
        if n == 0:
            return 0
        amount = n * price
        fees = _buy_fees(amount)
        while n > 0 and (amount + fees["total_fee"]) > budget:
            n -= 100; amount = n * price; fees = _buy_fees(amount)
        if n == 0:
            return 0
        entry_price = (shares * entry_price + n * price) / (shares + n)
        cash -= amount + fees["total_fee"]
        shares += n
        trades.append({
            "date": row["日期"], "direction": "买入", "reason": reason,
            "price": round(price, 2), "shares": n,
            "amount": round(amount, 2), **fees,
            "pnl": None, "remaining_cash": round(cash, 2),
        })
        return n

    for i in range(score_rising_days - 1, len(df)):
        row = df.iloc[i]
        price = float(row["收盘"])
        score = row.get("score", float("nan"))
        smean = row.get("score_mean", float("nan"))
        sstd = row.get("score_std", float("nan"))
        acted = False

        # Full: stop-loss
        if position == "full" and (price - entry_price) / entry_price <= -sl_pct:
            sell_all(row, f"全仓亏损{int(sl_pct*100)}%止损")
            acted = True

        # Half/Full: take-profit
        if not acted and shares > 0:
            valid = pd.notna(smean) and pd.notna(sstd) and sstd > 0
            tp1 = (price - entry_price) / entry_price >= tp_pct
            tp2 = valid and pd.notna(score) and score > smean + tp_mult * sstd
            if tp1 or tp2:
                sell_all(row, f"盈利{int(tp_pct*100)}%止盈" if tp1 else "score超上轨止盈")
                acted = True

        # Half: add position on dip
        if not acted and position == "half" and (price - entry_price) / entry_price <= -add_pct:
            if buy(row, cash, f"下跌{int(add_pct*100)}%加仓") > 0:
                position = "full"
            acted = True

        # None: three-factor buy signal
        if not acted and position == "none":
            scores_window = [df.iloc[i - k]["score"] for k in range(score_rising_days - 1, -1, -1)]
            if any(pd.isna(s) for s in scores_window):
                continue
            if pd.isna(smean) or pd.isna(sstd) or sstd == 0:
                continue
            rising = all(scores_window[j] < scores_window[j + 1] for j in range(len(scores_window) - 1))

            def below_lower(r):
                sm, ss = r["score_mean"], r["score_std"]
                return pd.notna(sm) and pd.notna(ss) and ss > 0 and r["score"] < sm - oversold_mult * ss

            oversold = any(below_lower(df.iloc[i - k]) for k in range(score_rising_days))
            if rising and oversold:
                if buy(row, cash * half_ratio, "三因子信号") > 0:
                    position = "half"

    return trades, cash, shares


# ── Public API ───────────────────────────────────────────────

def _to_list(s: pd.Series) -> list:
    return [None if pd.isna(v) else round(float(v), 4) for v in s]


def run_backtest(stock_code: str, start_date: str, end_date: str,
                 initial_cash: float, strategy_params: dict) -> dict:
    df_all = load_stock_data(stock_code)
    df_all = df_all[df_all["日期"] <= end_date].reset_index(drop=True)

    # Compute factors on full history (no lookahead)
    factors = compute_three_factors(df_all)
    df_all = df_all.merge(factors, on="日期", how="left")

    df = df_all[df_all["日期"] >= start_date].reset_index(drop=True)
    if df.empty:
        raise ValueError(f"{start_date} ~ {end_date} 期间无交易数据")

    trades, final_cash, final_shares = _run_strategy(df, initial_cash, strategy_params)

    # Indicators for chart
    close = df["收盘"]; high = df["最高"]; low = df["最低"]; open_ = df["开盘"]
    ma5 = calc_ma(close, 5); ma20 = calc_ma(close, 20); ma60 = calc_ma(close, 60)
    st_vals, st_dir = calc_supertrend(high, low, close, period=10, multiplier=3.0)

    # Summary
    last_price = float(close.iloc[-1])
    total_assets = final_shares * last_price + final_cash
    total_return = (total_assets - initial_cash) / initial_cash
    total_fees = sum(t["total_fee"] for t in trades)

    first_price = float(close.iloc[0])
    bh_shares = int(initial_cash // (first_price * 100)) * 100
    bh_cost = _buy_fees(bh_shares * first_price)["total_fee"]
    bh_assets = bh_shares * last_price + (initial_cash - bh_shares * first_price - bh_cost)
    bh_return = (bh_assets - initial_cash) / initial_cash

    def score_list(col):
        return [None if pd.isna(v) else round(float(v), 6) for v in df[col]]

    return {
        "success": True,
        "dates": df["日期"].tolist(),
        "open": _to_list(open_), "high": _to_list(high),
        "low": _to_list(low), "close": _to_list(close),
        "ma5": _to_list(ma5), "ma20": _to_list(ma20), "ma60": _to_list(ma60),
        "supertrend": _to_list(st_vals),
        "supertrend_direction": [None if pd.isna(v) else int(v) for v in st_dir],
        "score": score_list("score"),
        "score_mean": score_list("score_mean"),
        "score_std": score_list("score_std"),
        "trades": trades,
        "summary": {
            "initial_cash": initial_cash,
            "final_assets": round(total_assets, 2),
            "total_return": round(total_return, 4),
            "total_fees": round(total_fees, 2),
            "benchmark_return": round(bh_return, 4),
            "excess_return": round(total_return - bh_return, 4),
            "final_shares": final_shares,
            "final_cash": round(final_cash, 2),
        },
    }
```

- [ ] **Step 2: Implement backtest API router**

`backend/app/api/backtest.py`:
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.backtest_service import run_backtest

router = APIRouter()


class StrategyParams(BaseModel):
    score_rising_days: int = 3
    oversold_std_mult: float = 2.0
    take_profit_pct: float = 0.15
    take_profit_std_mult: float = 1.5
    stop_loss_pct: float = 0.05
    add_position_pct: float = 0.05
    half_position_ratio: float = 0.5


class BacktestRequest(BaseModel):
    stock_code: str
    start_date: str
    end_date: str
    initial_cash: float = 100000.0
    strategy_params: StrategyParams = StrategyParams()


@router.post("/run")
async def run_backtest_endpoint(request: BacktestRequest):
    try:
        return run_backtest(
            stock_code=request.stock_code,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_cash=request.initial_cash,
            strategy_params=request.strategy_params.model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回测失败: {e}")
```

- [ ] **Step 3: Verify backtest endpoint**

```bash
cd C:/GithubProjects/TradingSystem/backend
python run.py &
curl -s -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{"stock_code":"600519","start_date":"2023-01-01","end_date":"2026-04-10","initial_cash":100000}' \
  | python -c "import sys,json; d=json.load(sys.stdin); s=d['summary']; print('return:', s['total_return'], 'trades:', len(d['trades']))"
```

Expected: Something like `return: 0.12 trades: 4` (numbers will vary).

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/backtest_service.py backend/app/api/backtest.py
git commit -m "feat: three-factor backtest service and /api/backtest/run endpoint"
```

---

## Task 7: Frontend project scaffold (Vite + React + TypeScript)

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`

- [ ] **Step 1: Create frontend directory and package.json**

`frontend/package.json`:
```json
{
  "name": "trading-system-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "antd": "^5.22.0",
    "echarts": "^5.5.1",
    "echarts-for-react": "^3.0.2",
    "axios": "^1.7.9",
    "dayjs": "^1.11.13"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.6.3",
    "vite": "^5.4.11"
  }
}
```

- [ ] **Step 2: Write vite.config.ts**

`frontend/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

- [ ] **Step 3: Write tsconfig.json**

`frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Write index.html**

`frontend/index.html`:
```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>TradingSystem</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Write src/main.tsx**

`frontend/src/main.tsx`:
```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

- [ ] **Step 6: Install dependencies**

```bash
cd C:/GithubProjects/TradingSystem/frontend
npm install
```

Expected: `node_modules/` created, no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: frontend scaffold with Vite + React + TypeScript"
```

---

## Task 8: TypeScript types and API service

**Files:**
- Create: `frontend/src/types/stock.ts`
- Create: `frontend/src/types/backtest.ts`
- Create: `frontend/src/services/api.ts`

- [ ] **Step 1: Write stock.ts**

`frontend/src/types/stock.ts`:
```typescript
export interface AnalysisResponse {
  success: boolean
  stock_code: string
  dates: string[]
  open: (number | null)[]
  high: (number | null)[]
  low: (number | null)[]
  close: (number | null)[]
  volume: (number | null)[]
  ma5: (number | null)[]
  ma20: (number | null)[]
  ma60: (number | null)[]
  supertrend: (number | null)[]
  supertrend_direction: (number | null)[]
  current_price: number
  p20: number
  p50: number
  p80: number
  max_drawdown: number
  drawdown_peak_date: string
  drawdown_trough_date: string
  drawdown_peak_price: number
  drawdown_trough_price: number
}
```

- [ ] **Step 2: Write backtest.ts**

`frontend/src/types/backtest.ts`:
```typescript
export interface StrategyParams {
  score_rising_days: number
  oversold_std_mult: number
  take_profit_pct: number
  take_profit_std_mult: number
  stop_loss_pct: number
  add_position_pct: number
  half_position_ratio: number
}

export const DEFAULT_STRATEGY_PARAMS: StrategyParams = {
  score_rising_days: 3,
  oversold_std_mult: 2.0,
  take_profit_pct: 0.15,
  take_profit_std_mult: 1.5,
  stop_loss_pct: 0.05,
  add_position_pct: 0.05,
  half_position_ratio: 0.5,
}

export interface Trade {
  date: string
  direction: '买入' | '卖出'
  reason: string
  price: number
  shares: number
  amount: number
  transfer_fee: number
  commission: number
  stamp_tax: number | null
  total_fee: number
  pnl: number | null
  remaining_cash: number
}

export interface BacktestSummary {
  initial_cash: number
  final_assets: number
  total_return: number
  total_fees: number
  benchmark_return: number
  excess_return: number
  final_shares: number
  final_cash: number
}

export interface BacktestResponse {
  success: boolean
  dates: string[]
  open: (number | null)[]
  high: (number | null)[]
  low: (number | null)[]
  close: (number | null)[]
  ma5: (number | null)[]
  ma20: (number | null)[]
  ma60: (number | null)[]
  supertrend: (number | null)[]
  supertrend_direction: (number | null)[]
  score: (number | null)[]
  score_mean: (number | null)[]
  score_std: (number | null)[]
  trades: Trade[]
  summary: BacktestSummary
}

export interface BacktestRequest {
  stock_code: string
  start_date: string
  end_date: string
  initial_cash: number
  strategy_params: StrategyParams
}
```

- [ ] **Step 3: Write api.ts**

`frontend/src/services/api.ts`:
```typescript
import axios from 'axios'
import type { AnalysisResponse } from '../types/stock'
import type { BacktestRequest, BacktestResponse } from '../types/backtest'

const client = axios.create({
  baseURL: '/api',
  timeout: 180000,  // 3 min — three-factor computation can be slow
  headers: { 'Content-Type': 'application/json' },
})

export async function runAnalysis(stockCode: string): Promise<AnalysisResponse> {
  const { data } = await client.post<AnalysisResponse>('/analysis/run', { stock_code: stockCode })
  return data
}

export async function runBacktest(request: BacktestRequest): Promise<BacktestResponse> {
  const { data } = await client.post<BacktestResponse>('/backtest/run', request)
  return data
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/ frontend/src/services/
git commit -m "feat: TypeScript types and API service layer"
```

---

## Task 9: App shell, global styles, and Header component

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/App.css`
- Create: `frontend/src/components/layout/Header.tsx`

- [ ] **Step 1: Write App.css (dark theme base)**

`frontend/src/App.css`:
```css
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  background: #0d1117;
  color: #e6edf3;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: #161b22;
  border-bottom: 1px solid #30363d;
  padding: 0 24px;
  height: 60px;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}

.app-logo {
  font-size: 18px;
  font-weight: 700;
  color: #58a6ff;
  letter-spacing: 0.5px;
  white-space: nowrap;
}

.app-content {
  flex: 1;
  padding: 16px 24px;
  overflow: hidden;
}

.tab-pane-inner {
  padding-top: 16px;
}
```

- [ ] **Step 2: Write Header.tsx**

`frontend/src/components/layout/Header.tsx`:
```tsx
import React, { useState } from 'react'
import { Input, Button, Spin } from 'antd'
import { SearchOutlined } from '@ant-design/icons'

interface HeaderProps {
  onAnalyse: (code: string) => void
  loading: boolean
}

const Header: React.FC<HeaderProps> = ({ onAnalyse, loading }) => {
  const [code, setCode] = useState('')

  const handleSubmit = () => {
    const trimmed = code.trim()
    if (trimmed) onAnalyse(trimmed)
  }

  return (
    <div className="app-header">
      <span className="app-logo">📈 TradingSystem</span>
      <Input
        placeholder="输入股票/ETF代码，如 600519"
        value={code}
        onChange={e => setCode(e.target.value)}
        onPressEnter={handleSubmit}
        style={{ width: 260, background: '#21262d', borderColor: '#30363d', color: '#e6edf3' }}
        allowClear
      />
      <Button
        type="primary"
        icon={loading ? <Spin size="small" /> : <SearchOutlined />}
        onClick={handleSubmit}
        disabled={loading}
        style={{ background: '#238636', borderColor: '#238636' }}
      >
        分析
      </Button>
    </div>
  )
}

export default Header
```

- [ ] **Step 3: Write App.tsx**

`frontend/src/App.tsx`:
```tsx
import React, { useState } from 'react'
import { ConfigProvider, Tabs, theme, message } from 'antd'
import './App.css'
import Header from './components/layout/Header'
import TechnicalTab from './components/technical/TechnicalTab'
import BacktestTab from './components/backtest/BacktestTab'
import { runAnalysis } from './services/api'
import type { AnalysisResponse } from './types/stock'

const App: React.FC = () => {
  const [analysisData, setAnalysisData] = useState<AnalysisResponse | null>(null)
  const [stockCode, setStockCode] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('technical')

  const handleAnalyse = async (code: string) => {
    setLoading(true)
    try {
      const data = await runAnalysis(code)
      setAnalysisData(data)
      setStockCode(code.trim())
      setActiveTab('technical')
    } catch (err: any) {
      message.error(err?.response?.data?.detail || `分析失败: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const tabs = [
    {
      key: 'technical',
      label: '技术分析',
      children: (
        <div className="tab-pane-inner">
          <TechnicalTab data={analysisData} loading={loading} />
        </div>
      ),
    },
    {
      key: 'backtest',
      label: '回测',
      children: (
        <div className="tab-pane-inner">
          <BacktestTab stockCode={stockCode} />
        </div>
      ),
      disabled: !stockCode,
    },
  ]

  return (
    <ConfigProvider theme={{ algorithm: theme.darkAlgorithm }}>
      <div className="app-layout">
        <Header onAnalyse={handleAnalyse} loading={loading} />
        <div className="app-content">
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabs}
            style={{ height: '100%' }}
          />
        </div>
      </div>
    </ConfigProvider>
  )
}

export default App
```

- [ ] **Step 4: Create placeholder component files so the app compiles**

`frontend/src/components/technical/TechnicalTab.tsx`:
```tsx
import React from 'react'
import type { AnalysisResponse } from '../../types/stock'

interface Props { data: AnalysisResponse | null; loading: boolean }
const TechnicalTab: React.FC<Props> = () => <div>技术分析 (coming soon)</div>
export default TechnicalTab
```

`frontend/src/components/backtest/BacktestTab.tsx`:
```tsx
import React from 'react'
interface Props { stockCode: string }
const BacktestTab: React.FC<Props> = () => <div>回测 (coming soon)</div>
export default BacktestTab
```

- [ ] **Step 5: Verify the app starts**

```bash
cd C:/GithubProjects/TradingSystem/frontend
npm run dev
```

Expected: `VITE ready on http://localhost:5173`. Open browser, see header with input and button. No errors in console.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.tsx frontend/src/App.css \
        frontend/src/components/layout/ \
        frontend/src/components/technical/TechnicalTab.tsx \
        frontend/src/components/backtest/BacktestTab.tsx
git commit -m "feat: App shell, dark theme, Header component with stock search"
```

---

## Task 10: AnalysisCards component

**Files:**
- Create: `frontend/src/components/technical/AnalysisCards.tsx`

- [ ] **Step 1: Implement AnalysisCards.tsx**

`frontend/src/components/technical/AnalysisCards.tsx`:
```tsx
import React from 'react'
import { Card, Row, Col, Statistic, Tag } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons'
import type { AnalysisResponse } from '../../types/stock'

interface Props {
  data: AnalysisResponse
}

const fmt = (n: number) => n.toFixed(2)
const fmtPct = (n: number) => `${(n * 100).toFixed(2)}%`

const AnalysisCards: React.FC<Props> = ({ data }) => {
  const {
    current_price, p20, p50, p80,
    max_drawdown,
    drawdown_peak_date, drawdown_peak_price,
    drawdown_trough_date, drawdown_trough_price,
  } = data

  const priceTag = () => {
    if (current_price <= p20) return <Tag color="green">低位 (≤P20)</Tag>
    if (current_price >= p80) return <Tag color="red">高位 (≥P80)</Tag>
    return <Tag color="orange">中位</Tag>
  }

  return (
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      {/* Current price */}
      <Col xs={24} sm={8}>
        <Card
          size="small"
          style={{ background: '#161b22', border: '1px solid #30363d' }}
          title={<span style={{ color: '#8b949e' }}>当前价格</span>}
        >
          <Statistic
            value={current_price}
            precision={2}
            prefix="¥"
            valueStyle={{ color: '#e6edf3', fontSize: 24 }}
          />
          <div style={{ marginTop: 8 }}>{priceTag()}</div>
        </Card>
      </Col>

      {/* Percentiles */}
      <Col xs={24} sm={8}>
        <Card
          size="small"
          style={{ background: '#161b22', border: '1px solid #30363d' }}
          title={<span style={{ color: '#8b949e' }}>历史价格百分位（全量）</span>}
        >
          <Row gutter={8}>
            {[['P20', p20, '#26a69a'], ['P50', p50, '#ffd700'], ['P80', p80, '#ef5350']].map(
              ([label, val, color]) => (
                <Col key={label as string} span={8}>
                  <div style={{ color: color as string, fontWeight: 600, fontSize: 12 }}>{label as string}</div>
                  <div style={{ color: '#e6edf3', fontSize: 15 }}>¥{fmt(val as number)}</div>
                </Col>
              )
            )}
          </Row>
        </Card>
      </Col>

      {/* Max Drawdown */}
      <Col xs={24} sm={8}>
        <Card
          size="small"
          style={{ background: '#161b22', border: '1px solid #30363d' }}
          title={<span style={{ color: '#8b949e' }}>历史最大回撤（全量）</span>}
        >
          <Statistic
            value={Math.abs(max_drawdown) * 100}
            precision={2}
            suffix="%"
            prefix={<ArrowDownOutlined />}
            valueStyle={{ color: '#ef5350', fontSize: 20 }}
          />
          <div style={{ color: '#8b949e', fontSize: 11, marginTop: 4 }}>
            峰值 {drawdown_peak_date} ¥{fmt(drawdown_peak_price)}
          </div>
          <div style={{ color: '#8b949e', fontSize: 11 }}>
            谷底 {drawdown_trough_date} ¥{fmt(drawdown_trough_price)}
          </div>
        </Card>
      </Col>
    </Row>
  )
}

export default AnalysisCards
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/technical/AnalysisCards.tsx
git commit -m "feat: AnalysisCards showing price, percentiles, and max drawdown"
```

---

## Task 11: KLineChart component (K-line + MA + SuperTrend)

**Files:**
- Create: `frontend/src/components/technical/KLineChart.tsx`

- [ ] **Step 1: Implement KLineChart.tsx**

`frontend/src/components/technical/KLineChart.tsx`:
```tsx
import React, { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { AnalysisResponse } from '../../types/stock'

interface Props {
  data: AnalysisResponse
}

const KLineChart: React.FC<Props> = ({ data }) => {
  const option = useMemo(() => {
    const { dates, open, high, low, close, ma5, ma20, ma60, supertrend, supertrend_direction } = data

    const candleData = dates.map((_, i) => [open[i], close[i], low[i], high[i]])

    // Split SuperTrend into uptrend (green) / downtrend (red) segments
    const stUp = supertrend.map((v, i) => (supertrend_direction[i] === 1 ? v : null))
    const stDown = supertrend.map((v, i) => (supertrend_direction[i] === -1 ? v : null))

    return {
      backgroundColor: '#0d1117',
      animation: false,
      legend: {
        data: ['K线', 'MA5', 'MA20', 'MA60', 'ST↑', 'ST↓'],
        top: 8,
        textStyle: { color: '#8b949e' },
        inactiveColor: '#444',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross', crossStyle: { color: '#555' } },
        backgroundColor: 'rgba(22,27,34,0.95)',
        borderColor: '#30363d',
        textStyle: { color: '#e6edf3', fontSize: 12 },
        formatter: (params: any[]) => {
          if (!params.length) return ''
          const idx = params[0].dataIndex
          let html = `<div style="font-weight:600;margin-bottom:4px">${dates[idx]}</div>`
          html += `<div>开 <b>${open[idx]?.toFixed(2)}</b>　高 <b>${high[idx]?.toFixed(2)}</b></div>`
          html += `<div>低 <b>${low[idx]?.toFixed(2)}</b>　收 <b style="color:${(close[idx] ?? 0) >= (open[idx] ?? 0) ? '#ef5350' : '#26a69a'}">${close[idx]?.toFixed(2)}</b></div>`
          params.forEach(p => {
            if (p.seriesName === 'K线') return
            const v = Array.isArray(p.value) ? p.value[1] : p.value
            if (v == null) return
            html += `<div style="color:${p.color}">${p.seriesName}: ${Number(v).toFixed(2)}</div>`
          })
          return html
        },
      },
      grid: { left: '5%', right: '3%', top: 60, bottom: 80 },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: true,
        axisLine: { lineStyle: { color: '#30363d' } },
        axisLabel: {
          color: '#8b949e',
          formatter: (v: string) => v.slice(5),
          interval: Math.floor(dates.length / 10),
        },
      },
      yAxis: {
        scale: true,
        axisLine: { lineStyle: { color: '#30363d' } },
        axisLabel: { color: '#8b949e', formatter: (v: number) => v.toFixed(0) },
        splitLine: { lineStyle: { color: '#161b22' } },
      },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider', show: true, bottom: 20,
          start: 0, end: 100,
          borderColor: '#30363d', fillerColor: 'rgba(35,134,54,0.15)',
          textStyle: { color: '#8b949e' },
          handleStyle: { color: '#238636' },
        },
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: candleData,
          itemStyle: {
            color: '#ef5350', color0: '#26a69a',
            borderColor: '#ef5350', borderColor0: '#26a69a',
          },
        },
        { name: 'MA5', type: 'line', data: ma5, smooth: false,
          lineStyle: { color: '#ffffff', width: 1 }, showSymbol: false },
        { name: 'MA20', type: 'line', data: ma20, smooth: false,
          lineStyle: { color: '#ffd700', width: 1 }, showSymbol: false },
        { name: 'MA60', type: 'line', data: ma60, smooth: false,
          lineStyle: { color: '#1890ff', width: 1 }, showSymbol: false },
        { name: 'ST↑', type: 'line', data: stUp,
          lineStyle: { color: '#4caf50', width: 2 }, showSymbol: false, connectNulls: false },
        { name: 'ST↓', type: 'line', data: stDown,
          lineStyle: { color: '#f44336', width: 2 }, showSymbol: false, connectNulls: false },
      ],
    }
  }, [data])

  return (
    <ReactECharts
      option={option}
      style={{ height: 560 }}
      opts={{ renderer: 'canvas' }}
    />
  )
}

export default KLineChart
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/technical/KLineChart.tsx
git commit -m "feat: KLineChart with candlestick, MA5/20/60, and SuperTrend"
```

---

## Task 12: TechnicalTab (wire up cards + chart)

**Files:**
- Modify: `frontend/src/components/technical/TechnicalTab.tsx`

- [ ] **Step 1: Replace placeholder with real TechnicalTab**

`frontend/src/components/technical/TechnicalTab.tsx`:
```tsx
import React from 'react'
import { Spin, Empty, Typography } from 'antd'
import type { AnalysisResponse } from '../../types/stock'
import AnalysisCards from './AnalysisCards'
import KLineChart from './KLineChart'

interface Props {
  data: AnalysisResponse | null
  loading: boolean
}

const TechnicalTab: React.FC<Props> = ({ data, loading }) => {
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" />
        <div style={{ color: '#8b949e', marginTop: 16 }}>
          正在加载数据并计算指标…（首次加载需下载历史数据，请稍候）
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <Empty
        description={<span style={{ color: '#8b949e' }}>请在顶部输入股票代码并点击分析</span>}
        style={{ marginTop: 80 }}
      />
    )
  }

  return (
    <div>
      <Typography.Title level={5} style={{ color: '#8b949e', marginBottom: 12 }}>
        {data.stock_code} · 最新 ¥{data.current_price.toFixed(2)}
      </Typography.Title>
      <AnalysisCards data={data} />
      <KLineChart data={data} />
    </div>
  )
}

export default TechnicalTab
```

- [ ] **Step 2: End-to-end test**

1. Start backend: `cd backend && python run.py`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173
4. Enter `600519`, click 分析
5. Verify: cards show current price, P20/P50/P80, max drawdown; K-line chart renders with MA and SuperTrend lines; time slider at bottom is draggable

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/technical/TechnicalTab.tsx
git commit -m "feat: TechnicalTab wires up AnalysisCards and KLineChart"
```

---

## Task 13: BacktestConfig form

**Files:**
- Create: `frontend/src/components/backtest/BacktestConfig.tsx`

- [ ] **Step 1: Implement BacktestConfig.tsx**

`frontend/src/components/backtest/BacktestConfig.tsx`:
```tsx
import React, { useState } from 'react'
import {
  Form, DatePicker, InputNumber, Button, Collapse, Row, Col, Spin,
} from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import type { BacktestRequest, StrategyParams } from '../../types/backtest'
import { DEFAULT_STRATEGY_PARAMS } from '../../types/backtest'

interface Props {
  stockCode: string
  onRun: (req: BacktestRequest) => void
  loading: boolean
}

const BacktestConfig: React.FC<Props> = ({ stockCode, onRun, loading }) => {
  const [form] = Form.useForm()

  const handleFinish = (values: any) => {
    const req: BacktestRequest = {
      stock_code: stockCode,
      start_date: values.start_date.format('YYYY-MM-DD'),
      end_date: values.end_date.format('YYYY-MM-DD'),
      initial_cash: values.initial_cash,
      strategy_params: {
        score_rising_days: values.score_rising_days,
        oversold_std_mult: values.oversold_std_mult,
        take_profit_pct: values.take_profit_pct / 100,
        take_profit_std_mult: values.take_profit_std_mult,
        stop_loss_pct: values.stop_loss_pct / 100,
        add_position_pct: values.add_position_pct / 100,
        half_position_ratio: values.half_position_ratio / 100,
      },
    }
    onRun(req)
  }

  const p = DEFAULT_STRATEGY_PARAMS

  return (
    <Form
      form={form}
      layout="inline"
      onFinish={handleFinish}
      initialValues={{
        start_date: dayjs('2023-01-01'),
        end_date: dayjs(),
        initial_cash: 100000,
        score_rising_days: p.score_rising_days,
        oversold_std_mult: p.oversold_std_mult,
        take_profit_pct: p.take_profit_pct * 100,
        take_profit_std_mult: p.take_profit_std_mult,
        stop_loss_pct: p.stop_loss_pct * 100,
        add_position_pct: p.add_position_pct * 100,
        half_position_ratio: p.half_position_ratio * 100,
      }}
      style={{ background: '#161b22', padding: 16, borderRadius: 8, border: '1px solid #30363d', marginBottom: 16 }}
    >
      <Form.Item label="开始日期" name="start_date">
        <DatePicker format="YYYY-MM-DD" />
      </Form.Item>
      <Form.Item label="结束日期" name="end_date">
        <DatePicker format="YYYY-MM-DD" />
      </Form.Item>
      <Form.Item label="初始资金 (元)" name="initial_cash">
        <InputNumber min={10000} step={10000} style={{ width: 130 }} />
      </Form.Item>

      <Collapse
        ghost
        style={{ width: '100%', marginTop: 8 }}
        items={[{
          key: '1',
          label: <span style={{ color: '#8b949e' }}>策略参数 ▾</span>,
          children: (
            <Row gutter={[16, 0]}>
              <Col>
                <Form.Item label="score连升天数" name="score_rising_days">
                  <InputNumber min={1} max={10} style={{ width: 80 }} />
                </Form.Item>
              </Col>
              <Col>
                <Form.Item label="超卖倍数 (σ)" name="oversold_std_mult">
                  <InputNumber min={0.5} max={5} step={0.5} style={{ width: 80 }} />
                </Form.Item>
              </Col>
              <Col>
                <Form.Item label="止盈 (%)" name="take_profit_pct">
                  <InputNumber min={1} max={100} style={{ width: 80 }} />
                </Form.Item>
              </Col>
              <Col>
                <Form.Item label="score止盈倍数" name="take_profit_std_mult">
                  <InputNumber min={0.5} max={5} step={0.5} style={{ width: 80 }} />
                </Form.Item>
              </Col>
              <Col>
                <Form.Item label="止损 (%)" name="stop_loss_pct">
                  <InputNumber min={1} max={50} style={{ width: 80 }} />
                </Form.Item>
              </Col>
              <Col>
                <Form.Item label="加仓触发 (%)" name="add_position_pct">
                  <InputNumber min={1} max={50} style={{ width: 80 }} />
                </Form.Item>
              </Col>
              <Col>
                <Form.Item label="初始仓位 (%)" name="half_position_ratio">
                  <InputNumber min={10} max={100} style={{ width: 80 }} />
                </Form.Item>
              </Col>
            </Row>
          ),
        }]}
      />

      <Form.Item style={{ marginTop: 8 }}>
        <Button
          type="primary"
          htmlType="submit"
          icon={loading ? <Spin size="small" /> : <PlayCircleOutlined />}
          disabled={loading}
          style={{ background: '#238636', borderColor: '#238636' }}
        >
          运行回测
        </Button>
      </Form.Item>
    </Form>
  )
}

export default BacktestConfig
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/backtest/BacktestConfig.tsx
git commit -m "feat: BacktestConfig form with collapsible strategy params"
```

---

## Task 14: BacktestChart component (K-line + score panel + buy/sell markers)

**Files:**
- Create: `frontend/src/components/backtest/BacktestChart.tsx`

- [ ] **Step 1: Implement BacktestChart.tsx**

`frontend/src/components/backtest/BacktestChart.tsx`:
```tsx
import React, { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { BacktestResponse } from '../../types/backtest'

interface Props {
  data: BacktestResponse
}

const BacktestChart: React.FC<Props> = ({ data }) => {
  const option = useMemo(() => {
    const {
      dates, open, high, low, close,
      ma5, ma20, ma60, supertrend, supertrend_direction,
      score, score_mean, score_std, trades,
    } = data

    const candleData = dates.map((_, i) => [open[i], close[i], low[i], high[i]])
    const stUp = supertrend.map((v, i) => (supertrend_direction[i] === 1 ? v : null))
    const stDown = supertrend.map((v, i) => (supertrend_direction[i] === -1 ? v : null))

    // Score ± 2σ bands
    const scorePlus2 = score_mean.map((m, i) =>
      m !== null && score_std[i] !== null ? m + 2 * score_std[i]! : null
    )
    const scoreMinus2 = score_mean.map((m, i) =>
      m !== null && score_std[i] !== null ? m - 2 * score_std[i]! : null
    )

    // Build buy/sell markPoint data for the K-line series
    const buyPoints = trades
      .filter(t => t.direction === '买入')
      .map(t => {
        const idx = dates.indexOf(t.date)
        if (idx === -1) return null
        return {
          coord: [t.date, (low[idx] ?? t.price) * 0.985],
          value: '买',
          itemStyle: { color: '#ef5350' },
          symbol: 'triangle',
          symbolSize: 14,
          symbolRotate: 0,
          label: { show: true, formatter: '▲', fontSize: 10, color: '#ef5350', position: 'bottom' },
        }
      })
      .filter(Boolean)

    const sellPoints = trades
      .filter(t => t.direction === '卖出')
      .map(t => {
        const idx = dates.indexOf(t.date)
        if (idx === -1) return null
        return {
          coord: [t.date, (high[idx] ?? t.price) * 1.015],
          value: '卖',
          itemStyle: { color: '#26a69a' },
          symbol: 'triangle',
          symbolSize: 14,
          symbolRotate: 180,
          label: { show: true, formatter: '▼', fontSize: 10, color: '#26a69a', position: 'top' },
        }
      })
      .filter(Boolean)

    return {
      backgroundColor: '#0d1117',
      animation: false,
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      legend: {
        data: ['K线', 'MA5', 'MA20', 'MA60', 'ST↑', 'ST↓', 'Score', 'Mean', '+2σ', '-2σ'],
        top: 8,
        textStyle: { color: '#8b949e' },
        inactiveColor: '#444',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross', crossStyle: { color: '#555' } },
        backgroundColor: 'rgba(22,27,34,0.95)',
        borderColor: '#30363d',
        textStyle: { color: '#e6edf3', fontSize: 12 },
        formatter: (params: any[]) => {
          if (!params.length) return ''
          const idx = params[0].dataIndex
          const d = dates[idx]
          let html = `<div style="font-weight:600;margin-bottom:4px">${d}</div>`
          html += `<div>开 ${open[idx]?.toFixed(2)}　高 ${high[idx]?.toFixed(2)}</div>`
          html += `<div>低 ${low[idx]?.toFixed(2)}　收 ${close[idx]?.toFixed(2)}</div>`
          params.forEach(p => {
            if (p.seriesName === 'K线') return
            const v = Array.isArray(p.value) ? p.value[1] : p.value
            if (v == null) return
            html += `<div style="color:${p.color}">${p.seriesName}: ${Number(v).toFixed(p.seriesName.includes('Score') || p.seriesName.includes('σ') || p.seriesName === 'Mean' ? 4 : 2)}</div>`
          })
          return html
        },
      },
      grid: [
        { left: '5%', right: '3%', top: 60, bottom: '42%' },
        { left: '5%', right: '3%', top: '62%', bottom: 80 },
      ],
      xAxis: [
        {
          type: 'category', data: dates, gridIndex: 0, boundaryGap: true,
          axisLabel: { show: false },
          axisLine: { lineStyle: { color: '#30363d' } },
        },
        {
          type: 'category', data: dates, gridIndex: 1, boundaryGap: true,
          axisLabel: {
            color: '#8b949e',
            formatter: (v: string) => v.slice(0, 7),
            interval: Math.floor(dates.length / 8),
          },
          axisLine: { lineStyle: { color: '#30363d' } },
        },
      ],
      yAxis: [
        {
          scale: true, gridIndex: 0,
          axisLabel: { color: '#8b949e', formatter: (v: number) => v.toFixed(0) },
          splitLine: { lineStyle: { color: '#161b22' } },
        },
        {
          scale: true, gridIndex: 1,
          axisLabel: { color: '#8b949e', formatter: (v: number) => v.toFixed(2) },
          splitLine: { lineStyle: { color: '#161b22' } },
        },
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
        {
          type: 'slider', xAxisIndex: [0, 1], show: true, bottom: 20,
          start: 0, end: 100,
          borderColor: '#30363d', fillerColor: 'rgba(35,134,54,0.15)',
          textStyle: { color: '#8b949e' },
          handleStyle: { color: '#238636' },
        },
      ],
      series: [
        {
          name: 'K线', type: 'candlestick', xAxisIndex: 0, yAxisIndex: 0,
          data: candleData,
          itemStyle: {
            color: '#ef5350', color0: '#26a69a',
            borderColor: '#ef5350', borderColor0: '#26a69a',
          },
          markPoint: {
            data: [...buyPoints, ...sellPoints],
            animation: false,
          },
        },
        { name: 'MA5', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma5,
          lineStyle: { color: '#ffffff', width: 1 }, showSymbol: false },
        { name: 'MA20', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma20,
          lineStyle: { color: '#ffd700', width: 1 }, showSymbol: false },
        { name: 'MA60', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma60,
          lineStyle: { color: '#1890ff', width: 1 }, showSymbol: false },
        { name: 'ST↑', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: stUp,
          lineStyle: { color: '#4caf50', width: 2 }, showSymbol: false, connectNulls: false },
        { name: 'ST↓', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: stDown,
          lineStyle: { color: '#f44336', width: 2 }, showSymbol: false, connectNulls: false },
        // Score panel
        { name: 'Score', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: score,
          lineStyle: { color: '#1890ff', width: 1.5 }, showSymbol: false },
        { name: 'Mean', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: score_mean,
          lineStyle: { color: '#fa8c16', width: 1, type: 'dashed' }, showSymbol: false },
        {
          name: '+2σ', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: scorePlus2,
          lineStyle: { color: '#555', width: 0.8, type: 'dashed' }, showSymbol: false,
          areaStyle: { color: 'rgba(200,200,200,0.08)', origin: 'auto' },
          stack: 'sigma_band',
        },
        { name: '-2σ', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: scoreMinus2,
          lineStyle: { color: '#555', width: 0.8, type: 'dashed' }, showSymbol: false },
      ],
    }
  }, [data])

  return (
    <ReactECharts
      option={option}
      style={{ height: 700 }}
      opts={{ renderer: 'canvas' }}
    />
  )
}

export default BacktestChart
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/backtest/BacktestChart.tsx
git commit -m "feat: BacktestChart with K-line, score panel, buy/sell markers"
```

---

## Task 15: BacktestSummary and TradeTable

**Files:**
- Create: `frontend/src/components/backtest/BacktestSummary.tsx`
- Create: `frontend/src/components/backtest/TradeTable.tsx`

- [ ] **Step 1: Implement BacktestSummary.tsx**

`frontend/src/components/backtest/BacktestSummary.tsx`:
```tsx
import React from 'react'
import { Row, Col, Card, Statistic } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons'
import type { BacktestSummary } from '../../types/backtest'

interface Props { summary: BacktestSummary }

const pct = (n: number) => `${(n * 100).toFixed(2)}%`
const cny = (n: number) => `¥${n.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`

const BacktestSummary: React.FC<Props> = ({ summary }) => {
  const { total_return, benchmark_return, excess_return, total_fees, initial_cash, final_assets } = summary
  const isPositive = (n: number) => n >= 0

  return (
    <Row gutter={[16, 16]} style={{ marginTop: 16, marginBottom: 16 }}>
      {[
        {
          title: '策略累计收益', value: pct(total_return),
          color: isPositive(total_return) ? '#ef5350' : '#26a69a',
          icon: isPositive(total_return) ? <ArrowUpOutlined /> : <ArrowDownOutlined />,
        },
        {
          title: '基准收益（买入持有）', value: pct(benchmark_return),
          color: isPositive(benchmark_return) ? '#ef5350' : '#26a69a',
          icon: isPositive(benchmark_return) ? <ArrowUpOutlined /> : <ArrowDownOutlined />,
        },
        {
          title: '超额收益', value: pct(excess_return),
          color: isPositive(excess_return) ? '#4caf50' : '#f44336',
          icon: isPositive(excess_return) ? <ArrowUpOutlined /> : <ArrowDownOutlined />,
        },
        {
          title: '累计手续费', value: cny(total_fees),
          color: '#fa8c16', icon: null,
        },
        {
          title: '期末总资产', value: cny(final_assets),
          color: '#e6edf3', icon: null,
        },
      ].map(item => (
        <Col xs={24} sm={12} md={8} lg={5} key={item.title}>
          <Card
            size="small"
            style={{ background: '#161b22', border: '1px solid #30363d' }}
          >
            <Statistic
              title={<span style={{ color: '#8b949e', fontSize: 12 }}>{item.title}</span>}
              value={item.value}
              prefix={item.icon}
              valueStyle={{ color: item.color, fontSize: 18 }}
            />
          </Card>
        </Col>
      ))}
    </Row>
  )
}

export default BacktestSummary
```

- [ ] **Step 2: Implement TradeTable.tsx**

`frontend/src/components/backtest/TradeTable.tsx`:
```tsx
import React from 'react'
import { Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { Trade } from '../../types/backtest'

interface Props { trades: Trade[] }

const fmt2 = (n: number | null) => n == null ? '—' : n.toFixed(2)
const fmtCny = (n: number) => `¥${n.toFixed(2)}`

const TradeTable: React.FC<Props> = ({ trades }) => {
  const columns: ColumnsType<Trade> = [
    { title: '日期', dataIndex: 'date', key: 'date', width: 110, fixed: 'left' },
    {
      title: '方向', dataIndex: 'direction', key: 'direction', width: 70,
      render: (v: string) => (
        <Tag color={v === '买入' ? 'red' : 'cyan'}>{v}</Tag>
      ),
    },
    { title: '原因', dataIndex: 'reason', key: 'reason', width: 150 },
    { title: '价格', dataIndex: 'price', key: 'price', width: 90, render: fmtCny },
    { title: '数量 (股)', dataIndex: 'shares', key: 'shares', width: 90, align: 'right' },
    { title: '成交金额', dataIndex: 'amount', key: 'amount', width: 110, render: fmtCny, align: 'right' },
    { title: '过户费', dataIndex: 'transfer_fee', key: 'transfer_fee', width: 90, render: fmtCny, align: 'right' },
    {
      title: '印花税', dataIndex: 'stamp_tax', key: 'stamp_tax', width: 90, align: 'right',
      render: (v: number | null) => v == null ? <span style={{ color: '#555' }}>—</span> : fmtCny(v),
    },
    { title: '佣金', dataIndex: 'commission', key: 'commission', width: 90, render: fmtCny, align: 'right' },
    { title: '总手续费', dataIndex: 'total_fee', key: 'total_fee', width: 90, render: fmtCny, align: 'right' },
    {
      title: '盈亏', dataIndex: 'pnl', key: 'pnl', width: 100, align: 'right',
      render: (v: number | null) => {
        if (v == null) return <span style={{ color: '#555' }}>—</span>
        return <span style={{ color: v >= 0 ? '#ef5350' : '#26a69a' }}>{fmtCny(v)}</span>
      },
    },
    { title: '剩余现金', dataIndex: 'remaining_cash', key: 'remaining_cash', width: 120, render: fmtCny, align: 'right' },
  ]

  return (
    <Table
      columns={columns}
      dataSource={trades.map((t, i) => ({ ...t, key: i }))}
      size="small"
      scroll={{ x: 1200 }}
      pagination={false}
      style={{ background: '#161b22' }}
      rowClassName={(_, idx) => idx % 2 === 0 ? 'row-even' : 'row-odd'}
      summary={() => (
        <Table.Summary.Row>
          <Table.Summary.Cell index={0} colSpan={9} align="right">
            <b style={{ color: '#8b949e' }}>合计手续费</b>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={1} align="right">
            <b style={{ color: '#fa8c16' }}>
              ¥{trades.reduce((s, t) => s + t.total_fee, 0).toFixed(2)}
            </b>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={2} align="right">
            <b style={{ color: '#ef5350' }}>
              ¥{trades.filter(t => t.pnl != null).reduce((s, t) => s + (t.pnl ?? 0), 0).toFixed(2)}
            </b>
          </Table.Summary.Cell>
          <Table.Summary.Cell index={3} />
        </Table.Summary.Row>
      )}
    />
  )
}

export default TradeTable
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/backtest/BacktestSummary.tsx \
        frontend/src/components/backtest/TradeTable.tsx
git commit -m "feat: BacktestSummary cards and TradeTable with fee breakdown"
```

---

## Task 16: BacktestTab (wire everything together)

**Files:**
- Modify: `frontend/src/components/backtest/BacktestTab.tsx`

- [ ] **Step 1: Replace placeholder with full BacktestTab**

`frontend/src/components/backtest/BacktestTab.tsx`:
```tsx
import React, { useState } from 'react'
import { message, Spin, Empty } from 'antd'
import type { BacktestRequest, BacktestResponse } from '../../types/backtest'
import { runBacktest } from '../../services/api'
import BacktestConfig from './BacktestConfig'
import BacktestChart from './BacktestChart'
import BacktestSummary from './BacktestSummary'
import TradeTable from './TradeTable'

interface Props {
  stockCode: string
}

const BacktestTab: React.FC<Props> = ({ stockCode }) => {
  const [result, setResult] = useState<BacktestResponse | null>(null)
  const [loading, setLoading] = useState(false)

  const handleRun = async (req: BacktestRequest) => {
    setLoading(true)
    try {
      const data = await runBacktest(req)
      setResult(data)
    } catch (err: any) {
      message.error(err?.response?.data?.detail || `回测失败: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <BacktestConfig stockCode={stockCode} onRun={handleRun} loading={loading} />

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ color: '#8b949e', marginTop: 16 }}>
            正在计算三因子分数并运行回测…（首次运行较慢，请耐心等待）
          </div>
        </div>
      )}

      {!loading && !result && (
        <Empty
          description={<span style={{ color: '#8b949e' }}>配置参数后点击「运行回测」</span>}
          style={{ marginTop: 60 }}
        />
      )}

      {!loading && result && (
        <>
          <BacktestSummary summary={result.summary} />
          <BacktestChart data={result} />
          <div style={{ marginTop: 24 }}>
            <div style={{ color: '#8b949e', marginBottom: 8, fontWeight: 600 }}>交易明细</div>
            <TradeTable trades={result.trades} />
          </div>
        </>
      )}
    </div>
  )
}

export default BacktestTab
```

- [ ] **Step 2: Full integration test**

1. Backend running: `cd backend && python run.py`
2. Frontend running: `cd frontend && npm run dev`
3. Enter `600519`, click 分析 → Technical tab loads
4. Switch to 回测 tab
5. Set start=2023-01-01, end=today, cash=100000, click 运行回测
6. Verify:
   - Loading spinner appears with message
   - Chart renders with K-line + score panel + buy▲/sell▼ markers
   - Both panels scroll together via bottom slider
   - Summary cards show returns and fees
   - Trade table shows all columns including stamp_tax=— for buys

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/backtest/BacktestTab.tsx
git commit -m "feat: BacktestTab wires config, chart, summary, and trade table"
```

---

## Task 17: Final polish and self-review

**Files:**
- Modify: `frontend/src/App.css` (table row colors)

- [ ] **Step 1: Add table row CSS**

Append to `frontend/src/App.css`:
```css
/* Ant Design table dark row alternating colors */
.ant-table-tbody > tr.row-even > td {
  background: #161b22 !important;
}
.ant-table-tbody > tr.row-odd > td {
  background: #0d1117 !important;
}
.ant-table-tbody > tr:hover > td {
  background: #21262d !important;
}
```

- [ ] **Step 2: Verify end-to-end with a second stock (ETF)**

```bash
# In browser: enter 510300 (沪深300ETF), click 分析
# Verify: data loads, chart renders correctly with red/green candles
# Switch to backtest, run with default params
# Verify: backtest completes, trades shown in table
```

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: final polish — table styles and ETF compatibility verified"
```

---

## Self-Review Checklist

| Spec Requirement | Covered In |
|---|---|
| 漂亮UI界面 | Task 9, 10: Ant Design dark theme |
| frontend/backend/data 分离 | Task 1, 7: directory structure |
| 输入股票代码触发分析 | Task 9, 12: Header + TechnicalTab |
| 自动下载CSV到data/ | Task 4: data_service._download() |
| 股价百分位 P20/50/80 | Task 5, 10: indicator_service + AnalysisCards |
| 历史最大回撤 + 起止时间+价格 | Task 5, 10: indicator_service + AnalysisCards |
| K线图 红涨绿跌 | Task 11: KLineChart itemStyle |
| MA5/20/60均线 | Task 11: KLineChart series |
| SuperTrend(10,3) | Task 2, 11: calc_supertrend + KLineChart |
| 时间轴可拖动 | Task 11, 14: ECharts dataZoom |
| 回测 three_factors 策略 | Task 6: backtest_service |
| 回测K线+score图+买卖标记 | Task 14: BacktestChart markPoint |
| score图时间联动 | Task 14: axisPointer link + shared dataZoom |
| 回测参数完整可配 | Task 13: BacktestConfig form |
| 交易明细含手续费明细 | Task 6, 15: fee breakdown in trades + TradeTable |
| 基准对比 | Task 6, 15: buy-and-hold benchmark in summary |
