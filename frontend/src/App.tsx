import React, { useRef, useState } from 'react'
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
type AssetMode = 'stock' | 'fund'

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
  const [dailyDataGeneration, setDailyDataGeneration] = useState(0)
  const [fundAnalysisGeneration, setFundAnalysisGeneration] = useState(0)
  const [fundDataGeneration, setFundDataGeneration] = useState(0)
  const [stockInput, setStockInput] = useState('')
  const [fundInput, setFundInput] = useState('')
  const [stockCode, setStockCode] = useState('')
  const [fundCode, setFundCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [activeTab, setActiveTab] = useState(TECHNICAL_TAB_KEY)
  const latestStockActionRef = useRef(0)
  const latestFundActionRef = useRef(0)
  const latestAnalyseRequestRef = useRef(0)
  const latestRefreshRequestRef = useRef(0)
  const isFundMode = activeTab === FUND_TAB_KEY

  const beginAssetAction = (mode: AssetMode) => {
    if (mode === 'fund') {
      latestFundActionRef.current += 1
      return latestFundActionRef.current
    }

    latestStockActionRef.current += 1
    return latestStockActionRef.current
  }

  const isLatestAssetAction = (mode: AssetMode, actionId: number) =>
    (mode === 'fund' ? latestFundActionRef.current : latestStockActionRef.current) === actionId

  const handleValueChange = (value: string) => {
    if (isFundMode) {
      setFundInput(value)
      return
    }
    setStockInput(value)
  }

  const handleAnalyse = async () => {
    const mode: AssetMode = isFundMode ? 'fund' : 'stock'
    const code = (mode === 'fund' ? fundInput : stockInput).trim()
    const actionId = beginAssetAction(mode)
    const analyseRequestId = latestAnalyseRequestRef.current + 1
    latestAnalyseRequestRef.current = analyseRequestId
    setLoading(true)
    if (mode === 'fund') {
      setFundInput(code)
      setFundCode(code)
      setActiveTab(FUND_TAB_KEY)
    } else {
      setStockInput(code)
      setActiveTab(TECHNICAL_TAB_KEY)
    }

    try {
      if (mode === 'fund') {
        const data = await analyseFund(code)
        if (!isLatestAssetAction(mode, actionId)) {
          return
        }
        setFundAnalysis(data)
        setFundAnalysisGeneration((generation) => generation + 1)
        setFundCode(data.fund_code)
      } else {
        const data = await runAnalysis(code)
        if (!isLatestAssetAction(mode, actionId)) {
          return
        }
        setAnalysisData(data)
        setStockCode(data.stock_code)
      }
    } catch (err: any) {
      if (!isLatestAssetAction(mode, actionId)) {
        return
      }
      message.error(getErrorMessage(err, '分析失败'))
    } finally {
      if (analyseRequestId === latestAnalyseRequestRef.current) {
        setLoading(false)
      }
    }
  }

  const handleRefresh = async () => {
    const mode: AssetMode = isFundMode ? 'fund' : 'stock'
    const code = (mode === 'fund' ? fundInput : stockInput).trim()
    const shouldTriggerDailyChanRefresh = mode === 'stock' && code === stockCode
    const actionId = beginAssetAction(mode)
    const refreshRequestId = latestRefreshRequestRef.current + 1
    latestRefreshRequestRef.current = refreshRequestId
    setRefreshing(true)
    if (mode === 'fund') {
      setFundInput(code)
      setFundCode(code)
    } else {
      setStockInput(code)
    }

    try {
      if (mode === 'fund') {
        const result = await refreshFund(code)
        if (!isLatestAssetAction(mode, actionId)) {
          return
        }
        setFundDataGeneration((generation) => generation + 1)
        const data = await analyseFund(code)
        if (!isLatestAssetAction(mode, actionId)) {
          return
        }
        setFundAnalysis(data)
        setFundAnalysisGeneration((generation) => generation + 1)
        setFundCode(data.fund_code)
        message.success(
          `${result.fund_code} 数据已更新：${result.rows} 条，${result.date_from} ~ ${result.date_to}`,
        )
      } else {
        const result = await refreshData(code)
        const data = await runAnalysis(code)
        if (!isLatestAssetAction(mode, actionId)) {
          return
        }
        setAnalysisData(data)
        setStockCode(data.stock_code)
        if (shouldTriggerDailyChanRefresh) {
          setDailyDataGeneration((generation) => generation + 1)
        }
        message.success(
          `${result.stock_code} 数据已更新：${result.rows} 条，${result.date_from} ~ ${result.date_to}`,
        )
      }
    } catch (err: any) {
      if (!isLatestAssetAction(mode, actionId)) {
        return
      }
      message.error(getErrorMessage(err, '刷新失败'))
    } finally {
      if (refreshRequestId === latestRefreshRequestRef.current) {
        setRefreshing(false)
      }
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
          <FundInvestmentTab
            fundCode={fundCode}
            analysis={fundAnalysis}
            analysisGeneration={fundAnalysisGeneration}
            dataGeneration={fundDataGeneration}
          />
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
          <ChanTab stockCode={stockCode} dailyDataGeneration={dailyDataGeneration} />
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
