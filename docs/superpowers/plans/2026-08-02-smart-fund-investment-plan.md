# Smart Fund Investment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a weekly, no-lookahead smart fund strategy that buys only deep drawdowns, scales purchase size by drawdown, harvests a fully overbought profitable position, and produces at least 100% historical cumulative return for `010772` on the fixed inception-to-2026-07-31 dataset.

**Architecture:** Extend the existing fund core with a separate smart engine and shared portfolio response fields while keeping `run_weekly_investment` behavior intact. Smart decisions use a total-return index and the previous weekly snapshot only; backend service dispatches by strategy name, and the frontend renders unified portfolio/cash/trade information.

**Tech Stack:** Python 3.10+, pandas, Decimal, FastAPI, pytest, React 18, TypeScript, Ant Design 5, ECharts.

## Global Constraints

- Strategy name is exactly `smart_dip_investment`; existing `weekly_investment` remains unchanged.
- Evaluate at most once per natural week using the existing weekday and same-week fallback rules.
- A trade at week `W` uses only the snapshot recorded at week `W-1`; week `W` NAV cannot influence the week `W` decision.
- Indicators use a total-return index that adjusts for dividends and splits.
- Buy tiers are fixed: drawdown `<= -50%` buys `5.0 × amount`; `(-50%, -45%]` buys `3.0 × amount`; `(-45%, -40%]` buys `0.5 × amount`; above `-40%` buys nothing.
- Drawdowns at or below `-45%` reuse all accumulated sale cash; the `0.5 ×` tier does not reuse cash.
- Sell 100% only when the previous snapshot has position return `>= 90%` and Wilder RSI(14) `>= 70`.
- Sell has priority over buy.
- Only external buy contributions increase `total_invested`; recycled sale cash never counts twice.
- Portfolio value is cash plus fund market value.
- Transaction costs remain ignored.
- `010772`, start `2020-12-30`, Friday, base amount `1000`, refreshed through `2026-07-31` must produce `total_return >= 1.0`; report the exact measured result without implying future performance.
- Preserve the unrelated `.claude/settings.local.json` change.

---

## File Map

### Backend

- Modify `backend/app/core/fund_investment.py`: total-return index, RSI, smart snapshots, buy/sell accounting, unified weekly response defaults.
- Modify `backend/app/services/fund_investment_service.py`: dispatch both strategies.
- Modify `backend/tests/test_fund_investment.py`: indicator, no-lookahead, tier, sale, cash, accounting, and weekly regression tests.
- Modify `backend/tests/test_fund_api.py`: smart strategy request and unknown strategy behavior.

### Frontend

- Modify `frontend/src/types/fund.ts`: smart events, unified summary, cash series.
- Modify `frontend/src/components/fund/FundInvestmentConfig.tsx`: strategy option and fixed-rule explanation.
- Modify `frontend/src/components/fund/FundInvestmentSummary.tsx`: unified portfolio cards.
- Modify `frontend/src/components/fund/FundInvestmentChart.tsx`: cash line.
- Modify `frontend/src/components/fund/FundEventTable.tsx`: smart buy/sell rendering.

### Documentation

- Modify `README.md`: strategy rules, anti-lookahead timing, accounting, and historical-result disclaimer.

---

### Task 1: Implement Total-Return Signals and Smart Portfolio Engine

**Files:**
- Modify: `backend/app/core/fund_investment.py`
- Modify: `backend/tests/test_fund_investment.py`

**Interfaces:**
- Consumes:
  - existing `select_weekly_investment_dates(df, start_date, weekday)`;
  - normalized fund columns `日期`, `单位净值`, `每份分红`, `拆分类型`, `拆分折算比例`.
- Produces:
  - `run_smart_dip_investment(df: pd.DataFrame, start_date: str, weekday: int, amount: float) -> dict`;
  - the existing `run_weekly_investment(df: pd.DataFrame, start_date: str, weekday: int, amount: float) -> dict` with compatible added summary/series defaults.

- [ ] **Step 1: Write total-return-index tests**

Add:

```python
from app.core.fund_investment import run_smart_dip_investment


def test_smart_signal_index_adjusts_dividend_and_split():
    df = make_fund_df([
        {
            "日期": "2024-01-05",
            "单位净值": 1.0,
            "每份分红": 0.0,
            "拆分折算比例": 1.0,
        },
        {
            "日期": "2024-01-12",
            "单位净值": 0.45,
            "每份分红": 0.05,
            "拆分折算比例": 2.0,
        },
    ])

    result = run_smart_dip_investment(
        df, start_date="2024-01-01", weekday=5, amount=1000
    )

    assert result["signal_index_series"] == pytest.approx([1.0, 1.0])
```

The second factor is `2 × (0.45 + 0.05) / 1.0 = 1.0`, so corporate actions must not create a false drawdown.

- [ ] **Step 2: Write pure tier-boundary tests**

Expose no new public configuration. Test through the module-private helper:

```python
from decimal import Decimal
from app.core import fund_investment


@pytest.mark.parametrize(
    ("drawdown", "multiplier", "reuse_cash"),
    [
        ("-0.5000", "5.0", True),
        ("-0.4999", "3.0", True),
        ("-0.4500", "3.0", True),
        ("-0.4499", "0.5", False),
        ("-0.4000", "0.5", False),
        ("-0.3999", "0", False),
    ],
)
def test_smart_buy_tiers_are_exact(drawdown, multiplier, reuse_cash):
    actual_multiplier, actual_reuse = fund_investment._smart_buy_rule(
        Decimal(drawdown)
    )
    assert actual_multiplier == Decimal(multiplier)
    assert actual_reuse is reuse_cash
```

- [ ] **Step 3: Write strict one-week-lag tests**

Use four Friday rows:

```python
def test_smart_strategy_uses_previous_week_signal_not_execution_nav():
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 1.00},
        {"日期": "2024-01-12", "单位净值": 0.95},
        {"日期": "2024-01-19", "单位净值": 0.55},
        {"日期": "2024-01-26", "单位净值": 0.56},
    ])

    result = run_smart_dip_investment(
        df, start_date="2024-01-01", weekday=5, amount=1000
    )

    buys = [e for e in result["events"] if e["event_type"] == "smart_buy"]
    assert [event["date"] for event in buys] == ["2024-01-26"]
    assert buys[0]["signal_date"] == "2024-01-19"
```

The crash on January 19 must not buy at January 19's NAV. It becomes known only for the January 26 execution.

- [ ] **Step 4: Write cash-reuse and contribution-accounting tests**

Build a deterministic frame that triggers:

1. one deep-drawdown buy;
2. a synthetic profitable/overbought sell by monkeypatching `_weekly_wilder_rsi`;
3. a later drawdown buy that reuses all cash.

Assert:

```python
assert result["summary"]["total_invested"] == 8000.0
assert result["summary"]["total_sale_proceeds"] > 0
assert result["summary"]["cash_balance"] == 0.0
assert second_buy["reused_cash"] == first_sell["proceeds"]
assert second_buy["contribution_amount"] == 3000.0
assert second_buy["purchase_amount"] == pytest.approx(
    second_buy["contribution_amount"] + second_buy["reused_cash"]
)
```

The `8000` total is the first `5 × 1000` contribution plus the second `3 × 1000` contribution. Sale cash must not be counted again.

- [ ] **Step 5: Write sell-priority and full-liquidation tests**

Monkeypatch the signal helper so the previous snapshot simultaneously qualifies for a sell and a deep-drawdown buy:

```python
assert sell_event["sold_shares"] == pytest.approx(
    sell_event["shares_before"]
)
assert sell_event["shares_after"] == 0.0
assert not any(
    event["event_type"] == "smart_buy"
    and event["date"] == sell_event["date"]
    for event in result["events"]
)
```

- [ ] **Step 6: Write zero-trade and invalid-input tests**

Add:

```python
def test_smart_strategy_returns_zero_result_when_drawdown_never_reaches_40_percent():
    rows = [
        {
            "日期": timestamp.strftime("%Y-%m-%d"),
            "单位净值": 1.0 + index * 0.01,
        }
        for index, timestamp in enumerate(
            pd.date_range("2024-01-05", periods=16, freq="7D")
        )
    ]
    result = run_smart_dip_investment(
        make_fund_df(rows),
        start_date="2024-01-01",
        weekday=5,
        amount=1000,
    )
    assert result["summary"]["total_invested"] == 0.0
    assert result["summary"]["total_return"] == 0.0
    assert result["summary"]["buy_count"] == 0
    assert result["summary"]["sell_count"] == 0


@pytest.mark.parametrize("bad_nav", [0, -1, float("nan"), float("inf")])
def test_smart_strategy_rejects_invalid_nav(bad_nav):
    df = make_fund_df([
        {"日期": "2024-01-05", "单位净值": 1.0},
        {"日期": "2024-01-12", "单位净值": bad_nav},
    ])
    with pytest.raises(ValueError, match="单位净值"):
        run_smart_dip_investment(
            df,
            start_date="2024-01-01",
            weekday=5,
            amount=1000,
        )
```

Also reject non-positive/non-finite split ratios and non-positive/non-finite base amounts.

- [ ] **Step 7: Run tests to verify RED**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_fund_investment.py -q
```

Expected: new tests fail because the smart engine and response fields do not exist.

- [ ] **Step 8: Implement signal helpers**

Add constants:

```python
SMART_RSI_PERIOD = 14
SMART_SELL_POSITION_RETURN = Decimal("0.90")
SMART_SELL_RSI = Decimal("70")
```

Add:

```python
def _smart_buy_rule(drawdown: Decimal) -> tuple[Decimal, bool]:
    if drawdown <= Decimal("-0.50"):
        return Decimal("5.0"), True
    if drawdown <= Decimal("-0.45"):
        return Decimal("3.0"), True
    if drawdown <= Decimal("-0.40"):
        return Decimal("0.5"), False
    return Decimal("0"), False
```

Build the total-return index in chronological order. Validate every NAV and split ratio with `math.isfinite` plus positivity before converting to `Decimal`.

Implement Wilder RSI without using future rows:

```python
def _weekly_wilder_rsi(values: list[Decimal], period: int = 14) -> Decimal | None:
    if len(values) <= period:
        return None
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(change, Decimal("0")) for change in changes]
    losses = [max(-change, Decimal("0")) for change in changes]
    average_gain = sum(gains[:period]) / Decimal(period)
    average_loss = sum(losses[:period]) / Decimal(period)
    for gain, loss in zip(gains[period:], losses[period:]):
        average_gain = (
            average_gain * Decimal(period - 1) + gain
        ) / Decimal(period)
        average_loss = (
            average_loss * Decimal(period - 1) + loss
        ) / Decimal(period)
    if average_loss == 0:
        return Decimal("100")
    relative_strength = average_gain / average_loss
    return Decimal("100") - Decimal("100") / (
        Decimal("1") + relative_strength
    )
```

- [ ] **Step 9: Implement smart weekly snapshots**

Iterate all normalized rows from inception, not only rows after `start_date`.
Process split then dividend on each date. On each selected weekly execution:

1. if execution date is at or after `start_date`, apply the previous snapshot;
2. sell first if it qualifies;
3. otherwise apply `_smart_buy_rule`;
4. after the trade, append the current total-return index to weekly signal history;
5. create the new snapshot containing date, drawdown, RSI, and position return.

The first scheduled week has no previous snapshot and cannot trade.

- [ ] **Step 10: Implement cost basis and events**

Track `shares`, `cost_basis`, `cash_balance`, `total_invested`,
`total_sale_proceeds`, and `realized_profit`.

For smart buy:

```python
contribution = amount_decimal * multiplier
reused_cash = cash_balance if reuse_cash else Decimal("0")
purchase_amount = contribution + reused_cash
acquired_shares = purchase_amount / nav
```

For full sale:

```python
sold_shares = shares
proceeds = sold_shares * nav
realized = proceeds - cost_basis
cash_balance += proceeds
shares = Decimal("0")
cost_basis = Decimal("0")
```

Emit exact `smart_buy` and `smart_sell` fields from the design spec.

- [ ] **Step 11: Add unified response fields**

Both strategies return:

```python
"summary": {
    "investment_count": buy_count,
    "decision_count": decision_count,
    "buy_count": buy_count,
    "sell_count": sell_count,
    "total_invested": _to_float(total_invested),
    "final_shares": _to_float(shares),
    "latest_nav": _to_float(latest_nav),
    "fund_value": _to_float(fund_value),
    "cash_balance": _to_float(cash_balance),
    "current_value": _to_float(current_value),
    "total_sale_proceeds": _to_float(total_sale_proceeds),
    "realized_profit": _to_float(realized_profit),
    "total_profit": _to_float(total_profit),
    "total_return": _to_float(total_return),
},
"cash_balance_series": cash_balance_series,
"signal_index_series": signal_index_series,
```

For `weekly_investment`:

- `decision_count == investment_count`;
- `buy_count == investment_count`;
- `sell_count == 0`;
- `fund_value == current_value`;
- cash, sale proceeds, and realized profit are zero;
- `cash_balance_series` contains zeros;
- `signal_index_series` is the adjusted index aligned to response dates.

- [ ] **Step 12: Run core tests**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_fund_investment.py -q
```

Expected: PASS.

- [ ] **Step 13: Commit**

```powershell
Set-Location C:\Projects\TradingSystem
git add backend/app/core/fund_investment.py backend/tests/test_fund_investment.py
git commit -m "feat: add smart fund investment engine" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 2: Dispatch Smart Strategy Through Service and API

**Files:**
- Modify: `backend/app/services/fund_investment_service.py`
- Modify: `backend/tests/test_fund_api.py`

**Interfaces:**
- Consumes:
  - `run_weekly_investment(df: pd.DataFrame, start_date: str, weekday: int, amount: float) -> dict`;
  - `run_smart_dip_investment(df: pd.DataFrame, start_date: str, weekday: int, amount: float) -> dict`.
- Produces:
  - unchanged `POST /api/fund/backtest` request shape;
  - response containing the selected engine's unified fields.

- [ ] **Step 1: Write failing service/API tests**

Add:

```python
def test_smart_strategy_dispatches_through_api(monkeypatch):
    expected = {
        "summary": {
            "total_return": 1.01,
            "buy_count": 46,
            "sell_count": 1,
        },
        "dates": [],
        "total_invested_series": [],
        "asset_value_series": [],
        "cash_balance_series": [],
        "return_series": [],
        "signal_index_series": [],
        "events": [],
    }
    monkeypatch.setattr(
        "app.services.fund_investment_service.load_fund_data",
        lambda code: make_fund_df(),
    )
    monkeypatch.setattr(
        "app.services.fund_investment_service.run_smart_dip_investment",
        lambda df, start_date, weekday, amount: expected,
    )

    response = post_json("/api/fund/backtest", {
        "fund_code": "000001",
        "strategy_name": "smart_dip_investment",
        "start_date": "2024-01-01",
        "weekday": 5,
        "amount": 1000,
    })

    assert response.status_code == 200
    assert response.json()["summary"]["sell_count"] == 1
```

Keep the existing unknown-strategy HTTP 400 test.

- [ ] **Step 2: Run test to verify RED**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_fund_api.py -q
```

Expected: FAIL because the service rejects `smart_dip_investment`.

- [ ] **Step 3: Implement explicit dispatch**

Replace the single-name guard with:

```python
if strategy_name == "weekly_investment":
    result = run_weekly_investment(df, start_date, weekday, amount)
elif strategy_name == "smart_dip_investment":
    result = run_smart_dip_investment(df, start_date, weekday, amount)
else:
    raise ValueError(f"不支持的基金定投策略: {strategy_name}")
```

Load fund data once after validating the strategy name, then return the existing
`success` and `fund_code` wrapper.

- [ ] **Step 4: Run fund backend tests**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest tests/test_fund_investment.py tests/test_fund_api.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
Set-Location C:\Projects\TradingSystem
git add backend/app/services/fund_investment_service.py backend/tests/test_fund_api.py
git commit -m "feat: expose smart fund backtest strategy" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 3: Extend Frontend Contracts and Strategy Configuration

**Files:**
- Modify: `frontend/src/types/fund.ts`
- Modify: `frontend/src/components/fund/FundInvestmentConfig.tsx`

**Interfaces:**
- Consumes: Task 2 request/response.
- Produces:
  - `FundStrategyName = 'weekly_investment' | 'smart_dip_investment'`;
  - typed smart buy/sell events;
  - strategy selector and explanation.

- [ ] **Step 1: Extend request and event types**

Add:

```ts
export type FundStrategyName =
  | 'weekly_investment'
  | 'smart_dip_investment'
```

Set `FundBacktestRequest.strategy_name: FundStrategyName`.

Add `smart_buy` and `smart_sell` union members with every field from the design
spec. Add unified summary fields and:

```ts
cash_balance_series: number[]
signal_index_series: number[]
```

- [ ] **Step 2: Add the strategy option**

Use:

```tsx
const STRATEGIES = [
  { value: 'weekly_investment', label: '每周定投' },
  { value: 'smart_dip_investment', label: '智能定投' },
] satisfies Array<{
  value: FundStrategyName
  label: string
}>
```

Watch the strategy:

```tsx
const strategyName = Form.useWatch('strategy_name', form)
```

When smart is selected, render an Ant Design `Alert`:

```text
信号严格滞后一周：回撤 40%/45%/50% 分层买入；持仓收益达到 90% 且周 RSI(14) ≥ 70 时清仓。历史回测不代表未来收益。
```

Do not expose threshold controls.

- [ ] **Step 3: Build to verify types**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\frontend
npm run build
```

Expected: FAIL until Task 4 updates exhaustive event switches and new required summary fields.

- [ ] **Step 4: Commit contracts/config together**

Commit only after Task 4 completes the build-compatible rendering, or use one
temporary local commit that Task 4 immediately follows. The final Task 3+4
history must not leave an intentionally non-building commit as the task gate.

---

### Task 4: Render Smart Portfolio, Cash, Buys, and Sells

**Files:**
- Modify: `frontend/src/components/fund/FundInvestmentSummary.tsx`
- Modify: `frontend/src/components/fund/FundInvestmentChart.tsx`
- Modify: `frontend/src/components/fund/FundEventTable.tsx`

**Interfaces:**
- Consumes: Task 3's expanded `FundBacktestResponse`.
- Produces: complete build-compatible smart strategy UI.

- [ ] **Step 1: Update summary cards**

Render these eight cards:

```text
累计投入
组合价值
累计盈亏
累计收益率
买入次数
卖出次数
现金余额
期末份额
```

Use `summary.current_value`, `buy_count`, `sell_count`, and `cash_balance`.

- [ ] **Step 2: Add the cash series**

Add `现金余额` to the legend and:

```tsx
{
  name: '现金余额',
  type: 'line',
  data: data.cash_balance_series,
  showSymbol: false,
  lineStyle: { color: '#a371f7', width: 2 },
}
```

Keep `资产市值` as total portfolio value.

- [ ] **Step 3: Extend event tags and columns**

Add tags:

```tsx
case 'smart_buy':
  return <Tag color="volcano">智能买入</Tag>
case 'smart_sell':
  return <Tag color="green">智能卖出</Tag>
```

For smart buy:

- cash amount is `purchase_amount`;
- adjusted shares are `acquired_shares`;
- note includes drawdown percentage, RSI or `尚未形成`, multiplier, new contribution, and reused cash.

For smart sell:

- cash amount is `proceeds`;
- adjusted shares are negative `sold_shares`;
- note includes signal position return, RSI, and realized profit.

Use `signal_date` in the existing plan-date column and relabel that column
`计划/信号日期`.

- [ ] **Step 4: Run production build**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\frontend
npm run build
```

Expected: PASS with only the existing large-chunk warning.

- [ ] **Step 5: Commit Tasks 3 and 4**

```powershell
Set-Location C:\Projects\TradingSystem
git add frontend/src/types/fund.ts frontend/src/components/fund/FundInvestmentConfig.tsx frontend/src/components/fund/FundInvestmentSummary.tsx frontend/src/components/fund/FundInvestmentChart.tsx frontend/src/components/fund/FundEventTable.tsx
git commit -m "feat: add smart fund investment UI" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 5: Document and Verify the Fixed 010772 Historical Result

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: complete backend/frontend feature.
- Produces: documented behavior and measured real-data result.

- [ ] **Step 1: Update README**

Document:

- both fund strategies;
- strict previous-week signal timing;
- total-return-index adjustment;
- fixed drawdown tiers;
- 90% profit plus RSI 70 sell rule;
- external-contribution versus recycled-cash accounting;
- historical/in-sample disclaimer;
- the measured `010772` result with data end date.

- [ ] **Step 2: Run complete backend suite**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\backend
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run frontend production build**

Run:

```powershell
Set-Location C:\Projects\TradingSystem\frontend
npm run build
```

Expected: PASS.

- [ ] **Step 4: Refresh 010772**

Run from `backend`:

```powershell
$env:PYTHONIOENCODING='utf-8'
python -c "from app.services.fund_data_service import refresh_fund_data; print(refresh_fund_data('010772'))"
```

Verify:

```text
fund_code == 010772
date_from == 2020-12-30
date_to == 2026-07-31
```

If the live provider has newer data, create the acceptance slice ending exactly
`2026-07-31`; do not let later rows change the fixed historical target.

- [ ] **Step 5: Run fixed smart and weekly backtests**

Use a Python verification command that loads the cache, slices through
`2026-07-31`, and calls:

```python
weekly = run_weekly_investment(
    fixed, "2020-12-30", weekday=5, amount=1000
)
smart = run_smart_dip_investment(
    fixed, "2020-12-30", weekday=5, amount=1000
)
```

Assert:

```python
assert smart["summary"]["total_return"] >= 1.0
assert smart["summary"]["buy_count"] > 0
assert smart["summary"]["sell_count"] > 0
assert all(
    event["signal_date"] < event["date"]
    for event in smart["events"]
    if event["event_type"] in {"smart_buy", "smart_sell"}
)
assert len(smart["dates"]) == len(smart["asset_value_series"])
assert len(smart["dates"]) == len(smart["cash_balance_series"])
```

Print weekly and smart summaries and the complete smart buy/sell event list.

- [ ] **Step 6: Check deterministic result**

Run the fixed smart backtest twice and assert summaries and smart trade events
are identical.

- [ ] **Step 7: Commit**

```powershell
Set-Location C:\Projects\TradingSystem
git add README.md
git commit -m "docs: describe smart fund investment strategy" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

- [ ] **Step 8: Final branch review**

Review the complete branch for:

- future leakage;
- accidental current-week signal use;
- cash double-counting;
- cost-basis errors after split/dividend/sale;
- weekly strategy regressions;
- frontend exhaustive union errors;
- claims that imply guaranteed future performance.
