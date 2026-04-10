import axios from 'axios'
import type { AnalysisResponse } from '../types/stock'
import type { BacktestRequest, BacktestResponse } from '../types/backtest'

const client = axios.create({
  baseURL: '/api',
  timeout: 180000,
  headers: { 'Content-Type': 'application/json' },
})

export async function runAnalysis(stockCode: string): Promise<AnalysisResponse> {
  const { data } = await client.post<AnalysisResponse>('/analysis/run', { stock_code: stockCode })
  return data
}

export async function runBacktest(request: BacktestRequest): Promise<BacktestResponse> {
  const { data } = await client.post<BacktestResponse>('/backtest/run', request)
  return data
}
