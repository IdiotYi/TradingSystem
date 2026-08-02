import React, { useEffect } from 'react'
import { Alert, Button, DatePicker, Form, InputNumber, Select, Spin } from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'
import type {
  FundAnalysisResponse,
  FundBacktestRequest,
  FundStrategyName,
} from '../../types/fund'

const WEEKDAYS = [
  { value: 1, label: '周一' },
  { value: 2, label: '周二' },
  { value: 3, label: '周三' },
  { value: 4, label: '周四' },
  { value: 5, label: '周五' },
]

const STRATEGIES = [
  { value: 'weekly_investment', label: '每周定投' },
  { value: 'smart_dip_investment', label: '智能定投' },
] satisfies Array<{
  value: FundStrategyName
  label: string
}>

interface FundInvestmentFormValues {
  strategy_name: FundBacktestRequest['strategy_name']
  weekday: number
  amount: number
  start_date: Dayjs
}

interface Props {
  fundCode: string
  analysis: FundAnalysisResponse
  onRun: (req: FundBacktestRequest) => void
  loading: boolean
}

const FundInvestmentConfig: React.FC<Props> = ({ fundCode, analysis, onRun, loading }) => {
  const [form] = Form.useForm<FundInvestmentFormValues>()
  const strategyName = Form.useWatch('strategy_name', form) ?? 'weekly_investment'

  useEffect(() => {
    form.setFieldsValue({
      strategy_name: 'weekly_investment',
      weekday: 5,
      amount: 1000,
      start_date: dayjs(analysis.date_from),
    })
  }, [analysis.date_from, analysis.date_to, analysis.fund_code, form])

  const minDate = dayjs(analysis.date_from)
  const maxDate = dayjs(analysis.date_to)

  const handleFinish = (values: FundInvestmentFormValues) => {
    onRun({
      fund_code: fundCode,
      strategy_name: values.strategy_name,
      start_date: values.start_date.format('YYYY-MM-DD'),
      weekday: values.weekday,
      amount: Number(values.amount),
    })
  }

  return (
    <Form
      form={form}
      layout="inline"
      onFinish={handleFinish}
      initialValues={{
        strategy_name: 'weekly_investment',
        weekday: 5,
        amount: 1000,
        start_date: dayjs(analysis.date_from),
      }}
      style={{
        background: '#161b22',
        padding: 16,
        borderRadius: 8,
        border: '1px solid #30363d',
        marginTop: 16,
        marginBottom: 16,
      }}
    >
      <Form.Item
        label="策略"
        name="strategy_name"
        rules={[{ required: true, message: '请选择策略' }]}
      >
        <Select
          options={STRATEGIES}
          style={{ width: 140 }}
          disabled={loading}
        />
      </Form.Item>
      <Form.Item
        label={strategyName === 'smart_dip_investment' ? '决策日' : '定投日'}
        name="weekday"
        rules={[{ required: true, message: '请选择定投日' }]}
      >
        <Select options={WEEKDAYS} style={{ width: 100 }} disabled={loading} />
      </Form.Item>
      <Form.Item
        label="开始日期"
        name="start_date"
        rules={[{ required: true, message: '请选择开始日期' }]}
      >
        <DatePicker
          format="YYYY-MM-DD"
          allowClear={false}
          disabled={loading}
          disabledDate={current =>
            !!current
            && (current.isBefore(minDate, 'day') || current.isAfter(maxDate, 'day'))
          }
        />
      </Form.Item>
      <Form.Item
        label="每次金额 (元)"
        name="amount"
        rules={[
          { required: true, message: '请输入定投金额' },
          { type: 'number', min: 0.01, message: '定投金额必须大于 0 元' },
        ]}
      >
        <InputNumber
          min={0.01}
          step={0.01}
          precision={2}
          style={{ width: 140 }}
          disabled={loading}
        />
      </Form.Item>
      <Form.Item>
        <Button
          type="primary"
          htmlType="submit"
          icon={loading ? <Spin size="small" /> : <PlayCircleOutlined />}
          disabled={loading}
          style={{ background: '#238636', borderColor: '#238636' }}
        >
          {strategyName === 'smart_dip_investment' ? '运行智能回测' : '运行定投回测'}
        </Button>
      </Form.Item>
      {strategyName === 'smart_dip_investment' && (
        <div style={{ width: '100%', marginTop: 8 }}>
          <Alert
            type="info"
            showIcon
            message="信号严格滞后一周：回撤 40%/45%/50% 分层买入；持仓收益达到 90% 且周 RSI(14) ≥ 70 时清仓。历史回测不代表未来收益。"
          />
        </div>
      )}
    </Form>
  )
}

export default FundInvestmentConfig
