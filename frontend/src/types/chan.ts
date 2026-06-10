export interface ChanPen {
  start_idx: number
  start_date: string
  start_price: number
  end_idx: number
  end_date: string
  end_price: number
  direction: 'up' | 'down'
}

export interface ChanRequest {
  stock_code: string
  start_date: string         // YYYY-MM-DD
  end_date?: string
}

export interface ChanResponse {
  success: boolean
  stock_code: string
  dates: string[]
  open: number[]
  close: number[]
  high: number[]
  low: number[]
  pens: ChanPen[]
}
