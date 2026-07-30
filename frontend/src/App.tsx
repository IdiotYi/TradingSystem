import React, { useState } from 'react'
import { ConfigProvider, Tabs, theme, message } from 'antd'
import './App.css'
import Header from './components/layout/Header'
import TechnicalTab from './components/technical/TechnicalTab'
import BacktestTab from './components/backtest/BacktestTab'
import IndicatorTestTab from './components/indicator-test/IndicatorTestTab'
import ChanTab from './components/chan/ChanTab'
import FundInvestmentTab from './components/fund/FundInvestmentTab'
import { analyseFund, refreshData, refreshFund, runAnalysis } from './services/api'
import type { AnalysisResponse } from './types/stock'
import type { FundAnalysisResponse } from './types/fund'

const FUND_TAB_KEY = 'fund-investment'
const TECHNICAL_TAB_KEY = 'technical'

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

const App: React.FC = () => {
  const [analysisData, setAnalysisData] = useState<AnalysisResponse | null>(null)
  const [fundAnalysis, setFundAnalysis] = useState<FundAnalysisResponse | null>(null)
  const [stockInput, setStockInput] = useState('')
  const [fundInput, setFundInput] = useState('')
  const [stockCode, setStockCode] = useState('')
  const [fundCode, setFundCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [activeTab, setActiveTab] = useState(TECHNICAL_TAB_KEY)
  const isFundMode = activeTab === FUND_TAB_KEY

  const handleValueChange = (value: string) => {
    if (isFundMode) {
      setFundInput(value)
      return
    }
    setStockInput(value)
  }

  const handleAnalyse = async () => {
    const code = (isFundMode ? fundInput : stockInput).trim()
    setLoading(true)
    try {
      if (isFundMode) {
        const data = await analyseFund(code)
        setFundAnalysis(data)
        setFundInput(code)
        setFundCode(code)
        setActiveTab(FUND_TAB_KEY)
      } else {
        const data = await runAnalysis(code)
        setAnalysisData(data)
        setStockInput(code)
        setStockCode(code)
        setActiveTab(TECHNICAL_TAB_KEY)
      }
    } catch (err: any) {
      message.error(getErrorMessage(err, '分析失败'))
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    const code = (isFundMode ? fundInput : stockInput).trim()
    setRefreshing(true)
    try {
      if (isFundMode) {
        const result = await refreshFund(code)
        const data = await analyseFund(code)
        setFundAnalysis(data)
        setFundInput(code)
        setFundCode(code)
        message.success(
          `${result.fund_code} 数据已更新：${result.rows} 条，${result.date_from} ~ ${result.date_to}`,
        )
      } else {
        const result = await refreshData(code)
        const data = await runAnalysis(code)
        setAnalysisData(data)
        setStockInput(code)
        setStockCode(code)
        message.success(
          `${result.stock_code} 数据已更新：${result.rows} 条，${result.date_from} ~ ${result.date_to}`,
        )
      }
    } catch (err: any) {
      message.error(getErrorMessage(err, '刷新失败'))
    } finally {
      setRefreshing(false)
    }
  }

  const tabs = [
    {
      key: TECHNICAL_TAB_KEY,
      label: '技术分析',
      children: (
        <div className="tab-pane-inner">
          <TechnicalTab data={analysisData} loading={loading} />
        </div>
      ),
    },
    {
      key: 'backtest',
      label: '回测',
      children: (
        <div className="tab-pane-inner">
          <BacktestTab stockCode={stockCode} />
        </div>
      ),
      disabled: !stockCode,
    },
    {
      key: FUND_TAB_KEY,
      label: '基金定投',
      children: (
        <div className="tab-pane-inner">
          <FundInvestmentTab fundCode={fundCode} analysis={fundAnalysis} />
        </div>
      ),
    },
    {
      key: 'indicator-test',
      label: '指标测试',
      children: (
        <div className="tab-pane-inner">
          <IndicatorTestTab data={analysisData} loading={loading} />
        </div>
      ),
    },
    {
      key: 'chan',
      label: '缠论',
      children: (
        <div className="tab-pane-inner">
          <ChanTab stockCode={stockCode} />
        </div>
      ),
      disabled: !stockCode,
    },
  ]

  return (
    <ConfigProvider theme={{ algorithm: theme.darkAlgorithm }}>
      <div className="app-layout">
        <Header
          mode={isFundMode ? 'fund' : 'stock'}
          value={isFundMode ? fundInput : stockInput}
          loading={loading}
          refreshing={refreshing}
          onValueChange={handleValueChange}
          onAnalyse={handleAnalyse}
          onRefresh={handleRefresh}
        />
        <div className="app-content">
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabs}
            style={{ height: '100%' }}
          />
        </div>
      </div>
    </ConfigProvider>
  )
}

export default App
