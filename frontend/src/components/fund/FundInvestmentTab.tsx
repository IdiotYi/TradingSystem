import React from 'react'
import { Card, Descriptions, Empty, Tag, Typography } from 'antd'
import type { FundAnalysisResponse } from '../../types/fund'

interface Props {
  fundCode: string
  analysis: FundAnalysisResponse | null
}

const FundInvestmentTab: React.FC<Props> = ({ fundCode, analysis }) => {
  if (!analysis) {
    return (
      <Empty
        description={
          <span style={{ color: '#8b949e' }}>
            {fundCode
              ? `基金 ${fundCode} 暂无分析结果，请重新点击分析`
              : '请在顶部输入基金代码并点击分析'}
          </span>
        }
        style={{ marginTop: 80 }}
      />
    )
  }

  return (
    <div>
      <Typography.Title level={5} style={{ color: '#8b949e', marginBottom: 12 }}>
        {analysis.fund_code} · {analysis.fund_name}
      </Typography.Title>
      <Card
        size="small"
        title="基金基础信息"
        style={{ background: '#161b22', border: '1px solid #30363d' }}
      >
        <Descriptions
          bordered
          column={2}
          size="small"
          styles={{
            label: { color: '#8b949e' },
            content: { color: '#e6edf3' },
          }}
        >
          <Descriptions.Item label="基金代码">{analysis.fund_code}</Descriptions.Item>
          <Descriptions.Item label="基金类型">
            <Tag color="blue">{analysis.fund_type}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="最新净值">
            ¥{analysis.latest_nav.toFixed(4)}
          </Descriptions.Item>
          <Descriptions.Item label="覆盖记录">{analysis.rows.toLocaleString('zh-CN')} 条</Descriptions.Item>
          <Descriptions.Item label="起始日期">{analysis.date_from}</Descriptions.Item>
          <Descriptions.Item label="结束日期">{analysis.date_to}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Empty
        description={<span style={{ color: '#8b949e' }}>定投策略配置与结果展示将在后续任务中补齐</span>}
        style={{ marginTop: 48 }}
      />
    </div>
  )
}

export default FundInvestmentTab
