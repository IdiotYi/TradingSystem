# MAW + MACD Trend Pullback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a no-lookahead, MAW + MACD long-horizon trend-pullback stock backtest strategy with staged position management and visual explanations.

**Architecture:** Keep MAW and MACD calculations in `core`; implement the strategy state machine in a dedicated core module; retain trade execution, fee calculations, data loading, and response assembly in the existing backtest service. Extend the current API DTO and React backtest UI only for the new strategy response fields.

**Tech Stack:** Python 3.13, FastAPI, pandas, NumPy, pytest; React 18, TypeScript, Ant Design 5, ECharts 5, Vite.

**Spec:** `docs/superpowers/specs/2026-05-03-maw-macd-trend-pullback-design.md`

## Global Constraints

- Strategy identifier is exactly `trend_pullback_maw_macd`.
- Use daily OHLCV and same-day closing-price execution only.
- MAW requires `成交额`, `成交量`, and `换手率`; raise `ValueError` if unavailable.
- Use MAW20/60/120, MACD(12,26,9), and MAW60 20-day slope.
- Never read rows after the current bar; each trend trade has `signal_date == date`.
- Cap position at 80%, retain 100-share lots, and never allow negative cash.
- Preserve all existing strategy behavior and API fields.

---

## File Map

| File | Responsibility |
|---|---|
| `backend/app/core/indicators.py` | Add MACD sequence calculation. |
| `backend/app/core/trend_pullback.py` | Prepare indicators and run the rule-priority, staged-position state machine. |
| `backend/tests/test_trend_pullback.py` | Test signals, risk priority, lot/cash bounds, and no-lookahead invariance. |
| `backend/app/services/backtest_service.py` | Dispatch the new strategy and serialize its indicator/position series. |
| `backend/app/api/backtest.py` | Restrict stock strategy values and add validated trend parameters. |
| `backend/tests/test_backtest_api.py` | Test registered strategy acceptance and invalid/Missing-MAW 400 responses. |
| `frontend/src/types/backtest.ts` | Add strategy union, trend parameters, new response series and summary fields. |
| `frontend/src/components/backtest/BacktestConfig.tsx` | Add strategy selector and read-only long-horizon rule summary. |
| `frontend/src/components/backtest/BacktestChart.tsx` | Render MAW20/60/120 and MACD/position panel for this strategy. |
| `frontend/src/components/backtest/TradeTable.tsx` | Display the optional signal date. |

---

### Task 1: MACD core indicator

**Files:**
- Modify: `backend/app/core/indicators.py`
- Modify: `backend/tests/test_indicators.py`

**Interfaces:**
- Produces: `calc_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]`, returned as DIF, DEA, Histogram.

- [ ] **Step 1: Write failing MACD tests**

```python
def test_calc_macd_uses_adjust_false_ema():
    close = pd.Series([10.0, 11.0, 12.0, 11.0, 13.0])
    dif, dea, histogram = calc_macd(close, fast=2, slow=3, signal=2)
    expected_dif = close.ewm(span=2, adjust=False).mean() - close.ewm(span=3, adjust=False).mean()
    assert dif.equals(expected_dif)
    assert histogram.equals(dif - dea)
```

- [ ] **Step 2: Run the failing test**

Run: `python -m pytest tests/test_indicators.py::test_calc_macd_uses_adjust_false_ema -q`
Expected: FAIL because `calc_macd` cannot be imported.

- [ ] **Step 3: Implement the minimal indicator**

```python
def calc_macd(close, fast=12, slow=26, signal=9):
    fast_ema = close.ewm(span=fast, adjust=False).mean()
    slow_ema = close.ewm(span=slow, adjust=False).mean()
    dif = fast_ema - slow_ema
    dea = dif.ewm(span=signal, adjust=False).mean()
    return dif, dea, dif - dea
```

- [ ] **Step 4: Verify the indicator tests**

Run: `python -m pytest tests/test_indicators.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/indicators.py backend/tests/test_indicators.py
git commit -m "feat: add MACD indicator"
```

### Task 2: Trend-pullback core state machine

**Files:**
- Create: `backend/app/core/trend_pullback.py`
- Create: `backend/tests/test_trend_pullback.py`

**Interfaces:**
- Consumes: `calc_maw` and `calc_macd`; an ascending DataFrame containing `日期`, `收盘`, `成交量`, `成交额`, and `换手率`.
- Produces: `run_trend_pullback(df: pd.DataFrame, initial_cash: float, buy_fee: Callable[[float], dict], sell_fee: Callable[[float], dict]) -> tuple[list[dict], float, int, dict]`. The final dict contains `maw20`, `maw60`, `maw120`, `macd_dif`, `macd_dea`, `macd_histogram`, `target_position`, and `position_ratio`.

- [ ] **Step 1: Write failing rule tests using deterministic synthetic daily data**

```python
def test_trend_trade_uses_same_day_signal_and_close():
    trades, _, _, series = run_trend_pullback(frame_with_healthy_pullback(), 100000, buy_fee, sell_fee)
    first = trades[0]
    assert first["reason"] == "趋势回撤开仓"
    assert first["signal_date"] == first["date"]
    assert first["price"] == frame_with_healthy_pullback().loc[first_index, "收盘"]
    assert series["target_position"][first_index] == 0.4

def test_future_rows_do_not_change_prior_outputs():
    full = run_trend_pullback(frame_with_healthy_pullback(), 100000, buy_fee, sell_fee)
    cut = run_trend_pullback(frame_with_healthy_pullback().iloc[:170], 100000, buy_fee, sell_fee)
    assert full[3]["target_position"][:170] == cut[3]["target_position"]
    assert [t for t in full[0] if t["date"] <= cut_last_date] == cut[0]
```

- [ ] **Step 2: Run focused tests to establish failure**

Run: `python -m pytest tests/test_trend_pullback.py -q`
Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement indicator preparation and fixed target positions**

```python
def prepare_trend_indicators(df):
    required = {"成交额", "成交量", "换手率", "收盘"}
    if not required.issubset(df.columns):
        raise ValueError("MAW趋势策略需要成交额、成交量和换手率数据")
    result = df.copy()
    result["maw20"] = calc_maw(result, 20)
    result["maw60"] = calc_maw(result, 60)
    result["maw120"] = calc_maw(result, 120)
    result["macd_dif"], result["macd_dea"], result["macd_histogram"] = calc_macd(result["收盘"])
    return result
```

- [ ] **Step 4: Implement priority-ordered state transitions**

Implement close-to-target 100-share lot helpers and process each row in this exact order: 18% loss clear, MAW60/120 or two-day MAW120 clear, MAW60/cost risk reductions, high-profit reductions, then opening/adding. Record `signal_date`, preserve weighted average cost on purchases, reset it on full liquidation, and append end-of-day position ratios.

- [ ] **Step 5: Add tests for every threshold and invariant**

```python
def test_position_never_exceeds_eighty_percent_or_available_cash():
    trades, cash, shares, series = run_trend_pullback(volatile_frame(), 100000, buy_fee, sell_fee)
    assert cash >= 0
    assert shares % 100 == 0
    assert max(v for v in series["position_ratio"] if v is not None) <= 0.8 + 1e-9

def test_hard_stop_has_priority_over_profit_taking():
    trades, *_ = run_trend_pullback(frame_triggering_loss_and_other_rules(), 100000, buy_fee, sell_fee)
    assert trades[-1]["reason"] == "成本亏损18%清仓"
```

- [ ] **Step 6: Verify core tests**

Run: `python -m pytest tests/test_trend_pullback.py tests/test_indicators.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/trend_pullback.py backend/tests/test_trend_pullback.py
git commit -m "feat: add MAW MACD trend pullback engine"
```

### Task 3: Backtest API integration and contracts

**Files:**
- Modify: `backend/app/services/backtest_service.py`
- Modify: `backend/app/api/backtest.py`
- Create: `backend/tests/test_backtest_api.py`

**Interfaces:**
- Consumes: `run_trend_pullback` from Task 2.
- Produces: the existing backtest response plus trend indicator series; all trades may include optional `signal_date`; summary includes `max_position_ratio`, `average_position_ratio`, `rebalance_count`.

- [ ] **Step 1: Write failing service/API tests**

```python
def test_invalid_stock_strategy_returns_400(client):
    response = client.post("/api/backtest/run", json=valid_request(strategy_name="typo"))
    assert response.status_code == 400

def test_trend_strategy_returns_series_and_signal_dates(monkeypatch, client):
    monkeypatch.setattr("app.services.backtest_service.load_stock_data", lambda _: maw_ready_frame())
    data = client.post("/api/backtest/run", json=valid_request(strategy_name="trend_pullback_maw_macd")).json()
    assert len(data["maw120"]) == len(data["dates"])
    assert len(data["position_ratio"]) == len(data["dates"])
    assert all(t["signal_date"] == t["date"] for t in data["trades"])
```

- [ ] **Step 2: Run API tests to verify failure**

Run: `python -m pytest tests/test_backtest_api.py -q`
Expected: FAIL because the contract is not implemented.

- [ ] **Step 3: Add explicit stock strategy validation**

Use `Literal["three_factors", "three_factors_v2", "supertrend_ma", "supertrend_wma", "buy_and_hold", "trend_pullback_maw_macd"]` for `BacktestRequest.strategy_name`. Add validated trend defaults in `StrategyParams`: `maw_short_period=20`, `maw_medium_period=60`, `maw_long_period=120`, `maw_slope_days=20`, `min_rebalance_delta=0.10`, `min_buy_interval_days=5`.

- [ ] **Step 4: Dispatch and serialize the strategy**

Before date slicing, compute trend indicators over all rows through `end_date`; preserve pre-start rows for warm-up. Dispatch `trend_pullback_maw_macd` to Task 2 after the start-date slice. Return null-filled trend series for other strategies so the response remains structurally stable. Calculate position summary values from the strategy series.

- [ ] **Step 5: Verify API and all backend tests**

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/backtest.py backend/app/services/backtest_service.py backend/tests/test_backtest_api.py
git commit -m "feat: expose MAW MACD trend backtest"
```

### Task 4: Type-safe backtest UI and visualization

**Files:**
- Modify: `frontend/src/types/backtest.ts`
- Modify: `frontend/src/components/backtest/BacktestConfig.tsx`
- Modify: `frontend/src/components/backtest/BacktestChart.tsx`
- Modify: `frontend/src/components/backtest/TradeTable.tsx`

**Interfaces:**
- Consumes: the Task 3 response fields and `strategy_name === "trend_pullback_maw_macd"`.
- Produces: a selectable strategy with a clear rule summary and an ECharts layout showing MAW, MACD, target position, and actual position.

- [ ] **Step 1: Update TypeScript DTOs before component changes**

```typescript
export type StockStrategyName = /* existing names */ | "trend_pullback_maw_macd"
export interface Trade { signal_date?: string; /* existing fields */ }
export interface BacktestResponse {
  maw60: (number | null)[]
  maw120: (number | null)[]
  macd_dif: (number | null)[]
  macd_dea: (number | null)[]
  macd_histogram: (number | null)[]
  target_position: (number | null)[]
  position_ratio: (number | null)[]
}
```

- [ ] **Step 2: Add the selector and rule summary**

Add `trend_pullback_maw_macd` labelled `MAW+MACD中长线趋势回撤`. When selected, show a compact non-editable description: MAW20/60/120, MACD(12,26,9), 80% maximum position, five-day add interval, 12%/18% cost-loss controls, and same-day close execution. Send defaults defined in the type file.

- [ ] **Step 3: Render strategy-specific chart series**

For the trend strategy, use three grids: price with MAW20/60/120 and trade points; MACD DIF/DEA/histogram; target and actual positions formatted as percentages. Keep existing strategy chart branches unchanged.

- [ ] **Step 4: Display signal date in the transaction table**

Add a `信号日期` column only when at least one supplied trade has `signal_date`; use `-` for legacy trades.

- [ ] **Step 5: Build the frontend**

Run: `npm run build`
Expected: TypeScript passes and Vite produces `dist/`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/backtest.ts frontend/src/components/backtest
git commit -m "feat: visualize MAW MACD trend strategy"
```

### Task 5: Documentation and final verification

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-05-03-maw-macd-trend-pullback-design.md` only if implementation changes an approved contract.

- [ ] **Step 1: Document the selectable strategy and assumptions**

Add a short README subsection that identifies `trend_pullback_maw_macd`, its MAW/MACD parameters, 80% maximum position, same-day closing-price assumption, and the statement that results are research simulations rather than investment advice.

- [ ] **Step 2: Run full verification**

Run: `cd backend && python -m pytest -q`
Expected: PASS.

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 3: Inspect final changes**

Run: `git diff master...HEAD --check && git status --short`
Expected: no whitespace errors; only intended tracked files changed.

- [ ] **Step 4: Commit documentation**

```bash
git add README.md docs/superpowers/specs/2026-05-03-maw-macd-trend-pullback-design.md
git commit -m "docs: describe MAW MACD trend strategy"
```
