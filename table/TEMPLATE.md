# Table HTML Template

Complete vanilla JS template for sortable, filterable tables. Copy verbatim and replace the `DATA`, `COLUMNS`, and `TITLE` sections.

## Contents
- CSS design tokens
- Column type definitions
- Full HTML template with sort and filter implementation
- Cell rendering reference
- Data shape examples

---

## CSS design tokens

These seven variables must be defined on `:root`. Never hardcode their hex values anywhere else in the file.

```
--bg:          #1e1e2e   (page background)
--surface:     #2a2a3e   (table header and card surfaces)
--border:      rgba(255,255,255,0.1)   (all borders)
--text:        #cdd6f4   (primary text)
--text-muted:  rgba(255,255,255,0.4)  (secondary text, placeholders)
--accent:      #2980b9   (sort indicator, focus ring)
--hover:       rgba(255,255,255,0.05) (row hover background)
```

---

## Column type definitions

Each column object has: `key` (matches data object property), `label` (header display text), `sortable` (true/false), `type` (one of the six types below).

| Type | Data value | Rendered as |
|------|-----------|-------------|
| `text` | Any string | Plain text |
| `number` | Integer or float | Right-aligned, sorted numerically |
| `badge` | String | Colored pill with auto-assigned background |
| `rating` | Integer 1–5 | Star characters: ⭐ × N |
| `boolean` | true / false | ✓ (green) or ✗ (red) |
| `tag` | String | Small colored label (same as badge but smaller font) |

---

## Full HTML template

Replace `/* DATA */`, `/* COLUMNS */`, `/* TITLE */` with actual values. Do not modify the sort or filter logic.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>/* TITLE */</title>
<style>
  :root {
    --bg: #1e1e2e;
    --surface: #2a2a3e;
    --border: rgba(255,255,255,0.1);
    --text: #cdd6f4;
    --text-muted: rgba(255,255,255,0.4);
    --accent: #2980b9;
    --hover: rgba(255,255,255,0.05);
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 14px;
    padding: 32px;
    min-height: 100vh;
  }

  h1 {
    font-size: 20px;
    font-weight: 600;
    margin-bottom: 20px;
    color: var(--text);
  }

  .toolbar {
    margin-bottom: 16px;
  }

  #filter {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text);
    font-size: 14px;
    padding: 8px 14px;
    width: 280px;
    outline: none;
    transition: border-color 0.15s;
  }

  #filter::placeholder { color: var(--text-muted); }
  #filter:focus { border-color: var(--accent); }

  .table-wrap {
    overflow-x: auto;
    border-radius: 8px;
    border: 1px solid var(--border);
  }

  table {
    width: 100%;
    border-collapse: collapse;
    min-width: 480px;
  }

  thead {
    position: sticky;
    top: 0;
    z-index: 2;
  }

  th {
    background: var(--surface);
    color: var(--text);
    font-weight: 600;
    font-size: 13px;
    text-align: left;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    user-select: none;
  }

  th.sortable {
    cursor: pointer;
  }

  th.sortable:hover {
    color: var(--accent);
  }

  th .sort-indicator {
    display: inline-block;
    margin-left: 6px;
    color: var(--accent);
    font-size: 11px;
    width: 10px;
    text-align: center;
  }

  td {
    padding: 11px 16px;
    border-bottom: 1px solid var(--border);
    color: var(--text);
    vertical-align: middle;
  }

  tr:last-child td { border-bottom: none; }

  tbody tr:hover td { background: var(--hover); }

  td.type-number { text-align: right; font-variant-numeric: tabular-nums; }

  .badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
    white-space: nowrap;
  }

  .tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
    white-space: nowrap;
  }

  .bool-true  { color: #27ae60; font-weight: 600; }
  .bool-false { color: #c0392b; font-weight: 600; }

  .rating { letter-spacing: 1px; }

  #empty-msg {
    text-align: center;
    color: var(--text-muted);
    padding: 32px;
    font-size: 14px;
    display: none;
  }
</style>
</head>
<body>

<h1>/* TITLE */</h1>

<div class="toolbar">
  <input id="filter" type="text" placeholder="Filter..." autocomplete="off">
</div>

<div class="table-wrap">
  <table id="tbl">
    <thead id="thead"></thead>
    <tbody id="tbody"></tbody>
  </table>
  <div id="empty-msg">No matching rows.</div>
</div>

<script>
// ── DATA ──────────────────────────────────────────────────────────────────────
const data = /* DATA */;

// ── COLUMN DEFINITIONS ────────────────────────────────────────────────────────
// key: must match a property name in each data object
// label: displayed in column header
// sortable: true or false
// type: 'text' | 'number' | 'badge' | 'rating' | 'boolean' | 'tag'
const columns = /* COLUMNS */;

// ── BADGE / TAG COLOR MAP ─────────────────────────────────────────────────────
// Auto-assigned; values cycle through this palette by first appearance.
const PALETTE = [
  { bg: 'rgba(41,128,185,0.25)',  text: '#5dade2' },
  { bg: 'rgba(39,174,96,0.25)',   text: '#52be80' },
  { bg: 'rgba(192,57,43,0.25)',   text: '#ec7063' },
  { bg: 'rgba(142,68,173,0.25)',  text: '#af7ac5' },
  { bg: 'rgba(211,84,0,0.25)',    text: '#eb984e' },
  { bg: 'rgba(22,160,133,0.25)', text: '#45b39d' },
  { bg: 'rgba(241,196,15,0.2)',   text: '#f4d03f' },
];
const colorMap = {};
let colorIdx = 0;

function colorFor(val) {
  const key = String(val).toLowerCase();
  if (!colorMap[key]) colorMap[key] = PALETTE[colorIdx++ % PALETTE.length];
  return colorMap[key];
}

// ── CELL RENDERING ────────────────────────────────────────────────────────────
function renderCell(value, type) {
  if (value === null || value === undefined || value === '') return '<span style="color:var(--text-muted)">—</span>';

  switch (type) {
    case 'number':
      return `<td class="type-number">${value}</td>`;

    case 'rating': {
      const n = Math.min(5, Math.max(0, Number(value)));
      return `<td><span class="rating">${'⭐'.repeat(n)}</span></td>`;
    }

    case 'boolean': {
      const yes = value === true || value === 'true' || value === 'yes' || value === 1;
      return yes
        ? `<td><span class="bool-true">✓</span></td>`
        : `<td><span class="bool-false">✗</span></td>`;
    }

    case 'badge': {
      const c = colorFor(value);
      return `<td><span class="badge" style="background:${c.bg};color:${c.text}">${value}</span></td>`;
    }

    case 'tag': {
      const c = colorFor(value);
      return `<td><span class="tag" style="background:${c.bg};color:${c.text}">${value}</span></td>`;
    }

    default: // 'text'
      return `<td>${value}</td>`;
  }
}

// ── SORT STATE ────────────────────────────────────────────────────────────────
let sortKey = null;
let sortDir = 1; // 1 = ascending, -1 = descending
let filterText = '';

// ── RENDER ────────────────────────────────────────────────────────────────────
function buildHeader() {
  const ths = columns.map(col => {
    const cls = col.sortable ? 'sortable' : '';
    const active = sortKey === col.key;
    const indicator = active ? (sortDir === 1 ? '▲' : '▼') : '';
    return `<th class="${cls}" data-key="${col.key}">${col.label}<span class="sort-indicator">${indicator}</span></th>`;
  }).join('');
  document.getElementById('thead').innerHTML = `<tr>${ths}</tr>`;

  document.querySelectorAll('th.sortable').forEach(th => {
    th.addEventListener('click', () => {
      const key = th.dataset.key;
      if (sortKey === key) {
        sortDir *= -1;
      } else {
        sortKey = key;
        sortDir = 1;
      }
      render();
    });
  });
}

function render() {
  buildHeader();

  const q = filterText.toLowerCase();
  let rows = data.filter(row =>
    columns.some(col => String(row[col.key] ?? '').toLowerCase().includes(q))
  );

  if (sortKey) {
    const col = columns.find(c => c.key === sortKey);
    const isNum = col && col.type === 'number';
    rows = rows.slice().sort((a, b) => {
      const av = isNum ? Number(a[sortKey]) : String(a[sortKey] ?? '').toLowerCase();
      const bv = isNum ? Number(b[sortKey]) : String(b[sortKey] ?? '').toLowerCase();
      return av < bv ? -sortDir : av > bv ? sortDir : 0;
    });
  }

  const tbody = document.getElementById('tbody');
  const emptyMsg = document.getElementById('empty-msg');

  if (rows.length === 0) {
    tbody.innerHTML = '';
    emptyMsg.style.display = 'block';
    return;
  }

  emptyMsg.style.display = 'none';
  tbody.innerHTML = rows.map(row =>
    '<tr>' + columns.map(col => renderCell(row[col.key], col.type)).join('') + '</tr>'
  ).join('');
}

// ── FILTER ────────────────────────────────────────────────────────────────────
document.getElementById('filter').addEventListener('input', function () {
  filterText = this.value;
  render();
});

// ── INIT ──────────────────────────────────────────────────────────────────────
render();
</script>
</body>
</html>
```

---

## Data shape examples

### Replacing DATA

Replace `/* DATA */` with a JS array literal:

```javascript
const data = [
  { name: 'PostgreSQL', type: 'RDBMS', stars: 5, free: true, maturity: 'Stable' },
  { name: 'MongoDB',    type: 'NoSQL',  stars: 4, free: true, maturity: 'Stable' },
  { name: 'PlanetScale', type: 'RDBMS', stars: 3, free: false, maturity: 'Growing' },
];
```

### Replacing COLUMNS

Replace `/* COLUMNS */` with a JS array literal:

```javascript
const columns = [
  { key: 'name',     label: 'Database',  sortable: true,  type: 'text'    },
  { key: 'type',     label: 'Type',      sortable: true,  type: 'badge'   },
  { key: 'stars',    label: 'Rating',    sortable: true,  type: 'rating'  },
  { key: 'free',     label: 'Free Tier', sortable: false, type: 'boolean' },
  { key: 'maturity', label: 'Maturity',  sortable: true,  type: 'tag'     },
];
```

### Replacing TITLE

Replace both `/* TITLE */` occurrences (one in `<title>`, one in `<h1>`):

```
Database Comparison
```

---

## Cell type quick reference

| Type | Example value | Output |
|------|--------------|--------|
| `text` | `"React"` | React |
| `number` | `42` | 42 (right-aligned) |
| `badge` | `"NoSQL"` | Colored pill |
| `rating` | `4` | ⭐⭐⭐⭐ |
| `boolean` | `true` | ✓ |
| `boolean` | `false` | ✗ |
| `tag` | `"Beta"` | Small colored label |
| Any | `null` or `""` | — (em dash placeholder) |

---

## Wait-for text selection

After calling `new_page`, call `wait_for` on the exact text of the first column header label. For example, if the first column is `"Database"`, wait for `"Database"`. This text is injected by `buildHeader()` and appears only after JS runs successfully.
