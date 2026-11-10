import React, { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { AnalysisResponse } from '../../types/stock'
import { detectPriceDecimals } from '../../utils/priceFormat'
import { computeSMA } from '../../utils/wma'
import { createMawSeries } from '../../utils/mawSeries'

interface Props {
  data: AnalysisResponse
}

const TAIL = 2500

const WMAChart: React.FC<Props> = ({ data }) => {
  const option = useMemo(() => {
    const ma7Full   = computeSMA(data.close, 7)
    const ma23Full  = computeSMA(data.close, 23)
    const ma67Full  = computeSMA(data.close, 67)
    const ma133Full = computeSMA(data.close, 133)

    const n = data.dates.length
    const start = Math.max(0, n - TAIL)
    const dates  = data.dates.slice(start)
    const open   = data.open.slice(start)
    const high   = data.high.slice(start)
    const low    = data.low.slice(start)
    const close  = data.close.slice(start)
    const volume = data.volume.slice(start)
    const ma7    = ma7Full.slice(start)
    const ma23   = ma23Full.slice(start)
    const ma67   = ma67Full.slice(start)
    const ma133  = ma133Full.slice(start)
    const nullArr = new Array(n - start).fill(null) as (number | null)[]
    const mawGroups = [
      { name: 'MAW5', values: data.maw5, color: '#ffffff' },
      { name: 'MAW10', values: data.maw10, color: '#ffd700' },
      { name: 'MAW20', values: data.maw20, color: '#ef5350' },
      { name: 'MAW60', values: data.maw60, color: '#1890ff' },
      { name: 'MAW120', values: data.maw120, color: '#26a69a' },
      { name: 'MAW243', values: data.maw243, color: '#d980fa' },
    ]
    const mawSeries = mawGroups.flatMap(({ name, values, color }) =>
      createMawSeries(name, values?.slice(start) ?? nullArr, color),
    )
    const mawLabels = new Map(mawSeries.map(series => [series.id, series.id]))
    const legendNames = ['K线', '均价', 'MA7', 'MA23', 'MA67', 'MA133', ...mawGroups.map(group => group.name)]
    const vwap   = data.vwap   ? data.vwap.slice(start)   : nullArr

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
        data: legendNames,
        selected: Object.fromEntries(legendNames.map(name => [name, name === 'K线' || name === 'MAW243'])),
        type: 'scroll',
        top: 8,
        textStyle: { color: '#8b949e' },
        inactiveColor: '#444',
      },
      tooltip: {
        trigger: 'axis',
        confine: true,
        enterable: true,
        extraCssText: 'max-height: 360px; overflow-y: auto;',
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
            if (v == null || !Number.isFinite(Number(v))) return
            const label = mawLabels.get(p.seriesId) ?? p.seriesName
            html += `<div style="color:${p.color}">${label}: ${Number(v).toFixed(priceDecimals)}</div>`
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
        { name: '均价', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: vwap,
          lineStyle: { color: '#fa8c16', width: 1 }, showSymbol: false },
        { name: 'MA7',  type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma7,
          lineStyle: { color: '#ff7f50', width: 1 }, showSymbol: false },
        { name: 'MA23', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma23,
          lineStyle: { color: '#7cb342', width: 1 }, showSymbol: false },
        { name: 'MA67', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma67,
          lineStyle: { color: '#b57bee', width: 1 }, showSymbol: false },
        { name: 'MA133', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma133,
          lineStyle: { color: '#00bcd4', width: 1 }, showSymbol: false },
        ...mawSeries,
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
