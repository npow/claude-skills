---
name: table
description: Renders interactive sortable, filterable tables in the browser using pure vanilla HTML/CSS/JS — no external dependencies. Use when the user wants to compare alternatives, show a feature matrix, display structured data, create a comparison table, render a sortable table, show options side-by-side, or visualize rows and columns of data. Always renders live in browser — never as static text.
allowed-tools: Write, Edit, mcp__chrome-devtools__new_page, mcp__chrome-devtools__navigate_page, mcp__chrome-devtools__wait_for, mcp__chrome-devtools__take_screenshot, mcp__chrome-devtools__list_pages
---

# Table

Renders interactive sortable, filterable tables in the browser by writing a zero-dependency HTML file and opening it via Chrome DevTools.

## Workflow

1. **Extract columns and rows** — identify column names, value types (text, number, badge, rating, boolean, tag), and all row data from user context. See [TEMPLATE.md](TEMPLATE.md) for column type definitions.
2. **Map column types** — assign a `type` to each column: text, number, badge, rating, boolean, or tag. See [TEMPLATE.md](TEMPLATE.md) for rendering rules per type.
3. **Write the HTML file** — write a complete self-contained file to `/tmp/table.html` using the vanilla JS template. See [TEMPLATE.md](TEMPLATE.md) for the full template with sort and filter implementation.
4. **Open in browser** — call `mcp__chrome-devtools__new_page` with `url: file:///tmp/table.html`.
5. **Wait for render** — call `mcp__chrome-devtools__wait_for` on the text of the first column header. Timeout 8000ms.
6. **Take screenshot** — call `mcp__chrome-devtools__take_screenshot` and verify all columns and rows are visible without horizontal overflow.
7. **Fix and reload if broken** — if screenshot shows problems, edit `/tmp/table.html`, then call `mcp__chrome-devtools__navigate_page` with `type: reload`. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Self-review checklist

Before delivering, verify ALL:

- [ ] Screenshot shows all columns with readable headers and all rows with populated cells
- [ ] Sort works: clicking a column header changes row order and shows a ▲ or ▼ indicator
- [ ] Filter works: search input above the table is present with `placeholder="Filter..."`
- [ ] Dark background (#1e1e2e) is applied — not white or gray
- [ ] No horizontal scroll is visible when the table fits the viewport
- [ ] Sticky header (`position: sticky; top: 0`) is present in the CSS
- [ ] All CSS color values use `var(--token)` references — no hardcoded hex in element styles
- [ ] `wait_for` was called before `take_screenshot`
- [ ] Rating cells render as star characters (e.g. ⭐⭐⭐), not raw numbers
- [ ] Boolean cells render as ✓ or ✗, not true/false

## Golden rules

Hard rules. Never violate these.

1. **Always define colors as CSS variables on `:root`.** Never write a hex color value directly into an element style. Every color used must reference a `var(--token)`.
2. **Always include both sort AND filter.** A table missing either feature is incomplete. Both must be present in every output, even for small datasets.
3. **Never use an external library.** Implement sort and filter in plain JS. The complete implementation is under 50 lines. See [TEMPLATE.md](TEMPLATE.md).
4. **Always use `position: sticky; top: 0` on `thead`.** Apply this to every table regardless of row count.
5. **Always call `wait_for` before `take_screenshot`.** Wait on the first column header text string. Never screenshot immediately after `new_page`.
6. **Always use `overflow-x: auto` on the table container.** Without it, wide tables break the page layout.
7. **Always `.toLowerCase()` both sides in the filter comparison.** Case-sensitive filtering breaks on mixed-case data.

## Reference files

| File | Contents |
|------|----------|
| [TEMPLATE.md](TEMPLATE.md) | Complete vanilla JS HTML template with full sort and filter implementation, CSS design tokens, column type rendering rules |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Failure diagnosis table: symptoms, likely causes, and fixes |
