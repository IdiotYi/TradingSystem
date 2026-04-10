import React from 'react'
import { Spin, Empty, Typography } from 'antd'
import type { AnalysisResponse } from '../../types/stock'
import AnalysisCards from './AnalysisCards'
import KLineChart from './KLineChart'

interface Props {
  data: AnalysisResponse | null
  loading: boolean
}

const TechnicalTab: React.FC<Props> = ({ data, loading }) => {
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" />
        <div style={{ color: '#8b949e', marginTop: 16 }}>
          正在加载数据并计算指标…（首次加载需下载历史数据，请稍候）
        </div>
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
        {data.stock_code} · 最新 ¥{data.current_price.toFixed(2)}
      </Typography.Title>
      <AnalysisCards data={data} />
      <KLineChart data={data} />
    </div>
  )
}

export default TechnicalTab
