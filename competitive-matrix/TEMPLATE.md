# Competitive Matrix HTML Template

Complete copy-paste HTML template for the competitive matrix. Replace the DATA section with actual research results. No external dependencies — everything is self-contained.

## Contents
- Rating scale constants
- CSS design tokens
- Complete HTML template with sort, filter, and color-coded cell rendering
- How to inject data
- Failure diagnosis

---

## Rating scale constants

The four-point scale maps symbols to colors. These are the ONLY valid values for any non-Verdict, non-competitor cell.

| Symbol | Meaning | CSS variable | Hex |
|--------|---------|--------------|-----|
| ✓✓ | Excellent — best-in-class | `--color-excellent` | `#27ae60` |
| ✓ | Good — meets the bar | `--color-good` | `#2980b9` |
| ~ | Partial / mixed — incomplete or trade-offs | `--color-partial` | `#d35400` |
| ✗ | Poor / missing — not supported or clearly behind | `--color-poor` | `#c0392b` |

The Verdict column is always plain text on the default cell background — it is never color-coded.

---

## Complete HTML template

Write this file verbatim to `/tmp/matrix.html`, filling in only the DATA section.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Competitive Matrix</title>
<style>
  :root {
    --bg:              #1e1e2e;
    --surface:         #2a2a3e;
    --border:          #44475a;
    --text:            #cdd6f4;
    --text-muted:      #6272a4;
    --header-bg:       #313244;
    --hover-bg:        #363653;
    --color-excellent: #27ae60;
    --color-good:      #2980b9;
    --color-partial:   #d35400;
    --color-poor:      #c0392b;
    --color-verdict:   #2a2a3e;
    --sort-indicator:  #cdd6f4;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 14px;
    padding: 24px;
    min-height: 100vh;
  }

  h1 {
    font-size: 20px;
    font-weight: 600;
    margin-bottom: 4px;
    color: var(--text);
  }

  .meta {
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 16px;
  }

  .controls {
    margin-bottom: 14px;
  }

  #filter-input {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 7px 12px;
    border-radius: 6px;
    font-size: 13px;
    width: 260px;
    outline: none;
  }

  #filter-input:focus {
    border-color: var(--color-good);
  }

  .table-wrap {
    overflow-x: auto;
    border-radius: 8px;
    border: 1px solid var(--border);
  }

  table {
    border-collapse: collapse;
    width: 100%;
    min-width: 700px;
  }

  thead {
    position: sticky;
    top: 0;
    z-index: 10;
  }

  th {
    background: var(--header-bg);
    color: var(--text);
    padding: 11px 14px;
    text-align: left;
    font-weight: 600;
    font-size: 13px;
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
    border-bottom: 1px solid var(--border);
  }

  th:hover {
    background: var(--hover-bg);
  }

  th.sorted-asc::after  { content: ' ▲'; color: var(--sort-indicator); font-size: 10px; }
  th.sorted-desc::after { content: ' ▼'; color: var(--sort-indicator); font-size: 10px; }

  td {
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
    white-space: nowrap;
  }

  tr:last-child td { border-bottom: none; }

  tr:hover td { background: var(--hover-bg); }

  /* Competitor name column */
  td.col-name {
    font-weight: 600;
    color: var(--text);
    background: var(--surface);
    border-right: 1px solid var(--border);
  }

  /* Rating cells */
  td.rating {
    text-align: center;
    font-size: 15px;
    font-weight: 700;
    border-radius: 0;
  }

  td.rating-excellent { background: var(--color-excellent); color: #fff; }
  td.rating-good      { background: var(--color-good);      color: #fff; }
  td.rating-partial   { background: var(--color-partial);   color: #fff; }
  td.rating-poor      { background: var(--color-poor);      color: #fff; }

  /* Verdict column */
  td.col-verdict {
    font-style: italic;
    color: var(--text-muted);
    font-size: 13px;
    background: var(--color-verdict);
    border-left: 1px solid var(--border);
    white-space: normal;
    min-width: 160px;
    max-width: 240px;
  }

  .no-results {
    text-align: center;
    padding: 32px;
    color: var(--text-muted);
    font-style: italic;
  }

  .legend {
    display: flex;
    gap: 18px;
    margin-top: 16px;
    flex-wrap: wrap;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--text-muted);
  }

  .legend-swatch {
    width: 22px;
    height: 16px;
    border-radius: 3px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    color: #fff;
  }
</style>
</head>
<body>

<h1 id="matrix-title"><!-- REPLACE: e.g. "Vector Database Comparison" --></h1>
<p class="meta" id="matrix-meta"><!-- REPLACE: e.g. "Last updated: 2026-02-25 · 7 players · 6 dimensions" --></p>

<div class="controls">
  <input id="filter-input" type="text" placeholder="Filter by competitor name..." autocomplete="off">
</div>

<div class="table-wrap">
  <table id="matrix-table">
    <thead>
      <tr id="header-row">
        <!-- Headers are injected by JS from COLUMNS -->
      </tr>
    </thead>
    <tbody id="table-body">
      <!-- Rows are injected by JS from DATA -->
    </tbody>
  </table>
</div>

<div class="legend">
  <div class="legend-item"><span class="legend-swatch" style="background:var(--color-excellent)">✓✓</span> Excellent</div>
  <div class="legend-item"><span class="legend-swatch" style="background:var(--color-good)">✓</span> Good</div>
  <div class="legend-item"><span class="legend-swatch" style="background:var(--color-partial)">~</span> Partial / mixed</div>
  <div class="legend-item"><span class="legend-swatch" style="background:var(--color-poor)">✗</span> Poor / missing</div>
</div>

<script>
// ─── DATA SECTION — replace everything between these lines ───────────────────

const TITLE = 'Vector Database Comparison';
const META  = 'Last updated: 2026-02-25 · 7 players · 6 dimensions';

// Column definitions. The first entry is always the competitor name column.
// Set isVerdict: true on the last column for special styling.
const COLUMNS = [
  { key: 'name',        label: 'Competitor' },
  { key: 'latency',     label: 'Latency' },
  { key: 'scale',       label: 'Scalability' },
  { key: 'pricing',     label: 'Pricing' },
  { key: 'ecosystem',   label: 'Ecosystem' },
  { key: 'docs',        label: 'Docs' },
  { key: 'governance',  label: 'Governance' },
  { key: 'verdict',     label: 'Verdict', isVerdict: true },
];

// Valid rating values: '✓✓', '✓', '~', '✗'
// Verdict is plain text (5–10 words).
const DATA = [
  { name: 'Pinecone',   latency: '✓✓', scale: '✓✓', pricing: '~',  ecosystem: '✓✓', docs: '✓✓', governance: '✓',  verdict: 'Managed, polished, expensive at scale' },
  { name: 'Weaviate',   latency: '✓',  scale: '✓',  pricing: '✓',  ecosystem: '✓',  docs: '✓',  governance: '✓✓', verdict: 'Open-source with strong graph support' },
  { name: 'Qdrant',     latency: '✓✓', scale: '✓',  pricing: '✓✓', ecosystem: '~',  docs: '✓',  governance: '✓',  verdict: 'Rust-native, fast, growing ecosystem' },
  { name: 'Chroma',     latency: '~',  scale: '✗',  pricing: '✓✓', ecosystem: '✓',  docs: '~',  governance: '~',  verdict: 'Good for local prototyping, not prod' },
  { name: 'Milvus',     latency: '✓',  scale: '✓✓', pricing: '✓',  ecosystem: '✓',  docs: '~',  governance: '✓',  verdict: 'Scales well, complex to operate' },
  { name: 'pgvector',   latency: '~',  scale: '~',  pricing: '✓✓', ecosystem: '✓✓', docs: '✓',  governance: '✓✓', verdict: 'Best if already running Postgres' },
  { name: 'Vespa',      latency: '✓✓', scale: '✓✓', pricing: '✓',  ecosystem: '~',  docs: '~',  governance: '✓',  verdict: 'Enterprise-grade, steep learning curve' },
];

// ─── END DATA SECTION ────────────────────────────────────────────────────────

// Rating → CSS class mapping
const RATING_CLASS = {
  '✓✓': 'rating-excellent',
  '✓':  'rating-good',
  '~':  'rating-partial',
  '✗':  'rating-poor',
};

// Sort state
let sortKey = null;
let sortDir = 1; // 1 = asc, -1 = desc

// Filtered working set
let filteredData = DATA.slice();

function ratingOrder(v) {
  const order = { '✓✓': 3, '✓': 2, '~': 1, '✗': 0 };
  return order[v] !== undefined ? order[v] : -1;
}

function renderHeaders() {
  const row = document.getElementById('header-row');
  row.innerHTML = '';
  COLUMNS.forEach(col => {
    const th = document.createElement('th');
    th.textContent = col.label;
    th.dataset.key = col.key;
    if (sortKey === col.key) {
      th.classList.add(sortDir === 1 ? 'sorted-asc' : 'sorted-desc');
    }
    th.addEventListener('click', () => {
      if (sortKey === col.key) {
        sortDir *= -1;
      } else {
        sortKey = col.key;
        sortDir = 1;
      }
      renderHeaders();
      renderRows();
    });
    row.appendChild(th);
  });
}

function renderRows() {
  const tbody = document.getElementById('table-body');
  tbody.innerHTML = '';

  // Sort
  const sorted = filteredData.slice().sort((a, b) => {
    if (!sortKey) return 0;
    const av = a[sortKey] || '';
    const bv = b[sortKey] || '';
    // Verdict and name: alphabetical
    if (sortKey === 'name' || sortKey === 'verdict') {
      return sortDir * av.localeCompare(bv);
    }
    // Rating columns: by rating order
    return sortDir * (ratingOrder(av) - ratingOrder(bv));
  });

  if (sorted.length === 0) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = COLUMNS.length;
    td.className = 'no-results';
    td.textContent = 'No competitors match the filter.';
    tr.appendChild(td);
    tbody.appendChild(tr);
    return;
  }

  sorted.forEach(row => {
    const tr = document.createElement('tr');
    COLUMNS.forEach(col => {
      const td = document.createElement('td');
      const val = row[col.key] || '';

      if (col.key === 'name') {
        td.className = 'col-name';
        td.textContent = val;
      } else if (col.isVerdict) {
        td.className = 'col-verdict';
        td.textContent = val;
      } else {
        // Rating cell
        const cls = RATING_CLASS[val];
        td.className = 'rating ' + (cls || '');
        td.textContent = val;
      }

      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
}

// Filter
document.getElementById('filter-input').addEventListener('input', function () {
  const q = this.value.toLowerCase();
  filteredData = DATA.filter(row => row.name.toLowerCase().includes(q));
  renderRows();
});

// Initial render
document.getElementById('matrix-title').textContent = TITLE;
document.getElementById('matrix-meta').textContent  = META;
renderHeaders();
renderRows();
</script>

</body>
</html>
```

---

## How to inject data

1. Set `TITLE` to a descriptive string: `'LLM Inference Providers — February 2026'`
2. Set `META` to: `'Last updated: YYYY-MM-DD · N players · M dimensions'`
3. Define `COLUMNS` with one entry per column. Always start with `{ key: 'name', label: 'Competitor' }` and always end with `{ key: 'verdict', label: 'Verdict', isVerdict: true }`. Middle entries are your evaluation dimensions.
4. Define `DATA` with one object per player. Every key listed in `COLUMNS` must be present. Rating values must be exactly `'✓✓'`, `'✓'`, `'~'`, or `'✗'`. Verdict is a plain string of 5-10 words.

**CRITICAL**: Always use the literal UTF-8 characters ✓✓, ✓, ✗ when writing DATA values and RATING_CLASS keys — never write `\u2713` or `\u2717`. Unicode escape sequences are only interpreted inside JavaScript string literals, not in HTML. Copy the symbols directly from this file.

---

## Failure diagnosis

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| All cells same background color | Rating class not matching symbol — e.g. used `'✓✓'` vs `'✓✓'` with different Unicode | Ensure rating strings in DATA match exactly: `'✓✓'`, `'✓'`, `'~'`, `'✗'` |
| Cells show text but no background | `RATING_CLASS` lookup returned undefined | Check that the symbol in DATA exactly matches the key in `RATING_CLASS`; copy from this file |
| Sort does nothing | Column key in `COLUMNS` does not match key in `DATA` objects | Align `col.key` values to match DATA object property names exactly |
| Filter crashes | `row.name` is undefined | Ensure every DATA object has a `name` property |
| Table overflows horizontally | `min-width` on table too large for viewport | Reduce number of columns (cap at 8) or reduce `padding` on `td`/`th` |
| Screenshot shows blank page | `wait_for` was not called before `take_screenshot` | Always call `wait_for` on the first competitor name, then call `take_screenshot` |
| Verdict column same color as rating cells | `isVerdict: true` missing from column definition | Add `isVerdict: true` to the verdict column in `COLUMNS` |
