import React, { useEffect, useRef, useState } from 'react'
import { Alert, Form, DatePicker, Button, message, Select, Spin, Empty } from 'antd'
import { PlayCircleOutlined, SyncOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'
import type { ChanPeriod, ChanResponse } from '../../types/chan'
import { refreshChanData, runChanAnalysis } from '../../services/api'
import ChanChart from './ChanChart'

interface Props {
  stockCode: string
}

const { RangePicker } = DatePicker
const PERIOD_OPTIONS: Array<{ value: ChanPeriod; label: string }> = [
  { value: 'daily', label: '日线' },
  { value: '30', label: '30分钟' },
  { value: '5', label: '5分钟' },
]

const defaultRange = (value: ChanPeriod): [Dayjs, Dayjs] => {
  const end = dayjs()
  if (value === '5') return [end.subtract(3, 'month'), end]
  if (value === '30') return [end.subtract(1, 'year'), end]
  return [dayjs('2023-01-01'), end]
}

function getErrorMessage(err: any, fallback: string) {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') {
    return detail
  }
  if (detail) {
    return JSON.stringify(detail)
  }
  return `${fallback}: ${err.message}`
}

function getPeriodLabel(period: ChanPeriod) {
  return PERIOD_OPTIONS.find(option => option.value === period)?.label ?? period
}

const ChanTab: React.FC<Props> = ({ stockCode }) => {
  const [form] = Form.useForm()
  const [result, setResult] = useState<ChanResponse | null>(null)
  const [period, setPeriod] = useState<ChanPeriod>('daily')
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const latestActionRef = useRef(0)
  const latestAnalyzeRequestRef = useRef(0)
  const latestRefreshRequestRef = useRef(0)
  const latestStockCodeRef = useRef(stockCode)
  const latestPeriodRef = useRef<ChanPeriod>('daily')

  const beginAction = () => {
    latestActionRef.current += 1
    return latestActionRef.current
  }

  const isLatestAction = (actionId: number, nextStockCode: string, nextPeriod: ChanPeriod) =>
    actionId === latestActionRef.current
    && nextStockCode === latestStockCodeRef.current
    && nextPeriod === latestPeriodRef.current

  const runAnalysis = async (
    nextStockCode: string,
    nextPeriod: ChanPeriod,
    startDate: string,
    endDate: string,
    actionId: number,
  ) => {
    if (!nextStockCode) return
    const requestId = latestAnalyzeRequestRef.current + 1
    latestAnalyzeRequestRef.current = requestId
    setLoading(true)
    setResult(null)
    try {
      const data = await runChanAnalysis({
        stock_code: nextStockCode,
        period: nextPeriod,
        start_date: startDate,
        end_date: endDate,
      })
      if (!isLatestAction(actionId, nextStockCode, nextPeriod)) {
        return
      }
      setResult(data)
    } catch (err: any) {
      if (!isLatestAction(actionId, nextStockCode, nextPeriod)) {
        return
      }
      message.error(getErrorMessage(err, '缠论分析失败'))
    } finally {
      if (requestId === latestAnalyzeRequestRef.current) {
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    latestStockCodeRef.current = stockCode
  }, [stockCode])

  useEffect(() => {
    latestPeriodRef.current = period
  }, [period])

  useEffect(() => {
    if (!stockCode) {
      setResult(null)
      setLoading(false)
      setRefreshing(false)
      return
    }

    const actionId = beginAction()
    const range = form.getFieldValue('range') as [Dayjs, Dayjs] | undefined
    const [startValue, endValue] = range ?? defaultRange(period)
    void runAnalysis(
      stockCode,
      period,
      startValue.format('YYYY-MM-DD'),
      endValue.format('YYYY-MM-DD'),
      actionId,
    )
  }, [form, stockCode])

  const handleFinish = (values: any) => {
    const [start, end] = values.range as [Dayjs, Dayjs]
    const actionId = beginAction()
    void runAnalysis(
      stockCode,
      period,
      start.format('YYYY-MM-DD'),
      end.format('YYYY-MM-DD'),
      actionId,
    )
  }

  const handlePeriodChange = (value: ChanPeriod) => {
    setPeriod(value)
    const range = defaultRange(value)
    form.setFieldsValue({ range })
    if (!stockCode) {
      setResult(null)
      return
    }

    const actionId = beginAction()
    void runAnalysis(
      stockCode,
      value,
      range[0].format('YYYY-MM-DD'),
      range[1].format('YYYY-MM-DD'),
      actionId,
    )
  }

  const handleRefresh = async () => {
    if (!stockCode || period === 'daily') return

    const actionId = beginAction()
    const requestId = latestRefreshRequestRef.current + 1
    latestRefreshRequestRef.current = requestId
    setRefreshing(true)

    const range = (form.getFieldValue('range') as [Dayjs, Dayjs] | undefined) ?? defaultRange(period)

    try {
      const refreshResult = await refreshChanData(stockCode, period)
      if (!isLatestAction(actionId, stockCode, period)) {
        return
      }

      message.success(
        `${refreshResult.stock_code} ${getPeriodLabel(refreshResult.period)}数据已更新：`
        + `${refreshResult.rows} 条，${refreshResult.coverage_from} ~ ${refreshResult.coverage_to}`,
      )

      await runAnalysis(
        stockCode,
        period,
        range[0].format('YYYY-MM-DD'),
        range[1].format('YYYY-MM-DD'),
        actionId,
      )
    } catch (err: any) {
      if (!isLatestAction(actionId, stockCode, period)) {
        return
      }
      message.error(getErrorMessage(err, '分钟数据刷新失败'))
    } finally {
      if (requestId === latestRefreshRequestRef.current) {
        setRefreshing(false)
      }
    }
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
          range: defaultRange('daily'),
        }}
        style={{
          background: '#161b22', padding: 16, borderRadius: 8,
          border: '1px solid #30363d', marginBottom: 16,
        }}
      >
        <Form.Item label="周期">
          <Select
            value={period}
            options={PERIOD_OPTIONS}
            onChange={handlePeriodChange}
            style={{ width: 120 }}
            disabled={loading || refreshing}
          />
        </Form.Item>
        <Form.Item label="日期范围" name="range">
          <RangePicker format="YYYY-MM-DD" disabled={loading || refreshing} />
        </Form.Item>
        <Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            icon={loading ? <Spin size="small" /> : <PlayCircleOutlined />}
            disabled={loading || refreshing}
            style={{ background: '#238636', borderColor: '#238636' }}
          >
            运行分析
          </Button>
        </Form.Item>
        {period !== 'daily' && (
          <Form.Item>
            <Button
              icon={refreshing ? <Spin size="small" /> : <SyncOutlined />}
              onClick={handleRefresh}
              disabled={loading || refreshing}
              style={{ borderColor: '#30363d', color: '#8b949e' }}
            >
              刷新分钟数据
            </Button>
          </Form.Item>
        )}
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
          {result.period !== 'daily' && !result.target_coverage_met && (
            <Alert
              type="warning"
              showIcon
              message={`当前数据仅覆盖 ${result.coverage_from} ~ ${result.coverage_to}`}
              style={{ marginBottom: 12 }}
            />
          )}
          <div style={{ color: '#8b949e', marginBottom: 8 }}>
            股票 <b style={{ color: '#e6edf3' }}>{result.stock_code}</b> ·
            周期 <b style={{ color: '#e6edf3' }}>{getPeriodLabel(result.period)}</b> ·
            数据源 <b style={{ color: '#e6edf3' }}>{result.data_source}</b> ·
            实际覆盖 <b style={{ color: '#e6edf3' }}>{result.coverage_from} ~ {result.coverage_to}</b> ·
            响应范围 <b style={{ color: '#e6edf3' }}>{result.response_from} ~ {result.response_to}</b> ·
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
