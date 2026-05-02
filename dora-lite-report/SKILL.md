---
name: dora-lite-report
description: "Use when generating a weekly DORA metrics report, checking deployment frequency, lead time, change failure rate, recovery time, or assessing software delivery performance. Trigger phrases: DORA report, DORA metrics, deployment frequency, lead time for changes, change failure rate, MTTR, recovery time, delivery performance, software delivery metrics."

category: report
capabilities: [trend-tracking]
input_types: [repo]
output_types: [report, code]
complexity: moderate
cost_profile: low
maturity: beta
metadata_source: inferred
---

# Weekly DORA-Lite Report

Produce a weekly software delivery performance report using the four DORA metrics: Deployment Frequency, Lead Time for Changes, Change Failure Rate (CFR), and Failed Deployment Recovery Time (FDRT, formerly MTTR). Data comes from a configurable DORA metrics API with a Spinnaker-based fallback.

**Important context (DORA 2025):** The Elite/High/Medium/Low performance tiers were RETIRED in DORA 2025. Do NOT classify teams into those buckets. Report raw numbers with period-over-period trends. If the reader wants a framework, reference the 7 team archetypes model from the 2024/2025 DORA reports, but do not assign an archetype — that requires a full survey, not just metrics.

## Configuration

See [`_shared/report-config.md`](../_shared/report-config.md) for the standard config resolution pattern.

**Config schema** (`~/.claude/skills/dora-lite-report/config.json`):
- `apps`: list of Spinnaker application name strings
- `period_days`: number (default: 7)
- `comparison_periods`: number of past periods for trend comparison (default: 2)
- `digest_channel`: Slack channel for posting (default: `#team-digests`)
- `scribe_base_url`: DORA metrics API base URL string

**Required scope:** at least one `apps` entry (Spinnaker application names).

## Arguments

- **apps**: list of Spinnaker application names to measure
- **period_days**: reporting period length in days (default: 7)
- **comparison_periods**: how many past periods to compare for trend (default: 2, meaning current vs previous)
- **digest_channel**: Slack channel for posting (default: `#team-digests` — never a primary team channel)
- **scribe_base_url**: DORA metrics API base URL

## Workflow

### Phase 1: Attempt Scribe DORA API

1. **Fetch DORA metrics from Scribe.** For each app, attempt to call the Scribe DORA API:
   ```
   curl -s "https://{scribe_base_url}/metrics?app={app}&window=90d" \
     -H "Accept: application/json"
   ```
   The Scribe API returns a 90-day trailing window by default. Extract:
   - **Deployment Frequency (DF)**: deploys per day/week
   - **Lead Time for Changes (LT)**: median time from commit to production deploy
   - **Change Failure Rate (CFR)**: percentage of deployments causing incidents or rollbacks
   - **Failed Deployment Recovery Time (FDRT)**: median time from failed deploy detection to recovery

2. **If Scribe is accessible and returns data**, skip to Phase 3 (Compute Trends).

3. **If Scribe returns an error, times out, or is inaccessible**, log the failure reason and proceed to Phase 2 (Fallback).

### Phase 2: Fallback — Compute from Spinnaker Delivery Tools

If Scribe is unavailable, compute approximate DORA metrics from Spinnaker execution data.

4. **Get pipeline execution history.** For each app, invoke `delivery:delivery-spinnaker` to get pipeline executions for the current period and the comparison period. Request enough history to cover `period_days * comparison_periods` days.

5. **Compute Deployment Frequency.** Count successful production deployments per period. A deployment = a pipeline execution with status SUCCEEDED that deployed to a production environment.
   - `DF = successful_prod_deploys / period_days`

6. **Compute Lead Time for Changes (approximate).** For each successful deployment, calculate the time delta between the build trigger (commit timestamp or pipeline start) and the deployment completion timestamp.
   - `LT = median(deploy_completion - trigger_timestamp)` across all deploys in the period
   - Note: this is an approximation. True lead time requires commit-to-deploy tracking which Spinnaker alone cannot provide precisely.

7. **Compute Change Failure Rate.** Count deployments that resulted in a rollback, failed canary, or incident.
   - For each app, invoke `delivery:delivery-managed-delivery` to check for failed canaries and rollbacks.
   - For failed pipeline executions, invoke `delivery:delivery-execution-failure-analysis` to classify failures.
   - `CFR = failed_deploys / total_deploys * 100`
   - A "failed deploy" is one that either: triggered an automatic rollback, failed canary analysis, or required manual intervention after reaching production.

8. **Compute Failed Deployment Recovery Time (approximate).** For each failed deployment identified above, calculate the time from failure detection to the next successful deployment.
   - `FDRT = median(next_success_time - failure_time)` across all failures in the period
   - If no failures occurred, FDRT = N/A (which is good).

### Phase 3: Compute Trends and Statistical Reliability

9. **Compute period-over-period trends.** For each metric, compare the current period value to the previous period value:
   - `trend = ((current - previous) / previous) * 100` (percentage change)
   - Direction: for DF and LT-improvement, UP is good. For CFR and FDRT, DOWN is good.

10. **Assess statistical reliability.** Flag metrics that lack sufficient sample size:
    - **Deployment Frequency**: reliable if >= 5 deploys in the period (otherwise note "low deploy volume — DF trend may not be meaningful")
    - **Lead Time**: reliable if >= 5 deploys (same reasoning — median of < 5 values is noisy)
    - **Change Failure Rate**: reliable if >= 30 deploys in the period (CFR is a proportion — needs n >= 30 for the normal approximation to hold; with < 30 deploys, a single failure swings CFR by > 3 percentage points)
    - **Failed Deployment Recovery Time**: reliable if >= 3 failure incidents in the period (median of fewer than 3 values is not a meaningful central tendency)
    - For a ~20-person team deploying weekly, expect 5-15 deploys/week — CFR and FDRT will almost always carry a reliability caveat. State this clearly.

### Phase 4: Generate Report

11. **Generate report.** Output markdown:

```
## DORA-Lite Report — {date}
Apps: {app1, app2, ...} | Period: {period_days} days ending {end_date}
Data source: {Scribe API | Spinnaker fallback (Scribe unavailable: {reason})}

### Metric Summary

| Metric | Current Period | Previous Period | Trend | Reliable? |
|--------|---------------|-----------------|-------|-----------|
| Deployment Frequency | {N} deploys/week ({N}/day) | {N} deploys/week | {+/-N%} {arrow} | {Yes / No: reason} |
| Lead Time for Changes | {median} (p50) | {median} | {+/-N%} {arrow} | {Yes / No: reason} |
| Change Failure Rate | {N%} ({failures}/{total}) | {N%} | {+/-N pp} {arrow} | {Yes / No: reason} |
| Failed Deploy Recovery Time | {median} | {median} | {+/-N%} {arrow} | {Yes / No: reason} |

### Velocity + Stability Pairing

**Velocity (how fast):** DF = {value}, LT = {value}
**Stability (how safe):** CFR = {value}, FDRT = {value}
**Balance assessment:** {One sentence: are velocity and stability moving in the same direction, or is one improving at the cost of the other?}

### Statistical Reliability Notes

{For each metric flagged as unreliable, explain why and what sample size would be needed.}
{Example: "CFR of 10% is based on 1 failure in 10 deploys. With n=10, a single additional failure would shift CFR to 18%. Need >= 30 deploys for a stable CFR estimate."}

### Per-App Breakdown

{For each app: DF, LT, CFR, FDRT with the raw counts behind each percentage.}

### Failed Deployments Detail

{For each failed deployment in the period: app, time, failure type (rollback/canary fail/incident), recovery time, link.}
{If no failures: "No failed deployments in this period."}

### Trend Context

{2-3 sentences of LLM-generated narrative contextualizing the numbers. E.g., "Deployment frequency increased 20% week-over-week, likely driven by the feature freeze lift on Tuesday. CFR remained stable at 5%, suggesting the higher velocity did not compromise stability."}
{This section is the ONLY place the LLM adds interpretive narrative. All numbers above are deterministic.}
```

12. **Deliver as HTML.** Follow the shared HTML delivery pattern in [`_shared/html-delivery.md`](../_shared/html-delivery.md). Report name: `dora-lite`. TLDR includes deployment frequency, change failure rate, and trend direction.

13. **Terminate.** Report is complete when all four metrics are computed with trends and reliability notes.

## Design Principles

1. **Team-level only.** Never surface individual-level metrics (commits per person, deploys per author). Aggregate to team/app level. Netflix policy + EU AI Act (Aug 2026) require this.
2. **Deterministic math first, LLM narrates only.** All metric computation (DF, LT, CFR, FDRT), trend calculation, and reliability assessment are deterministic arithmetic. The LLM writes the "Trend Context" prose section and nothing else. The LLM never assigns severity, classifies performance tiers, or judges whether a metric is "good" or "bad."
3. **Pair metrics with counter-metrics.** Always present velocity (DF, LT) alongside stability (CFR, FDRT). Never report one dimension without the other. A team that ships fast but breaks things is not performing well; a team that never breaks anything but ships once a month is not either.
4. **No retired performance tiers.** DORA 2025 retired Elite/High/Medium/Low. Do not use these labels. Report raw numbers and trends. If the reader asks about tiers, explain the retirement and point to the 7 archetypes model.
5. **Statistical honesty over false precision.** A CFR of 0% from 3 deploys is not "elite stability" — it is insufficient data. Always flag sample size limitations.

## Golden Rules

1. **Try Scribe first.** The Scribe DORA API is the authoritative source. Only fall back to Spinnaker computation if Scribe is genuinely inaccessible.
2. **Always compute all four metrics.** Even if one is N/A (e.g., FDRT with zero failures), include it in the table with an explanation.
3. **Always show the raw counts.** "CFR = 10%" is incomplete. "CFR = 10% (1 failure / 10 deploys)" tells the reader whether to trust the number.
4. **Always include reliability flags.** Every metric gets a Yes/No reliability assessment with sample-size reasoning.
5. **Always pair velocity with stability.** The "Velocity + Stability Pairing" section is mandatory. Trends that show velocity up + stability down (or vice versa) must be called out.
6. **Check ALL configured apps.** Every app in the config gets measured. A missed app is a blind spot.
7. **Trend requires two periods.** If history is insufficient for a comparison period, note "insufficient history for trend" — do not fabricate a baseline.
8. **LLM narrative is confined to Trend Context.** The LLM does not editorialize in the Metric Summary table, the reliability notes, or the per-app breakdown. Those sections are data only.

## Anti-Rationalization Counter-Table

| Excuse | Reality |
|---|---|
| "I computed DF and LT, that gives a good picture of delivery performance." | DORA has four metrics for a reason. Velocity without stability is reckless speed. Compute all four or note explicitly which are missing and why. |
| "CFR is 0%, the team is doing great." | How many deploys? If it's 3 deploys, 0% CFR is meaningless — one failure next week makes it 25%. Show the denominator. Flag the sample size. |
| "I'll classify the team as High performers based on these numbers." | The Elite/High/Medium/Low tiers were retired in DORA 2025. Do not use them. Report raw numbers and trends. |
| "Scribe returned an error so I'll just report that metrics are unavailable." | Fall back to Spinnaker-based computation. The fallback exists for exactly this scenario. Only report "unavailable" if both Scribe AND Spinnaker fail. |
| "FDRT is N/A because there were no failures, so I'll skip it." | N/A is a valid and good result. Include it in the table with "No failures in period" — skipping it hides the fact that you checked. |
| "Lead time from Spinnaker is accurate enough." | Spinnaker measures pipeline-start-to-deploy, not commit-to-deploy. Note the approximation explicitly. True lead time requires SCM integration that Spinnaker alone doesn't provide. |
| "The team only had 4 deploys this week, I'll report the trends anyway." | You can report the numbers, but you MUST flag that DF/LT trends from n=4 are statistically noisy. The reliability column exists for this. |
| "I'll post this to #team-engineering so everyone sees it." | Digest reports go to the configured digest channel only. Never post to a primary team channel unless the user explicitly overrides. |

## Termination Labels

| Label | Meaning |
|---|---|
| `report_complete` | All four metrics computed, trends calculated, reliability flags set, all apps covered |
| `report_complete_fallback` | Scribe unavailable, metrics computed from Spinnaker fallback — noted in report header |
| `report_partial` | Some metrics or apps could not be computed — noted which and why |
| `no_apps_configured` | No apps specified — need config.json or user input |
| `insufficient_data` | Apps found but zero deployments in the period — report states this explicitly |
| `api_error` | Both Scribe and Spinnaker unavailable — report what was gathered before failure |

## Self-Review Checklist

- [ ] All four DORA metrics are present in the summary table (DF, LT, CFR, FDRT)
- [ ] Every metric shows raw counts (e.g., "10% (1/10)"), not just percentages
- [ ] Every metric has a reliability flag with sample-size reasoning
- [ ] Velocity + Stability Pairing section is present
- [ ] Trends computed from actual previous-period data, not fabricated baselines
- [ ] No Elite/High/Medium/Low tier labels anywhere in the report
- [ ] Per-app breakdown included for multi-app configs
- [ ] Failed deployments section present (even if "No failures")
- [ ] Data source noted in header (Scribe vs Spinnaker fallback)
- [ ] LLM narrative confined to Trend Context section only
- [ ] All configured apps were checked
- [ ] Lead time approximation noted if using Spinnaker fallback
- [ ] Report has date header and app list noted
- [ ] HTML version uploaded to S3 with commuter link (unless `--no-html` or upload failed with noted fallback)
- [ ] Slack/chat delivery uses TLDR + link, not the full report
