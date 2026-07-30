import React, { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { FundBacktestResponse } from '../../types/fund'

interface Props {
  data: FundBacktestResponse
}

const formatCny = (value: number) =>
  `¥${value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

const FundInvestmentChart: React.FC<Props> = ({ data }) => {
  const option = useMemo(() => ({
    backgroundColor: '#0d1117',
    animation: false,
    legend: {
      data: ['累计投入', '资产市值'],
      top: 8,
      textStyle: { color: '#8b949e' },
      inactiveColor: '#444',
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', crossStyle: { color: '#555' } },
      backgroundColor: 'rgba(22,27,34,0.95)',
      borderColor: '#30363d',
      textStyle: { color: '#e6edf3', fontSize: 12 },
      formatter: (params: Array<{ axisValue: string; seriesName: string; value: number; color: string }>) => {
        if (!params.length) return ''
        const rows = params.map(item =>
          `<div style="color:${item.color}">${item.seriesName}: ${formatCny(Number(item.value))}</div>`,
        )
        return `<div style="font-weight:600;margin-bottom:4px">${params[0].axisValue}</div>${rows.join('')}`
      },
    },
    grid: {
      left: '5%',
      right: '3%',
      top: 60,
      bottom: 80,
    },
    xAxis: {
      type: 'category',
      data: data.dates,
      boundaryGap: false,
      axisLabel: {
        color: '#8b949e',
        formatter: (value: string) => value.slice(0, 7),
        interval: Math.max(0, Math.floor(data.dates.length / 8)),
      },
      axisLine: { lineStyle: { color: '#30363d' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#8b949e',
        formatter: (value: number) => formatCny(value),
      },
      splitLine: { lineStyle: { color: '#161b22' } },
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      {
        type: 'slider',
        show: true,
        bottom: 20,
        start: 0,
        end: 100,
        borderColor: '#30363d',
        fillerColor: 'rgba(35,134,54,0.15)',
        textStyle: { color: '#8b949e' },
        handleStyle: { color: '#238636' },
      },
    ],
    series: [
      {
        name: '累计投入',
        type: 'line',
        data: data.total_invested_series,
        showSymbol: false,
        lineStyle: { color: '#faad14', width: 2 },
      },
      {
        name: '资产市值',
        type: 'line',
        data: data.asset_value_series,
        showSymbol: false,
        lineStyle: { color: '#58a6ff', width: 2 },
      },
    ],
  }), [data])

  return (
    <div className="fund-chart-shell">
      <ReactECharts
        option={option}
        style={{ height: 420 }}
        opts={{ renderer: 'canvas' }}
      />
    </div>
  )
}

export default FundInvestmentChart
