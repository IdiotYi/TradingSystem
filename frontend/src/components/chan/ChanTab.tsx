import React, { useEffect, useState } from 'react'
import { Form, DatePicker, Button, message, Spin, Empty } from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'
import type { ChanResponse } from '../../types/chan'
import { runChanAnalysis } from '../../services/api'
import ChanChart from './ChanChart'

interface Props {
  stockCode: string
}

const { RangePicker } = DatePicker

const ChanTab: React.FC<Props> = ({ stockCode }) => {
  const [form] = Form.useForm()
  const [result, setResult] = useState<ChanResponse | null>(null)
  const [loading, setLoading] = useState(false)

  const runAnalysis = async (startDate: string, endDate: string) => {
    if (!stockCode) return
    setLoading(true)
    try {
      const data = await runChanAnalysis({
        stock_code: stockCode,
        start_date: startDate,
        end_date: endDate,
      })
      setResult(data)
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      const msg = typeof detail === 'string'
        ? detail
        : detail
          ? JSON.stringify(detail)
          : `缠论分析失败: ${err.message}`
      message.error(msg)
    } finally {
      setLoading(false)
    }
  }

  // Auto-run when stockCode changes.
  useEffect(() => {
    if (!stockCode) return
    const range = form.getFieldValue('range') as [Dayjs, Dayjs] | undefined
    const start = range?.[0]?.format('YYYY-MM-DD') ?? '2023-01-01'
    const end = range?.[1]?.format('YYYY-MM-DD') ?? dayjs().format('YYYY-MM-DD')
    runAnalysis(start, end)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stockCode])

  const handleFinish = (values: any) => {
    const [start, end] = values.range as [Dayjs, Dayjs]
    runAnalysis(start.format('YYYY-MM-DD'), end.format('YYYY-MM-DD'))
  }

  if (!stockCode) {
    return (
      <Empty
        description={<span style={{ color: '#8b949e' }}>请在顶部输入股票代码并点击分析</span>}
        style={{ marginTop: 80 }}
      />
    )
  }

  return (
    <div>
      <Form
        form={form}
        layout="inline"
        onFinish={handleFinish}
        initialValues={{
          range: [dayjs('2023-01-01'), dayjs()],
        }}
        style={{
          background: '#161b22', padding: 16, borderRadius: 8,
          border: '1px solid #30363d', marginBottom: 16,
        }}
      >
        <Form.Item label="日期范围" name="range">
          <RangePicker format="YYYY-MM-DD" />
        </Form.Item>
        <Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            icon={loading ? <Spin size="small" /> : <PlayCircleOutlined />}
            disabled={loading}
            style={{ background: '#238636', borderColor: '#238636' }}
          >
            运行分析
          </Button>
        </Form.Item>
      </Form>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ color: '#8b949e', marginTop: 16 }}>正在运行缠论分析…</div>
        </div>
      )}

      {!loading && !result && (
        <Empty
          description={<span style={{ color: '#8b949e' }}>选择日期范围后点击「运行分析」</span>}
          style={{ marginTop: 60 }}
        />
      )}

      {!loading && result && (
        <>
          <div style={{ color: '#8b949e', marginBottom: 8 }}>
            股票 <b style={{ color: '#e6edf3' }}>{result.stock_code}</b> ·
            数据点 <b style={{ color: '#e6edf3' }}>{result.dates.length}</b> ·
            笔数 <b style={{ color: '#e6edf3' }}>{result.pens.length}</b>
          </div>
          <ChanChart data={result} />
        </>
      )}
    </div>
  )
}

export default ChanTab
