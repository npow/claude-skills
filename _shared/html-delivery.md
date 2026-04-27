# HTML Report Delivery

Shared delivery pattern for all report-generating skills. Converts reports to styled HTML pages and delivers them locally or via a configurable remote upload.

## When to use

- **Always** when the report is delivered to a chat context (long text gets truncated)
- **By default** for all runs unless `--no-html` is explicitly passed
- The markdown file is still written locally as the source of truth

## HTML conversion

Convert the markdown report into a self-contained, dark-themed HTML page with:
- Metrics bar at the top (adapt metrics to the report type)
- Color-coded sections by severity/status (green = good, amber = warning, red = critical, blue = action items, purple = highlights)
- Priority tags where applicable (High/Med/Low)
- Callout boxes for incidents or critical findings
- Clean typography, readable on desktop and mobile
- Report footer preserved

Every cited source (PR link, Slack thread permalink, ticket URL, doc URL) must be a clickable `<a href="...">` hyperlink in the HTML — not plain text. The reader should be able to click through to the supporting evidence directly from the report.

The HTML must be a single self-contained file (inline CSS, no external dependencies).

## Local delivery

Save the HTML file to a local reports directory:

```
./reports/<report-name>-YYYY-MM-DD-HHmmss/index.html
```

Where `<report-name>` matches the skill name (e.g. `sprint-retro`, `activity-report`, `friction-report`, `pipeline-health`).

Attempt to open in the default browser (`open` on macOS, `xdg-open` on Linux). If that fails, print the local file path.

## Remote upload (optional)

If `~/.claude/skills/_shared/delivery-config.json` exists, use it for remote upload:

```json
{
  "method": "s3",
  "bucket": "my-reports-bucket",
  "prefix": "reports/$(whoami)",
  "base_url": "https://my-viewer.example.com/s3-files",
  "content_type": "text/html"
}
```

Supported methods: `s3` (requires `aws` CLI configured). After upload, provide the viewer URL. If upload fails, fall back to the local file and note the failure.

## Chat delivery

Post a **TLDR** (5-8 lines max) with:
- Report title and date range
- Top 2-3 key findings or highlights
- Link to the HTML report (remote URL if uploaded, local path otherwise)

Never paste the full report into chat. The TLDR gives readers enough context to decide whether to click through.

## Fallback

If HTML generation or upload fails, fall back to the markdown file and note the failure in the output. Don't block the report on delivery.

## Evidence file integration

When the skill uses an evidence/termination file, include:

```json
"html_delivery": {
  "uploaded": true,
  "url": "...",
  "local_path": "./reports/...",
  "error": null
}
```

Set `uploaded: false` and populate `error` if the upload failed.

## Mandatory deep-qa-temporal pass

**Before publishing**, run a deep-qa-temporal -> fix loop on the generated report markdown until it converges. This is load-bearing — it catches attribution errors (bystander items attributed to the team), privacy leaks, uncited filler, and factual mistakes that the generating skill's self-review checklist misses.

**General principle: every factual claim must trace to a specific data source.** If it can't, it's fabricated — even if it "sounds right." The LLM narrates and synthesizes; it does not invent facts.

**QA dimensions to check (in addition to deep-qa-temporal's default dimensions):**
- **Fabricated identity metadata**: roles, titles, levels, team names not sourced from a people directory
- **Wrong numbers**: PR counts, review counts, ticket counts that don't match the actual data queried
- **Wrong status**: claiming something "shipped" when the PR is still open, or "in progress" when it was abandoned
- **Inflated/deflated scope**: "38 tables impacted" when the source says "38 tables scanned" — misquoting severity or scale
- **Causal claims without evidence**: "X caused Y" when the data only shows temporal proximity
- **Wrong dates/timing**: attributing work to the wrong sprint window, or saying "this week" for something from last month
- **Bystander attribution**: items the team observed but didn't own
- **Uncited claims**: any statement without a linked source (PR, thread, ticket)
- **Dead or placeholder links**: every `<a href>` must resolve to a real URL. Placeholder `#` links or `example.com` links are critical defects
- **Missing members**: group alias resolved to N members but report shows fewer

**Loop:**
1. Run `deep-qa-temporal` on the report markdown
2. If critical or major defects found: fix them in the markdown, then re-run deep-qa-temporal (go to step 1)
3. Repeat until deep-qa-temporal returns zero critical/major defects (convergence)
4. Minor defects can be noted in the evidence file but don't block delivery

Cap at 3 rounds to avoid infinite loops. If still failing after 3 rounds, deliver with a warning noting unresolved defects in the evidence file.

## Self-review checklist items

Add these to the skill's self-review checklist:
- [ ] HTML version saved locally and optionally uploaded (unless `--no-html` or upload failed with noted fallback)
- [ ] Chat delivery uses TLDR + link, not the full report
