import React from 'react'
import { Spin, Empty, Typography } from 'antd'
import type { AnalysisResponse } from '../../types/stock'
import WMAChart from './WMAChart'

interface Props {
  data: AnalysisResponse | null
  loading: boolean
}

const IndicatorTestTab: React.FC<Props> = ({ data, loading }) => {
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!data) {
    return (
      <Empty
        description={<span style={{ color: '#8b949e' }}>请在顶部输入股票代码并点击分析</span>}
        style={{ marginTop: 80 }}
      />
    )
  }

  return (
    <div>
      <Typography.Title level={5} style={{ color: '#8b949e', marginBottom: 12 }}>
        {data.stock_code} · 韦氏移动平均线 WMA(5/20/60) · 最近 250 个交易日
      </Typography.Title>
      <WMAChart data={data} />
    </div>
  )
}

export default IndicatorTestTab
