# Troubleshooting

Failure diagnosis for the diagram skill. Match the symptom you observe, apply the fix, then reload and re-screenshot.

## Failure diagnosis table

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| All edges are dashed when only some should be | Edge `dashed` attribute stored as boolean `true`/`false` instead of string | Change all edge data to `dashed: 'yes'` or `dashed: 'no'`. Update selector to `edge[dashed = "yes"]` |
| Nodes are tiny / diagram is a small cluster in one corner | `cy.fit()` not called, or called before elements were added | Ensure `cy.fit(cy.elements(), 60)` is the last line of the script |
| Node labels overflow or are cut off | `text-max-width` missing or `text-wrap` not set to `'wrap'` | Add `'text-wrap': 'wrap'` and `'text-max-width': '180px'` to node style |
| Page loads but Cytoscape canvas is blank / white | CDN script failed to load (wrong URL or network blocked) | Confirm URL is exactly `https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.29.2/cytoscape.min.js` |
| `wait_for` times out | Wait text doesn't appear in the rendered page | Change `wait_for` text to match a string that actually appears in legend or a node label |
| Screenshot taken before diagram renders | `take_screenshot` called immediately after `new_page` without waiting | Always call `wait_for` before `take_screenshot`. Wait on a legend text string. |
| `navigate_page reload` fails with "page closed" error | The page was closed between open and reload | Call `mcp__chrome-devtools__list_pages` to find the right page ID, then `select_page` before reloading |
| Nodes overlap badly | Preset positions too close together | Increase horizontal spacing to ≥220px and vertical spacing to ≥250px between rows |
| Edge labels not visible | `label` field in edge data is missing or undefined | Set `label: ''` (empty string) for unlabelled edges. The selector `edge[label != ""]` hides empty labels automatically |
| Node colors all the same | `color` not included in node data, or `'background-color': 'data(color)'` missing from style | Ensure each node has `data: { color: '#hexcode' }` and the style uses `'background-color': 'data(color)'` |
| Diagram renders but is in wrong order (Layer 2 at top) | y positions not matching intended hierarchy | Layer 0 = smallest y (top). Layer 1 = medium y. Layer 2 = largest y (bottom). |

## Reload procedure

After editing `/tmp/diagram.html`:

1. Call `mcp__chrome-devtools__navigate_page` with `{ type: 'reload' }` on the selected page.
2. Call `mcp__chrome-devtools__wait_for` on a text string in the legend.
3. Call `mcp__chrome-devtools__take_screenshot` to verify.

If the page was closed (error on reload):
1. Call `mcp__chrome-devtools__new_page` with `url: file:///tmp/diagram.html`.
2. Proceed with wait → screenshot.

## Validating the template before opening

Before calling `new_page`, mentally verify:

- [ ] Every node has `data.id`, `data.label`, `data.color`, and `position.x`/`position.y`
- [ ] Every edge has `data.id`, `data.source`, `data.target`, `data.dashed` (string), `data.label` (string, may be empty)
- [ ] `dashed` is `'yes'` or `'no'` — never `true` or `false`
- [ ] `cy.fit(cy.elements(), 60)` is present as the last line
- [ ] CDN script tag is present with the correct URL
- [ ] Legend HTML has at least one entry matching the colors used
