import React from 'react'
import { Row, Col, Card, Statistic } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons'
import type { BacktestSummary } from '../../types/backtest'

interface Props { summary: BacktestSummary }

const pct = (n: number) => `${(n * 100).toFixed(2)}%`
const cny = (n: number) => `¥${n.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`

const BacktestSummaryCard: React.FC<Props> = ({ summary }) => {
  const { total_return, benchmark_return, excess_return, total_fees, final_assets, win_rate, profit_loss_ratio } = summary
  const pos = (n: number) => n >= 0

  const items: { title: string; value: string; color: string; icon: React.ReactNode }[] = [
    { title: '策略累计收益', value: pct(total_return), color: pos(total_return) ? '#ef5350' : '#26a69a', icon: pos(total_return) ? <ArrowUpOutlined /> : <ArrowDownOutlined /> },
    { title: '基准收益（买入持有）', value: pct(benchmark_return), color: pos(benchmark_return) ? '#ef5350' : '#26a69a', icon: pos(benchmark_return) ? <ArrowUpOutlined /> : <ArrowDownOutlined /> },
    { title: '超额收益', value: pct(excess_return), color: pos(excess_return) ? '#4caf50' : '#f44336', icon: pos(excess_return) ? <ArrowUpOutlined /> : <ArrowDownOutlined /> },
    { title: '累计手续费', value: cny(total_fees), color: '#fa8c16', icon: null },
    { title: '期末总资产', value: cny(final_assets), color: '#e6edf3', icon: null },
  ]

  if (win_rate !== null && win_rate !== undefined) {
    items.push({ title: '胜率', value: pct(win_rate), color: '#1890ff', icon: null })
  }
  if (profit_loss_ratio !== null && profit_loss_ratio !== undefined) {
    const value = profit_loss_ratio === -1 ? '∞' : profit_loss_ratio.toFixed(2)
    items.push({ title: '盈亏比', value, color: '#722ed1', icon: null })
  }

  return (
    <Row gutter={[16, 16]} style={{ marginTop: 16, marginBottom: 16 }}>
      {items.map(item => (
        <Col xs={24} sm={12} md={8} lg={5} key={item.title}>
          <Card size="small" style={{ background: '#161b22', border: '1px solid #30363d' }}>
            <Statistic
              title={<span style={{ color: '#8b949e', fontSize: 12 }}>{item.title}</span>}
              value={item.value}
              prefix={item.icon}
              valueStyle={{ color: item.color, fontSize: 18 }}
            />
          </Card>
        </Col>
      ))}
    </Row>
  )
}

export default BacktestSummaryCard
