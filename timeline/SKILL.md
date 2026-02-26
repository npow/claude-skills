---
name: timeline
description: Renders interactive Gantt-style project timelines and roadmaps in the browser using vis-timeline. Use when the user mentions timeline, gantt, roadmap, project plan, phases, milestones, schedule, sprints, quarters, or asks when things happen or to show a schedule. Writes /tmp/timeline.html and opens it via Chrome DevTools MCP.
allowed-tools: Write, Edit, mcp__chrome-devtools__new_page, mcp__chrome-devtools__navigate_page, mcp__chrome-devtools__wait_for, mcp__chrome-devtools__take_screenshot, mcp__chrome-devtools__list_pages
---

# Timeline

Renders interactive Gantt-style timelines and roadmaps in the browser using vis-timeline from context-supplied phases, milestones, and tasks.

## Workflow

1. **Extract items and groups** — identify tasks/phases (items) and workstreams/swimlanes (groups) from context. See [TEMPLATE.md](TEMPLATE.md) for data shapes.
2. **Convert all dates to ISO strings** — translate every vague time reference ("month 1-3", "Q2", "next sprint") to "YYYY-MM-DD" format. Default base date is today. See [TEMPLATE.md](TEMPLATE.md) for conversion patterns.
3. **Assign group colors** — give each group a className and matching CSS color class. See [TEMPLATE.md](TEMPLATE.md) for the color class system.
4. **Write the HTML file** — write a complete self-contained file to /tmp/timeline.html using the vis-timeline template. See [TEMPLATE.md](TEMPLATE.md) for the full template.
5. **Open in browser** — call mcp__chrome-devtools__new_page with url: file:///tmp/timeline.html.
6. **Wait for render** — call mcp__chrome-devtools__wait_for on a group label string that appears after vis-timeline renders. Timeout 10000ms.
7. **Take screenshot** — call mcp__chrome-devtools__take_screenshot and verify all items and group labels are visible.
8. **Fix and reload if broken** — if screenshot shows problems, edit /tmp/timeline.html, then call mcp__chrome-devtools__navigate_page with type: reload. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Self-review checklist

Before delivering, verify ALL:

- [ ] Screenshot shows all group swimlane labels in the left panel
- [ ] Screenshot shows colored item bars spanning correct date ranges
- [ ] No items are invisible or rendering as unstyled plain text (CSS CDN loaded)
- [ ] Timeline container has explicit pixel height — vis-timeline did not collapse to 0px
- [ ] All start/end values in items array are ISO date strings "YYYY-MM-DD", not relative strings
- [ ] Every item has a group property matching a group id
- [ ] stack: false is present in timeline options
- [ ] Dark theme CSS overrides are present and text is readable on dark background
- [ ] wait_for was called before take_screenshot

## Golden rules

Hard rules. Never violate these.

1. **Never use relative date strings.** Always convert vague references ("month 1", "Q3", "next sprint") to explicit ISO date strings "YYYY-MM-DD" before passing to vis-timeline. Relative strings will throw a parse error or render at wrong positions.
2. **Always set explicit pixel height on the container div.** vis-timeline collapses to 0px without it. Use height: 500px; width: 100%; at minimum.
3. **Always include the CSS CDN link tag.** Without the vis-timeline CSS CDN, items render as unstyled plain text with no bar shape or color.
4. **Use `stack: true` when items within a group overlap in time; use `stack: false` only when items are guaranteed non-overlapping.** `stack: false` causes overlapping items in the same group to render on top of each other, hiding all but the topmost. Default to `stack: true` for safety.
5. **Always assign every item to a group.** Ungrouped items pile into a single unlabelled row, defeating swimlane separation.
6. **Always call wait_for on a group label string before screenshotting.** The group label only appears after vis-timeline fully renders; screenshotting before it appears captures a blank or partially-rendered page.
7. **Always use new_page for first open.** Use mcp__chrome-devtools__new_page with url: file:///tmp/timeline.html. Use navigate_page with type: reload only for subsequent fixes.

## Reference files

| File | Contents |
|------|----------|
| [TEMPLATE.md](TEMPLATE.md) | Complete vis-timeline HTML template, date conversion patterns, color class system, group/item data format |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Failure diagnosis table: symptoms, causes, fixes |
