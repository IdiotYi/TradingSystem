import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as echarts from 'echarts'

// Use the project's TypeScript compiler so tests also run on Node 18.
const source = readFileSync(new URL('../src/utils/mawSeries.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
})
const { createMawSeries } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)

test('MAW has three symmetric percentage bands and preserves missing values', () => {
  const series = createMawSeries('MAW243', [null, 100, 200], '#ff00ff')
  assert.equal(series.length, 7)
  assert.equal(new Set(series.map(line => line.id)).size, 7)
  assert.deepEqual(series[0].data, [null, 100, 200])
  const values = series.slice(1).map(line => line.data[1]).sort((a, b) => a - b)
  const expected = [38.2, 50, 61.8, 138.2, 150, 161.8]
  values.forEach((value, i) => assert.ok(Math.abs(value - expected[i]) < 1e-9))
  for (const line of series) {
    assert.equal(line.data[0], null)
    assert.equal(line.data[2], line.data[1] * 2)
    assert.equal(line.lineStyle.type, 'solid')
  }
})

test('ECharts legend hides and restores an entire MAW group independently', () => {
  const chart = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 800, height: 400 })
  try {
    chart.setOption({
      animation: false, legend: { data: ['MAW5', 'MAW243'] },
      xAxis: { type: 'category', data: ['day1', 'day2'] }, yAxis: { type: 'value' },
      series: [
        ...createMawSeries('MAW5', [100, 110], '#ffffff'),
        ...createMawSeries('MAW243', [80, 90], '#ff00ff'),
      ],
    })
    const visible = () => {
      const names = []
      chart.getModel().eachSeries(series => names.push(series.name))
      return names
    }
    assert.equal(visible().length, 14)
    assert.ok(chart.renderToSVGString().includes('<path'))
    chart.dispatchAction({ type: 'legendUnSelect', name: 'MAW5' })
    assert.deepEqual(visible(), Array(7).fill('MAW243'))
    chart.dispatchAction({ type: 'legendUnSelect', name: 'MAW243' })
    assert.deepEqual(visible(), [])
    chart.dispatchAction({ type: 'legendSelect', name: 'MAW5' })
    assert.deepEqual(visible(), Array(7).fill('MAW5'))
  } finally {
    chart.dispose()
  }
})
