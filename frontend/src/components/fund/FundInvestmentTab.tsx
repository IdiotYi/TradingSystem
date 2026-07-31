import React, { useEffect, useRef, useState } from 'react'
import { Card, Descriptions, Empty, Spin, Tag, Typography, message } from 'antd'
import { runFundBacktest } from '../../services/api'
import type {
  FundAnalysisResponse,
  FundBacktestRequest,
  FundBacktestResponse,
} from '../../types/fund'
import FundEventTable from './FundEventTable'
import FundInvestmentChart from './FundInvestmentChart'
import FundInvestmentConfig from './FundInvestmentConfig'
import FundInvestmentSummary from './FundInvestmentSummary'

interface Props {
  fundCode: string
  analysis: FundAnalysisResponse | null
  analysisGeneration: number
  dataGeneration: number
}

const FundInvestmentTab: React.FC<Props> = ({
  fundCode,
  analysis,
  analysisGeneration,
  dataGeneration,
}) => {
  const [result, setResult] = useState<FundBacktestResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const requestIdRef = useRef(0)
  const latestFundCodeRef = useRef(fundCode)

  useEffect(() => {
    latestFundCodeRef.current = analysis?.fund_code ?? fundCode
    requestIdRef.current += 1
    setResult(null)
    setLoading(false)
  }, [analysis?.fund_code, analysisGeneration, dataGeneration, fundCode])

  const handleRun = async (req: FundBacktestRequest) => {
    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId
    setLoading(true)
    setResult(null)
    try {
      const data = await runFundBacktest(req)
      if (requestId !== requestIdRef.current || req.fund_code !== latestFundCodeRef.current) {
        return
      }
      setResult(data)
    } catch (err: any) {
      if (requestId !== requestIdRef.current || req.fund_code !== latestFundCodeRef.current) {
        return
      }
      const detail = err?.response?.data?.detail
      const msg = typeof detail === 'string'
        ? detail
        : detail
          ? JSON.stringify(detail)
          : `基金定投回测失败: ${err.message}`
      message.error(msg)
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false)
      }
    }
  }

  if (!analysis || analysis.fund_code !== fundCode) {
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

      <FundInvestmentConfig
        fundCode={analysis.fund_code}
        analysis={analysis}
        onRun={handleRun}
        loading={loading}
      />

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ color: '#8b949e', marginTop: 16 }}>
            正在运行基金定投回测…（计算由后端完成，请稍候）
          </div>
        </div>
      )}

      {!loading && !result && (
        <Empty
          description={<span style={{ color: '#8b949e' }}>配置参数后点击「运行定投回测」</span>}
          style={{ marginTop: 48 }}
        />
      )}

      {!loading && result && (
        <>
          <FundInvestmentSummary summary={result.summary} />
          <FundInvestmentChart data={result} />
          <div style={{ marginTop: 24 }}>
            <div style={{ color: '#8b949e', marginBottom: 8, fontWeight: 600 }}>事件明细</div>
            <FundEventTable events={result.events} />
          </div>
        </>
      )}
    </div>
  )
}

export default FundInvestmentTab
