# Fund Investment Final Fix Report

## Status

All four final-review findings were fixed together and verified in the existing worktree:

```text
C:\Projects\TradingSystem\.worktrees\fund-investment-and-intraday-chan
```

Branch:

```text
feature/fund-investment-intraday-chan
```

## Finding-to-Fix Mapping

### 1. HIGH — Cache reload stripped leading zeros

**Root cause**

`backend/app/services/fund_data_service.py::_read_fund_csv` used an unconstrained
`pandas.read_csv`. Pandas inferred `基金代码` as numeric, so the cached value
`000001` became integer `1`. The analysis response then exposed `"1"`, and using
that response code in `/api/fund/backtest` failed six-digit code validation.

**Fix**

- Read `基金代码` with pandas string dtype.
- Strip and `zfill(6)` values after loading.
- Re-run `normalize_fund_code` on every cached code.
- This also repairs legacy cache rows already interpreted as short digit strings.

**Regression coverage**

- `test_load_fund_data_downloads_when_cache_missing`
  - verifies an actual CSV write/read round trip returns `["000001", "000001"]`.
- `test_cached_000001_analysis_code_can_round_trip_into_backtest`
  - installs a real cache file;
  - calls `/api/fund/analysis`;
  - feeds the returned `fund_code` into `/api/fund/backtest`;
  - verifies both responses retain `000001`.

### 2. MEDIUM — Exchange ETFs bypassed type-keyword gating

**Root cause**

The implementation rejected only fund-type keywords. Real AKShare metadata for
`510300` is `指数型-股票`, which contains none of the existing ETF/type rejection
keywords.

**Fix**

- Added `_fetch_exchange_listed_fund_codes`.
- It reads AKShare `fund_etf_fund_daily_em`, the EastMoney exchange-traded fund
  listing, and normalizes its `基金代码` values.
- `_download_normalized_fund_data` now checks the requested code against that
  listing after metadata/type validation and before any
  `fund_open_fund_info_em` NAV/event download.
- Exchange-listed `510300` is rejected with
  `不支持场内ETF基金: 510300`.
- Off-exchange funds whose metadata type is `指数型-股票` remain supported when
  their code is absent from the exchange listing.
- Empty or malformed exchange-list responses fail closed instead of allowing an
  ETF through to the NAV path.

**Regression coverage**

- `test_refresh_rejects_exchange_listed_etf_before_nav_download`
  - supplies `510300` metadata as `指数型-股票`;
  - supplies `510300` in the authoritative listing;
  - verifies rejection and zero NAV-download calls.
- `test_refresh_supports_off_exchange_index_fund`
  - supplies ordinary off-exchange index-fund metadata;
  - verifies refresh remains supported when the code is not listed.

### 3. MEDIUM — Incomplete current week invested before a future target

**Root cause**

The weekly selector grouped available NAV rows by week and moved a Friday target
back to Thursday without checking whether that scheduled Friday was later than
the dataset's latest NAV date.

**Fix**

- Compute the latest normalized NAV date once.
- Skip any weekly target whose scheduled date is later than that latest date.
- Historical completed weeks still retain the existing same-week backward
  adjustment behavior.

**Regression coverage**

- `test_incomplete_current_week_does_not_schedule_future_friday`
  - uses deterministic data ending Thursday;
  - selects Friday;
  - verifies no investment is scheduled for that incomplete week.
- Existing `test_missing_friday_moves_to_thursday_in_same_week` continues to
  verify backward adjustment for a completed historical week.

### 4. MEDIUM — Successful refresh could leave stale backtest results visible

**Root cause**

`FundInvestmentTab` invalidated results from a `useEffect` keyed only by metadata
values. A same-fund historical refresh can install a new successful analysis
payload whose code, range, row count, and latest NAV are identical, so none of
those dependencies changed.

**Fix**

- Added `fundAnalysisGeneration` state in `App`.
- Increment it only after a latest-action-guarded fund analysis payload is
  successfully installed, for both Analyze and Refresh flows.
- Pass the generation identity to `FundInvestmentTab`.
- Include it in the invalidation effect so every successful installed payload
  cancels in-flight backtests and clears the previous result.
- The result is not cleared at the start of a same-fund refresh, preserving the
  prior same-fund refresh UX until a successful replacement arrives.
- Existing per-asset action IDs and per-backtest request IDs remain intact, so
  stale async completions cannot repopulate invalid results.

**Verification**

- The repository has no frontend test runner by design.
- TypeScript and the Vite production build validate the new required prop and
  state flow.
- Direct self-review traced same-fund success, failed refresh, different-fund
  refresh, and stale-request sequences.

## TDD RED Evidence

Command:

```powershell
Set-Location 'C:\Projects\TradingSystem\.worktrees\fund-investment-and-intraday-chan\backend'
python -m pytest tests\test_fund_data_service.py tests\test_fund_investment.py tests\test_fund_api.py -q
```

Output before production fixes:

```text
........F....F.F............F..........                                  [100%]
FAILED tests/test_fund_data_service.py::test_refresh_rejects_exchange_listed_etf_before_nav_download
FAILED tests/test_fund_data_service.py::test_load_fund_data_downloads_when_cache_missing
FAILED tests/test_fund_investment.py::test_incomplete_current_week_does_not_schedule_future_friday
FAILED tests/test_fund_api.py::test_cached_000001_analysis_code_can_round_trip_into_backtest
4 failed, 35 passed in 2.98s
```

The failures respectively showed:

- exchange-listed `510300` was not rejected;
- cache reload returned `[1, 1]`;
- Thursday data generated a future Friday target;
- analysis returned `"1"` instead of `"000001"`.

## Focused Backend Verification

Command:

```powershell
Set-Location 'C:\Projects\TradingSystem\.worktrees\fund-investment-and-intraday-chan\backend'
python -m pytest tests\test_fund_data_service.py tests\test_fund_investment.py tests\test_fund_api.py -q
```

Output:

```text
.......................................                                  [100%]
39 passed in 2.48s
```

## Complete Backend Verification

Command:

```powershell
Set-Location 'C:\Projects\TradingSystem\.worktrees\fund-investment-and-intraday-chan\backend'
python -m pytest -q
```

Output:

```text
...............................................................          [100%]
63 passed in 8.49s
```

## Frontend Production Build

Command:

```powershell
Set-Location 'C:\Projects\TradingSystem\.worktrees\fund-investment-and-intraday-chan\frontend'
npm run build
```

Output:

```text
> trading-system-frontend@1.0.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 3649 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                     0.45 kB │ gzip:   0.29 kB
dist/assets/index-BLhOlFsy.css      0.89 kB │ gzip:   0.48 kB
dist/assets/index-BgowHtJZ.js   2,245.27 kB │ gzip: 728.86 kB

(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rollupOptions.output.manualChunks to improve chunking: https://rollupjs.org/configuration-options/#output-manualchunks
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
✓ built in 10.43s
```

The large-chunk message is the existing non-failing Vite warning.

## Real Data/API Exercise

A temporary Uvicorn server was started on port `8011`.

Command:

```powershell
Set-Location 'C:\Projects\TradingSystem\.worktrees\fund-investment-and-intraday-chan\backend'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```

The existing ignored cache was confirmed to contain:

```text
日期,基金代码,基金名称,基金类型,单位净值,日增长率,每份分红,拆分类型,拆分折算比例
2001-12-18,000001,华夏成长混合,混合型-灵活,1.0,0.0,0.0,,1.0
```

The API exercise called:

1. `POST /api/fund/analysis` with `000001`;
2. `POST /api/fund/backtest` using the analysis response's `fund_code`;
3. `POST /api/fund/refresh` with exchange ETF `510300`.

Command:

```powershell
Set-Location 'C:\Projects\TradingSystem\.worktrees\fund-investment-and-intraday-chan'
$analysis = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8011/api/fund/analysis' -ContentType 'application/json' -Body '{"fund_code":"000001"}'
$backtestBody = @{ fund_code = $analysis.fund_code; strategy_name = 'weekly_investment'; start_date = '2020-01-01'; weekday = 5; amount = 1000 } | ConvertTo-Json -Compress
$backtest = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8011/api/fund/backtest' -ContentType 'application/json' -Body $backtestBody
$etfStatus = $null
$etfDetail = $null
try {
  Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8011/api/fund/refresh' -ContentType 'application/json' -Body '{"fund_code":"510300"}' | Out-Null
  $etfStatus = 200
} catch {
  $etfStatus = [int]$_.Exception.Response.StatusCode
  $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
  $etfDetail = ($reader.ReadToEnd() | ConvertFrom-Json).detail
}
[pscustomobject]@{
  analysis_fund_code = $analysis.fund_code
  analysis_rows = $analysis.rows
  analysis_date_from = $analysis.date_from
  analysis_date_to = $analysis.date_to
  backtest_request_code = ($backtestBody | ConvertFrom-Json).fund_code
  backtest_response_code = $backtest.fund_code
  investment_count = $backtest.summary.investment_count
  total_invested = $backtest.summary.total_invested
  etf_status = $etfStatus
  etf_detail = $etfDetail
  etf_cache_exists = (Test-Path 'data\Fund_510300.csv')
} | Format-List
```

Observed output:

```text
analysis_fund_code     : 000001
analysis_rows          : 5974
analysis_date_from     : 2001-12-18
analysis_date_to       : 2026-07-30
backtest_request_code  : 000001
backtest_response_code : 000001
investment_count       : 336
total_invested         : 336000.0
etf_status             : 400
etf_detail             :
etf_cache_exists       : False
```

Readable ETF response capture:

Command:

```powershell
$OutputEncoding = [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$env:PYTHONIOENCODING='utf-8'
python -c "import httpx; r=httpx.post('http://127.0.0.1:8011/api/fund/refresh', json={'fund_code':'510300'}, timeout=120); print(r.status_code); print(r.json())"
```

Output:

```text
400
{'detail': '不支持场内ETF基金: 510300'}
```

The temporary server was stopped after verification.

## Files Changed

- `backend/app/core/fund_investment.py`
- `backend/app/services/fund_data_service.py`
- `backend/tests/test_fund_api.py`
- `backend/tests/test_fund_data_service.py`
- `backend/tests/test_fund_investment.py`
- `frontend/src/App.tsx`
- `frontend/src/components/fund/FundInvestmentTab.tsx`
- `.superpowers/sdd/2026-07-29-fund-investment-plan/final-fix-report.md`

## Self-Review

Commands:

```powershell
git diff --check
git status --short
git diff --stat
git diff
```

Results:

- `git diff --check` produced no errors.
- Reviewed every changed production and test hunk.
- Confirmed ETF rejection occurs before all three NAV/event download calls.
- Confirmed the listing check does not reject a non-listed ordinary index fund.
- Confirmed cache normalization repairs leading-zero loss at the source.
- Confirmed the incomplete-week guard does not change completed-week fallback.
- Confirmed generation increments occur only after the existing latest-action
  guard accepts a successful payload.
- Confirmed failed same-fund refreshes retain the previous result, while each
  successful installed payload invalidates it.
- A read-only final code review reported:

```text
No significant issues found in the reviewed changes.
```

## Commit

All production fixes, regressions, and this report are staged for one final
commit with the required Copilot co-author trailer.

## Extra Final Fix Round

Date:

```text
2026-07-31
```

This explicitly authorized round closed the two residual load-bearing
findings from the prior final review.

### 1. ETF listing now fails closed when every row is invalid

**Residual root cause**

`_fetch_exchange_listed_fund_codes` rejected a missing dataframe, an empty
dataframe, and a missing `基金代码` column, but returned an empty set after
filtering malformed values such as `["bad", None]`. The caller interpreted
that empty set as an authoritative list containing no exchange ETFs and
continued into the NAV download path.

**Fix**

- Normalize and filter the listing as before.
- Require the resulting set to contain at least one valid six-digit code.
- Raise `ValueError("场内ETF列表未包含有效基金代码")` when no valid code remains.
- Keep accepting mixed listings such as `["bad", None, "510300"]`, ignoring
  malformed rows because the authoritative response still contains a valid
  code.
- Validation still runs before every NAV/event request and before the atomic
  cache write, so all invalid-listing failures preserve the prior cache.

**Regression coverage**

- `test_refresh_rejects_empty_exchange_listing_and_preserves_cache`
- `test_refresh_rejects_exchange_listing_without_code_column_and_preserves_cache`
- `test_refresh_rejects_all_invalid_exchange_codes_and_preserves_cache`
- `test_refresh_supports_off_exchange_index_fund_with_mixed_listing_rows`

The three fail-closed tests install an existing cache, assert the exact
listing error, assert zero NAV/event calls, and compare the cache bytes after
the failure.

**TDD RED evidence**

Command:

```powershell
Set-Location 'C:\Projects\TradingSystem\.worktrees\fund-investment-and-intraday-chan\backend'
python -m pytest tests\test_fund_data_service.py -k "empty_exchange_listing or without_code_column or all_invalid_exchange_codes or mixed_listing_rows" -q
```

Output before the production check was added:

```text
..F.                                                                     [100%]
FAILED tests/test_fund_data_service.py::test_refresh_rejects_all_invalid_exchange_codes_and_preserves_cache
1 failed, 3 passed, 13 deselected in 1.52s
```

The failing case showed that an all-invalid listing escaped the listing
validator and entered downstream NAV/event normalization instead of raising
the required `ValueError`.

### 2. Cache refresh generation now invalidates results before analysis

**Residual root cause**

`fundAnalysisGeneration` advanced only after the follow-up
`/api/fund/analysis` response passed the latest-action guard and was installed.
The cache had already changed when `/api/fund/refresh` returned, so an analysis
failure or superseded analysis completion could leave a backtest result based
on the old cache visible.

**Fix**

- Added an explicit `fundDataGeneration` state in `App`.
- After `/api/fund/refresh` succeeds, immediately check the existing
  fund-action ID.
- If the refresh is still the latest fund action, advance
  `fundDataGeneration` before starting `/api/fund/analysis`.
- If it is obsolete, return before changing the generation or starting the
  follow-up analysis.
- Pass the generation through the `App`/`FundInvestmentTab` contract as
  `dataGeneration`.
- Include `dataGeneration` in the tab invalidation effect. The effect advances
  its backtest request ID, clears the result, and clears loading, so an
  in-flight completion from the prior cache cannot repopulate the UI.
- Retain `fundAnalysisGeneration` for the existing successful-analysis
  invalidation behavior.

**Sequence analysis**

1. **Latest refresh succeeds, analysis succeeds:** the cache response passes
   the action guard; `fundDataGeneration` advances and clears/cancels the old
   result before analysis begins. The accepted analysis then installs the new
   payload and advances `fundAnalysisGeneration`.
2. **Latest refresh succeeds, analysis fails:** the data generation has
   already advanced. The error path does not roll it back, so the old result
   remains cleared.
3. **Latest refresh succeeds, then analysis is superseded:** the cache really
   changed while that refresh was latest, so its generation advance remains
   valid. The later action changes the action ID, causing the old analysis
   completion to be discarded.
4. **Refresh becomes obsolete before its cache response returns:** a newer
   fund action changes the action ID. The old response fails the guard and
   returns before advancing `fundDataGeneration`, so it cannot invalidate the
   newer selected fund.
5. **Old backtest completes after invalidation:** the tab effect has already
   incremented `requestIdRef`; the completion's request ID no longer matches
   and neither success nor failure can update the result.

The frontend intentionally has no test runner. TypeScript/Vite compilation
validates the required prop contract, and the sequence analysis above checks
the async ordering and stale-request invariants directly.

### Verification

Focused backend command:

```powershell
Set-Location 'C:\Projects\TradingSystem\.worktrees\fund-investment-and-intraday-chan\backend'
python -m pytest tests\test_fund_data_service.py -q
```

Output:

```text
.................                                                        [100%]
17 passed in 1.05s
```

Complete backend command:

```powershell
Set-Location 'C:\Projects\TradingSystem\.worktrees\fund-investment-and-intraday-chan\backend'
python -m pytest -q
```

Output:

```text
..................................................................       [100%]
66 passed in 8.70s
```

Frontend command:

```powershell
Set-Location 'C:\Projects\TradingSystem\.worktrees\fund-investment-and-intraday-chan\frontend'
npm run build
```

Output:

```text
> trading-system-frontend@1.0.0 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 3649 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                     0.45 kB │ gzip:   0.29 kB
dist/assets/index-BLhOlFsy.css      0.89 kB │ gzip:   0.48 kB
dist/assets/index-9qDctDhL.js   2,245.36 kB │ gzip: 728.89 kB

(!) Some chunks are larger than 500 kB after minification.
✓ built in 10.56s
```

The large-chunk message remains the existing non-failing Vite warning.

### Final review

- `git diff --check` produced no errors after the report update.
- A read-only review of the complete extra-round diff reported:

```text
No significant issues found in the reviewed changes.
```

Files changed in this round:

- `backend/app/services/fund_data_service.py`
- `backend/tests/test_fund_data_service.py`
- `frontend/src/App.tsx`
- `frontend/src/components/fund/FundInvestmentTab.tsx`
- `.superpowers/sdd/2026-07-29-fund-investment-plan/final-fix-report.md`

## Extra Final Fix Round 2

The targeted re-review found that whitespace-only listing values were stripped
to an empty string and then padded to `000000`. That synthetic value passed the
six-digit check, so an otherwise invalid ETF listing was treated as
authoritative.

The normalization now validates the stripped value as one to six digits before
padding it to six digits. Blank, null, and non-numeric rows are discarded, while
legitimate shorter numeric representations still normalize consistently.

The all-invalid regression now includes `"   "` and failed before the
production change by entering the NAV/event path. After the fix:

```text
66 passed in 8.49s
```

The frontend production build also completed successfully with only the
existing large-chunk warning.

Commit:

```text
283a1df fix: reject blank exchange fund codes
```

The scoped review reported no significant issues and confirmed the fund
feature is safe to serve as the dependency for the intraday Chan plan.
