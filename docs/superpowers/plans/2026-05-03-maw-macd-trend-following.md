# MAW + MACD 趋势增强策略 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the return-focused `trend_following_maw_macd` strategy and a reproducible in-sample/out-of-sample evaluator.

**Architecture:** Reuse existing MAW/MACD calculation and backtest fee/accounting conventions. Put the independent sequential trend-following state machine in `core`, make service dispatch and DTO serialization additive, and provide a command-line evaluator that reads only local cached CSV data.

**Tech Stack:** Python, pandas, FastAPI, pytest; React, TypeScript, ECharts, Vite.

**Spec:** `docs/superpowers/specs/2026-05-03-maw-macd-trend-following-design.md`

## Global Constraints

- Strategy identifier: `trend_following_maw_macd`.
- Use daily data, same-day closing-price execution, 100-share lots and the existing fee functions.
- Strong trend allows 100% exposure; all calculations use current or prior data only.
- Fixed evaluation periods: 2021-01-01–2023-12-31 and 2024-01-01–2025-12-31.
- Do not auto-select or modify default parameters based on evaluation output.

---

### Task 1: Core trend-following engine

**Files:**
- Create: `backend/app/core/trend_following.py`
- Create: `backend/tests/test_trend_following.py`

**Interfaces:**
- Produces: `prepare_trend_following_indicators(df, short_period=20, medium_period=60, long_period=120, slope_days=20) -> pd.DataFrame`.
- Produces: `run_trend_following(df, initial_cash, buy_fee, sell_fee, prepared=None, params=None) -> tuple[list[dict], float, int, dict]`.

- [ ] **Step 1: Write failing deterministic tests**

```python
def test_strong_trend_reaches_full_position_without_macd_profit_sell():
    trades, _, _, series = run_trend_following(strong_trend_frame(), 100000, no_fee, no_fee)
    assert max(series["position_ratio"]) > 0.99
    assert not any(t["reason"] == "短期MACD止盈" for t in trades)

def test_future_truncation_keeps_prior_trades_identical():
    full = run_trend_following(frame(), 100000, no_fee, no_fee)
    cut = run_trend_following(frame().iloc[:180], 100000, no_fee, no_fee)
    assert full[0][:len(cut[0])] == cut[0]
```

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest tests/test_trend_following.py -q`
Expected: FAIL because module is missing.

- [ ] **Step 3: Implement state machine**

Implement strong/normal/recovery targets 1.0/.7/.85, five-bar buy interval, 10-point rebalance threshold, 25% cost stop, MAW60/120 and three-day structural exits. Retain actual per-trade fee, cash, PnL and `signal_date`.

- [ ] **Step 4: Add tests for each exit and accounting invariant**

```python
def test_maw60_below_maw120_liquidates():
    trades, _, shares, _ = run_trend_following(structural_break_frame(), 100000, no_fee, no_fee)
    assert trades[-1]["reason"] == "MAW60跌破MAW120清仓"
    assert shares == 0
```

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/test_trend_following.py -q`
Expected: PASS.

```bash
git add backend/app/core/trend_following.py backend/tests/test_trend_following.py
git commit -m "feat: add return-focused trend strategy"
```

### Task 2: Backtest API and evaluator

**Files:**
- Modify: `backend/app/api/backtest.py`
- Modify: `backend/app/services/backtest_service.py`
- Create: `backend/app/services/strategy_evaluation.py`
- Create: `backend/tests/test_strategy_evaluation.py`

**Interfaces:**
- Produces: `evaluate_cached_strategies(data_dir: Path, codes: list[str] | None = None) -> dict`.
- Returns per-code/per-period metrics `total_return`, `max_drawdown`, `trade_count`; aggregated OOS mean/median return, mean drawdown and buy-and-hold win rate.

- [ ] **Step 1: Write failing API/evaluation tests**

```python
def test_evaluator_uses_fixed_train_and_out_of_sample_windows(tmp_path):
    result = evaluate_cached_strategies(tmp_path, ["600001"])
    assert set(result["periods"]) == {"train", "out_of_sample"}
    assert result["periods"]["out_of_sample"]["start"] == "2024-01-01"
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_strategy_evaluation.py -q`
Expected: FAIL because evaluator is missing.

- [ ] **Step 3: Integrate strategy and evaluator**

Add `trend_following_maw_macd` to the API Literal and service dispatch. Serialize the existing MAW/MACD/target/position contract. Evaluator must skip missing-MAW files with reasons, compare all five strategies on fixed windows, and never tune parameters.

- [ ] **Step 4: Verify and commit**

Run: `python -m pytest tests/test_strategy_evaluation.py tests/test_backtest_api.py -q`
Expected: PASS.

```bash
git add backend/app/api/backtest.py backend/app/services/backtest_service.py backend/app/services/strategy_evaluation.py backend/tests/test_strategy_evaluation.py
git commit -m "feat: evaluate return-focused trend strategy"
```

### Task 3: Frontend selection and results

**Files:**
- Modify: `frontend/src/types/backtest.ts`
- Modify: `frontend/src/components/backtest/BacktestConfig.tsx`
- Modify: `frontend/src/components/backtest/BacktestChart.tsx`
- Modify: `README.md`

- [ ] **Step 1: Add typed strategy selection**

Add exact identifier with label `MAW+MACD趋势增强（收益优先）`; send existing MAW parameter defaults.

- [ ] **Step 2: Add compact rule description and reuse MAW/MACD chart**

Display 100% strong-trend holding, three-day structural exits, 25% disaster stop, and same-day-close execution. Reuse the existing trend chart branch for MAW/MACD/position series.

- [ ] **Step 3: Build and commit**

Run: `npm run build`
Expected: PASS.

```bash
git add frontend/src/types/backtest.ts frontend/src/components/backtest README.md
git commit -m "feat: add return-focused trend strategy UI"
```

### Task 4: Fixed-sample evaluation and final verification

**Files:**
- Create: `docs/evaluations/2026-05-03-trend-following-baseline.json`
- Modify: `README.md`

- [ ] **Step 1: Run evaluator against cached local data**

Run: `python -m app.services.strategy_evaluation --data-dir ../data --output ../docs/evaluations/2026-05-03-trend-following-baseline.json` from `backend`.
Expected: JSON reports skipped instruments and train/OOS summaries without changing defaults.

- [ ] **Step 2: Record outcome limitations**

Document fixed periods, included/skipped instruments, and that evaluation does not establish future performance or investment advice.

- [ ] **Step 3: Final verification and commit**

Run: `python -m pytest -q && cd ../frontend && npm run build`
Expected: PASS.

```bash
git add docs/evaluations README.md
git commit -m "docs: record trend strategy evaluation baseline"
```
