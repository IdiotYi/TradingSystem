import React, { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { AnalysisResponse } from '../../types/stock'
import { detectPriceDecimals } from '../../utils/priceFormat'
import { computeWMA, computeWMAPred } from '../../utils/wma'

interface Props {
  data: AnalysisResponse
}

const TAIL = 250

const WMAChart: React.FC<Props> = ({ data }) => {
  const option = useMemo(() => {
    // Compute WMA on full history (recurrence needs full past), then slice last TAIL bars for display
    const wma5Full  = computeWMA(data.open, data.close, 5)
    const wma20Full = computeWMA(data.open, data.close, 20)
    const wma60Full = computeWMA(data.open, data.close, 60)
    const pred5Full  = computeWMAPred(data.open, wma5Full)
    const pred20Full = computeWMAPred(data.open, wma20Full)
    const pred60Full = computeWMAPred(data.open, wma60Full)

    const n = data.dates.length
    const start = Math.max(0, n - TAIL)
    const dates  = data.dates.slice(start)
    const open   = data.open.slice(start)
    const high   = data.high.slice(start)
    const low    = data.low.slice(start)
    const close  = data.close.slice(start)
    const volume = data.volume.slice(start)
    const wma5   = wma5Full.slice(start)
    const wma20  = wma20Full.slice(start)
    const wma60  = wma60Full.slice(start)
    const pred5  = pred5Full.slice(start)
    const pred20 = pred20Full.slice(start)
    const pred60 = pred60Full.slice(start)

    const candleData = dates.map((_, i) => [open[i], close[i], low[i], high[i]])
    const priceDecimals = detectPriceDecimals([...close, ...open, ...high, ...low])

    const volData = volume.map((v, i) => ({
      value: v,
      itemStyle: {
        color: (close[i] ?? 0) >= (open[i] ?? 0) ? '#ef5350' : '#26a69a',
      },
    }))

    return {
      backgroundColor: '#0d1117',
      animation: false,
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      legend: {
        data: ['K线', 'WMA5', 'WMA20', 'WMA60', 'WMAPred5', 'WMAPred20', 'WMAPred60'],
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
          html += `<div>开 <b>${open[idx]?.toFixed(priceDecimals)}</b>　高 <b>${high[idx]?.toFixed(priceDecimals)}</b></div>`
          html += `<div>低 <b>${low[idx]?.toFixed(priceDecimals)}</b>　收 <b style="color:${(close[idx] ?? 0) >= (open[idx] ?? 0) ? '#ef5350' : '#26a69a'}">${close[idx]?.toFixed(priceDecimals)}</b></div>`
          params.forEach((p: any) => {
            if (p.seriesName === 'K线' || p.seriesName === '成交量') return
            const v = Array.isArray(p.value) ? p.value[1] : p.value
            if (v == null) return
            html += `<div style="color:${p.color}">${p.seriesName}: ${Number(v).toFixed(priceDecimals)}</div>`
          })
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
          axisLabel: { color: '#8b949e', formatter: (v: number) => v.toFixed(priceDecimals) },
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
        {
          name: 'K线', type: 'candlestick', xAxisIndex: 0, yAxisIndex: 0,
          data: candleData,
          itemStyle: {
            color: '#ef5350', color0: '#26a69a',
            borderColor: '#ef5350', borderColor0: '#26a69a',
          },
        },
        { name: 'WMA5',  type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: wma5,
          lineStyle: { color: '#ffffff', width: 1 }, showSymbol: false },
        { name: 'WMA20', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: wma20,
          lineStyle: { color: '#ffd700', width: 1 }, showSymbol: false },
        { name: 'WMA60', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: wma60,
          lineStyle: { color: '#1890ff', width: 1 }, showSymbol: false },
        { name: 'WMAPred5',  type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: pred5,
          lineStyle: { color: '#ffffff', width: 1, type: 'dashed' }, showSymbol: false },
        { name: 'WMAPred20', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: pred20,
          lineStyle: { color: '#ffd700', width: 1, type: 'dashed' }, showSymbol: false },
        { name: 'WMAPred60', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: pred60,
          lineStyle: { color: '#1890ff', width: 1, type: 'dashed' }, showSymbol: false },
        {
          name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1,
          data: volData,
          barMaxWidth: 6,
        },
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

export default WMAChart
