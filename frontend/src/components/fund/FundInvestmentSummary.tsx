import React from 'react'
import { Card, Col, Row, Statistic } from 'antd'
import { ArrowDownOutlined, ArrowUpOutlined } from '@ant-design/icons'
import type { FundBacktestSummary } from '../../types/fund'

interface Props {
  summary: FundBacktestSummary
}

const cny = (n: number) =>
  `¥${n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const pct = (n: number) => `${(n * 100).toFixed(2)}%`
const shares = (n: number) =>
  n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 4 })

const FundInvestmentSummary: React.FC<Props> = ({ summary }) => {
  const positive = (value: number) => value >= 0

  const items = [
    { title: '累计投入', value: cny(summary.total_invested), color: '#faad14' },
    { title: '组合价值', value: cny(summary.current_value), color: '#58a6ff' },
    {
      title: '累计盈亏',
      value: cny(summary.total_profit),
      color: positive(summary.total_profit) ? '#ef5350' : '#26a69a',
      icon: positive(summary.total_profit) ? <ArrowUpOutlined /> : <ArrowDownOutlined />,
    },
    {
      title: '累计收益率',
      value: pct(summary.total_return),
      color: positive(summary.total_return) ? '#ef5350' : '#26a69a',
      icon: positive(summary.total_return) ? <ArrowUpOutlined /> : <ArrowDownOutlined />,
    },
    { title: '买入次数', value: summary.buy_count.toLocaleString('zh-CN'), color: '#1890ff' },
    { title: '卖出次数', value: summary.sell_count.toLocaleString('zh-CN'), color: '#52c41a' },
    { title: '现金余额', value: cny(summary.cash_balance), color: '#a371f7' },
    { title: '期末份额', value: shares(summary.final_shares), color: '#e6edf3' },
  ]

  return (
    <Row gutter={[16, 16]} style={{ marginTop: 16, marginBottom: 16 }}>
      {items.map(item => (
        <Col xs={24} sm={12} md={8} xl={6} key={item.title}>
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

export default FundInvestmentSummary
