import axios from 'axios'
import type { AnalysisResponse } from '../types/stock'
import type { BacktestRequest, BacktestResponse } from '../types/backtest'
import type { ChanRequest, ChanResponse } from '../types/chan'
import type {
  FundAnalysisResponse,
  FundBacktestRequest,
  FundBacktestResponse,
  FundRefreshResponse,
} from '../types/fund'

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

export async function refreshData(stockCode: string): Promise<{ stock_code: string; rows: number; date_from: string; date_to: string }> {
  const { data } = await client.post('/data/refresh', { stock_code: stockCode })
  return data
}

export async function runChanAnalysis(request: ChanRequest): Promise<ChanResponse> {
  const { data } = await client.post<ChanResponse>('/chan/analyze', request)
  return data
}

export async function analyseFund(fundCode: string): Promise<FundAnalysisResponse> {
  const { data } = await client.post<FundAnalysisResponse>('/fund/analysis', {
    fund_code: fundCode,
  })
  return data
}

export async function refreshFund(fundCode: string): Promise<FundRefreshResponse> {
  const { data } = await client.post<FundRefreshResponse>('/fund/refresh', {
    fund_code: fundCode,
  })
  return data
}

export async function runFundBacktest(
  request: FundBacktestRequest,
): Promise<FundBacktestResponse> {
  const { data } = await client.post<FundBacktestResponse>('/fund/backtest', request)
  return data
}
