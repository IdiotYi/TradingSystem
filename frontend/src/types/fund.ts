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
  strategy_name: string
  start_date: string
  weekday: number
  amount: number
}

export interface FundBacktestSummary {
  investment_count: number
  total_invested: number
  final_shares: number
  latest_nav: number
  current_value: number
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
  return_series: number[]
  events: FundEvent[]
}
