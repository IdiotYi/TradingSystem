// 韦氏移动平均线 (Wei's Moving Average)
// t = 2 / (N+1)
// blend[i] = t*open[i] + (1-t)*close[i]
// WMA[i] = 0.5*blend[i] + 0.5*WMA[i-1]
// Seed: WMA[0] = blend[0]
export function computeWMA(
  open: (number | null)[],
  close: (number | null)[],
  period: number,
): (number | null)[] {
  const n = close.length
  const t = 2 / (period + 1)
  const out: (number | null)[] = new Array(n).fill(null)
  let prev: number | null = null
  for (let i = 0; i < n; i++) {
    const o = open[i]
    const c = close[i]
    if (o == null || c == null) {
      out[i] = prev
      continue
    }
    const blend = t * o + (1 - t) * c
    const cur = prev == null ? blend : 0.5 * blend + 0.5 * prev
    out[i] = cur
    prev = cur
  }
  return out
}

// WMAPred: 用前一日的 WMA 与当日开盘价预测当日 WMA 走势
// WMAPred[i] = 0.5*WMA[i-1] + 0.5*open[i]
// 首日无前日 WMA，返回 null
export function computeWMAPred(
  open: (number | null)[],
  wma: (number | null)[],
): (number | null)[] {
  const n = open.length
  const out: (number | null)[] = new Array(n).fill(null)
  for (let i = 1; i < n; i++) {
    const o = open[i]
    const prev = wma[i - 1]
    if (o == null || prev == null) continue
    out[i] = 0.5 * prev + 0.5 * o
  }
  return out
}

// 指数移动平均线 (Exponential Moving Average)
// alpha = 2 / (period + 1)
// 种子：第一个有效 close
export function computeEMA(
  close: (number | null)[],
  period: number,
): (number | null)[] {
  const n = close.length
  const out: (number | null)[] = new Array(n).fill(null)
  const alpha = 2 / (period + 1)
  let prev: number | null = null
  for (let i = 0; i < n; i++) {
    const c = close[i]
    if (c == null) { out[i] = prev; continue }
    const cur = prev == null ? c : alpha * c + (1 - alpha) * prev
    out[i] = cur
    prev = cur
  }
  return out
}
// 简单移动平均线 (Simple Moving Average)
// 不足 period 个有效值时为 null
export function computeSMA(
  close: (number | null)[],
  period: number,
): (number | null)[] {
  const n = close.length
  const out: (number | null)[] = new Array(n).fill(null)
  let sum = 0
  let count = 0
  const buf: (number | null)[] = []
  for (let i = 0; i < n; i++) {
    const c = close[i]
    buf.push(c)
    if (c != null) { sum += c; count++ }
    if (buf.length > period) {
      const old = buf.shift()!
      if (old != null) { sum -= old; count-- }
    }
    out[i] = buf.length === period && count === period ? sum / period : null
  }
  return out
}
