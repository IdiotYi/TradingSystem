import React, { useState } from 'react'
import { Input, Button, Spin } from 'antd'
import { SearchOutlined } from '@ant-design/icons'

interface HeaderProps {
  onAnalyse: (code: string) => void
  loading: boolean
}

const Header: React.FC<HeaderProps> = ({ onAnalyse, loading }) => {
  const [code, setCode] = useState('')

  const handleSubmit = () => {
    const trimmed = code.trim()
    if (trimmed) onAnalyse(trimmed)
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
        disabled={loading}
        style={{ background: '#238636', borderColor: '#238636' }}
      >
        分析
      </Button>
    </div>
  )
}

export default Header
