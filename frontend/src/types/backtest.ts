export type StockStrategyName =
  | 'three_factors'
  | 'three_factors_v2'
  | 'supertrend_ma'
  | 'supertrend_wma'
  | 'buy_and_hold'
  | 'trend_pullback_maw_macd'
  | 'trend_following_maw_macd'

export interface StrategyParams {
  score_rising_days: number
  oversold_std_mult: number
  take_profit_pct: number
  take_profit_std_mult: number
  stop_loss_pct: number
  add_position_pct: number
  half_position_ratio: number
  bias_n: number
  momentum_day: number
  slope_n: number
  efficiency_n: number
  zscore_window: number
  recent_high_window: number
  maw_short_period: number
  maw_medium_period: number
  maw_long_period: number
  maw_slope_days: number
  min_rebalance_delta: number
  min_buy_interval_days: number
}

export const DEFAULT_STRATEGY_PARAMS: StrategyParams = {
  score_rising_days: 3, oversold_std_mult: 2.0, take_profit_pct: 0.15,
  take_profit_std_mult: 1.5, stop_loss_pct: 0.05, add_position_pct: 0.05,
  half_position_ratio: 0.5, bias_n: 20, momentum_day: 20, slope_n: 20,
  efficiency_n: 20, zscore_window: 60, recent_high_window: 25,
  maw_short_period: 20, maw_medium_period: 60, maw_long_period: 120,
  maw_slope_days: 20, min_rebalance_delta: 0.10, min_buy_interval_days: 5,
}

export interface Trade {
  date: string
  signal_date?: string
  direction: '买入' | '卖出'
  reason: string
  price: number
  shares: number
  amount: number
  transfer_fee: number
  commission: number
  stamp_tax: number | null
  total_fee: number
  pnl: number | null
  remaining_cash: number
}

export interface BacktestSummary {
  initial_cash: number
  final_assets: number
  total_return: number
  total_fees: number
  benchmark_return: number
  excess_return: number
  final_shares: number
  final_cash: number
  win_rate: number | null
  profit_loss_ratio: number | null
  max_position_ratio: number
  average_position_ratio: number
  rebalance_count: number
}

export interface BacktestResponse {
  success: boolean
  strategy_name: StockStrategyName
  dates: string[]
  open: (number | null)[]
  high: (number | null)[]
  low: (number | null)[]
  close: (number | null)[]
  ma5: (number | null)[]
  ma20: (number | null)[]
  ma60: (number | null)[]
  maw20: (number | null)[]
  maw60: (number | null)[]
  maw120: (number | null)[]
  kama: (number | null)[]
  supertrend: (number | null)[]
  supertrend_direction: (number | null)[]
  score: (number | null)[]
  score_mean: (number | null)[]
  score_std: (number | null)[]
  macd_dif: (number | null)[]
  macd_dea: (number | null)[]
  macd_histogram: (number | null)[]
  target_position: (number | null)[]
  position_ratio: (number | null)[]
  trades: Trade[]
  summary: BacktestSummary
}

export interface BacktestRequest {
  stock_code: string
  start_date: string
  end_date: string
  initial_cash: number
  strategy_name: StockStrategyName
  strategy_params: StrategyParams
}
