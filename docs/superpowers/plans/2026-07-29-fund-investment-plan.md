# Fund Investment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a context-aware “基金定投” workflow that downloads and caches full fund NAV history, models weekly investments with dividend reinvestment and share splits, and presents summary, chart, and event details.

**Architecture:** Add fund-specific API, service, data, and pure backtest-core modules without routing fund codes through stock services. The React shell switches Header behavior by active Tab, while a dedicated FundInvestmentTab owns fund metadata and backtest results.

**Tech Stack:** Python 3.10+, FastAPI, pandas, AKShare, pytest, React 18, TypeScript, Ant Design 5, ECharts.

## Global Constraints

- Support only off-exchange public funds with daily unit NAV; reject money funds and exchange-traded ETFs.
- Cache normalized data as `data/Fund_<six-digit-code>.csv`.
- Refresh full history and atomically replace the cache only after validation.
- Weekly target days are Monday through Friday; missing target dates move backward within the same natural week only.
- Default investment is CNY 1,000 and remains editable.
- Use fractional shares and ignore subscription/redemption costs.
- Process same-day events in this order: split, cash-dividend reinvestment, scheduled investment.
- Do not add a frontend test runner; use the existing TypeScript production build.
- Preserve the unrelated `.claude/settings.local.json` worktree change.
- Complete this plan before the intraday Chan plan so the shared frontend build baseline is clean.

---

## File Map

### Backend

- Create `backend/app/core/fund_investment.py`: pure weekly schedule and fund-share simulation.
- Create `backend/app/services/fund_data_service.py`: AKShare adapters, normalization, validation, atomic cache writes.
- Create `backend/app/services/fund_investment_service.py`: load data and serialize analysis/backtest responses.
- Create `backend/app/api/fund.py`: Pydantic requests and `/analysis`, `/refresh`, `/backtest` routes.
- Modify `backend/app/main.py`: register the fund router.
- Create `backend/tests/test_fund_data_service.py`: data normalization and cache-safety tests.
- Create `backend/tests/test_fund_investment.py`: schedule, dividend, split, and result tests.
- Create `backend/tests/test_fund_api.py`: route validation and service-error mapping.

### Frontend

- Create `frontend/src/types/fund.ts`: fund request/response contracts.
- Modify `frontend/src/services/api.ts`: fund API client functions.
- Create `frontend/src/components/fund/FundInvestmentTab.tsx`: fund workflow state and orchestration.
- Create `frontend/src/components/fund/FundInvestmentConfig.tsx`: weekly strategy form.
- Create `frontend/src/components/fund/FundInvestmentSummary.tsx`: metric cards.
- Create `frontend/src/components/fund/FundInvestmentChart.tsx`: contribution/value chart.
- Create `frontend/src/components/fund/FundEventTable.tsx`: investment/dividend/split detail table.
- Modify `frontend/src/components/layout/Header.tsx`: stock/fund mode and delegated refresh action.
- Modify `frontend/src/App.tsx`: separate stock/fund state and context-aware Header routing.
- Modify `frontend/src/App.css`: small fund metadata/warning styles only if component-level styles are insufficient.
- Modify `frontend/src/components/backtest/BacktestConfig.tsx`: repair existing `StrategyParams` construction.
- Modify `frontend/src/utils/wma.ts`: add explicit local numeric annotations required by strict TypeScript.
- Modify `README.md`: document fund support and limits.

---

### Task 1: Restore the Existing Frontend Build Baseline

**Files:**
- Modify: `frontend/src/components/backtest/BacktestConfig.tsx:40-54`
- Modify: `frontend/src/utils/wma.ts:23,62`

**Interfaces:**
- Consumes: existing `StrategyParams` and `DEFAULT_STRATEGY_PARAMS`.
- Produces: a clean `npm run build` baseline before fund UI changes.

- [ ] **Step 1: Reproduce the current failures**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\frontend
npm run build
```

Expected: FAIL because the three-factor object omits `recent_high_window`, and both `cur` locals in `wma.ts` are inferred as implicit `any`.

- [ ] **Step 2: Make strategy parameter construction total**

In the three-factor branch in `BacktestConfig.tsx`, include the required field:

```tsx
recent_high_window: p.recent_high_window,
```

Do not use another cast to hide the missing field.

- [ ] **Step 3: Add explicit numeric annotations in WMA utilities**

Change both recursive locals:

```ts
const cur: number = prev == null ? blend : 0.5 * blend + 0.5 * prev
```

and:

```ts
const cur: number = prev == null ? c : alpha * c + (1 - alpha) * prev
```

- [ ] **Step 4: Verify the baseline build**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\frontend
npm run build
```

Expected: PASS and create `frontend/dist`.

- [ ] **Step 5: Commit**

```powershell
Set-Location C:\Projects\TradingSystem
git add frontend/src/components/backtest/BacktestConfig.tsx frontend/src/utils/wma.ts
git commit -m "fix: restore frontend type safety" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 2: Normalize and Cache Fund History

**Files:**
- Create: `backend/app/services/fund_data_service.py`
- Create: `backend/tests/test_fund_data_service.py`

**Interfaces:**
- Consumes: `app.config.DATA_DIR`, AKShare `fund_name_em()` and `fund_open_fund_info_em()`.
- Produces:
  - `FundNotFoundError(ValueError)`
  - `normalize_fund_code(fund_code: str) -> str`
  - `normalize_fund_history(nav_df, dividend_df, split_df, fund_code, fund_name, fund_type) -> pd.DataFrame`
  - `load_fund_data(fund_code: str) -> pd.DataFrame`
  - `refresh_fund_data(fund_code: str) -> dict`

- [ ] **Step 1: Write failing normalization tests**

Create `backend/tests/test_fund_data_service.py` with representative upstream frames:

```python
import pandas as pd
import pytest

from app.services.fund_data_service import (
    normalize_fund_code,
    normalize_fund_history,
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_fund_data_service.py -q
```

Expected: FAIL because `fund_data_service` does not exist.

- [ ] **Step 3: Implement code validation and event parsing**

Create focused helpers:

```python
FUND_COLUMNS = [
    "日期", "基金代码", "基金名称", "基金类型",
    "单位净值", "日增长率", "每份分红",
    "拆分类型", "拆分折算比例",
]


def normalize_fund_code(fund_code: str) -> str:
    code = fund_code.strip()
    if len(code) != 6 or not code.isdigit():
        raise ValueError("基金代码必须为6位数字")
    return code


def _parse_dividend_per_share(value: object) -> float:
    # Accept strings such as "每10份派现金0.1000元".
    match = re.search(r"每10份派现金([0-9.]+)元", str(value))
    if not match:
        raise ValueError(f"无法解析基金分红: {value}")
    return float(match.group(1)) / 10


def _parse_split_ratio(value: object) -> float:
    match = re.fullmatch(r"\s*([0-9.]+)\s*:\s*([0-9.]+)\s*", str(value))
    if not match or float(match.group(1)) == 0:
        raise ValueError(f"无法解析基金拆分比例: {value}")
    return float(match.group(2)) / float(match.group(1))
```

`normalize_fund_history` must:

1. rename NAV columns to the standard schema;
2. normalize all dates to `YYYY-MM-DD`;
3. left-join dividends by `除息日`;
4. left-join splits by `拆分折算日`;
5. fill no-event values with `0.0`, empty string, and `1.0`;
6. reject duplicate dates, non-finite NAV, and NAV `<= 0`;
7. sort ascending and return exactly `FUND_COLUMNS`.

- [ ] **Step 4: Run normalization tests**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_fund_data_service.py -q
```

Expected: PASS for code and event normalization tests.

- [ ] **Step 5: Write failing cache and fund-type tests**

Add tests using `monkeypatch` and `tmp_path`:

```python
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
```

- [ ] **Step 6: Implement AKShare adapters and atomic replacement**

Use these internal boundaries:

```python
class FundNotFoundError(ValueError):
    pass


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


def _atomic_write_csv(df: pd.DataFrame, target: Path) -> None:
    temp = target.with_suffix(target.suffix + ".tmp")
    try:
        df.to_csv(temp, index=False, encoding="utf-8-sig")
        pd.read_csv(temp, encoding="utf-8-sig")
        temp.replace(target)
    finally:
        if temp.exists():
            temp.unlink()
```

Reject fund types containing `货币`, `ETF`, or other explicit exchange-traded classification before downloading history. If `fund_name_em()` has no code match, raise `FundNotFoundError(f"基金代码不存在: {code}")`.

- [ ] **Step 7: Run all fund-data tests**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_fund_data_service.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
Set-Location C:\Projects\TradingSystem
git add backend/app/services/fund_data_service.py backend/tests/test_fund_data_service.py
git commit -m "feat: cache normalized fund history" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 3: Implement the Weekly Fund Investment Engine

**Files:**
- Create: `backend/app/core/fund_investment.py`
- Create: `backend/tests/test_fund_investment.py`

**Interfaces:**
- Consumes: normalized fund DataFrame from Task 2.
- Produces:
  - `select_weekly_investment_dates(df: pd.DataFrame, start_date: str, weekday: int) -> list[dict]`
  - `run_weekly_investment(df: pd.DataFrame, start_date: str, weekday: int, amount: float) -> dict`

- [ ] **Step 1: Write failing date-selection tests**

```python
import pandas as pd
import pytest

from app.core.fund_investment import (
    run_weekly_investment,
    select_weekly_investment_dates,
)


def make_fund_df(rows):
    frame = pd.DataFrame(rows)
    frame["基金代码"] = "000001"
    frame["基金名称"] = "示例基金"
    frame["基金类型"] = "混合型"
    frame["日增长率"] = 0.0
    frame["每份分红"] = frame.get("每份分红", 0.0)
    frame["拆分类型"] = frame.get("拆分类型", "")
    frame["拆分折算比例"] = frame.get("拆分折算比例", 1.0)
    return frame


def test_missing_friday_moves_to_thursday_in_same_week():
    df = make_fund_df([
        {"日期": "2024-01-08", "单位净值": 1.0},
        {"日期": "2024-01-11", "单位净值": 1.1},
        {"日期": "2024-01-15", "单位净值": 1.2},
    ])
    events = select_weekly_investment_dates(df, "2024-01-01", weekday=5)
    assert events[0] == {
        "scheduled_date": "2024-01-12",
        "execution_date": "2024-01-11",
        "advanced": True,
    }


def test_missing_monday_does_not_cross_into_previous_week():
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 1.0},
        {"日期": "2024-01-09", "单位净值": 1.1},
    ])
    events = select_weekly_investment_dates(df, "2024-01-08", weekday=1)
    assert events == []
```

- [ ] **Step 2: Run selection tests to verify failure**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_fund_investment.py -q
```

Expected: FAIL because the core module does not exist.

- [ ] **Step 3: Implement natural-week scheduling**

Implement with ISO weeks and explicit bounds:

```python
def select_weekly_investment_dates(
    df: pd.DataFrame,
    start_date: str,
    weekday: int,
) -> list[dict]:
    if weekday not in range(1, 6):
        raise ValueError("weekday 必须为 1 到 5")

    start = pd.Timestamp(start_date).normalize()
    dates = pd.to_datetime(df["日期"]).sort_values()
    result = []

    for (iso_year, iso_week), week_dates in dates.groupby(
        [dates.dt.isocalendar().year, dates.dt.isocalendar().week]
    ):
        monday = pd.Timestamp.fromisocalendar(int(iso_year), int(iso_week), 1)
        target = monday + pd.Timedelta(days=weekday - 1)
        eligible = week_dates[(week_dates <= target) & (week_dates >= start)]
        if eligible.empty:
            continue
        execution = eligible.max()
        result.append({
            "scheduled_date": target.strftime("%Y-%m-%d"),
            "execution_date": execution.strftime("%Y-%m-%d"),
            "advanced": execution != target,
        })
    return result
```

- [ ] **Step 4: Verify scheduling tests pass**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_fund_investment.py -q
```

Expected: PASS for scheduling tests.

- [ ] **Step 5: Write failing split/dividend/investment-order test**

```python
def test_same_day_order_is_split_then_dividend_then_investment():
    df = make_fund_df([
        {
            "日期": "2024-01-05",
            "单位净值": 1.0,
            "每份分红": 0.0,
            "拆分类型": "",
            "拆分折算比例": 1.0,
        },
        {
            "日期": "2024-01-12",
            "单位净值": 1.0,
            "每份分红": 0.1,
            "拆分类型": "份额折算",
            "拆分折算比例": 2.0,
        },
    ])

    result = run_weekly_investment(
        df, start_date="2024-01-01", weekday=5, amount=100.0
    )

    # Jan 5 buys 100 shares. Jan 12 split -> 200, dividend -> 20 shares,
    # then the scheduled CNY 100 investment -> 100 shares.
    assert result["summary"]["final_shares"] == pytest.approx(320.0)
    assert result["summary"]["total_invested"] == 200.0
    assert [e["event_type"] for e in result["events"]] == [
        "investment", "split", "dividend", "investment"
    ]
```

- [ ] **Step 6: Implement the daily event simulation**

Use Decimal for money/share accumulation or consistently round only response values, not internal state. The result shape must be:

```python
{
    "summary": {
        "investment_count": int,
        "total_invested": float,
        "final_shares": float,
        "latest_nav": float,
        "current_value": float,
        "total_profit": float,
        "total_return": float,
    },
    "dates": list[str],
    "total_invested_series": list[float],
    "asset_value_series": list[float],
    "return_series": list[float],
    "events": list[dict],
}
```

For each NAV row:

1. apply `拆分折算比例`;
2. reinvest `shares * 每份分红 / 单位净值`;
3. apply the scheduled investment if the date is selected;
4. append daily series values.

Reject empty data, invalid start dates, `amount <= 0`, and a start date after the latest NAV date.

- [ ] **Step 7: Add summary and validation tests**

Add concrete tests:

```python
def test_summary_uses_fractional_shares_and_latest_nav():
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 3.0},
        {"日期": "2024-01-12", "单位净值": 4.0},
    ])
    result = run_weekly_investment(
        df, start_date="2024-01-01", weekday=5, amount=100.0
    )
    summary = result["summary"]
    assert summary["investment_count"] == 2
    assert summary["total_invested"] == 200.0
    assert summary["final_shares"] == pytest.approx(100 / 3 + 25)
    assert summary["current_value"] == pytest.approx(
        summary["final_shares"] * 4.0
    )
    assert summary["total_profit"] == pytest.approx(
        summary["current_value"] - 200.0
    )
    assert summary["total_return"] == pytest.approx(
        summary["total_profit"] / 200.0
    )


def test_start_after_latest_nav_is_rejected():
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 1.0},
    ])
    with pytest.raises(ValueError, match="晚于最新净值日"):
        run_weekly_investment(
            df, start_date="2024-02-01", weekday=5, amount=100.0
        )


def test_split_and_dividend_do_not_increase_user_contributions():
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 1.0},
        {
            "日期": "2024-01-12",
            "单位净值": 1.0,
            "每份分红": 0.1,
            "拆分类型": "份额折算",
            "拆分折算比例": 2.0,
        },
    ])
    result = run_weekly_investment(
        df, start_date="2024-01-01", weekday=5, amount=100.0
    )
    assert result["summary"]["total_invested"] == 200.0
    assert result["total_invested_series"][-1] == 200.0
```

- [ ] **Step 8: Run the fund engine tests**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_fund_investment.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```powershell
Set-Location C:\Projects\TradingSystem
git add backend/app/core/fund_investment.py backend/tests/test_fund_investment.py
git commit -m "feat: add weekly fund investment engine" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 4: Expose Fund Analysis, Refresh, and Backtest APIs

**Files:**
- Create: `backend/app/services/fund_investment_service.py`
- Create: `backend/app/api/fund.py`
- Modify: `backend/app/main.py:4-18`
- Create: `backend/tests/test_fund_api.py`

**Interfaces:**
- Consumes: Task 2 data functions and Task 3 `run_weekly_investment`.
- Produces:
  - `GET` is not added.
  - `POST /api/fund/analysis`
  - `POST /api/fund/refresh`
  - `POST /api/fund/backtest`

- [ ] **Step 1: Write failing service and route tests**

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_fund_backtest_rejects_invalid_weekday():
    response = client.post("/api/fund/backtest", json={
        "fund_code": "000001",
        "strategy_name": "weekly_investment",
        "start_date": "2020-01-01",
        "weekday": 0,
        "amount": 1000,
    })
    assert response.status_code == 422


def test_fund_analysis_maps_value_error_to_400(monkeypatch):
    monkeypatch.setattr(
        "app.api.fund.get_fund_analysis",
        lambda code: (_ for _ in ()).throw(ValueError("基金类型不支持")),
    )
    response = client.post("/api/fund/analysis", json={"fund_code": "000009"})
    assert response.status_code == 400
    assert response.json()["detail"] == "基金类型不支持"


def test_missing_fund_maps_to_404(monkeypatch):
    from app.services.fund_data_service import FundNotFoundError

    monkeypatch.setattr(
        "app.api.fund.get_fund_analysis",
        lambda code: (_ for _ in ()).throw(FundNotFoundError("基金代码不存在")),
    )
    response = client.post("/api/fund/analysis", json={"fund_code": "999999"})
    assert response.status_code == 404
```

- [ ] **Step 2: Run API tests to verify failure**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_fund_api.py -q
```

Expected: FAIL because the route is not registered.

- [ ] **Step 3: Implement service serializers**

Create:

```python
def get_fund_analysis(fund_code: str) -> dict:
    df = load_fund_data(fund_code)
    latest = df.iloc[-1]
    return {
        "success": True,
        "fund_code": latest["基金代码"],
        "fund_name": latest["基金名称"],
        "fund_type": latest["基金类型"],
        "date_from": df["日期"].iloc[0],
        "date_to": df["日期"].iloc[-1],
        "rows": len(df),
        "latest_nav": round(float(latest["单位净值"]), 6),
    }


def run_fund_backtest(
    fund_code: str,
    strategy_name: str,
    start_date: str,
    weekday: int,
    amount: float,
) -> dict:
    if strategy_name != "weekly_investment":
        raise ValueError(f"不支持的基金定投策略: {strategy_name}")
    df = load_fund_data(fund_code)
    result = run_weekly_investment(df, start_date, weekday, amount)
    return {"success": True, "fund_code": fund_code, **result}
```

- [ ] **Step 4: Implement Pydantic requests and routes**

```python
class FundCodeRequest(BaseModel):
    fund_code: str


class FundBacktestRequest(BaseModel):
    fund_code: str
    strategy_name: Literal["weekly_investment"] = "weekly_investment"
    start_date: date
    weekday: int = Field(ge=1, le=5)
    amount: float = Field(gt=0)
```

Map `FundNotFoundError` to HTTP 404, other `ValueError` instances to HTTP 400, and unexpected errors to HTTP 500 with endpoint-specific Chinese detail. Register:

```python
from app.api import analysis, backtest, chan, data, fund

app.include_router(fund.router, prefix="/api/fund", tags=["fund"])
```

- [ ] **Step 5: Run API and fund tests**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_fund_api.py tests/test_fund_data_service.py tests/test_fund_investment.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
Set-Location C:\Projects\TradingSystem
git add backend/app/services/fund_investment_service.py backend/app/api/fund.py backend/app/main.py backend/tests/test_fund_api.py
git commit -m "feat: expose fund investment APIs" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 5: Add Frontend Fund Contracts and API Client

**Files:**
- Create: `frontend/src/types/fund.ts`
- Modify: `frontend/src/services/api.ts`

**Interfaces:**
- Consumes: Task 4 JSON shapes.
- Produces:
  - `analyseFund(fundCode: string): Promise<FundAnalysisResponse>`
  - `refreshFund(fundCode: string): Promise<FundRefreshResponse>`
  - `runFundBacktest(request: FundBacktestRequest): Promise<FundBacktestResponse>`

- [ ] **Step 1: Define exact frontend contracts**

Create discriminated event types:

```ts
export type FundEvent =
  | {
      event_type: 'investment'
      date: string
      scheduled_date: string
      advanced: boolean
      nav: number
      amount: number
      acquired_shares: number
      shares_after: number
    }
  | {
      event_type: 'dividend'
      date: string
      dividend_per_share: number
      dividend_cash: number
      acquired_shares: number
      shares_after: number
    }
  | {
      event_type: 'split'
      date: string
      split_type: string
      split_ratio: number
      shares_before: number
      shares_after: number
    }
```

Define `FundAnalysisResponse`, `FundRefreshResponse`, `FundBacktestRequest`, `FundBacktestSummary`, and `FundBacktestResponse` using the exact snake_case fields from Task 4.

- [ ] **Step 2: Add API calls**

```ts
export async function analyseFund(fundCode: string): Promise<FundAnalysisResponse> {
  const { data } = await client.post<FundAnalysisResponse>(
    '/fund/analysis',
    { fund_code: fundCode },
  )
  return data
}

export async function refreshFund(fundCode: string): Promise<FundRefreshResponse> {
  const { data } = await client.post<FundRefreshResponse>(
    '/fund/refresh',
    { fund_code: fundCode },
  )
  return data
}

export async function runFundBacktest(
  request: FundBacktestRequest,
): Promise<FundBacktestResponse> {
  const { data } = await client.post<FundBacktestResponse>(
    '/fund/backtest',
    request,
  )
  return data
}
```

- [ ] **Step 3: Verify TypeScript**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\frontend
npm run build
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
Set-Location C:\Projects\TradingSystem
git add frontend/src/types/fund.ts frontend/src/services/api.ts
git commit -m "feat: add fund API client contracts" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 6: Make Header and App Asset-Aware

**Files:**
- Modify: `frontend/src/components/layout/Header.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/fund/FundInvestmentTab.tsx`

**Interfaces:**
- Consumes: Task 5 `analyseFund` and `refreshFund`.
- Produces:
  - Header props `mode`, `value`, `onValueChange`, `onAnalyse`, `onRefresh`.
  - Separate `stockCode`, `fundCode`, `analysisData`, and `fundAnalysis`.

- [ ] **Step 1: Refactor Header into a controlled, mode-aware component**

Replace internal code state with:

```ts
interface HeaderProps {
  mode: 'stock' | 'fund'
  value: string
  loading: boolean
  refreshing: boolean
  onValueChange: (value: string) => void
  onAnalyse: () => void
  onRefresh: () => Promise<void>
}
```

Derive copy without guessing asset type from the code:

```tsx
const assetLabel = mode === 'fund' ? '基金' : '股票/ETF'
const placeholder = mode === 'fund'
  ? '输入基金代码，如 000001'
  : '输入股票/ETF代码，如 600519'
```

Header performs only empty-input validation and delegates API work.

- [ ] **Step 2: Add separate App state and mode routing**

Use:

```tsx
const [stockInput, setStockInput] = useState('')
const [fundInput, setFundInput] = useState('')
const [stockCode, setStockCode] = useState('')
const [fundCode, setFundCode] = useState('')
const [fundAnalysis, setFundAnalysis] = useState<FundAnalysisResponse | null>(null)
const isFundMode = activeTab === 'fund-investment'
```

`handleAnalyse` dispatches to `runAnalysis` or `analyseFund`; stock success activates `technical`, while fund success remains on `fund-investment`.

`handleRefresh` dispatches to `refreshData` or `refreshFund`, then re-runs the corresponding analysis so visible metadata is current.

- [ ] **Step 3: Add the fund Tab shell**

Add:

```tsx
{
  key: 'fund-investment',
  label: '基金定投',
  children: (
    <div className="tab-pane-inner">
      <FundInvestmentTab
        fundCode={fundCode}
        analysis={fundAnalysis}
      />
    </div>
  ),
}
```

Create `FundInvestmentTab.tsx` initially with metadata and Empty state only. It must not call stock APIs.

- [ ] **Step 4: Verify mode switching and build**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\frontend
npm run build
```

Expected: PASS with no prop or union errors.

Manually run Vite and confirm:

1. Fund Tab changes placeholder to fund copy.
2. Switching back restores the previous stock input.
3. Fund analysis does not switch to Technical Analysis.
4. Fund refresh calls `/api/fund/refresh`.

- [ ] **Step 5: Commit**

```powershell
Set-Location C:\Projects\TradingSystem
git add frontend/src/components/layout/Header.tsx frontend/src/App.tsx frontend/src/components/fund/FundInvestmentTab.tsx
git commit -m "feat: add fund-aware application mode" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 7: Build the Fund Strategy Form and Results

**Files:**
- Create: `frontend/src/components/fund/FundInvestmentConfig.tsx`
- Create: `frontend/src/components/fund/FundInvestmentSummary.tsx`
- Create: `frontend/src/components/fund/FundInvestmentChart.tsx`
- Create: `frontend/src/components/fund/FundEventTable.tsx`
- Modify: `frontend/src/components/fund/FundInvestmentTab.tsx`
- Modify: `frontend/src/App.css`

**Interfaces:**
- Consumes: Task 5 fund contracts and `runFundBacktest`.
- Produces: complete fund configuration and result UI.

- [ ] **Step 1: Implement the config form**

Use Ant Design `Select`, `DatePicker`, `InputNumber`, and `Button`.

```tsx
const WEEKDAYS = [
  { value: 1, label: '周一' },
  { value: 2, label: '周二' },
  { value: 3, label: '周三' },
  { value: 4, label: '周四' },
  { value: 5, label: '周五' },
]
```

Initial values:

```tsx
{
  strategy_name: 'weekly_investment',
  weekday: 5,
  amount: 1000,
  start_date: dayjs(analysis.date_from),
}
```

Disable dates before `analysis.date_from` and after `analysis.date_to`. Convert the Dayjs value to `YYYY-MM-DD` before calling `onRun`.

- [ ] **Step 2: Implement summary cards**

Show:

- total invested;
- current value;
- total profit;
- total return;
- investment count;
- final shares.

Use red for non-negative return/profit and green for negative values, matching the repository’s A-share color convention.

- [ ] **Step 3: Implement the contribution/value chart**

Create one ECharts option with:

```tsx
series: [
  { name: '累计投入', type: 'line', data: data.total_invested_series },
  { name: '资产市值', type: 'line', data: data.asset_value_series },
]
```

Use `data.dates` as the category axis, an inside and slider dataZoom, CNY tooltip formatting, and no candlestick series.

- [ ] **Step 4: Implement the discriminated event table**

Use a single table with columns:

- date;
- event type;
- scheduled date;
- NAV;
- amount/dividend cash;
- acquired or adjusted shares;
- shares after;
- note.

Render fields by `event.event_type`; never access investment-only fields without narrowing the union.

- [ ] **Step 5: Wire FundInvestmentTab**

`FundInvestmentTab` owns:

```tsx
const [result, setResult] = useState<FundBacktestResponse | null>(null)
const [loading, setLoading] = useState(false)
```

On fund-code change, clear stale results. Render metadata, config, loading state, summary, chart, and table in the same composition pattern as `BacktestTab`.

- [ ] **Step 6: Verify the production build**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\frontend
npm run build
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
Set-Location C:\Projects\TradingSystem
git add frontend/src/components/fund frontend/src/App.css
git commit -m "feat: add fund investment results UI" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 8: Document and Verify Fund Investment End-to-End

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: all previous fund tasks.
- Produces: documented and verified fund workflow.

- [ ] **Step 1: Update README**

Add:

- “基金定投” to the feature list;
- supported fund scope;
- `Fund_<code>.csv` naming;
- weekly scheduling and same-week backward adjustment;
- dividend reinvestment and split handling;
- explicit exclusions for money funds, ETF NAV backtests, and fees.

- [ ] **Step 2: Run the complete backend suite**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest -q
```

Expected: all existing and new tests PASS.

- [ ] **Step 3: Run the frontend production build**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\frontend
npm run build
```

Expected: PASS.

- [ ] **Step 4: Exercise real fund data**

Start the backend and call:

```powershell
$analysis = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/fund/analysis `
  -ContentType 'application/json' `
  -Body '{"fund_code":"000001"}'

$backtest = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/fund/backtest `
  -ContentType 'application/json' `
  -Body '{"fund_code":"000001","strategy_name":"weekly_investment","start_date":"2020-01-01","weekday":5,"amount":1000}'
```

Verify:

- `data/Fund_000001.csv` exists;
- `date_from` is the fund’s first NAV date;
- `investment_count > 0`;
- `total_invested == investment_count * 1000`;
- event ordering can reconstruct `final_shares`;
- no fund API response contains stock OHLC fields.

- [ ] **Step 5: Commit**

```powershell
Set-Location C:\Projects\TradingSystem
git add README.md
git commit -m "docs: describe fund investment workflow" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```
