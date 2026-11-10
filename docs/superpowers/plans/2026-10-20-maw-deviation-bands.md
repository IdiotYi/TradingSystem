# MAW deviation bands implementation plan

Goal: Apply the requested indicator-test changes in the current checkout.

Design: MAW5/10/20/60/120/243 use solid center lines. Selecting a MAW
legend item controls its center line plus three pairs of solid, thinner,
translucent bands. Bands are MAW × (1 ± r), for r = 0.382, 0.5, 0.618.
Each group retains one legend item, a consistent color, distinct tooltip labels,
and null gaps. Existing non-MAW indicators and strategies retain their behavior.
MAW243 uses the existing backend calculation and full history before chart slicing.

Implementation and validation:

- [x] Add backend regression coverage for MAW243 warmup, weighting, adjustment, and missing data.
- [x] Add frontend tests for six band values, null handling, and actual ECharts legend grouping.
- [x] Extend the analysis response and TypeScript type with maw243.
- [x] Generate MAW series groups and integrate them into the indicator-test chart.
- [x] Run focused tests, frontend build, and local API smoke test; verify chart rendering.

Validation: 10 focused backend tests and 2 frontend tests passed; production
build passed. A headless Edge check loaded 002156, verified all 42 MAW series,
hid MAW20 and observed 35 remaining series, and rendered MAW243 plus all six
bands without page errors. The local analysis API returned 4,546 aligned
MAW243 values, with the latest value 57.6967.

Work stays in the current checkout so the existing local development servers
serve the result directly. Preserve the earlier backend responsiveness changes.
