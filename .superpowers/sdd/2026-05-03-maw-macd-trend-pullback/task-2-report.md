# Task 2 Report — Trend-pullback core state machine

## Files

- Created `backend/app/core/trend_pullback.py`.
- Created `backend/tests/test_trend_pullback.py`.
- Created this report.
- No API or frontend files changed.

## TDD evidence

### RED

Command: `cd backend && python -m pytest tests/test_trend_pullback.py -q`

Result: exit 1 during collection with `ModuleNotFoundError: No module named 'app.core.trend_pullback'` (1 error), proving the production module was absent before implementation.

### GREEN

Command: `cd backend && python -m pytest tests/test_trend_pullback.py -q`

Result: exit 0, `5 passed in 0.36s`.

Coverage includes required MAW fields, same-day signal and close execution, equal-length output series, future-truncation invariance, 80%/cash/100-share-lot invariants, and 18% hard-stop priority.

## Self-review

- Calls existing `calc_maw` for 20/60/120 and `calc_macd` with defaults.
- Evaluates rows sequentially and records `signal_date == date` at same-day close.
- Implements target priority (80/60/40/0), opening/add gates, exact exit priority, and approved Chinese reason strings.
- Uses before-trade total assets for target sizing, caps purchases at 80%, rounds trades to 100-share lots, accounts for fee callbacks, and prevents negative cash.
- Maintains fee-inclusive weighted average buy cost and resets cost/purchase state after liquidation.
- No API/frontend files were touched.

## Commit

Commit SHA: `0c60333` for initial implementation; review correction SHA: `2ab0a04ea3ca2ab1e64e51e20869911d8acbb09d`.
Commit message: `feat: add MAW MACD trend pullback engine.`

## Review fix round
- Verified defects: exit branches previously set `acted` from sale success, allowing same-bar buys when target rounding required no shares sold; buy sizing checked cash but not post-fee exposure.
- RED: expanded suite produced focused failures before production corrections.
- GREEN focused command: `python -m pytest tests/test_trend_pullback.py -q`; result `11 passed in 0.39s`.
- GREEN full command: `python -m pytest -q`; result recorded below.
- Added deterministic coverage for exact 40/60/80 targets, five-bar add gates, matched-exit suppression, fee-inclusive 80% cap, combined risk reduction, and lowest profit target priority.
- Review correction commit SHA: `2ab0a04ea3ca2ab1e64e51e20869911d8acbb09d`.
- Full suite: ........................................................................ [ 51%] ....................................................................     [100%] ============================== warnings summary =============================== tests/test_fund_data_service.py::test_refresh_supports_off_exchange_index_fund_with_mixed_listing_rows   E:\Projects\TradingSystem\.worktrees\maw-macd-trend-pullback\backend\app\services\fund_data_service.py:112: FutureWarning: Downcasting object dtype arrays on .fillna, .ffill, .bfill is deprecated and will change in a future version. Call result.infer_objects(copy=False) instead. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`     result["ÿ�ݷֺ�"] = result["ÿ�ݷֺ�"].fillna(0.0)  tests/test_fund_data_service.py::test_refresh_supports_off_exchange_index_fund_with_mixed_listing_rows   E:\Projects\TradingSystem\.worktrees\maw-macd-trend-pullback\backend\app\services\fund_data_service.py:114: FutureWarning: Downcasting object dtype arrays on .fillna, .ffill, .bfill is deprecated and will change in a future version. Call result.infer_objects(copy=False) instead. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`     result["����������"] = result["����������"].fillna(1.0)  -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html 140 passed, 2 warnings in 10.17s

## Review fix round 2
- Corrected the matched-exit regression: the prior test did not actually match an exit rule.
- The replacement deterministically opens a 100-share position, then matches the higher-priority 70% high-MAW20 momentum exit on a bar whose 100-share lot rounding yields no sale.
- That same bar independently satisfies the add gates and an 80% buy target; assertions prove there is neither a sell nor a same-day buy, covering acted suppression.
- Focused command: `python -m pytest tests/test_trend_pullback.py::test_matched_exit_suppresses_same_bar_buy_when_rounding_needs_no_sale -q`; result: `1 passed in 0.31s`.
- Full file command: `python -m pytest tests/test_trend_pullback.py -q`; result: `11 passed in 0.37s`.
- Production logic was not modified.

