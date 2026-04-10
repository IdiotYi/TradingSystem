import React, { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { AnalysisResponse } from '../../types/stock'

interface Props {
  data: AnalysisResponse
}

const KLineChart: React.FC<Props> = ({ data }) => {
  const option = useMemo(() => {
    const { dates, open, high, low, close, ma5, ma20, ma60, supertrend, supertrend_direction } = data

    const candleData = dates.map((_, i) => [open[i], close[i], low[i], high[i]])
    const stUp = supertrend.map((v, i) => (supertrend_direction[i] === 1 ? v : null))
    const stDown = supertrend.map((v, i) => (supertrend_direction[i] === -1 ? v : null))

    return {
      backgroundColor: '#0d1117',
      animation: false,
      legend: {
        data: ['K线', 'MA5', 'MA20', 'MA60', 'ST↑', 'ST↓'],
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
        formatter: (params: any[]) => {
          if (!params.length) return ''
          const idx = params[0].dataIndex
          let html = `<div style="font-weight:600;margin-bottom:4px">${dates[idx]}</div>`
          html += `<div>开 <b>${open[idx]?.toFixed(2)}</b>　高 <b>${high[idx]?.toFixed(2)}</b></div>`
          html += `<div>低 <b>${low[idx]?.toFixed(2)}</b>　收 <b style="color:${(close[idx] ?? 0) >= (open[idx] ?? 0) ? '#ef5350' : '#26a69a'}">${close[idx]?.toFixed(2)}</b></div>`
          params.forEach((p: any) => {
            if (p.seriesName === 'K线') return
            const v = Array.isArray(p.value) ? p.value[1] : p.value
            if (v == null) return
            html += `<div style="color:${p.color}">${p.seriesName}: ${Number(v).toFixed(2)}</div>`
          })
          return html
        },
      },
      grid: { left: '5%', right: '3%', top: 60, bottom: 80 },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: true,
        axisLine: { lineStyle: { color: '#30363d' } },
        axisLabel: {
          color: '#8b949e',
          formatter: (v: string) => v.slice(5),
          interval: Math.floor(dates.length / 10),
        },
      },
      yAxis: {
        scale: true,
        axisLine: { lineStyle: { color: '#30363d' } },
        axisLabel: { color: '#8b949e', formatter: (v: number) => v.toFixed(0) },
        splitLine: { lineStyle: { color: '#161b22' } },
      },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider', show: true, bottom: 20,
          start: 0, end: 100,
          borderColor: '#30363d', fillerColor: 'rgba(35,134,54,0.15)',
          textStyle: { color: '#8b949e' },
          handleStyle: { color: '#238636' },
        },
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: candleData,
          itemStyle: {
            color: '#ef5350', color0: '#26a69a',
            borderColor: '#ef5350', borderColor0: '#26a69a',
          },
        },
        { name: 'MA5', type: 'line', data: ma5, smooth: false,
          lineStyle: { color: '#ffffff', width: 1 }, showSymbol: false },
        { name: 'MA20', type: 'line', data: ma20, smooth: false,
          lineStyle: { color: '#ffd700', width: 1 }, showSymbol: false },
        { name: 'MA60', type: 'line', data: ma60, smooth: false,
          lineStyle: { color: '#1890ff', width: 1 }, showSymbol: false },
        { name: 'ST↑', type: 'line', data: stUp,
          lineStyle: { color: '#4caf50', width: 2 }, showSymbol: false, connectNulls: false },
        { name: 'ST↓', type: 'line', data: stDown,
          lineStyle: { color: '#f44336', width: 2 }, showSymbol: false, connectNulls: false },
      ],
    }
  }, [data])

  return (
    <ReactECharts
      option={option}
      style={{ height: 560 }}
      opts={{ renderer: 'canvas' }}
    />
  )
}

export default KLineChart
