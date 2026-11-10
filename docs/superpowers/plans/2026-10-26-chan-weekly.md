# Weekly Chan chart

Add a weekly option to the existing Chan period selector, using the same chart
and pen analysis. Preserve the current daily default and existing appearance.

Weekly bars use the cached adjusted daily data, grouped Monday through Sunday:
first open, maximum high, minimum low, last close. Label each bar with its last
actual trading date. Exclude daily records after the requested end before
aggregation, so a midweek cutoff never reads later trading days. Include the
available part of the final week; do not manufacture bars for empty weeks.
Filter the start date by the resulting weekly bar date. Retain the ten-bar
minimum and apply pen detection to weekly bars. Refreshing daily data must also
update the weekly view. The minute refresh endpoint remains minute-only.

- [x] Test aggregation, holiday/empty weeks, midweek cutoff, weekly pens, API validation.
- [x] Extend backend period handling and aggregate before pen detection.
- [x] Update frontend types, selector, date labels, and daily refresh integration.
- [x] Run focused tests, build, local API and browser checks.

Validation: 27 Chan tests passed; frontend production build passed. After
restarting the backend, the local weekly API returned 195 bars and 17 pens
for 002156 over the default range. Headless Edge confirmed selecting 周线
renders the chart, hides the minute refresh button, and produces no page errors.
