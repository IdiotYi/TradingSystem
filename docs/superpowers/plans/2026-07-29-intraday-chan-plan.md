# Intraday Chan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend Chan analysis from daily bars to cached 30-minute and 5-minute bars, using BaoStock for A shares and AKShare fallback with explicit coverage reporting.

**Architecture:** Add a minute-data service responsible for provider selection, normalization, two-year caching, and atomic refresh. Extend the existing Chan service/API with a period parameter while leaving the core containment/fractal/pen algorithm unchanged.

**Tech Stack:** Python 3.10+, FastAPI, pandas, BaoStock, AKShare, pytest, React 18, TypeScript, Ant Design 5, ECharts.

## Global Constraints

- Execute `2026-07-29-fund-investment-plan.md` first so the existing frontend TypeScript baseline is fixed.
- Support periods `daily`, `30`, and `5` only.
- Cache minute data as `data/Minute_<code>_<period>.csv`.
- Keep a rolling two-year minute-data window.
- Use BaoStock first for A shares and AKShare as fallback.
- For ETF minute data, try AKShare and report actual coverage; do not promise two years.
- Use forward-adjusted prices and record the provider and adjustment mode in the cache.
- Never silently truncate an oversized Chan response; return an actionable 400 error.
- Keep the existing Chan core algorithm behavior unchanged.
- Preserve the unrelated `.claude/settings.local.json` worktree change.

---

## File Map

### Backend

- Modify `backend/requirements.txt`: add BaoStock.
- Create `backend/app/services/minute_data_service.py`: provider adapters, normalization, cache, refresh.
- Create `backend/tests/test_minute_data_service.py`: mapping, fallback, validation, cache tests.
- Modify `backend/app/services/chan_service.py`: period-aware data loading and response metadata.
- Modify `backend/app/api/chan.py`: period validation and minute refresh route.
- Create `backend/tests/test_chan_service.py`: daily regression, minute timestamps, size limit.
- Modify `backend/tests/test_chan.py`: only if a reusable regression fixture belongs with core tests.

### Frontend

- Modify `frontend/src/types/chan.ts`: period and coverage fields.
- Modify `frontend/src/services/api.ts`: minute refresh function.
- Modify `frontend/src/components/chan/ChanTab.tsx`: period selector, defaults, refresh, coverage warning.
- Modify `frontend/src/components/chan/ChanChart.tsx`: timestamp-aware axis labels/tooltips.
- Modify `README.md`: data-source and support limits.

---

### Task 1: Add BaoStock and Minute-Data Normalization

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/app/services/minute_data_service.py`
- Create: `backend/tests/test_minute_data_service.py`

**Interfaces:**
- Consumes: `app.config.DATA_DIR`, existing stock-code normalization conventions.
- Produces:
  - `MinutePeriod = Literal["5", "30"]`
  - `normalize_minute_code(stock_code: str) -> str`
  - `to_baostock_code(code: str) -> str`
  - `normalize_baostock_minutes(rows: list[list[str]], code: str, period: str) -> pd.DataFrame`
  - `normalize_akshare_minutes(df: pd.DataFrame, code: str, period: str, source: str) -> pd.DataFrame`

- [ ] **Step 1: Add the dependency**

Append:

```text
baostock>=0.8.9
```

Install through the existing requirements file:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pip install -r requirements.txt
```

- [ ] **Step 2: Write failing code-mapping and normalization tests**

```python
import pandas as pd
import pytest

from app.services.minute_data_service import (
    normalize_baostock_minutes,
    to_baostock_code,
)


def test_to_baostock_code_maps_shenzhen_and_shanghai():
    assert to_baostock_code("600519") == "sh.600519"
    assert to_baostock_code("000001") == "sz.000001"
    with pytest.raises(ValueError, match="暂不支持"):
        to_baostock_code("430047")


def test_normalize_baostock_rows_uses_full_timestamp():
    rows = [[
        "2026-07-29", "20260729150000000", "sh.600519",
        "1319.8", "1325", "1319", "1321", "148791",
        "196561700", "2",
    ]]
    result = normalize_baostock_minutes(rows, "600519", "5")
    assert result.iloc[0].to_dict() == {
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
    }
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_minute_data_service.py -q
```

Expected: FAIL because the service does not exist.

- [ ] **Step 4: Implement standard schema and validation**

Define:

```python
MINUTE_COLUMNS = [
    "时间", "股票代码", "周期",
    "开盘", "最高", "最低", "收盘",
    "成交量", "成交额", "复权", "数据源",
]
VALID_PERIODS = {"5", "30"}
```

Normalization must:

1. parse BaoStock `time` as `%Y%m%d%H%M%S%f`;
2. convert all OHLC and volume fields to numeric;
3. reject non-finite OHLC or `high < low`;
4. sort and deduplicate by `时间`;
5. return exactly `MINUTE_COLUMNS`.

AKShare normalization must accept either:

- Sina columns `day/open/high/low/close/volume/amount`; or
- Eastmoney Chinese minute columns.

- [ ] **Step 5: Verify normalization tests**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_minute_data_service.py -q
```

Expected: PASS for mapping and normalization.

- [ ] **Step 6: Commit**

```powershell
Set-Location C:\Projects\TradingSystem
git add backend/requirements.txt backend/app/services/minute_data_service.py backend/tests/test_minute_data_service.py
git commit -m "feat: normalize minute market data" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 2: Implement Provider Fallback and Two-Year Atomic Cache

**Files:**
- Modify: `backend/app/services/minute_data_service.py`
- Modify: `backend/tests/test_minute_data_service.py`

**Interfaces:**
- Consumes: Task 1 normalizers.
- Produces:
  - `is_etf_code(code: str) -> bool`
  - `download_minute_data(stock_code: str, period: MinutePeriod) -> tuple[pd.DataFrame, dict]`
  - `load_minute_data(stock_code: str, period: MinutePeriod) -> tuple[pd.DataFrame, dict]`
  - `refresh_minute_data(stock_code: str, period: MinutePeriod) -> dict`

- [ ] **Step 1: Write failing fallback tests**

```python
def test_a_share_falls_back_to_akshare(monkeypatch):
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
    frame, metadata = download_minute_data("600519", "5")
    assert metadata["data_source"] == "akshare_sina"
    assert len(frame) == 1


def test_etf_skips_baostock(monkeypatch):
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
    frame, metadata = download_minute_data("510300", "30")
    assert len(frame) == 1
    assert metadata["data_source"] == "akshare_sina"
```

- [ ] **Step 2: Write failing cache tests**

Add deterministic cache tests:

```python
from datetime import date


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

    result = refresh_minute_data("600519", "5")
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
        refresh_minute_data("600519", "30")
    assert target.read_text(encoding="utf-8") == "existing-cache"
```

Add `_today() -> date` as a tiny internal clock seam so the two-year boundary is deterministic in tests.

- [ ] **Step 3: Run tests to verify failure**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_minute_data_service.py -q
```

Expected: FAIL because provider and cache functions are absent.

- [ ] **Step 4: Implement the BaoStock adapter**

Use one login/logout scope:

```python
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
        rows = []
        while rs.next():
            rows.append(rs.get_row_data())
        return normalize_baostock_minutes(rows, code, period)
    finally:
        bs.logout()
```

An empty result is a provider failure, not a successful cache.

- [ ] **Step 5: Implement AKShare fallback**

Try Eastmoney first:

```python
ak.stock_zh_a_hist_min_em(
    symbol=code,
    start_date=f"{start_date} 09:30:00",
    end_date=f"{end_date} 15:00:00",
    period=period,
    adjust="qfq",
)
```

Then try Sina:

```python
ak.stock_zh_a_minute(
    symbol=_exchange_prefix(code),
    period=period,
    adjust="qfq",
)
```

Collect provider error messages and raise one `ValueError` only after all applicable sources fail.

- [ ] **Step 6: Implement cache and coverage metadata**

Use:

```python
def _minute_cache_path(code: str, period: MinutePeriod) -> Path:
    return DATA_DIR / f"Minute_{code}_{period}.csv"
```

The two-year request window is `[today - DateOffset(years=2), today]`. After normalization:

```python
coverage_from = frame["时间"].iloc[0]
coverage_to = frame["时间"].iloc[-1]
target_coverage_met = (
    pd.Timestamp(coverage_from) <= pd.Timestamp(start_date) + pd.Timedelta(days=7)
)
```

Allow partial AKShare ETF caches but include `target_coverage_met=False`. For A shares, partial fallback data is usable but must also report false.

Write through a `.tmp` sibling and `Path.replace`.

- [ ] **Step 7: Run all minute service tests**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_minute_data_service.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
Set-Location C:\Projects\TradingSystem
git add backend/app/services/minute_data_service.py backend/tests/test_minute_data_service.py
git commit -m "feat: cache minute data with fallback" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 3: Extend Chan Service and API for Periods

**Files:**
- Modify: `backend/app/services/chan_service.py`
- Modify: `backend/app/api/chan.py`
- Create: `backend/tests/test_chan_service.py`

**Interfaces:**
- Consumes: `load_stock_data`, Task 2 `load_minute_data` and `refresh_minute_data`.
- Produces:
  - `analyze_chan(stock_code, start_date, end_date, period="daily") -> dict`
  - `POST /api/chan/analyze` with `period`
  - `POST /api/chan/refresh`

- [ ] **Step 1: Write a failing daily regression test**

Use a deterministic fixture and monkeypatch the loader:

```python
import pandas as pd
import pytest

from app.core.chan import Bar, merge_kbars, detect_fractals, detect_pens
from app.services.chan_service import analyze_chan


def make_chan_frame(count: int, with_time: bool) -> pd.DataFrame:
    wave = [10, 12, 14, 13, 11, 9, 8, 10, 13, 15]
    close = [float(wave[i % len(wave)]) for i in range(count)]
    if with_time:
        labels = pd.date_range(
            "2026-07-01 09:30:00", periods=count, freq="5min"
        ).strftime("%Y-%m-%d %H:%M:%S")
        time_column = "时间"
    else:
        labels = pd.date_range(
            "2023-01-01", periods=count, freq="D"
        ).strftime("%Y-%m-%d")
        time_column = "日期"
    return pd.DataFrame({
        time_column: labels,
        "开盘": close,
        "最高": [value + 1 for value in close],
        "最低": [value - 1 for value in close],
        "收盘": close,
        "成交量": [1000.0] * count,
    })


def test_daily_period_preserves_existing_response_shape(monkeypatch):
    frame = make_chan_frame(40, with_time=False)
    bars = [
        Bar(
            idx=i,
            date=row["日期"],
            high=float(row["最高"]),
            low=float(row["最低"]),
        )
        for i, row in frame.iterrows()
    ]
    merged = merge_kbars(bars)
    expected_pens = detect_pens(
        merged, detect_fractals(merged), raw_bars=bars
    )
    expected = [
        (
            pen.start_src_idx, pen.end_src_idx,
            pen.start_price, pen.end_price, pen.direction,
        )
        for pen in expected_pens
    ]
    monkeypatch.setattr(
        "app.services.chan_service.load_stock_data",
        lambda code: frame,
    )
    result = analyze_chan(
        "600519", "2023-01-01", "2023-12-31", period="daily"
    )
    assert result["period"] == "daily"
    assert result["dates"] == frame["日期"].tolist()
    assert result["data_source"] == "stock_daily_cache"
    actual = [
        (
            pen["start_idx"], pen["end_idx"],
            pen["start_price"], pen["end_price"], pen["direction"],
        )
        for pen in result["pens"]
    ]
    assert actual == expected
```

- [ ] **Step 2: Write failing minute timestamp and limit tests**

```python
def test_minute_period_uses_timestamp_column(monkeypatch):
    frame = make_chan_frame(40, with_time=True)
    metadata = {
        "coverage_from": frame["时间"].iloc[0],
        "coverage_to": frame["时间"].iloc[-1],
        "data_source": "baostock",
        "target_coverage_met": True,
    }
    monkeypatch.setattr(
        "app.services.chan_service.load_minute_data",
        lambda code, period: (frame, metadata),
    )
    result = analyze_chan(
        "600519",
        "2026-07-01 09:30:00",
        "2026-07-29 15:00:00",
        period="5",
    )
    assert " " in result["dates"][0]
    assert result["period"] == "5"


def test_oversized_response_requires_smaller_range(monkeypatch):
    frame = make_chan_frame(20_001, with_time=True)
    metadata = {
        "coverage_from": frame["时间"].iloc[0],
        "coverage_to": frame["时间"].iloc[-1],
        "data_source": "baostock",
        "target_coverage_met": True,
    }
    monkeypatch.setattr(
        "app.services.chan_service.load_minute_data",
        lambda code, period: (frame, metadata),
    )
    with pytest.raises(ValueError, match="缩小日期范围"):
        analyze_chan(
            "600519",
            frame["时间"].iloc[0],
            frame["时间"].iloc[-1],
            period="5",
        )
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_chan_service.py -q
```

Expected: FAIL because the current service has no period support.

- [ ] **Step 4: Refactor period-aware data loading**

Add:

```python
VALID_CHAN_PERIODS = {"daily", "30", "5"}
MAX_CHAN_BARS = 20_000


def _load_chan_frame(stock_code: str, period: str) -> tuple[pd.DataFrame, dict]:
    if period == "daily":
        frame = load_stock_data(stock_code).rename(columns={"日期": "时间"})
        return frame, {
            "coverage_from": frame["时间"].iloc[0],
            "coverage_to": frame["时间"].iloc[-1],
            "data_source": "stock_daily_cache",
            "target_coverage_met": True,
        }
    return load_minute_data(stock_code, period)
```

Filter with parsed pandas timestamps rather than lexicographic strings. After filtering, reject fewer than 10 rows and more than `MAX_CHAN_BARS`.

Return:

```python
{
    "success": True,
    "stock_code": stock_code,
    "period": period,
    "coverage_from": metadata["coverage_from"],
    "coverage_to": metadata["coverage_to"],
    "response_from": dates_list[0],
    "response_to": dates_list[-1],
    "data_source": metadata["data_source"],
    "target_coverage_met": metadata["target_coverage_met"],
    "dates": dates_list,
    "open": [round(float(v), 4) for v in df["开盘"]],
    "close": [round(float(v), 4) for v in df["收盘"]],
    "high": [round(float(v), 4) for v in df["最高"]],
    "low": [round(float(v), 4) for v in df["最低"]],
    "pens": pen_points,
}
```

- [ ] **Step 5: Extend API models and add refresh**

```python
class ChanRequest(BaseModel):
    stock_code: str
    period: Literal["daily", "30", "5"] = "daily"
    start_date: str = "2023-01-01"
    end_date: Optional[str] = None


class ChanRefreshRequest(BaseModel):
    stock_code: str
    period: Literal["30", "5"]
```

Add:

```python
@router.post("/refresh")
async def refresh(req: ChanRefreshRequest):
    try:
        return refresh_minute_data(req.stock_code, req.period)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
```

- [ ] **Step 6: Run Chan service and core tests**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_chan_service.py tests/test_chan.py -q
```

Expected: PASS, including exact daily pen regression.

- [ ] **Step 7: Commit**

```powershell
Set-Location C:\Projects\TradingSystem
git add backend/app/services/chan_service.py backend/app/api/chan.py backend/tests/test_chan_service.py
git commit -m "feat: add intraday chan API periods" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 4: Extend Frontend Chan Contracts and Controls

**Files:**
- Modify: `frontend/src/types/chan.ts`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/components/chan/ChanTab.tsx`

**Interfaces:**
- Consumes: Task 3 request and response fields.
- Produces:
  - `ChanPeriod = 'daily' | '30' | '5'`
  - `refreshChanData(stockCode, period)`
  - period-aware Chan form and result metadata.

- [ ] **Step 1: Extend types**

```ts
export type ChanPeriod = 'daily' | '30' | '5'

export interface ChanRequest {
  stock_code: string
  period: ChanPeriod
  start_date: string
  end_date?: string
}

export interface ChanResponse {
  success: boolean
  stock_code: string
  period: ChanPeriod
  coverage_from: string
  coverage_to: string
  response_from: string
  response_to: string
  data_source: string
  target_coverage_met: boolean
  dates: string[]
  open: number[]
  close: number[]
  high: number[]
  low: number[]
  pens: ChanPen[]
}
```

- [ ] **Step 2: Add minute refresh client**

```ts
export interface ChanRefreshResponse {
  stock_code: string
  period: Exclude<ChanPeriod, 'daily'>
  rows: number
  coverage_from: string
  coverage_to: string
  data_source: string
  target_coverage_met: boolean
}

export async function refreshChanData(
  stockCode: string,
  period: Exclude<ChanPeriod, 'daily'>,
): Promise<ChanRefreshResponse> {
  const { data } = await client.post<ChanRefreshResponse>(
    '/chan/refresh',
    { stock_code: stockCode, period },
  )
  return data
}
```

- [ ] **Step 3: Add period state and defaults**

Use:

```tsx
const [period, setPeriod] = useState<ChanPeriod>('daily')

const defaultRange = (value: ChanPeriod): [Dayjs, Dayjs] => {
  const end = dayjs()
  if (value === '5') return [end.subtract(3, 'month'), end]
  if (value === '30') return [end.subtract(1, 'year'), end]
  return [dayjs('2023-01-01'), end]
}
```

Add an Ant Design `Select` with labels `日线`, `30分钟`, `5分钟`. On change, update the form range and run analysis for the selected period.

- [ ] **Step 4: Add explicit minute refresh behavior**

For daily, keep the existing top Header refresh behavior. In ChanTab, show a “刷新分钟数据” button only for `5` and `30`; call `refreshChanData`, show coverage in the success message, then rerun analysis.

Do not silently auto-refresh on every date-range change.

- [ ] **Step 5: Render metadata and partial-coverage warning**

Show:

```tsx
<Alert
  type="warning"
  showIcon
  message={`当前数据仅覆盖 ${result.coverage_from} ~ ${result.coverage_to}`}
/>
```

only when `period !== 'daily' && !result.target_coverage_met`.

The metadata line includes period, provider, actual coverage, response points, and pen count.

- [ ] **Step 6: Verify production build**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\frontend
npm run build
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
Set-Location C:\Projects\TradingSystem
git add frontend/src/types/chan.ts frontend/src/services/api.ts frontend/src/components/chan/ChanTab.tsx
git commit -m "feat: add chan period controls" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 5: Make the Chan Chart Timestamp-Aware

**Files:**
- Modify: `frontend/src/components/chan/ChanChart.tsx`

**Interfaces:**
- Consumes: `ChanResponse.period` and full timestamp `dates`.
- Produces: readable daily and intraday axes/tooltips without changing pen coordinates.

- [ ] **Step 1: Add period-aware date formatting helpers**

Inside the component:

```tsx
const formatAxisLabel = (value: string) => {
  if (data.period === 'daily') return value.slice(0, 7)
  return value.slice(5, 16)
}

const formatTooltipDate = (value: string) =>
  data.period === 'daily' ? value.slice(0, 10) : value.slice(0, 16)
```

- [ ] **Step 2: Apply formatting consistently**

Use `formatAxisLabel` in `xAxis.axisLabel.formatter`. Use `formatTooltipDate` for candlestick and endpoint tooltips.

Keep line coordinates keyed by the original full `start_date` and `end_date`; do not format values before passing them to ECharts.

- [ ] **Step 3: Prevent zero axis intervals**

Replace:

```tsx
interval: Math.floor(dates.length / 8),
```

with:

```tsx
interval: Math.max(0, Math.floor(dates.length / 8) - 1),
```

- [ ] **Step 4: Verify production build**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\frontend
npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
Set-Location C:\Projects\TradingSystem
git add frontend/src/components/chan/ChanChart.tsx
git commit -m "feat: render intraday chan timestamps" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 6: Document and Verify Intraday Chan End-to-End

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: all previous intraday tasks.
- Produces: documented and verified multi-period Chan workflow.

- [ ] **Step 1: Update README**

Document:

- daily, 30-minute, and 5-minute Chan periods;
- BaoStock primary source for A shares;
- AKShare fallback and ETF best-effort support;
- two-year minute cache naming;
- 5-minute default three-month view and 30-minute default one-year view;
- partial-coverage warning and no guaranteed third-party SLA.

- [ ] **Step 2: Run the complete backend suite**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest -q
```

Expected: all tests PASS.

- [ ] **Step 3: Run the frontend production build**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\frontend
npm run build
```

Expected: PASS.

- [ ] **Step 4: Exercise real A-share minute data**

Start the backend and run:

```powershell
$refresh = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/chan/refresh `
  -ContentType 'application/json' `
  -Body '{"stock_code":"600519","period":"5"}'

$analysis = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/chan/analyze `
  -ContentType 'application/json' `
  -Body '{"stock_code":"600519","period":"5","start_date":"2026-04-01 09:30:00","end_date":"2026-07-29 15:00:00"}'
```

Verify:

- `data/Minute_600519_5.csv` exists;
- provider is `baostock` when available;
- timestamps include time;
- `dates`, OHLC arrays, and pen indices align;
- coverage metadata matches the cache;
- a deliberately oversized range returns 400 with “缩小日期范围”.

- [ ] **Step 5: Exercise ETF fallback**

Use one known ETF code from the existing application. Verify either:

- data renders with the actual coverage warning; or
- the API returns a clear unsupported-source message.

An empty successful chart is a failure.

- [ ] **Step 6: Commit**

```powershell
Set-Location C:\Projects\TradingSystem
git add README.md
git commit -m "docs: describe intraday chan data support" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```
