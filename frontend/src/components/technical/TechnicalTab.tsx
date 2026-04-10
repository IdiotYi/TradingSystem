import React from 'react'
import type { AnalysisResponse } from '../../types/stock'

interface Props { data: AnalysisResponse | null; loading: boolean }
const TechnicalTab: React.FC<Props> = () => <div style={{color:'#8b949e', padding: 40}}>技术分析 (loading...)</div>
export default TechnicalTab
