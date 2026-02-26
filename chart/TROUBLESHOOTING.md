# Troubleshooting

Failure diagnosis for the chart skill. Match the symptom you observe, apply the fix, then reload and re-screenshot.

## Failure diagnosis table

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Canvas is blank — no chart renders at all | `Chart.defaults.color` not set before `new Chart()`, or container div has no explicit height | Add `Chart.defaults.color = '#cdd6f4'` and `Chart.defaults.borderColor = 'rgba(255,255,255,0.1)'` before `new Chart()`. Ensure `.chart-container` has `height: 500px` in CSS. |
| Chart renders but all text (title, labels, ticks) is invisible | Forgot to set `Chart.defaults.color` — text defaults to black, invisible on dark background | Add `Chart.defaults.color = '#cdd6f4'` before `new Chart()`. |
| Chart renders but collapses to 0 height or shows as a thin line | `responsive: true` without `maintainAspectRatio: false`, or container div has no height | Set both `responsive: true` and `maintainAspectRatio: false` in options. Add explicit `height` to `.chart-container`. |
| `width` or `height` HTML attributes on the canvas cause wrong sizing | Canvas element has explicit `width`/`height` attributes | Remove `width` and `height` from the `<canvas>` element. Control size via CSS on the wrapper div only. |
| CDN script fails to load — `Chart is not defined` error in console | Wrong CDN URL or network issue | Confirm URL is exactly `https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js` |
| `wait_for` times out | Chart.js renders all text (title, labels, ticks) onto a `<canvas>` element — canvas text is NOT in the DOM and `wait_for` cannot detect it | Instead of waiting on the chart title, add a visible `<h2 id="chart-title">` element above the canvas with the same title text, and `wait_for` that. Or wait for a static string like the page `<title>` tag content. |
| Screenshot is taken before chart renders — shows blank page | `take_screenshot` called immediately after `new_page` without waiting | Add a static `<h2 id="ready">` element to the HTML, call `wait_for ["ready"]` before `take_screenshot`. Canvas content is not detectable by `wait_for`. |
| Bar segments or lines are all the same color | Dataset colors not assigned from PALETTE, or all datasets share PALETTE[0] | Each dataset must use a different palette index: `PALETTE[0]`, `PALETTE[1]`, `PALETTE[2]`, etc. |
| Pie/doughnut shows slices but they're all the same color | `backgroundColor` on the dataset is a single string instead of an array | For pie/doughnut, `backgroundColor` must be an array: `[PALETTE[0], PALETTE[1], PALETTE[2], ...]` |
| `navigate_page reload` fails with page-not-found or closed error | The browser tab was closed between open and reload | Call `mcp__chrome-devtools__list_pages` to find the page, then `select_page`, then reload. If gone, call `new_page` again. |

## Reload procedure

After editing `/tmp/chart.html`:

1. Call `mcp__chrome-devtools__navigate_page` with `{ type: 'reload' }` on the selected page.
2. Call `mcp__chrome-devtools__wait_for` on the chart title text.
3. Call `mcp__chrome-devtools__take_screenshot` to verify.

If the page was closed:
1. Call `mcp__chrome-devtools__new_page` with `url: file:///tmp/chart.html`.
2. Proceed with wait_for → take_screenshot.

## Validating the template before opening

Before calling `new_page`, verify:

- [ ] `Chart.defaults.color = '#cdd6f4'` appears before `new Chart()`
- [ ] `Chart.defaults.borderColor = 'rgba(255,255,255,0.1)'` appears before `new Chart()`
- [ ] `.chart-container` has an explicit `height` in CSS (not on the `<canvas>` element)
- [ ] Chart options include both `responsive: true` and `maintainAspectRatio: false`
- [ ] `plugins.title.display` is `true` and `plugins.title.text` is set
- [ ] All dataset colors reference `PALETTE[N]` — no inline hex strings
- [ ] CDN script tag is present with the correct URL

## If none of the above applies

Take a screenshot and inspect: is the page fully white (CDN failed), fully dark with no chart (JS error), or dark with a chart but wrong output? Check the browser console via `mcp__chrome-devtools__list_console_messages` for JavaScript errors, then fix the specific error reported.
