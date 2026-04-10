import React from 'react'
import {
  Form, DatePicker, InputNumber, Button, Collapse, Row, Col, Spin,
} from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import type { BacktestRequest, StrategyParams } from '../../types/backtest'
import { DEFAULT_STRATEGY_PARAMS } from '../../types/backtest'

interface Props {
  stockCode: string
  onRun: (req: BacktestRequest) => void
  loading: boolean
}

const BacktestConfig: React.FC<Props> = ({ stockCode, onRun, loading }) => {
  const [form] = Form.useForm()

  const handleFinish = (values: any) => {
    const req: BacktestRequest = {
      stock_code: stockCode,
      start_date: values.start_date.format('YYYY-MM-DD'),
      end_date: values.end_date.format('YYYY-MM-DD'),
      initial_cash: values.initial_cash,
      strategy_params: {
        score_rising_days: values.score_rising_days,
        oversold_std_mult: values.oversold_std_mult,
        take_profit_pct: values.take_profit_pct / 100,
        take_profit_std_mult: values.take_profit_std_mult,
        stop_loss_pct: values.stop_loss_pct / 100,
        add_position_pct: values.add_position_pct / 100,
        half_position_ratio: values.half_position_ratio / 100,
      },
    }
    onRun(req)
  }

  const p = DEFAULT_STRATEGY_PARAMS

  return (
    <Form
      form={form}
      layout="inline"
      onFinish={handleFinish}
      initialValues={{
        start_date: dayjs('2023-01-01'),
        end_date: dayjs(),
        initial_cash: 100000,
        score_rising_days: p.score_rising_days,
        oversold_std_mult: p.oversold_std_mult,
        take_profit_pct: p.take_profit_pct * 100,
        take_profit_std_mult: p.take_profit_std_mult,
        stop_loss_pct: p.stop_loss_pct * 100,
        add_position_pct: p.add_position_pct * 100,
        half_position_ratio: p.half_position_ratio * 100,
      }}
      style={{ background: '#161b22', padding: 16, borderRadius: 8, border: '1px solid #30363d', marginBottom: 16 }}
    >
      <Form.Item label="开始日期" name="start_date">
        <DatePicker format="YYYY-MM-DD" />
      </Form.Item>
      <Form.Item label="结束日期" name="end_date">
        <DatePicker format="YYYY-MM-DD" />
      </Form.Item>
      <Form.Item label="初始资金 (元)" name="initial_cash">
        <InputNumber min={10000} step={10000} style={{ width: 130 }} />
      </Form.Item>

      <Collapse
        ghost
        style={{ width: '100%', marginTop: 8 }}
        items={[{
          key: '1',
          label: <span style={{ color: '#8b949e' }}>策略参数 ▾</span>,
          children: (
            <Row gutter={[16, 0]}>
              <Col>
                <Form.Item label="score连升天数" name="score_rising_days">
                  <InputNumber min={1} max={10} style={{ width: 80 }} />
                </Form.Item>
              </Col>
              <Col>
                <Form.Item label="超卖倍数 (σ)" name="oversold_std_mult">
                  <InputNumber min={0.5} max={5} step={0.5} style={{ width: 80 }} />
                </Form.Item>
              </Col>
              <Col>
                <Form.Item label="止盈 (%)" name="take_profit_pct">
                  <InputNumber min={1} max={100} style={{ width: 80 }} />
                </Form.Item>
              </Col>
              <Col>
                <Form.Item label="score止盈倍数" name="take_profit_std_mult">
                  <InputNumber min={0.5} max={5} step={0.5} style={{ width: 80 }} />
                </Form.Item>
              </Col>
              <Col>
                <Form.Item label="止损 (%)" name="stop_loss_pct">
                  <InputNumber min={1} max={50} style={{ width: 80 }} />
                </Form.Item>
              </Col>
              <Col>
                <Form.Item label="加仓触发 (%)" name="add_position_pct">
                  <InputNumber min={1} max={50} style={{ width: 80 }} />
                </Form.Item>
              </Col>
              <Col>
                <Form.Item label="初始仓位 (%)" name="half_position_ratio">
                  <InputNumber min={10} max={100} style={{ width: 80 }} />
                </Form.Item>
              </Col>
            </Row>
          ),
        }]}
      />

      <Form.Item style={{ marginTop: 8 }}>
        <Button
          type="primary"
          htmlType="submit"
          icon={loading ? <Spin size="small" /> : <PlayCircleOutlined />}
          disabled={loading}
          style={{ background: '#238636', borderColor: '#238636' }}
        >
          运行回测
        </Button>
      </Form.Item>
    </Form>
  )
}

export default BacktestConfig
