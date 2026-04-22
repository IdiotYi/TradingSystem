import React, { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { BacktestResponse } from '../../types/backtest'
import { detectPriceDecimals } from '../../utils/priceFormat'

interface Props {
  data: BacktestResponse
}

const BacktestChart: React.FC<Props> = ({ data }) => {
  const option = useMemo(() => {
    const {
      dates, open, high, low, close,
      ma5, ma20, ma60, kama, supertrend, supertrend_direction,
      score, score_mean, score_std, trades, strategy_name,
    } = data

    const isSTMA = strategy_name === 'supertrend_ma'

    const candleData = dates.map((_, i) => [open[i], close[i], low[i], high[i]])
    const priceDecimals = detectPriceDecimals([...close, ...open, ...high, ...low])
    const stUp = supertrend.map((v, i) => (supertrend_direction[i] === 1 ? v : null))
    const stDown = supertrend.map((v, i) => (supertrend_direction[i] === -1 ? v : null))

    const scorePlus2 = score_mean.map((m, i) =>
      m !== null && score_std[i] !== null ? m + 2 * (score_std[i] as number) : null
    )
    const scoreMinus2 = score_mean.map((m, i) =>
      m !== null && score_std[i] !== null ? m - 2 * (score_std[i] as number) : null
    )

    const buyPoints = trades
      .filter(t => t.direction === '买入')
      .map(t => {
        const idx = dates.indexOf(t.date)
        if (idx === -1) return null
        const lowVal = low[idx] ?? t.price
        return {
          coord: [t.date, lowVal * 0.985],
          itemStyle: { color: '#ef5350' },
          symbol: 'triangle',
          symbolSize: 14,
          symbolRotate: 0,
          label: { show: false },
        }
      })
      .filter((x): x is NonNullable<typeof x> => x !== null)

    const sellPoints = trades
      .filter(t => t.direction === '卖出')
      .map(t => {
        const idx = dates.indexOf(t.date)
        if (idx === -1) return null
        const highVal = high[idx] ?? t.price
        return {
          coord: [t.date, highVal * 1.015],
          itemStyle: { color: '#26a69a' },
          symbol: 'triangle',
          symbolSize: 14,
          symbolRotate: 180,
          label: { show: false },
        }
      })
      .filter((x): x is NonNullable<typeof x> => x !== null)

    const legendData = isSTMA
      ? ['K线', 'MA20', 'KAMA', 'ST(12,3)↑', 'ST(12,3)↓']
      : ['K线', 'MA5', 'MA20', 'MA60', 'ST↑', 'ST↓', 'Score', 'Mean', '+2σ', '-2σ']

    const series: any[] = [
      {
        name: 'K线', type: 'candlestick', xAxisIndex: 0, yAxisIndex: 0,
        data: candleData,
        itemStyle: {
          color: '#ef5350', color0: '#26a69a',
          borderColor: '#ef5350', borderColor0: '#26a69a',
        },
        markPoint: { data: [...buyPoints, ...sellPoints], animation: false },
      },
    ]

    if (isSTMA) {
      series.push(
        { name: 'MA20', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma20,
          lineStyle: { color: '#ffd700', width: 1 }, showSymbol: false },
        { name: 'KAMA', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: kama,
          lineStyle: { color: '#b57bee', width: 1.5 }, showSymbol: false },
        { name: 'ST(12,3)↑', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: stUp,
          lineStyle: { color: '#4caf50', width: 2 }, showSymbol: false, connectNulls: false },
        { name: 'ST(12,3)↓', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: stDown,
          lineStyle: { color: '#f44336', width: 2 }, showSymbol: false, connectNulls: false },
      )
    } else {
      series.push(
        { name: 'MA5', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma5,
          lineStyle: { color: '#ffffff', width: 1 }, showSymbol: false },
        { name: 'MA20', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma20,
          lineStyle: { color: '#ffd700', width: 1 }, showSymbol: false },
        { name: 'MA60', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma60,
          lineStyle: { color: '#1890ff', width: 1 }, showSymbol: false },
        { name: 'ST↑', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: stUp,
          lineStyle: { color: '#4caf50', width: 2 }, showSymbol: false, connectNulls: false },
        { name: 'ST↓', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: stDown,
          lineStyle: { color: '#f44336', width: 2 }, showSymbol: false, connectNulls: false },
        { name: 'Score', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: score,
          lineStyle: { color: '#1890ff', width: 1.5 }, showSymbol: false },
        { name: 'Mean', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: score_mean,
          lineStyle: { color: '#fa8c16', width: 1, type: 'dashed' }, showSymbol: false },
        { name: '+2σ', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: scorePlus2,
          lineStyle: { color: '#555', width: 0.8, type: 'dashed' }, showSymbol: false },
        { name: '-2σ', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: scoreMinus2,
          lineStyle: { color: '#555', width: 0.8, type: 'dashed' }, showSymbol: false },
      )
    }

    const grid = isSTMA
      ? [{ left: '5%', right: '3%', top: 60, bottom: 80 }]
      : [
          { left: '5%', right: '3%', top: 60, bottom: '42%' },
          { left: '5%', right: '3%', top: '62%', bottom: 80 },
        ]

    const xAxis = isSTMA
      ? [{
          type: 'category', data: dates, gridIndex: 0, boundaryGap: true,
          axisLabel: {
            color: '#8b949e',
            formatter: (v: string) => v.slice(0, 7),
            interval: Math.floor(dates.length / 8),
          },
          axisLine: { lineStyle: { color: '#30363d' } },
        }]
      : [
          {
            type: 'category', data: dates, gridIndex: 0, boundaryGap: true,
            axisLabel: { show: false },
            axisLine: { lineStyle: { color: '#30363d' } },
          },
          {
            type: 'category', data: dates, gridIndex: 1, boundaryGap: true,
            axisLabel: {
              color: '#8b949e',
              formatter: (v: string) => v.slice(0, 7),
              interval: Math.floor(dates.length / 8),
            },
            axisLine: { lineStyle: { color: '#30363d' } },
          },
        ]

    const yAxis = isSTMA
      ? [{
          scale: true, gridIndex: 0,
          axisLabel: { color: '#8b949e', formatter: (v: number) => v.toFixed(priceDecimals) },
          splitLine: { lineStyle: { color: '#161b22' } },
        }]
      : [
          {
            scale: true, gridIndex: 0,
            axisLabel: { color: '#8b949e', formatter: (v: number) => v.toFixed(priceDecimals) },
            splitLine: { lineStyle: { color: '#161b22' } },
          },
          {
            scale: true, gridIndex: 1,
            axisLabel: { color: '#8b949e', formatter: (v: number) => v.toFixed(2) },
            splitLine: { lineStyle: { color: '#161b22' } },
          },
        ]

    const dataZoom = isSTMA
      ? [
          { type: 'inside', xAxisIndex: 0, start: 0, end: 100 },
          {
            type: 'slider', xAxisIndex: 0, show: true, bottom: 20,
            start: 0, end: 100,
            borderColor: '#30363d', fillerColor: 'rgba(35,134,54,0.15)',
            textStyle: { color: '#8b949e' },
            handleStyle: { color: '#238636' },
          },
        ]
      : [
          { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
          {
            type: 'slider', xAxisIndex: [0, 1], show: true, bottom: 20,
            start: 0, end: 100,
            borderColor: '#30363d', fillerColor: 'rgba(35,134,54,0.15)',
            textStyle: { color: '#8b949e' },
            handleStyle: { color: '#238636' },
          },
        ]

    return {
      backgroundColor: '#0d1117',
      animation: false,
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      legend: {
        data: legendData,
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
          html += `<div>开 ${open[idx]?.toFixed(priceDecimals)}　高 ${high[idx]?.toFixed(priceDecimals)}</div>`
          html += `<div>低 ${low[idx]?.toFixed(priceDecimals)}　收 ${close[idx]?.toFixed(priceDecimals)}</div>`
          params.forEach((p: any) => {
            if (p.seriesName === 'K线') return
            const v = Array.isArray(p.value) ? p.value[1] : p.value
            if (v == null) return
            const decimals = ['Score','Mean','+2σ','-2σ'].includes(p.seriesName) ? 4 : priceDecimals
            html += `<div style="color:${p.color}">${p.seriesName}: ${Number(v).toFixed(decimals)}</div>`
          })
          return html
        },
      },
      grid, xAxis, yAxis, dataZoom,
      series,
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

export default BacktestChart
