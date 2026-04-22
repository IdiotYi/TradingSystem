import React, { useState } from 'react'
import { message, Spin, Empty } from 'antd'
import type { BacktestRequest, BacktestResponse } from '../../types/backtest'
import { runBacktest } from '../../services/api'
import BacktestConfig from './BacktestConfig'
import BacktestChart from './BacktestChart'
import BacktestSummaryCard from './BacktestSummary'
import TradeTable from './TradeTable'

interface Props {
  stockCode: string
}

const BacktestTab: React.FC<Props> = ({ stockCode }) => {
  const [result, setResult] = useState<BacktestResponse | null>(null)
  const [loading, setLoading] = useState(false)

  const handleRun = async (req: BacktestRequest) => {
    setLoading(true)
    try {
      const data = await runBacktest(req)
      setResult(data)
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      const msg = typeof detail === 'string'
        ? detail
        : detail
          ? JSON.stringify(detail)
          : `回测失败: ${err.message}`
      message.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <BacktestConfig stockCode={stockCode} onRun={handleRun} loading={loading} />

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ color: '#8b949e', marginTop: 16 }}>
            正在计算三因子分数并运行回测…（首次运行较慢，请耐心等待）
          </div>
        </div>
      )}

      {!loading && !result && (
        <Empty
          description={<span style={{ color: '#8b949e' }}>配置参数后点击「运行回测」</span>}
          style={{ marginTop: 60 }}
        />
      )}

      {!loading && result && (
        <>
          <BacktestSummaryCard summary={result.summary} />
          <BacktestChart data={result} />
          <div style={{ marginTop: 24 }}>
            <div style={{ color: '#8b949e', marginBottom: 8, fontWeight: 600 }}>交易明细</div>
            <TradeTable trades={result.trades} />
          </div>
        </>
      )}
    </div>
  )
}

export default BacktestTab
