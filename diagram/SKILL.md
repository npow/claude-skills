---
name: diagram
description: Renders interactive diagrams in the browser using Cytoscape.js. Use when the user asks to visualize, diagram, draw, render, or show a graph, flowchart, dependency tree, roadmap, architecture diagram, or any node-and-edge structure. Always renders live in browser — never as a static image.
allowed-tools: Write, Edit, mcp__chrome-devtools__new_page, mcp__chrome-devtools__navigate_page, mcp__chrome-devtools__wait_for, mcp__chrome-devtools__take_screenshot, mcp__chrome-devtools__evaluate_script, mcp__chrome-devtools__list_pages
---

# Diagram

Renders interactive, draggable diagrams in the browser using Cytoscape.js from context-supplied nodes and edges.

## Workflow

1. **Extract nodes and edges** — read labels, connections, and any grouping/color hints from the user's request or conversation context.
2. **Assign colors and positions** — choose a color scheme and set x/y coordinates for a readable layout. See [TEMPLATE.md](TEMPLATE.md) for layout patterns.
3. **Write the HTML file** — write a complete self-contained file to `/tmp/diagram.html` using the Cytoscape.js template. See [TEMPLATE.md](TEMPLATE.md) for the full template.
4. **Open in browser** — call `mcp__chrome-devtools__new_page` with `url: file:///tmp/diagram.html`.
5. **Wait for render** — call `mcp__chrome-devtools__wait_for` on a string that will appear in the legend or a node label. Timeout 10000ms.
6. **Take screenshot** — call `mcp__chrome-devtools__take_screenshot` and verify nodes are visible and not overlapping.
7. **Fix and reload if broken** — if screenshot shows problems, edit `/tmp/diagram.html`, then call `mcp__chrome-devtools__navigate_page` with `type: reload`. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Self-review checklist

Before delivering, verify ALL:

- [ ] Screenshot shows all nodes with readable text — no overflow, no overlap
- [ ] Solid edges are solid, dashed edges are dashed (check `dashed: 'yes'` not `dashed: true`)
- [ ] `cy.fit(cy.elements(), 60)` is the last line of the script
- [ ] CDN URL is exactly `https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.29.2/cytoscape.min.js`
- [ ] Legend matches the color scheme used in the diagram
- [ ] Hint text `drag nodes · scroll to zoom · drag background to pan` is present
- [ ] No node has `width` or `height` set to `label` — always use explicit pixel values
- [ ] `wait_for` is called before `take_screenshot`

## Golden rules

Hard rules. Never violate these.

1. **Never use boolean edge attributes.** Cytoscape selectors do not reliably match boolean data values. Always store edge style flags as strings: `dashed: 'yes'` or `dashed: 'no'`. Use selector `edge[dashed = "yes"]`.
2. **Never render to PNG.** Always write `/tmp/diagram.html` and open in browser. Static images cannot be dragged or zoomed by the user.
3. **Always call `cy.fit` last.** `cy.fit(cy.elements(), 60)` must be the final line in the script block. Without it, the diagram may render off-screen or at wrong zoom.
4. **Always use `new_page` for first open.** Use `mcp__chrome-devtools__new_page` with `url: file:///tmp/diagram.html`. Only use `navigate_page` with `type: reload` for subsequent reloads.
5. **Always wait before screenshotting.** Call `wait_for` on a text string that appears after Cytoscape renders (legend text or a node label). Never call `take_screenshot` immediately after `new_page`.
6. **Never set node dimensions to `label`.** Always use explicit pixel widths and heights (e.g. `width: 200px`, `height: 80px`). The `label` value causes unpredictable sizing.
7. **Always use `text-wrap: wrap` with `text-max-width`.** Without these, long labels overflow node boundaries invisibly.

## Reference files

| File | Contents |
|------|----------|
| [TEMPLATE.md](TEMPLATE.md) | Complete Cytoscape.js HTML template, color palette, layout patterns for common diagram types |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Failure diagnosis table: symptoms, causes, fixes |
