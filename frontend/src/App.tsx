import React, { useState } from 'react'
import { ConfigProvider, Tabs, theme, message } from 'antd'
import './App.css'
import Header from './components/layout/Header'
import TechnicalTab from './components/technical/TechnicalTab'
import BacktestTab from './components/backtest/BacktestTab'
import IndicatorTestTab from './components/indicator-test/IndicatorTestTab'
import { runAnalysis } from './services/api'
import type { AnalysisResponse } from './types/stock'

const App: React.FC = () => {
  const [analysisData, setAnalysisData] = useState<AnalysisResponse | null>(null)
  const [stockCode, setStockCode] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('technical')

  const handleAnalyse = async (code: string) => {
    setLoading(true)
    try {
      const data = await runAnalysis(code)
      setAnalysisData(data)
      setStockCode(code.trim())
      setActiveTab('technical')
    } catch (err: any) {
      message.error(err?.response?.data?.detail || `分析失败: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const tabs = [
    {
      key: 'technical',
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
      key: 'indicator-test',
      label: '指标测试',
      children: (
        <div className="tab-pane-inner">
          <IndicatorTestTab data={analysisData} loading={loading} />
        </div>
      ),
    },
  ]

  return (
    <ConfigProvider theme={{ algorithm: theme.darkAlgorithm }}>
      <div className="app-layout">
        <Header onAnalyse={handleAnalyse} loading={loading} />
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
