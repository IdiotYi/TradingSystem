import React, { useState } from 'react'
import { Input, Button, Spin, message } from 'antd'
import { SearchOutlined, SyncOutlined } from '@ant-design/icons'
import { refreshData } from '../../services/api'

interface HeaderProps {
  onAnalyse: (code: string) => void
  loading: boolean
}

const Header: React.FC<HeaderProps> = ({ onAnalyse, loading }) => {
  const [code, setCode] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  const handleSubmit = () => {
    const trimmed = code.trim()
    if (trimmed) onAnalyse(trimmed)
  }

  const handleRefresh = async () => {
    const trimmed = code.trim()
    if (!trimmed) {
      message.warning('请先输入股票代码')
      return
    }
    setRefreshing(true)
    try {
      const result = await refreshData(trimmed)
      message.success(`${result.stock_code} 数据已更新：${result.rows} 条，${result.date_from} ~ ${result.date_to}`)
    } catch (err: any) {
      message.error(err?.response?.data?.detail || `刷新失败: ${err.message}`)
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <div className="app-header">
      <span className="app-logo">📈 TradingSystem</span>
      <Input
        placeholder="输入股票/ETF代码，如 600519"
        value={code}
        onChange={e => setCode(e.target.value)}
        onPressEnter={handleSubmit}
        style={{ width: 260, background: '#21262d', borderColor: '#30363d', color: '#e6edf3' }}
        allowClear
      />
      <Button
        type="primary"
        icon={loading ? <Spin size="small" /> : <SearchOutlined />}
        onClick={handleSubmit}
        disabled={loading || refreshing}
        style={{ background: '#238636', borderColor: '#238636' }}
      >
        分析
      </Button>
      <Button
        icon={refreshing ? <Spin size="small" /> : <SyncOutlined />}
        onClick={handleRefresh}
        disabled={loading || refreshing}
        style={{ borderColor: '#30363d', color: '#8b949e' }}
      >
        刷新数据
      </Button>
    </div>
  )
}

export default Header
