export interface StrategyParams {
  score_rising_days: number
  oversold_std_mult: number
  take_profit_pct: number
  take_profit_std_mult: number
  stop_loss_pct: number
  add_position_pct: number
  half_position_ratio: number
  // 三因子计算参数
  bias_n: number
  momentum_day: number
  slope_n: number
  efficiency_n: number
  zscore_window: number
}

export const DEFAULT_STRATEGY_PARAMS: StrategyParams = {
  score_rising_days: 3,
  oversold_std_mult: 2.0,
  take_profit_pct: 0.15,
  take_profit_std_mult: 1.5,
  stop_loss_pct: 0.05,
  add_position_pct: 0.05,
  half_position_ratio: 0.5,
  bias_n: 20,
  momentum_day: 20,
  slope_n: 20,
  efficiency_n: 20,
  zscore_window: 60,
}

export interface Trade {
  date: string
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
}

export interface BacktestResponse {
  success: boolean
  dates: string[]
  open: (number | null)[]
  high: (number | null)[]
  low: (number | null)[]
  close: (number | null)[]
  ma5: (number | null)[]
  ma20: (number | null)[]
  ma60: (number | null)[]
  supertrend: (number | null)[]
  supertrend_direction: (number | null)[]
  score: (number | null)[]
  score_mean: (number | null)[]
  score_std: (number | null)[]
  trades: Trade[]
  summary: BacktestSummary
}

export interface BacktestRequest {
  stock_code: string
  start_date: string
  end_date: string
  initial_cash: number
  strategy_name: string
  strategy_params: StrategyParams
}
