import React, { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { AnalysisResponse } from '../../types/stock'

interface Props {
  data: AnalysisResponse
}

function rollingMA(arr: (number | null)[], period: number): (number | null)[] {
  return arr.map((_, i) => {
    if (i < period - 1) return null
    const slice = arr.slice(i - period + 1, i + 1)
    if (slice.some(v => v === null)) return null
    return (slice as number[]).reduce((s, v) => s + v, 0) / period
  })
}

const KLineChart: React.FC<Props> = ({ data }) => {
  const option = useMemo(() => {
    const {
      dates, open, high, low, close, volume,
      ma5, ma20, ma60, kama,
      supertrend, supertrend_direction,
      supertrend2, supertrend2_direction,
      supertrend3, supertrend3_direction,
    } = data

    const candleData = dates.map((_, i) => [open[i], close[i], low[i], high[i]])

    // ST series
    const stUp   = supertrend.map((v, i) => (supertrend_direction[i] === 1  ? v : null))
    const stDown = supertrend.map((v, i) => (supertrend_direction[i] === -1 ? v : null))
    const st2Up  = supertrend2.map((v, i) => (supertrend2_direction[i] === 1  ? v : null))
    const st2Down = supertrend2.map((v, i) => (supertrend2_direction[i] === -1 ? v : null))
    const st3Up  = supertrend3.map((v, i) => (supertrend3_direction[i] === 1  ? v : null))
    const st3Down = supertrend3.map((v, i) => (supertrend3_direction[i] === -1 ? v : null))

    // Volume bars — red if close >= open (up day), green otherwise
    const volData = volume.map((v, i) => ({
      value: v,
      itemStyle: {
        color: (close[i] ?? 0) >= (open[i] ?? 0) ? '#ef5350' : '#26a69a',
      },
    }))
    const volMA5  = rollingMA(volume, 5)
    const volMA20 = rollingMA(volume, 20)

    return {
      backgroundColor: '#0d1117',
      animation: false,
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      legend: {
        data: ['K线', 'MA5', 'MA20', 'MA60', 'KAMA',
               'ST(10,1)↑', 'ST(10,1)↓',
               'ST(11,2)↑', 'ST(11,2)↓',
               'ST(12,3)↑', 'ST(12,3)↓',
               '量MA5', '量MA20'],
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
            if (p.seriesName === 'K线' || p.seriesName === '成交量') return
            const v = Array.isArray(p.value) ? p.value[1] : p.value
            if (v == null) return
            html += `<div style="color:${p.color}">${p.seriesName}: ${Number(v).toFixed(2)}</div>`
          })
          // volume
          if (volume[idx] != null) {
            const fmt = (v: number) => v >= 1e8 ? `${(v / 1e8).toFixed(2)}亿` : v >= 1e4 ? `${(v / 1e4).toFixed(0)}万` : String(v)
            html += `<div style="color:#8b949e">成交量: ${fmt(volume[idx] as number)}</div>`
          }
          return html
        },
      },
      grid: [
        { left: '5%', right: '3%', top: 50, bottom: '36%' },
        { left: '5%', right: '3%', top: '68%', bottom: 80 },
      ],
      xAxis: [
        {
          type: 'category', data: dates, gridIndex: 0, boundaryGap: true,
          axisLine: { lineStyle: { color: '#30363d' } },
          axisLabel: { show: false },
        },
        {
          type: 'category', data: dates, gridIndex: 1, boundaryGap: true,
          axisLine: { lineStyle: { color: '#30363d' } },
          axisLabel: {
            color: '#8b949e',
            formatter: (v: string) => v.slice(0, 7),
            interval: Math.floor(dates.length / 8),
          },
        },
      ],
      yAxis: [
        {
          scale: true, gridIndex: 0,
          axisLine: { lineStyle: { color: '#30363d' } },
          axisLabel: { color: '#8b949e', formatter: (v: number) => v.toFixed(0) },
          splitLine: { lineStyle: { color: '#161b22' } },
        },
        {
          scale: false, gridIndex: 1,
          axisLine: { lineStyle: { color: '#30363d' } },
          axisLabel: {
            color: '#8b949e',
            formatter: (v: number) =>
              v >= 1e8 ? `${(v / 1e8).toFixed(1)}亿` : v >= 1e4 ? `${(v / 1e4).toFixed(0)}万` : String(v),
          },
          splitLine: { lineStyle: { color: '#161b22' } },
        },
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
        {
          type: 'slider', xAxisIndex: [0, 1], show: true, bottom: 20,
          start: 0, end: 100,
          borderColor: '#30363d', fillerColor: 'rgba(35,134,54,0.15)',
          textStyle: { color: '#8b949e' },
          handleStyle: { color: '#238636' },
        },
      ],
      series: [
        // ── K-line grid ──────────────────────────────────────
        {
          name: 'K线', type: 'candlestick', xAxisIndex: 0, yAxisIndex: 0,
          data: candleData,
          itemStyle: {
            color: '#ef5350', color0: '#26a69a',
            borderColor: '#ef5350', borderColor0: '#26a69a',
          },
        },
        { name: 'MA5',  type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma5,
          lineStyle: { color: '#ffffff', width: 1 }, showSymbol: false },
        { name: 'MA20', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma20,
          lineStyle: { color: '#ffd700', width: 1 }, showSymbol: false },
        { name: 'MA60', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma60,
          lineStyle: { color: '#1890ff', width: 1 }, showSymbol: false },
        { name: 'KAMA', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: kama,
          lineStyle: { color: '#b57bee', width: 1.5 }, showSymbol: false },
        { name: 'ST(10,1)↑', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: stUp,
          lineStyle: { color: '#4caf50', width: 2 }, showSymbol: false, connectNulls: false },
        { name: 'ST(10,1)↓', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: stDown,
          lineStyle: { color: '#f44336', width: 2 }, showSymbol: false, connectNulls: false },
        { name: 'ST(11,2)↑', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: st2Up,
          lineStyle: { color: '#69f0ae', width: 1.5, type: 'dashed' }, showSymbol: false, connectNulls: false },
        { name: 'ST(11,2)↓', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: st2Down,
          lineStyle: { color: '#ff8a80', width: 1.5, type: 'dashed' }, showSymbol: false, connectNulls: false },
        { name: 'ST(12,3)↑', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: st3Up,
          lineStyle: { color: '#00796b', width: 1.5, type: 'dotted' }, showSymbol: false, connectNulls: false },
        { name: 'ST(12,3)↓', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: st3Down,
          lineStyle: { color: '#c62828', width: 1.5, type: 'dotted' }, showSymbol: false, connectNulls: false },
        // ── Volume grid ──────────────────────────────────────
        {
          name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1,
          data: volData,
          barMaxWidth: 6,
        },
        { name: '量MA5',  type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: volMA5,
          lineStyle: { color: '#ffffff', width: 1 }, showSymbol: false },
        { name: '量MA20', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: volMA20,
          lineStyle: { color: '#ffd700', width: 1 }, showSymbol: false },
      ],
    }
  }, [data])

  return (
    <ReactECharts
      option={option}
      style={{ height: 700 }}
      opts={{ renderer: 'canvas' }}
    />
  )
}

export default KLineChart
