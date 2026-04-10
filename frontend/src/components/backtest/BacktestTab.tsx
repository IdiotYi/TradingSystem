import React from 'react'
interface Props { stockCode: string }
const BacktestTab: React.FC<Props> = () => <div style={{color:'#8b949e', padding: 40}}>回测 (loading...)</div>
export default BacktestTab
