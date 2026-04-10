export interface AnalysisResponse {
  success: boolean
  stock_code: string
  dates: string[]
  open: (number | null)[]
  high: (number | null)[]
  low: (number | null)[]
  close: (number | null)[]
  volume: (number | null)[]
  ma5: (number | null)[]
  ma20: (number | null)[]
  ma60: (number | null)[]
  supertrend: (number | null)[]
  supertrend_direction: (number | null)[]
  current_price: number
  p20: number
  p50: number
  p80: number
  max_drawdown: number
  drawdown_peak_date: string
  drawdown_trough_date: string
  drawdown_peak_price: number
  drawdown_trough_price: number
}
