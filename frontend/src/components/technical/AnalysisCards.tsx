import React from 'react'
import { Card, Row, Col, Statistic, Tag } from 'antd'
import { ArrowDownOutlined } from '@ant-design/icons'
import type { AnalysisResponse } from '../../types/stock'

interface Props {
  data: AnalysisResponse
}

const fmt = (n: number) => n.toFixed(2)

const AnalysisCards: React.FC<Props> = ({ data }) => {
  const {
    current_price, p20, p50, p80,
    max_drawdown,
    drawdown_peak_date, drawdown_peak_price,
    drawdown_trough_date, drawdown_trough_price,
  } = data

  const priceTag = () => {
    if (current_price <= p20) return <Tag color="green">低位 (≤P20)</Tag>
    if (current_price >= p80) return <Tag color="red">高位 (≥P80)</Tag>
    return <Tag color="orange">中位</Tag>
  }

  return (
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      <Col xs={24} sm={8}>
        <Card
          size="small"
          style={{ background: '#161b22', border: '1px solid #30363d' }}
          title={<span style={{ color: '#8b949e' }}>当前价格</span>}
        >
          <Statistic
            value={current_price}
            precision={2}
            prefix="¥"
            valueStyle={{ color: '#e6edf3', fontSize: 24 }}
          />
          <div style={{ marginTop: 8 }}>{priceTag()}</div>
        </Card>
      </Col>

      <Col xs={24} sm={8}>
        <Card
          size="small"
          style={{ background: '#161b22', border: '1px solid #30363d' }}
          title={<span style={{ color: '#8b949e' }}>历史价格百分位（全量）</span>}
        >
          <Row gutter={8}>
            {([['P20', p20, '#26a69a'], ['P50', p50, '#ffd700'], ['P80', p80, '#ef5350']] as [string, number, string][]).map(
              ([label, val, color]) => (
                <Col key={label} span={8}>
                  <div style={{ color, fontWeight: 600, fontSize: 12 }}>{label}</div>
                  <div style={{ color: '#e6edf3', fontSize: 15 }}>¥{fmt(val)}</div>
                </Col>
              )
            )}
          </Row>
        </Card>
      </Col>

      <Col xs={24} sm={8}>
        <Card
          size="small"
          style={{ background: '#161b22', border: '1px solid #30363d' }}
          title={<span style={{ color: '#8b949e' }}>历史最大回撤（全量）</span>}
        >
          <Statistic
            value={Math.abs(max_drawdown) * 100}
            precision={2}
            suffix="%"
            prefix={<ArrowDownOutlined />}
            valueStyle={{ color: '#ef5350', fontSize: 20 }}
          />
          <div style={{ color: '#8b949e', fontSize: 11, marginTop: 4 }}>
            峰值 {drawdown_peak_date} ¥{fmt(drawdown_peak_price)}
          </div>
          <div style={{ color: '#8b949e', fontSize: 11 }}>
            谷底 {drawdown_trough_date} ¥{fmt(drawdown_trough_price)}
          </div>
        </Card>
      </Col>
    </Row>
  )
}

export default AnalysisCards
