---
name: competitive-matrix
description: Researches a market or technology space and renders an interactive color-coded comparison matrix in the browser. Use when the user asks for competitive analysis, competitive matrix, compare competitors, market landscape, who are the players, alternatives to X, compare these tools, feature comparison, how does X compare to Y, or competitive landscape.
allowed-tools: WebSearch, Write, Edit, mcp__chrome-devtools__new_page, mcp__chrome-devtools__navigate_page, mcp__chrome-devtools__wait_for, mcp__chrome-devtools__take_screenshot, mcp__chrome-devtools__list_pages
---

# Competitive Matrix

Researches a market or technology space and renders an interactive, color-coded comparison matrix in the browser by combining web research with a zero-dependency HTML table.

## Workflow

1. **Identify the space** — confirm the market, product category, or technology being compared; ask for clarification if ambiguous. See [RESEARCH.md](RESEARCH.md).
2. **List the players** — enumerate 5-10 key competitors or options to include; no more, no fewer. See [RESEARCH.md](RESEARCH.md).
3. **Choose evaluation dimensions** — select 5-8 columns relevant to this specific domain; avoid generic filler columns. See [RESEARCH.md](RESEARCH.md).
4. **Research each player** — run at least one web search per player to verify current status and ratings; never rely solely on training data. See [RESEARCH.md](RESEARCH.md).
5. **Assign ratings** — score every cell using the four-point scale (checkcheck/check/tilde/x) with evidence from step 4. See [RESEARCH.md](RESEARCH.md).
6. **Write the HTML file** — write a complete self-contained file to `/tmp/matrix.html` using the template with color-coded cells, sort, and filter. See [TEMPLATE.md](TEMPLATE.md).
7. **Open in browser** — call `mcp__chrome-devtools__new_page` with `url: file:///tmp/matrix.html`, then `wait_for` the first competitor name (timeout 8000ms), then `take_screenshot`.
8. **Deliver summary** — after the screenshot, output 3-5 bullet points naming the key differentiators and the standout winner(s) per use case.

## Self-review checklist

Before delivering, verify ALL:

- [ ] At least one web search was run per player — no player was rated from training data alone
- [ ] Between 5 and 10 players are in the matrix — not fewer, not more
- [ ] Between 5 and 8 evaluation dimension columns are present — plus a Verdict column as the last column
- [ ] Every cell has a rating from the four-point scale: checkcheck, check, tilde, or x — no blanks, no numbers
- [ ] Every cell is color-coded: green for checkcheck, blue for check, orange for tilde, red for x
- [ ] A "Last updated: YYYY-MM-DD" line appears above the table in the rendered HTML
- [ ] Sort works on every column — clicking a header reorders rows
- [ ] Filter input is present and filters by competitor name (case-insensitive)
- [ ] Dark background (#1e1e2e) is applied — not white or gray
- [ ] Screenshot was taken after `wait_for` — not immediately after `new_page`

## Golden rules

Hard rules. Never violate these.

1. **Never rate from training data alone.** Run at least one web search per player before assigning any rating. Training data goes stale; search results do not.
2. **Always use the four-point scale exclusively.** The only valid ratings are checkcheck (excellent), check (good), tilde (partial/mixed), and x (poor/missing). Never use numbers, percentages, stars, or prose in cells.
3. **Always include a Verdict column as the last column.** Every row must end with a 5-10 word phrase summarizing that player's position.
4. **Always color-code every cell.** Green (#27ae60) for checkcheck, blue (#2980b9) for check, orange (#d35400) for tilde, red (#c0392b) for x. A matrix where all cells look the same is broken.
5. **Never include more than 10 players.** Matrices with more than 10 rows become unreadable. If the user lists more, select the 10 most relevant and note the exclusions.
6. **Always include a "Last updated" date.** Competitive landscapes change. The date the research was conducted must appear above the table in the rendered output.

## Reference files

| File | Contents |
|------|----------|
| [TEMPLATE.md](TEMPLATE.md) | Complete HTML template with color-coded cell rendering, sort/filter JS, CSS design tokens, and rating scale constants |
| [RESEARCH.md](RESEARCH.md) | How to choose evaluation dimensions, research each player, assign ratings, and handle stale or conflicting data |
