export type FundStrategyName =
  | 'weekly_investment'
  | 'smart_dip_investment'

export type FundEvent =
  | {
      event_type: 'investment'
      date: string
      scheduled_date: string
      advanced: boolean
      nav: number
      amount: number
      acquired_shares: number
      shares_after: number
    }
  | {
      event_type: 'dividend'
      date: string
      dividend_per_share: number
      dividend_cash: number
      acquired_shares: number
      shares_after: number
    }
  | {
      event_type: 'split'
      date: string
      split_type: string
      split_ratio: number
      shares_before: number
      shares_after: number
    }
  | {
      event_type: 'smart_buy'
      date: string
      scheduled_date: string
      advanced: boolean
      signal_date: string
      nav: number
      drawdown: number
      rsi: number | null
      multiplier: number
      contribution_amount: number
      reused_cash: number
      purchase_amount: number
      acquired_shares: number
      shares_after: number
      cash_balance_after: number
    }
  | {
      event_type: 'smart_sell'
      date: string
      scheduled_date: string
      advanced: boolean
      signal_date: string
      nav: number
      position_return: number
      rsi: number
      shares_before: number
      sold_shares: number
      proceeds: number
      realized_profit: number
      shares_after: number
      cash_balance_after: number
    }

export interface FundAnalysisResponse {
  success: boolean
  fund_code: string
  fund_name: string
  fund_type: string
  date_from: string
  date_to: string
  rows: number
  latest_nav: number
}

export interface FundRefreshResponse {
  fund_code: string
  fund_name: string
  fund_type: string
  rows: number
  date_from: string
  date_to: string
}

export interface FundBacktestRequest {
  fund_code: string
  strategy_name: FundStrategyName
  start_date: string
  weekday: number
  amount: number
}

export interface FundBacktestSummary {
  investment_count: number
  decision_count: number
  buy_count: number
  sell_count: number
  total_invested: number
  final_shares: number
  latest_nav: number
  fund_value: number
  cash_balance: number
  current_value: number
  total_sale_proceeds: number
  realized_profit: number
  total_profit: number
  total_return: number
}

export interface FundBacktestResponse {
  success: boolean
  fund_code: string
  summary: FundBacktestSummary
  dates: string[]
  total_invested_series: number[]
  asset_value_series: number[]
  cash_balance_series: number[]
  return_series: number[]
  signal_index_series: number[]
  events: FundEvent[]
}
