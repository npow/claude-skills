# vis-timeline Template and Data Patterns

## Contents
- Full HTML template
- Group and item data format
- Date conversion patterns
- Color class system
- Reload procedure

---

## Full HTML template

Copy this template verbatim. Replace GROUP_DATA, ITEM_DATA, COLOR_CLASSES, and WAIT_TEXT sections.

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://cdnjs.cloudflare.com/ajax/libs/vis-timeline/7.7.3/vis-timeline-graph2d.min.css" rel="stylesheet">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #1e1e2e; font-family: 'Segoe UI', sans-serif; color: #cdd6f4; }
  #timeline-container {
    width: 100%;
    height: 500px;
    margin: 20px 0;
  }
  #header {
    padding: 16px 20px 0;
    font-size: 18px;
    font-weight: 600;
    color: #cdd6f4;
  }
  #hint {
    padding: 8px 20px;
    font-size: 12px;
    color: rgba(255,255,255,0.3);
  }

  /* Dark theme overrides */
  .vis-timeline { background: #1e1e2e; border-color: rgba(255,255,255,0.1); }
  .vis-item { background-color: #2980b9; border-color: #2980b9; color: #fff; font-size: 12px; }
  .vis-item.vis-selected { background-color: #c0392b; border-color: #c0392b; }
  .vis-label { color: #cdd6f4; font-size: 13px; }
  .vis-time-axis .vis-text { color: rgba(255,255,255,0.5); font-size: 11px; }
  .vis-grid.vis-minor { border-color: rgba(255,255,255,0.05); }
  .vis-grid.vis-major { border-color: rgba(255,255,255,0.1); }
  .vis-panel.vis-left { border-right-color: rgba(255,255,255,0.15); }
  .vis-panel.vis-top, .vis-panel.vis-bottom { border-color: rgba(255,255,255,0.1); }
  .vis-current-time { background-color: rgba(255,100,100,0.4); }

  /* COLOR_CLASSES: one class per group, replace with actual group classNames */
  .vis-item.group-0 { background-color: #2980b9; border-color: #2980b9; }
  .vis-item.group-1 { background-color: #27ae60; border-color: #27ae60; }
  .vis-item.group-2 { background-color: #8e44ad; border-color: #8e44ad; }
  .vis-item.group-3 { background-color: #d35400; border-color: #d35400; }
  .vis-item.group-4 { background-color: #16a085; border-color: #16a085; }
  .vis-item.group-5 { background-color: #c0392b; border-color: #c0392b; }
</style>
</head>
<body>

<div id="header">Project Timeline</div>
<div id="hint">scroll to zoom · drag to pan · click item to select</div>
<div id="timeline-container"></div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/vis-timeline/7.7.3/vis-timeline-graph2d.min.js"></script>
<script>
// GROUP_DATA: one object per swimlane/workstream
const groups = new vis.DataSet([
  { id: 1, content: 'Workstream A' },
  { id: 2, content: 'Workstream B' },
  { id: 3, content: 'Workstream C' },
]);

// ITEM_DATA: one object per task/phase/milestone
const items = new vis.DataSet([
  { id: 1, content: 'Phase 1', start: '2025-01-01', end: '2025-03-31', group: 1, className: 'group-0' },
  { id: 2, content: 'Phase 2', start: '2025-04-01', end: '2025-06-30', group: 1, className: 'group-0' },
  { id: 3, content: 'Task A',  start: '2025-02-01', end: '2025-04-30', group: 2, className: 'group-1' },
  { id: 4, content: 'Task B',  start: '2025-05-01', end: '2025-08-31', group: 2, className: 'group-1' },
  { id: 5, content: 'Milestone', start: '2025-06-01', end: '2025-06-01', group: 3, className: 'group-2' },
]);

const container = document.getElementById('timeline-container');
const options = {
  stack: false,
  showMajorLabels: true,
  showMinorLabels: true,
  orientation: 'top',
  zoomMin: 1000 * 60 * 60 * 24 * 7,
  moveable: true,
  zoomable: true,
};

const timeline = new vis.Timeline(container, items, groups, options);
</script>
</body>
</html>
```

---

## Group and item data format

### Groups (swimlanes)

Each group defines one horizontal swimlane row.

```javascript
{ id: 1, content: 'Frontend' }
{ id: 2, content: 'Backend' }
{ id: 3, content: 'Infrastructure' }
```

- `id`: unique integer or string, referenced by item `group` field
- `content`: label shown in the left panel — this is the text used for `wait_for`

### Items (tasks / phases / milestones)

```javascript
{ id: 1, content: 'Phase 1', start: '2025-01-01', end: '2025-03-31', group: 1, className: 'group-0' }
```

- `id`: unique integer or string
- `content`: label shown inside the bar
- `start`: ISO date string "YYYY-MM-DD" — never a relative string
- `end`: ISO date string "YYYY-MM-DD" — for milestones, end equals start
- `group`: must match a group `id`
- `className`: CSS class string like `'group-0'` for color assignment

For a point milestone (no duration), set `end` equal to `start`.

---

## Date conversion patterns

Always compute concrete ISO dates. Never pass relative strings to vis-timeline.

### From quarter notation (Q1, Q2, Q3, Q4)

Use the year in context, or the current year if unspecified.

| Quarter | Start | End |
|---------|-------|-----|
| Q1 | YYYY-01-01 | YYYY-03-31 |
| Q2 | YYYY-04-01 | YYYY-06-30 |
| Q3 | YYYY-07-01 | YYYY-09-30 |
| Q4 | YYYY-10-01 | YYYY-12-31 |

### From month number ("month 1-3", "months 4 through 6")

Set base date = today (or a project start date if given). Add month offsets.

```
base = 2026-02-25 (today)
"month 1"   → base month       → 2026-02
"month 1-3" → base to base+2m  → 2026-02-01 to 2026-04-30
"month 4"   → base+3m          → 2026-05
```

Always resolve to the first day of the start month and last day of the end month.

### From sprint notation ("sprint 1", "sprint 2")

Default sprint length = 2 weeks unless stated. Set sprint 1 start = project start date or today.

```
sprint 1: base to base+13 days
sprint 2: base+14 to base+27 days
```

### From relative phrases ("next quarter", "in 6 months", "by end of year")

Compute from today: 2026-02-25.

| Phrase | Resolved |
|--------|---------|
| next quarter | 2026-04-01 to 2026-06-30 |
| in 6 months | 2026-08-25 |
| by end of year | 2026-12-31 |
| next month | 2026-03-01 to 2026-03-31 |

---

## Color class system

Assign one className per group. Add matching CSS in the style block. Colors are categorical — use a consistent palette across all groups.

| className | Color hex | Suggested use |
|-----------|-----------|---------------|
| group-0 | #2980b9 | First workstream / primary track |
| group-1 | #27ae60 | Second workstream / delivery |
| group-2 | #8e44ad | Third workstream / platform |
| group-3 | #d35400 | Fourth workstream / risk / ops |
| group-4 | #16a085 | Fifth workstream / infra |
| group-5 | #c0392b | Sixth workstream / critical / blocked |

To add more groups, continue the pattern with additional hex colors. Define one CSS rule per class:

```css
.vis-item.group-6 { background-color: #555566; border-color: #555566; }
```

Assign group className consistently: all items in group id 1 get `className: 'group-0'`, all items in group id 2 get `className: 'group-1'`, and so on.

---

## Reload procedure

After editing /tmp/timeline.html to fix an issue:

1. Call mcp__chrome-devtools__navigate_page with type: reload on the selected page.
2. Call mcp__chrome-devtools__wait_for on the same group label string used initially.
3. Call mcp__chrome-devtools__take_screenshot to verify the fix.

If the page was closed (error on reload):
1. Call mcp__chrome-devtools__new_page with url: file:///tmp/timeline.html.
2. Call mcp__chrome-devtools__wait_for then mcp__chrome-devtools__take_screenshot.
