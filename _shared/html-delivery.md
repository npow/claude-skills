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

Upload the HTML file to the Netflix genpop S3 bucket:

```
s3://us-east-1.netflix.s3.genpop.prod/presentations/$(whoami)/<report-name>-YYYY-MM-DD/index.html
```

Where `<report-name>` matches the skill name (e.g. `sprint-retro`, `activity-report`, `friction-report`, `pipeline-health`).

**Auth:** Try ambient AWS credentials first (works on Workbench via Titus IAM role). If that fails, try `weep file arn:aws:iam::149510111645:role/awsprod_user` then retry.

Set `--content-type "text/html"` on the upload so it renders correctly in the browser.

## Slack delivery

After upload, provide the commuter link:
```
https://commuter.dynprod.netflix.net:7002/s3-files/us-east-1.netflix.s3.genpop.prod/presentations/<username>/<report-name>-YYYY-MM-DD/index.html
```

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

## Self-review checklist items

Add these to the skill's self-review checklist:
- [ ] HTML version uploaded to S3 with commuter link (unless `--no-html` or upload failed with noted fallback)
- [ ] Slack/chat delivery uses TLDR + link, not the full report
