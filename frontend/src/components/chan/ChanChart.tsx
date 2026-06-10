import React, { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { ChanResponse } from '../../types/chan'
import { detectPriceDecimals } from '../../utils/priceFormat'

interface Props {
  data: ChanResponse
}

const ChanChart: React.FC<Props> = ({ data }) => {
  const option = useMemo(() => {
    const { dates, open, high, low, close, pens } = data

    const candleData = dates.map((_, i) => [open[i], close[i], low[i], high[i]])
    const priceDecimals = detectPriceDecimals([...close, ...open, ...high, ...low])

    // Pens: lines series — each pen is a 2-point polyline from start to end.
    const penLines = pens.map(p => ({
      coords: [[p.start_date, p.start_price], [p.end_date, p.end_price]],
      lineStyle: {
        color: p.direction === 'up' ? '#ef5350' : '#26a69a',
        width: 2,
      },
    }))

    // Endpoints: scatter points colored by the pen's direction (red for up, green for down).
    // Build a map keyed by date so shared endpoints between adjacent pens collapse into one dot.
    // For shared endpoints, the latter pen's direction wins (i.e. the dot reflects the next pen).
    type EndpointInfo = { date: string; price: number; direction: 'up' | 'down' }
    const endpointMap = new Map<string, EndpointInfo>()
    pens.forEach(p => {
      endpointMap.set(p.start_date, { date: p.start_date, price: p.start_price, direction: p.direction })
      endpointMap.set(p.end_date,   { date: p.end_date,   price: p.end_price,   direction: p.direction })
    })
    const endpointData = Array.from(endpointMap.values()).map(e => ({
      value: [e.date, e.price],
      itemStyle: { color: e.direction === 'up' ? '#ef5350' : '#26a69a' },
      _meta: e,
    }))

    return {
      backgroundColor: '#0d1117',
      animation: false,
      legend: {
        data: ['K线', '笔', '端点'],
        top: 8,
        textStyle: { color: '#8b949e' },
        inactiveColor: '#444',
      },
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(22,27,34,0.95)',
        borderColor: '#30363d',
        textStyle: { color: '#e6edf3', fontSize: 12 },
        formatter: (p: any) => {
          if (p.seriesName === 'K线') {
            const idx = p.dataIndex as number
            const c = close[idx] ?? 0
            const o = open[idx] ?? 0
            const upDownColor = c >= o ? '#ef5350' : '#26a69a'
            let html = `<div style="font-weight:600;margin-bottom:4px">${dates[idx]}</div>`
            html += `<div>开 <b>${o.toFixed(priceDecimals)}</b>　高 <b>${(high[idx] ?? 0).toFixed(priceDecimals)}</b></div>`
            html += `<div>低 <b>${(low[idx] ?? 0).toFixed(priceDecimals)}</b>　收 <b style="color:${upDownColor}">${c.toFixed(priceDecimals)}</b></div>`
            return html
          }
          if (p.seriesName === '端点') {
            const meta = p.data?._meta
            if (!meta) return ''
            const dirLabel = meta.direction === 'up' ? '上升笔' : '下降笔'
            const dirColor = meta.direction === 'up' ? '#ef5350' : '#26a69a'
            return (
              `<div style="font-weight:600;margin-bottom:4px">${meta.date}</div>` +
              `<div>价格: <b>${Number(meta.price).toFixed(priceDecimals)}</b></div>` +
              `<div>方向: <b style="color:${dirColor}">${dirLabel}</b></div>`
            )
          }
          return ''
        },
      },
      grid: { left: '5%', right: '3%', top: 50, bottom: 70 },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: true,
        axisLabel: {
          color: '#8b949e',
          formatter: (v: string) => v.slice(0, 7),
          interval: Math.floor(dates.length / 8),
        },
        axisLine: { lineStyle: { color: '#30363d' } },
      },
      yAxis: {
        scale: true,
        axisLabel: { color: '#8b949e', formatter: (v: number) => v.toFixed(priceDecimals) },
        splitLine: { lineStyle: { color: '#161b22' } },
      },
      dataZoom: [
        { type: 'inside', xAxisIndex: 0, start: 0, end: 100 },
        {
          type: 'slider', xAxisIndex: 0, show: true, bottom: 20,
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
          z: 2,
        },
        {
          name: '笔',
          type: 'lines',
          coordinateSystem: 'cartesian2d',
          polyline: false,
          data: penLines,
          silent: true,
          z: 5,
        },
        {
          name: '端点',
          type: 'scatter',
          data: endpointData,
          symbolSize: 8,
          z: 10,
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

export default ChanChart
