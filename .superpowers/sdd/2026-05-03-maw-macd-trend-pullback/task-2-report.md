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

Commit SHA: populated by the commit containing this report; see repository HEAD.
Commit message: `feat: add MAW MACD trend pullback engine.`
