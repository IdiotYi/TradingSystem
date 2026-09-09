import React, { useState } from 'react'
import { Alert, Form, DatePicker, InputNumber, Button, Collapse, Row, Col, Spin, Select } from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import type { BacktestRequest, StockStrategyName, StrategyParams } from '../../types/backtest'
import { DEFAULT_STRATEGY_PARAMS } from '../../types/backtest'

interface Props { stockCode: string; onRun: (req: BacktestRequest) => void; loading: boolean }

const STRATEGIES: Array<{ value: StockStrategyName; label: string }> = [
  { value: 'three_factors', label: '三因子策略' },
  { value: 'three_factors_v2', label: '三因子v2' },
  { value: 'supertrend_ma', label: 'SuperTrend+MA' },
  { value: 'supertrend_wma', label: 'SuperTrend+WMA' },
  { value: 'trend_pullback_maw_macd', label: 'MAW+MACD中长线趋势回撤' },
  { value: 'buy_and_hold', label: '买入持有' },
]

const BacktestConfig: React.FC<Props> = ({ stockCode, onRun, loading }) => {
  const [form] = Form.useForm()
  const [strategy, setStrategy] = useState<StockStrategyName>('three_factors')
  const p = DEFAULT_STRATEGY_PARAMS
  const handleFinish = (values: any) => {
    const num = (v: any, fallback: number) => v == null || Number.isNaN(v) ? fallback : Number(v)
    const pct = (v: any, fallback: number) => num(v, fallback * 100) / 100
    let strategyParams: StrategyParams = { ...p }
    if (values.strategy_name === 'three_factors' || values.strategy_name === 'three_factors_v2') {
      strategyParams = { ...p, score_rising_days: num(values.score_rising_days, p.score_rising_days), oversold_std_mult: num(values.oversold_std_mult, p.oversold_std_mult), take_profit_pct: pct(values.take_profit_pct, p.take_profit_pct), take_profit_std_mult: num(values.take_profit_std_mult, p.take_profit_std_mult), stop_loss_pct: pct(values.stop_loss_pct, p.stop_loss_pct), add_position_pct: pct(values.add_position_pct, p.add_position_pct), half_position_ratio: pct(values.half_position_ratio, p.half_position_ratio), bias_n: num(values.bias_n, p.bias_n), momentum_day: num(values.momentum_day, p.momentum_day), slope_n: num(values.slope_n, p.slope_n), efficiency_n: num(values.efficiency_n, p.efficiency_n), zscore_window: num(values.zscore_window, p.zscore_window) }
    } else if (values.strategy_name === 'supertrend_ma' || values.strategy_name === 'supertrend_wma') {
      strategyParams = { ...p, recent_high_window: num(values.recent_high_window, p.recent_high_window) }
    }
    onRun({ stock_code: stockCode, start_date: values.start_date.format('YYYY-MM-DD'), end_date: values.end_date.format('YYYY-MM-DD'), initial_cash: num(values.initial_cash, 100000), strategy_name: values.strategy_name, strategy_params: strategyParams })
  }
  const factorFields = [
    ['score连升天数','score_rising_days',1,10,1], ['超卖倍数 (σ)','oversold_std_mult',0.5,5,0.5], ['止盈 (%)','take_profit_pct',1,100,1], ['score止盈倍数','take_profit_std_mult',0.5,5,0.5], ['止损 (%)','stop_loss_pct',1,50,1], ['加仓触发 (%)','add_position_pct',1,50,1], ['初始仓位 (%)','half_position_ratio',10,100,1], ['乖离率窗口','bias_n',5,250,1], ['动量回看天数','momentum_day',5,250,1], ['斜率窗口','slope_n',5,250,1], ['效率窗口','efficiency_n',5,250,1], ['Z-score窗口','zscore_window',50,500,1],
  ] as const
  return <Form form={form} layout="inline" onFinish={handleFinish} initialValues={{ strategy_name:'three_factors', start_date:dayjs('2023-01-01'), end_date:dayjs(), initial_cash:100000, score_rising_days:p.score_rising_days, oversold_std_mult:p.oversold_std_mult, take_profit_pct:p.take_profit_pct*100, take_profit_std_mult:p.take_profit_std_mult, stop_loss_pct:p.stop_loss_pct*100, add_position_pct:p.add_position_pct*100, half_position_ratio:p.half_position_ratio*100, bias_n:p.bias_n, momentum_day:p.momentum_day, slope_n:p.slope_n, efficiency_n:p.efficiency_n, zscore_window:p.zscore_window, recent_high_window:p.recent_high_window }} style={{ background:'#161b22', padding:16, borderRadius:8, border:'1px solid #30363d', marginBottom:16 }}>
    <Form.Item label="策略" name="strategy_name"><Select options={STRATEGIES} style={{ width:220 }} onChange={setStrategy}/></Form.Item>
    <Form.Item label="开始日期" name="start_date"><DatePicker format="YYYY-MM-DD"/></Form.Item>
    <Form.Item label="结束日期" name="end_date"><DatePicker format="YYYY-MM-DD"/></Form.Item>
    <Form.Item label="初始资金 (元)" name="initial_cash"><InputNumber min={10000} step={10000} style={{width:130}}/></Form.Item>
    {(strategy==='three_factors'||strategy==='three_factors_v2') && <Collapse ghost style={{width:'100%',marginTop:8}} items={[{key:'f',label:<span style={{color:'#8b949e'}}>策略参数 ▾</span>,children:<Row gutter={[16,0]}>{factorFields.map(([label,name,min,max,step])=><Col key={name}><Form.Item label={label} name={name}><InputNumber min={min} max={max} step={step} style={{width:80}}/></Form.Item></Col>)}</Row>}]} />}
    {(strategy==='supertrend_ma'||strategy==='supertrend_wma') && <Collapse ghost style={{width:'100%',marginTop:8}} items={[{key:'s',label:<span style={{color:'#8b949e'}}>策略参数 ▾</span>,children:<Form.Item label="新高回看天数" name="recent_high_window"><InputNumber min={1} max={250} style={{width:90}}/></Form.Item>}]} />}
    {strategy==='trend_pullback_maw_macd' && <Alert type="info" showIcon style={{width:'100%',marginTop:12}} message="中长线固定规则" description="MAW20/60/120 判断趋势与回撤，MACD(12,26,9) 确认动能；最大仓位80%，加仓至少间隔5个交易日；成本亏损12%减仓、18%清仓；信号按当日收盘价成交。"/>}
    <Form.Item style={{marginTop:8}}><Button type="primary" htmlType="submit" icon={loading?<Spin size="small"/>:<PlayCircleOutlined/>} disabled={loading} style={{background:'#238636',borderColor:'#238636'}}>运行回测</Button></Form.Item>
  </Form>
}
export default BacktestConfig
