# Troubleshooting

Failure diagnosis for the timeline skill. Match the symptom you observe, apply the fix, then reload and re-screenshot.

## Failure diagnosis table

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Items render as plain text with no colored bar shape | CSS CDN link tag is missing or failed to load | Verify the `<link>` tag for `vis-timeline-graph2d.min.css` is present and the URL matches exactly: `https://cdnjs.cloudflare.com/ajax/libs/vis-timeline/7.7.3/vis-timeline-graph2d.min.css` |
| All items appear stacked in one row, no swimlane separation | Groups not defined, or items missing `group` property, or `group` value doesn't match any group `id` | Define a `groups` DataSet with one entry per swimlane. Set `group: <id>` on every item. Confirm each item's `group` value matches a group `id`. |
| Timeline container is 0 height — nothing visible | Missing explicit height on `#timeline-container` | Set `height: 500px` (or larger) on the container div. vis-timeline does not auto-size. |
| Timeline renders but item bars have wrong colors or all the same color | `className` missing from items, or CSS class rules not defined in `<style>` | Add `className: 'group-N'` to each item. Add `.vis-item.group-N { background-color: #hex; border-color: #hex; }` to the `<style>` block for each N used. |
| Items appear at wrong dates or in wrong order | Relative date strings ("month 3", "Q2") passed directly to vis-timeline instead of ISO strings | Convert all date references to explicit "YYYY-MM-DD" strings. Use the date conversion table in TEMPLATE.md. |
| vis-timeline throws a parse error on dates | Invalid date format (e.g. "Month 1", "week 3", "TBD") in start or end fields | Replace every non-ISO date with a computed "YYYY-MM-DD" string. Never leave start or end as a non-date string. |
| wait_for times out — never resolves | The text passed to wait_for does not appear in the rendered page | Use the exact text of a group `content` label (e.g. "Frontend"). Avoid content labels with special characters that may be escaped in HTML. |
| Screenshot taken before render completes — shows blank or partial timeline | take_screenshot called without prior wait_for | Always call mcp__chrome-devtools__wait_for on a group label string before calling take_screenshot. |
| Items with stack: true overlap vertically within a group | stack option is true or omitted | Set `stack: false` in timeline options. This is required for Gantt-style horizontal swimlane rendering. |
| navigate_page reload fails with "page closed" error | Page was closed between open and reload | Call mcp__chrome-devtools__list_pages to find the correct page, then mcp__chrome-devtools__select_page before reloading. If page is gone, call new_page again. |
| Text on dark background is invisible (group labels, axis labels) | Dark theme CSS overrides missing from style block | Include all dark theme overrides from the template: .vis-label, .vis-time-axis .vis-text, .vis-grid classes, and .vis-timeline background. |
| Milestones (point events) show no bar | end is omitted for milestone items | Set `end` equal to `start` for milestone items. vis-timeline renders a point marker when start equals end. |

## Validating the template before opening

Before calling new_page, verify mentally:

- [ ] CSS CDN link tag is present with the exact URL
- [ ] JS CDN script tag is present with the exact URL
- [ ] groups DataSet has at least one entry with id and content
- [ ] Every item has: id, content, start ("YYYY-MM-DD"), end ("YYYY-MM-DD"), group (matching a group id), className
- [ ] No start or end value is a relative string, quarter name, or month number
- [ ] stack: false is in options
- [ ] #timeline-container has explicit height in pixels
- [ ] One CSS rule per group-N class exists in the style block
- [ ] Dark theme CSS overrides are present

## CDN URLs (exact — do not modify)

- JS: `https://cdnjs.cloudflare.com/ajax/libs/vis-timeline/7.7.3/vis-timeline-graph2d.min.js`
- CSS: `https://cdnjs.cloudflare.com/ajax/libs/vis-timeline/7.7.3/vis-timeline-graph2d.min.css`

Both must be present. The CSS CDN is what gives items their bar shape. The JS CDN provides the Timeline constructor. Missing either one causes silent rendering failure.

## Page selection

When multiple pages are open, the Chrome DevTools MCP may drift to a different page after `new_page`. Before calling `take_screenshot`, call `mcp__chrome-devtools__list_pages` and then `mcp__chrome-devtools__select_page` with `bringToFront: true` on the correct page ID to ensure the screenshot captures the right page.

