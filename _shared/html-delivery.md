# HTML Report Delivery

Shared delivery pattern for all report-generating skills. Converts reports to styled HTML pages, uploads to S3, and shares a TLDR + commuter link in Slack.

## When to use

- **Always** when the report is delivered to Slack or any chat context (long text gets truncated)
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

The HTML must be a single self-contained file (inline CSS, no external dependencies).

## S3 upload

Upload the HTML file to the `netflix-dataoven-test-users` S3 bucket (writable from Workbench via TitusContainerRole):

```
s3://netflix-dataoven-test-users/reports/$(whoami)/<report-name>-YYYY-MM-DD-HHmmss/index.html
```

Where `<report-name>` matches the skill name (e.g. `sprint-retro`, `activity-report`, `friction-report`, `pipeline-health`).

Set `--content-type "text/html"` on the upload so commuter renders it in the browser instead of triggering a download.

**Why not genpop?** `s3://us-east-1.netflix.s3.genpop.prod/presentations/` requires `weep` for cross-account auth, which isn't available on Workbench. The dataoven-test-users bucket is writable via the ambient TitusContainerRole and commuter serves it with Metatron browser auth.

## Slack delivery

After upload, provide the commuter link:
```
https://commuter.dynprod.netflix.net:7002/s3-files/netflix-dataoven-test-users/reports/<username>/<report-name>-YYYY-MM-DD-HHmmss/index.html
```

Readers need Metatron browser auth (standard Netflix SSO) to view the link.

Post a **TLDR in Slack** (5-8 lines max) with:
- Report title and date range
- Top 2-3 key findings or highlights
- Link to the full HTML report

Never paste the full report into Slack. The TLDR gives readers enough context to decide whether to click through.

## Fallback

If S3 upload fails (no credentials, bucket access denied), fall back to the markdown file and note the failure in the output. Don't block the report on upload.

## Evidence file integration

When the skill uses an evidence/termination file, include:

```json
"html_delivery": {
  "uploaded": true,
  "s3_path": "s3://...",
  "commuter_url": "https://commuter.dynprod.netflix.net:7002/...",
  "error": null
}
```

Set `uploaded: false` and populate `error` if the upload failed.

## Mandatory deep-qa pass

**Before uploading to S3**, run a deep-qa → fix loop on the generated report markdown until it converges. This is load-bearing — it catches attribution errors (bystander items attributed to the team), privacy leaks, uncited filler, and factual mistakes that the generating skill's self-review checklist misses.

**Loop:**
1. Run `deep-qa` on the report markdown
2. If critical or major defects found: fix them in the markdown, then re-run deep-qa (go to step 1)
3. Repeat until deep-qa returns zero critical/major defects (convergence)
4. Minor defects can be noted in the evidence file but don't block delivery

Cap at 3 rounds to avoid infinite loops. If still failing after 3 rounds, deliver with a warning noting unresolved defects in the evidence file.

## Self-review checklist items

Add these to the skill's self-review checklist:
- [ ] HTML version uploaded to S3 with commuter link (unless `--no-html` or upload failed with noted fallback)
- [ ] Slack/chat delivery uses TLDR + link, not the full report
