// Detect the number of decimal places used by a price series.
// Looks at up to `sample` values, returns max observed decimals, capped at `cap`.
export function detectPriceDecimals(
  values: (number | null | undefined)[],
  cap = 4,
  sample = 200,
): number {
  let max = 0
  let n = 0
  for (let i = 0; i < values.length && n < sample; i++) {
    const v = values[i]
    if (v == null || !Number.isFinite(v)) continue
    n++
    // toFixed(cap) then strip trailing zeros to find true decimals
    const s = Math.abs(v).toFixed(cap)
    const dot = s.indexOf('.')
    if (dot === -1) continue
    let end = s.length - 1
    while (end > dot && s[end] === '0') end--
    const d = end - dot
    if (d > max) max = d
    if (max >= cap) break
  }
  // Always show at least 2 decimals for prices
  return Math.max(2, Math.min(cap, max))
}
