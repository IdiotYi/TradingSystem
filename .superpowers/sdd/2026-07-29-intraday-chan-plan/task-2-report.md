# Task 2 Report: Provider Fallback and Two-Year Atomic Minute Cache

## Changed files
- `backend/app/services/minute_data_service.py`
- `backend/tests/test_minute_data_service.py`
- `.superpowers/sdd/2026-07-29-intraday-chan-plan/task-2-report.md` (this report)

## Provider and error-handling decisions
- Preserved Task 1 invariants by keeping BaoStock row-code equality validation and requiring every `adjustflag` to equal `"2"` before normalized output is accepted.
- Added `is_etf_code()` with a conservative exchange-traded-fund heuristic (`1*` and `5*` codes). ETF minute downloads skip BaoStock entirely.
- For non-ETF A shares, `download_minute_data()` tries BaoStock first, then AKShare Eastmoney, then AKShare Sina.
- Treated empty provider results as failures instead of successful empty caches.
- Aggregated provider failure messages and raised a single `ValueError` only after every applicable source failed.
- Preserved partial fallback data as usable cache content, while reporting `target_coverage_met=False` when coverage does not reach the requested two-year start window within the allowed 7-day tolerance.

## Cache and atomicity behavior
- Added `_today()` as the internal clock seam used to build the deterministic two-year request window `[today - DateOffset(years=2), today]`.
- Added minute cache naming via `data/Minute_<code>_<period>.csv`.
- Refresh now crops normalized minute rows to the rolling two-year window, sorts by `时间`, and deduplicates by `时间` before writing.
- Cache writes use a same-directory unique `*.tmp` file followed by `Path.replace()` so failed writes do not replace the existing cache.
- Cache reads now validate that every cached row matches the requested stock code and period, preventing misnamed or corrupted cache files from being silently served.

## RED (Task 2 feature tests)
### Command
```powershell
python -m pytest tests/test_minute_data_service.py -q
```

### Output
```text
..............FFFF                                                       [100%]
================================== FAILURES ===================================
FAILED tests/test_minute_data_service.py::test_a_share_falls_back_to_akshare
FAILED tests/test_minute_data_service.py::test_etf_skips_baostock
FAILED tests/test_minute_data_service.py::test_refresh_crops_two_years_and_deduplicates
FAILED tests/test_minute_data_service.py::test_failed_refresh_preserves_existing_cache
4 failed, 14 passed in 1.32s
```

### Why it was red
- The new provider-download and cache interfaces did not exist yet (`_download_baostock`, `download_minute_data`, `refresh_minute_data`, `DATA_DIR` usage for minute caches).

## GREEN (Task 2 feature tests)
### Command
```powershell
python -m pytest tests/test_minute_data_service.py -q
```

### Output
```text
..................                                                       [100%]
18 passed in 1.15s
```

## Self-review and reviewer follow-up
- Ran `git --no-pager diff --check -- backend/app/services/minute_data_service.py backend/tests/test_minute_data_service.py` with a clean result.
- Requested a code review against `c797a3d0eff6cc6d9ee7c86a7211a081f9e377e4..e03e7a8beb4e984aa326dd026c7742dffa7cceb1`.
- Reviewer strengths: fallback order matched the brief, targeted tests passed, and cache-failure preservation was covered.
- Reviewer issues fixed before completion:
  - Cache reads were hardened to reject stock-code and period mismatches.
  - Atomic writes were hardened to use unique temp files for same-key concurrent refreshes.

## RED (reviewer-driven hardening)
### Command
```powershell
python -m pytest tests/test_minute_data_service.py -q
```

### Output
```text
..................FFF                                                    [100%]
================================== FAILURES ===================================
FAILED tests/test_minute_data_service.py::test_load_rejects_cache_metadata_mismatch[股票代码-000001-股票代码]
FAILED tests/test_minute_data_service.py::test_load_rejects_cache_metadata_mismatch[周期-30-周期]
FAILED tests/test_minute_data_service.py::test_atomic_write_uses_unique_temp_files_for_same_target
3 failed, 18 passed in 1.42s
```

## GREEN (final verification)
### Command
```powershell
python -m pytest tests/test_minute_data_service.py -q
```

### Output
```text
.....................                                                    [100%]
21 passed in 1.03s
```

## Self-review summary
- Re-read `backend/app/services/minute_data_service.py` to confirm:
  - BaoStock login/logout scope is single-call and always logs out.
  - BaoStock normalization invariants from Task 1 remain enforced.
  - AKShare fallback order is Eastmoney then Sina.
  - ETF codes skip BaoStock.
  - Coverage metadata is derived from cached normalized rows.
  - Cache writes are atomic and use unique temporary files.
  - Cache reads validate code, period, and `qfq` invariants.
- Re-read `backend/tests/test_minute_data_service.py` to confirm the suite covers fallback, ETF skip, two-year crop/dedup, refresh failure preservation, cache-key validation, and temp-file collision protection.

## Commit SHA(s)
- `e03e7a8beb4e984aa326dd026c7742dffa7cceb1` — `feat: cache minute data with fallback`
- `dab69be30dc32cc241a36eaa63eebcb93508769c` — `fix: harden minute cache integrity`

## Concerns
- No live-provider integration call was exercised in this task; validation is limited to deterministic unit tests and adapter structure.
- ETF detection is heuristic by code prefix (`1*` / `5*`), which matches current requirements and examples but may need refinement if additional minute-capable instrument classes are introduced.

## Round 1: Existing cache rolling-window enforcement

### RED (existing-cache rolling window)
#### Command
```powershell
python -m pytest tests/test_minute_data_service.py -q
```

#### Output
```text
....................FF.
================================== FAILURES ===================================
__________ test_load_trims_existing_cache_to_current_two_year_window __________
AssertionError: assert ['2024-07-20 15:00:00', '2024-07-29 15:00:00', '2026-07-29 15:00:00'] == ['2024-07-29 15:00:00', '2026-07-29 15:00:00']

_____ test_load_raises_when_existing_cache_has_no_rows_in_current_window ______
Failed: DID NOT RAISE <class 'ValueError'>

2 failed, 21 passed in 1.40s
```

### GREEN (existing-cache rolling window)
#### Command
```powershell
python -m pytest tests/test_minute_data_service.py -q
```

#### Output
```text
.......................                                                  [100%]
23 passed in 1.10s
```

### Design notes
- Added deterministic load-path tests by freezing `_today()` and seeding cache files directly, so the regression is proven without any provider calls.
- Introduced `_load_cached_minute_data()` to keep `load_minute_data()` explicit: validate cached metadata first, crop to the current `[today - 2 years, today]` window, atomically rewrite only when trimming changed the cache, and never download unless the cache file is missing.
- When trimming removes every row, loading now raises `ValueError("分钟数据缓存在当前两年窗口内无可用数据，请显式刷新")` instead of returning an empty success.

### Self-review
- Re-read `backend/app/services/minute_data_service.py` to confirm the load path still uses `_read_minute_csv()` for metadata validation and `_atomic_write_minute_csv()` for any persisted trim.
- Re-read `backend/tests/test_minute_data_service.py` to confirm the new tests cover both required behaviors: trimming stale cached rows and raising on an empty usable window without invoking refresh.
- Requested a read-only review for `dab69be30dc32cc241a36eaa63eebcb93508769c..a6c47a14d066fa4cc6089061a18a9820efd14141`; reviewer found no Critical/Important/Minor issues and marked it ready to merge.

### Commit SHA
- `a6c47a14d066fa4cc6089061a18a9820efd14141` — `fix: trim stale minute cache window`
