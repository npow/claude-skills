# Troubleshooting

Failure diagnosis for the table skill. Match the symptom you observe, apply the fix, then reload and re-screenshot.

## Failure diagnosis table

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Clicking a column header does nothing | Event listener attached in `buildHeader()` but `buildHeader()` was not called, or the `sortable: true` flag is missing on the column | Verify the column definition has `sortable: true` and that `render()` is called on init |
| Sorting changes order but ▲/▼ indicator is missing | `sort-indicator` span is not inside the `<th>`, or `sortKey` is not being compared correctly | Confirm `buildHeader()` injects `<span class="sort-indicator">` and checks `sortKey === col.key` |
| Filter input does nothing | `input` event listener not attached, or filter is comparing against the wrong field | Confirm the `addEventListener('input', ...)` block is present and `columns.some(...)` iterates over all columns |
| Filter is case-sensitive (partial matches fail) | Missing `.toLowerCase()` on one or both sides of the comparison | Apply `.toLowerCase()` to both `filterText` and `String(row[col.key] ?? '').toLowerCase()` |
| Table overflows horizontally, page has a scrollbar | Missing `overflow-x: auto` on the `.table-wrap` div, or `min-width` not set on `<table>` | Add `overflow-x: auto` to `.table-wrap` and `min-width: 480px` to `table` |
| Page is white / light background instead of dark | `background: var(--bg)` missing from `body`, or CSS variables not defined on `:root` | Confirm `:root` block is present with all seven `--` variables and `body` sets `background: var(--bg)` |
| Rating cells show raw number instead of stars | Cell renderer does not handle `type: 'rating'`, or the `switch` case is missing | Confirm the `case 'rating':` branch uses `'⭐'.repeat(n)` |
| Boolean cells show `true`/`false` text | Cell renderer is not handling `type: 'boolean'`, or the value coercion check is wrong | Confirm `case 'boolean':` checks `=== true`, `=== 'true'`, `=== 'yes'`, and `=== 1` |
| Badge / tag cells show plain text | Cell renderer is not handling `type: 'badge'` or `type: 'tag'`, or `colorFor()` is not defined | Confirm `case 'badge':` and `case 'tag':` call `colorFor(value)` and inject a `<span>` with inline `style` |
| Table body is empty but data array is populated | Column `key` values do not match property names in data objects | Check that every `key` in `columns` exactly matches a property name in the data array (case-sensitive) |
| Header does not stick when scrolling | `position: sticky; top: 0` missing from `thead`, or a parent element has `overflow: hidden` | Confirm `thead` has `position: sticky; top: 0; z-index: 2` and no ancestor has `overflow: hidden` |
| `wait_for` times out | Waiting on text that does not appear in the rendered page | Change `wait_for` text to match the exact label of the first column (e.g. `"Name"` or `"Option"`) |
| Screenshot taken before table renders | `take_screenshot` called immediately after `new_page` | Always call `wait_for` on the first column header text before calling `take_screenshot` |
| Colors are hardcoded hex values in element styles | CSS variables not used consistently | Move all color values to `:root` tokens and replace inline hex values with `var(--token)` |
| Empty table shows no feedback | `#empty-msg` div missing or `display: none` not toggled | Confirm the `#empty-msg` div exists and `render()` toggles its `display` between `'none'` and `'block'` |

## Reload procedure

After editing `/tmp/table.html`:

1. Call `mcp__chrome-devtools__navigate_page` with `{ type: 'reload' }` on the currently selected page.
2. Call `mcp__chrome-devtools__wait_for` on the first column header text.
3. Call `mcp__chrome-devtools__take_screenshot` to verify the fix.

If the page was closed (error on reload):

1. Call `mcp__chrome-devtools__new_page` with `url: file:///tmp/table.html`.
2. Proceed with `wait_for` then `take_screenshot`.

## Pre-open validation checklist

Before calling `new_page`, verify:

- [ ] `const data = [...]` is a valid JS array with at least one object
- [ ] `const columns = [...]` is a valid JS array and every `key` matches a property in the data objects
- [ ] Every column has a `type` field set to one of: `text`, `number`, `badge`, `rating`, `boolean`, `tag`
- [ ] Both `/* DATA */` and `/* COLUMNS */` placeholders have been replaced
- [ ] Both `/* TITLE */` placeholders (in `<title>` and `<h1>`) have been replaced
- [ ] `:root` block contains all seven CSS variable declarations
- [ ] `overflow-x: auto` is present on `.table-wrap`
- [ ] `position: sticky; top: 0` is present on `thead`
