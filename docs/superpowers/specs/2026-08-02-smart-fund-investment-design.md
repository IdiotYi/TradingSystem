# Smart Fund Investment Strategy Design

**Date:** 2026-08-02

## Goal

Add a second fund strategy, `smart_dip_investment`, that evaluates the fund
once per week, buys more during deep drawdowns, skips expensive periods, and
sells an overbought position after a large profit.

The strategy must:

- support both buys and sells;
- make at most one strategy decision per natural week;
- use no future data;
- preserve dividend reinvestment and split handling;
- ignore transaction costs, matching the existing fund backtest;
- retain the existing `weekly_investment` strategy unchanged;
- expose enough event and portfolio detail to explain every trade.

The historical target is a cumulative return above 100% on fund `010772` from
its available inception data through 2026-07-31. This is an in-sample research
target, not a guarantee of future performance.

## Approaches Considered

### 1. Rolling z-score target allocation

Continuously rebalance between fund and cash using rolling mean and volatility.
This is smooth and diversified, but exploratory `010772` results were below the
existing weekly investment return because the strategy held too much cash
during the long recovery.

### 2. Short/long moving-average regime switching

Move between fully invested and cash using weekly moving-average crossovers.
This avoids large downtrends, but reacts too slowly to this fund's sharp
reversals and did not reach the historical target.

### 3. Deep-drawdown accumulation with profit harvesting

Use the drawdown from the historical total-return peak to scale purchases, then
sell the complete position only when both the position profit and weekly RSI
show an exceptional rebound.

This is the selected design because it is interpretable, directly implements
"buy the dip", naturally supports buy/skip/sell decisions, and can be executed
with a strict one-week signal lag.

## Strategy Rules

### Weekly schedule

The user still chooses Monday through Friday. Missing target dates use the
existing same-week backward adjustment. An incomplete current week cannot be
executed before its target date.

The engine builds the complete weekly schedule from the fund's history so a
backtest starting after inception still has historical indicator warm-up.

### Strict anti-lookahead timing

For weekly execution `W`:

1. the signal is the snapshot recorded at execution `W-1`;
2. the trade executes at `W`'s unit NAV;
3. `W`'s NAV is not included in the signal that decides the `W` trade;
4. after the trade, the engine records a new snapshot for `W+1`.

Therefore every buy or sell is delayed by one complete weekly observation.
Changing a date range or starting the strategy later never exposes future NAVs
to an earlier decision.

### Signal price

Indicators use a total-return index rather than raw unit NAV so dividends and
splits do not create false drawdowns:

```text
period factor =
    split ratio × (current NAV + dividend per share) / previous NAV
```

The first valid row starts at index `1.0`. Invalid/non-positive NAVs, split
ratios, or non-finite values are rejected.

### Drawdown

At each weekly signal snapshot:

```text
drawdown = current total-return index / running historical peak - 1
```

The peak uses only observations available through that signal date.

### Buy tiers

`amount` remains the base amount entered by the user.

| Previous-week drawdown | New contribution | Reuse sale cash |
| --- | ---: | --- |
| `<= -50%` | `5.0 × amount` | all available cash |
| `(-50%, -45%]` | `3.0 × amount` | all available cash |
| `(-45%, -40%]` | `0.5 × amount` | no |
| `> -40%` | `0` | no |

Only new contributions increase `total_invested`. Reused sale cash is not
counted again.

### Sell rule

Compute 14-period weekly Wilder RSI from total-return-index snapshots. Sell
100% of the position when the previous weekly snapshot satisfies both:

```text
position return >= 90%
RSI(14) >= 70
```

Position return uses the remaining position's adjusted average cost. A split
changes shares but not total cost basis. Dividend reinvestment adds shares
without adding user cost. A partial-basis operation is retained internally even
though version one sells the full position.

Sell has priority over buy in a week. Sale proceeds remain as strategy cash and
are included in portfolio value.

## Accounting

The strategy tracks:

- fund shares;
- remaining position cost basis;
- sale cash balance;
- cumulative external contributions;
- fund market value;
- total portfolio value (`cash + fund value`);
- cumulative profit and return.

For both strategies:

```text
total profit = portfolio value - external contributions
total return = total profit / external contributions
```

For the existing strategy, cash is always zero and behavior remains unchanged.

The daily chart's asset series becomes total portfolio value. A new cash series
shows sale proceeds waiting for the next deep drawdown.

## Event Contract

Existing `investment`, `dividend`, and `split` events remain compatible.

Add:

### `smart_buy`

- execution and scheduled dates;
- signal date;
- NAV;
- drawdown and RSI;
- contribution multiplier;
- new contribution;
- reused cash;
- total purchase amount;
- acquired shares;
- shares and cash after the trade.

### `smart_sell`

- execution and scheduled dates;
- signal date;
- NAV;
- signal position return and RSI;
- sold shares;
- sale proceeds;
- realized profit;
- shares and cash after the trade.

Skipped weekly decisions are not emitted as table rows; aggregate
`decision_count` makes the evaluated frequency visible without producing a
large no-op event table.

## API and Service

The existing `/api/fund/backtest` request shape remains:

```json
{
  "fund_code": "010772",
  "strategy_name": "smart_dip_investment",
  "start_date": "2020-12-30",
  "weekday": 5,
  "amount": 1000
}
```

`fund_investment_service` dispatches:

- `weekly_investment` to the unchanged engine;
- `smart_dip_investment` to the new engine;
- any other value to the existing HTTP 400 path.

The response adds unified summary fields:

- `decision_count`;
- `buy_count`;
- `sell_count`;
- `cash_balance`;
- `fund_value`;
- `total_sale_proceeds`;
- `realized_profit`.

It also adds `cash_balance_series`. Weekly investment fills the new fields and
series with compatible zero/default values.

## Frontend

The strategy selector gains `智能定投`.

The same weekday, start date, and base amount controls apply to both strategies.
When smart investment is selected, a concise explanation displays the fixed
drawdown tiers, one-week signal lag, and sell condition. The thresholds are not
user-configurable in version one to prevent parameter mining through the UI.

Summary cards show:

- cumulative contributions;
- portfolio value;
- cumulative profit;
- cumulative return;
- buy count;
- sell count;
- cash balance;
- ending shares.

The chart adds `现金余额`. The event table renders smart buys and sells with
their signal date, drawdown/RSI, contribution multiplier, recycled cash, sale
proceeds, and realized profit.

## Error Handling

- Reject empty data, non-positive base amounts, invalid weekdays, invalid NAVs,
  invalid split ratios, and a start date after the latest NAV.
- If no smart purchase ever occurs, return a valid zero-investment result with
  zero return rather than dividing by zero.
- Provider/cache eligibility validation remains unchanged.
- No broad exception handling is added in the strategy core.

## Testing

Backend unit tests cover:

- strict previous-week signal use;
- current execution NAV cannot influence the current decision;
- exact drawdown tier boundaries;
- cash reuse without double-counting contributions;
- sell priority and full liquidation;
- cost-basis changes for buys, splits, dividends, and sales;
- daily portfolio, cash, and return series;
- zero-trade history;
- existing weekly strategy regression.

API tests cover both strategy names and unknown-strategy HTTP 400 behavior.

Frontend validation uses the existing TypeScript/Vite production build.

Real-data verification refreshes `010772`, runs both strategies from
`2020-12-30` with Friday and a base amount of `1000`, checks the smart strategy
has buy and sell events, verifies every signal date precedes its execution
date, and reports the actual return. The implementation is accepted only if
the measured smart-strategy cumulative return is at least 100% on that fixed
historical dataset; the result remains explicitly historical and in-sample.
