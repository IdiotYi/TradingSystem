# Task 3 report

Status: DONE

Files: backend/app/api/backtest.py; backend/app/services/backtest_service.py; backend/tests/test_backtest_api.py.

RED: python -m pytest tests/test_backtest_api.py -q -> 4 failed before production integration (unknown strategy accepted, response fields absent, trend dispatch absent).

GREEN: python -m pytest tests/test_backtest_api.py -q -> 4 passed in 1.20s.

Regression: python -m pytest -q -> 144 passed, 2 existing pandas FutureWarnings in fund data service.

Commit: 47bef6fed19e02369e92387419395355a81c27e3

Self-review: Literal rejects unknown strategies with 422; trend engine retains pre-start warmup while response is sliced; new arrays align to dates; legacy strategies get null arrays and safe zero summaries; trend trades are normalized to existing response shape with signal_date preserved.

## Review fix: requested-start portfolio isolation

RED: `python -m pytest tests/test_backtest_api.py -q` -> 1 failed, 4 passed. The deterministic warmup test produced no requested trade because execution had already opened a position before `start_date`, demonstrating leaked cash/share/cost/last-buy state.

GREEN: `python -m pytest tests/test_backtest_api.py tests/test_trend_pullback.py -q` -> 16 passed. Indicators are prepared through `end_date`, requested rows retain full-history MAW/MACD values and required previous/lag values, and the state machine initializes and executes only on requested rows.

Regression: `python -m pytest -q` -> 145 passed, 2 existing pandas FutureWarnings in fund data service.

Correction: The earlier self-review statement that filtering full-history execution artifacts safely restricted the backtest was incorrect. The implementation now performs no pre-start execution, and legacy strategies explicitly return date-aligned null arrays for all seven new-only trend series plus safe zero position/rebalance summaries.
