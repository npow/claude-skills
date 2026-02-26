---
name: chart
description: Renders interactive charts in the browser using Chart.js. Use when the user wants to visualize data, plot numbers, draw a bar chart, line chart, pie chart, doughnut chart, radar chart, graph metrics, compare benchmarks, show a cost curve, or display a time series. Always renders live in browser — never as a static image.
allowed-tools: Write, Edit, mcp__chrome-devtools__new_page, mcp__chrome-devtools__navigate_page, mcp__chrome-devtools__wait_for, mcp__chrome-devtools__take_screenshot, mcp__chrome-devtools__list_pages
---

# Chart

Renders interactive charts in the browser using Chart.js from context-supplied data and chart type.

## Workflow

1. **Extract data and chart type** — identify labels, datasets, and chart type (bar, line, pie, doughnut, radar) from the user's request or conversation context.
2. **Choose colors** — assign dataset colors from the standard palette. See [TEMPLATE.md](TEMPLATE.md) for the palette.
3. **Write the HTML file** — write a complete self-contained file to `/tmp/chart.html` using the Chart.js template matching the chart type. See [TEMPLATE.md](TEMPLATE.md) for all templates.
4. **Open in browser** — call `mcp__chrome-devtools__new_page` with `url: file:///tmp/chart.html`.
5. **Wait for render** — call `mcp__chrome-devtools__wait_for` on a static DOM element (e.g. `<h2 id="ready">` added above the canvas). Chart.js renders to canvas — canvas text is NOT detectable by `wait_for`. Timeout 10000ms.
6. **Take screenshot** — call `mcp__chrome-devtools__take_screenshot` and verify the chart is visible with labeled axes and readable text.
7. **Fix and reload if broken** — if screenshot shows problems, edit `/tmp/chart.html`, then call `mcp__chrome-devtools__navigate_page` with `type: reload`. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Self-review checklist

Before delivering, verify ALL:

- [ ] Screenshot shows the chart with visible title, labels, and data — no blank canvas
- [ ] Chart text is readable on dark background — not invisible black-on-dark
- [ ] Container div has explicit `height` (e.g. `500px`) in CSS — not just on the canvas element
- [ ] Both `responsive: true` and `maintainAspectRatio: false` are set in chart options
- [ ] `Chart.defaults.color` and `Chart.defaults.borderColor` are set before `new Chart()`
- [ ] Dataset colors are from the standard palette — no ad-hoc inline colors
- [ ] CDN URL is exactly `https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js`
- [ ] `wait_for` is called with the chart title text before `take_screenshot`

## Golden rules

Hard rules. Never violate these.

1. **Never set width or height on the canvas element.** Set dimensions on the wrapper div via CSS (`height: 500px`). Canvas attributes override Chart.js responsive sizing.
2. **Always set both `responsive: true` and `maintainAspectRatio: false`.** Either alone is insufficient — the chart collapses to 0 height without both.
3. **Always set `Chart.defaults.color` and `Chart.defaults.borderColor` before creating any chart.** Without them, all text renders as black and is invisible on the dark background.
4. **Always use `new_page` for first open.** Use `mcp__chrome-devtools__new_page` with `url: file:///tmp/chart.html`. Use `navigate_page` with `type: reload` only for subsequent fixes.
5. **Always add a static `<h2 id="ready">Title</h2>` above the canvas and `wait_for` it.** Chart.js renders text onto canvas — canvas text is invisible to `wait_for`. The static element is the only reliable render signal.
6. **Never hardcode colors inline in datasets.** Always use colors from the standard palette array defined in TEMPLATE.md.

## Reference files

| File | Contents |
|------|----------|
| [TEMPLATE.md](TEMPLATE.md) | Complete Chart.js HTML templates for bar, line, and pie/doughnut; color palette; data format patterns |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Failure diagnosis table: symptoms, causes, fixes |
