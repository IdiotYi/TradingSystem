export interface ChanPen {
  start_idx: number
  start_date: string
  start_price: number
  end_idx: number
  end_date: string
  end_price: number
  direction: 'up' | 'down'
}

export type ChanPeriod = 'daily' | '30' | '5'

export interface ChanRequest {
  stock_code: string
  period: ChanPeriod
  start_date: string
  end_date?: string
}

export interface ChanResponse {
  success: boolean
  stock_code: string
  period: ChanPeriod
  coverage_from: string
  coverage_to: string
  response_from: string
  response_to: string
  data_source: string
  target_coverage_met: boolean
  dates: string[]
  open: number[]
  close: number[]
  high: number[]
  low: number[]
  pens: ChanPen[]
}

export interface ChanRefreshResponse {
  stock_code: string
  period: Exclude<ChanPeriod, 'daily'>
  rows: number
  coverage_from: string
  coverage_to: string
  data_source: string
  target_coverage_met: boolean
}
