# Cytoscape.js Template and Layout Patterns

## Contents
- Full HTML template
- Color palette
- Layout patterns by diagram type
- Edge styling patterns
- Legend construction

---

## Full HTML template

Copy this template verbatim. Replace the `NODES`, `EDGES`, `LEGEND_ITEMS`, and `WAIT_TEXT` sections.

```html
<!DOCTYPE html>
<html>
<head>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #1e1e2e; font-family: 'Segoe UI', sans-serif; }
  #cy { width: 100vw; height: 100vh; }
  #legend {
    position: fixed; bottom: 20px; left: 20px;
    background: rgba(255,255,255,0.08);
    border-radius: 8px; padding: 12px 16px;
    color: #cdd6f4; font-size: 13px; line-height: 2;
  }
  .dot { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 8px; vertical-align: middle; }
  #hint {
    position: fixed; top: 20px; right: 20px;
    color: rgba(255,255,255,0.3); font-size: 12px;
  }
</style>
</head>
<body>
<div id="cy"></div>
<div id="legend">
  <!-- LEGEND_ITEMS: one line per color group, e.g.: -->
  <!-- <div><span class="dot" style="background:#c0392b"></span>Layer 0 — no deps</div> -->
</div>
<div id="hint">drag nodes · scroll to zoom · drag background to pan</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.29.2/cytoscape.min.js"></script>
<script>
const cy = cytoscape({
  container: document.getElementById('cy'),
  elements: [
    // NODES — one object per node:
    // { data: { id: 'A', label: 'Node Label', color: '#c0392b' }, position: { x: 400, y: 100 } },

    // EDGES — one object per edge:
    // { data: { id: 'e1', source: 'A', target: 'B', dashed: 'no', label: '' } },
    // { data: { id: 'e2', source: 'A', target: 'C', dashed: 'yes', label: 'soft dep' } },
  ],
  style: [
    {
      selector: 'node',
      style: {
        'background-color': 'data(color)',
        'label': 'data(label)',
        'text-valign': 'center',
        'text-halign': 'center',
        'color': '#ffffff',
        'font-size': '13px',
        'font-family': 'monospace',
        'text-wrap': 'wrap',
        'text-max-width': '180px',
        'width': '200px',
        'height': '80px',
        'shape': 'roundrectangle',
        'border-width': '0px',
      }
    },
    {
      selector: 'node:selected',
      style: { 'border-width': '2px', 'border-color': '#ffffff' }
    },
    {
      selector: 'edge',
      style: {
        'width': 2,
        'line-color': 'rgba(255,255,255,0.25)',
        'target-arrow-color': 'rgba(255,255,255,0.4)',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'arrow-scale': 1.2,
      }
    },
    {
      selector: 'edge[dashed = "yes"]',
      style: {
        'line-style': 'dashed',
        'line-dash-pattern': [6, 4],
        'line-color': 'rgba(255,255,255,0.18)',
      }
    },
    {
      selector: 'edge[label != ""]',
      style: {
        'label': 'data(label)',
        'font-size': '11px',
        'color': 'rgba(255,255,255,0.45)',
        'text-background-color': '#1e1e2e',
        'text-background-opacity': 1,
        'text-background-padding': '3px',
      }
    },
  ],
  layout: { name: 'preset' },
  userZoomingEnabled: true,
  userPanningEnabled: true,
  boxSelectionEnabled: false,
  minZoom: 0.3,
  maxZoom: 3,
});

cy.fit(cy.elements(), 60);
</script>
</body>
</html>
```

---

## Color palette

Standard colors for categorical grouping. Pick a consistent scheme and document it in the legend.

| Role | Hex | Use for |
|------|-----|---------|
| Red | `#c0392b` | Layer 0 / foundation / blockers / critical |
| Blue | `#2980b9` | Layer 1 / mid-tier / services / in-progress |
| Green | `#27ae60` | Layer 2 / outcomes / completed / leaf nodes |
| Purple | `#8e44ad` | External / third-party / optional |
| Orange | `#d35400` | Warning / risk / deprecated |
| Teal | `#16a085` | Infrastructure / platform / shared |
| Gray | `#555566` | Inactive / disabled / future |

For simple two-tone diagrams (e.g. done vs todo): use green + gray.
For three-layer dependency graphs: use red + blue + green (as in the roadmap example).

---

## Layout patterns by diagram type

### Three-layer dependency graph (most common)

Space nodes horizontally across 3 rows. Leave ~250px vertical gap between rows. Leave ~220px horizontal gap between nodes.

```
Layer 0 (y=100):  x = 200, 450, 700, 950  (space evenly across width)
Layer 1 (y=350):  x = 200, 450, 700, 950
Layer 2 (y=600):  x = 200, 450, 700, 950
```

Start with canvas width = number_of_nodes_in_widest_layer × 220.

### Linear pipeline / flowchart

Top-to-bottom or left-to-right. 200px gap between steps.

```
Top-to-bottom: x = 600 (centered), y = 100, 300, 500, 700 ...
Left-to-right: y = 400 (centered), x = 100, 320, 540, 760 ...
```

### Star / hub-and-spoke

Center hub at (600, 400). Spokes radiate outward at equal angles.
For N spokes: angle = (2π / N) × i. Radius = 250px.

```javascript
// Position N spoke nodes around a center hub
const cx = 600, cy = 400, r = 250;
nodes.forEach((n, i) => {
  const angle = (2 * Math.PI / N) * i - Math.PI / 2;
  n.x = cx + r * Math.cos(angle);
  n.y = cy + r * Math.sin(angle);
});
```

### Two-column comparison

Left column (x=250), right column (x=750). Rows at y=100, 250, 400...

---

## Edge styling patterns

All edge dashed values must be strings, not booleans.

| Edge type | `dashed` value | Meaning |
|-----------|---------------|---------|
| Hard dependency | `'no'` | Must complete before target |
| Soft / optional | `'yes'` | Helps but not required |
| Data flow | `'no'` + label | Data passes from source to target |
| Inhibits | `'yes'` + label `'blocks'` | Source blocks target |

To add a label to an edge, set `label: 'your text'` in edge data. Empty string `''` means no label — the `edge[label != ""]` selector will hide it automatically.

---

## Legend construction

Match every color in the diagram to a legend entry. One `<div>` per color group:

```html
<div><span class="dot" style="background:#c0392b"></span>Layer 0 — start now, no deps</div>
<div><span class="dot" style="background:#2980b9"></span>Layer 1 — unlocked by Layer 0</div>
<div><span class="dot" style="background:#27ae60"></span>Layer 2 — unlocked by Layer 1</div>
```

The `wait_for` text for the `mcp__chrome-devtools__wait_for` call should match the first word of the first legend entry (e.g. `"Layer 0"`) — this text appears only after the page has fully loaded.
