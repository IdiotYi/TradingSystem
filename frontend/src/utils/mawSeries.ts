/** One legend item controls the MAW center and all six deviation lines. */
export function createMawSeries(name: string, values: (number | null)[], color: string) {
  const line = (id: string, data: (number | null)[], width: number, opacity: number) => ({
    id, name, type: 'line' as const, xAxisIndex: 0, yAxisIndex: 0, data,
    lineStyle: { color, width, opacity, type: 'solid' as const },
    itemStyle: { color }, showSymbol: false, connectNulls: false,
    z: id === name ? 3 : 2,
  })

  return [
    line(name, values, 1.5, 1),
    ...[0.382, 0.5, 0.618].flatMap((ratio, index) =>
      [1, -1].map(sign => line(
        `${name} ${sign > 0 ? '+' : '-'}${Number((ratio * 100).toFixed(1))}%`,
        values.map(value => value == null ? null : value * (1 + sign * ratio)),
        1, 0.55 - index * 0.12,
      )),
    ),
  ]
}
