import React from 'react'
import { Input, Button, Spin, message } from 'antd'
import { SearchOutlined, SyncOutlined } from '@ant-design/icons'

interface HeaderProps {
  mode: 'stock' | 'fund'
  value: string
  loading: boolean
  refreshing: boolean
  onValueChange: (value: string) => void
  onAnalyse: () => void
  onRefresh: () => Promise<void>
}

const Header: React.FC<HeaderProps> = ({
  mode,
  value,
  loading,
  refreshing,
  onValueChange,
  onAnalyse,
  onRefresh,
}) => {
  const assetLabel = mode === 'fund' ? '基金' : '股票/ETF'
  const placeholder = mode === 'fund'
    ? '输入基金代码，如 000001'
    : '输入股票/ETF代码，如 600519'

  const handleSubmit = () => {
    if (!value.trim()) {
      message.warning(`请先输入${assetLabel}代码`)
      return
    }
    onAnalyse()
  }

  const handleRefresh = async () => {
    if (!value.trim()) {
      message.warning(`请先输入${assetLabel}代码`)
      return
    }
    await onRefresh()
  }

  return (
    <div className="app-header">
      <span className="app-logo">📈 TradingSystem</span>
      <Input
        placeholder={placeholder}
        value={value}
        onChange={e => onValueChange(e.target.value)}
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
