---
name: ml-pipeline-report
description: "Use when checking ML pipeline health, Metaflow flow status, failed runs, or generating an ML pipeline report. Trigger phrases: metaflow status, ML pipeline health, flow runs, metaflow report, are my flows running, ML pipeline check."

category: report
capabilities: [defect-detection, static-analysis, novelty-discovery]
input_types: [repo]
output_types: [report, code]
complexity: moderate
cost_profile: low
maturity: beta
metadata_source: inferred
---

# ML Pipeline Health Report

Produce an actionable report on Metaflow ML pipeline runs using Metaflow MCP tools and the debug-run skill.

## Configuration

See [`_shared/report-config.md`](../_shared/report-config.md) for the standard config resolution pattern.

**Config schema** (`~/.claude/skills/ml-pipeline-report/config.json`):
- `flows`: list of Metaflow flow name strings
- `namespaces`: list of Metaflow namespace strings (default: `["production"]`)
- `lookback_days`: number (default: 7)

**Required scope:** at least one of `flows` or `namespaces`.

## Arguments

- **flows**: list of Metaflow flow names to check
- **namespaces**: Metaflow namespaces to search (default: `["production"]`)
- **lookback_days**: how far back to check runs (default: match your cadence — 1 for daily, 7 for weekly)

## Workflow

1. **Discover recent runs.** For each configured flow/namespace, query Metaflow for runs within lookback_days. Use the Metaflow MCP tools or invoke the `debug-run` skill pattern to inspect runs.

2. **Classify run status.** For each run: succeeded, failed, running, or timed out. Record run ID, start time, end time (if complete), and duration.

3. **Diagnose failures.** For every failed run, get the failing step, error message, and stack trace summary. Use `Skill(skill="debug-run", args="<FlowName>/<run_id>")` to inspect the run's step-level status and logs.

4. **Check resource usage.** For running flows, note duration so far. Flag any run exceeding 2x its typical duration as "long-running" (compare against recent successful run durations if available).

5. **Generate report.** Output markdown:

```
## ML Pipeline Health Report — {date}
Period: last {lookback_days} days | Flows checked: {N} | Total runs: {N}

### Summary
- Failed: {count} | Running: {count} | Succeeded: {count} | Timed out: {count}

### Failed Runs
(For each: flow name, run ID, failing step, error summary, duration, link/command to inspect)

### Long-Running
(For each: flow name, run ID, duration so far, expected duration)

### Currently Running
(Compact list: flow name, run ID, start time, current step)

### Recently Succeeded
(Compact table: flow name, run ID, duration, completion time)
```

6. **Deliver as HTML.** Follow the shared HTML delivery pattern in [`_shared/html-delivery.md`](../_shared/html-delivery.md). Report name: `ml-pipeline`. TLDR includes flows checked, failure count, and longest running flow.

7. **Terminate.** Report is complete when all sections are populated.

## Design Principles

1. **Team-level only.** Aggregate to team level — it is the right granularity for a periodic digest. Individual-level detail (commits per person, PR count per author) is too noisy for a team report.
2. **Deterministic math first, LLM narrates only.** All classification (severity, flaky vs broken, pass/fail) must be computed deterministically from data. The LLM writes prose around the numbers but never assigns severity or makes classification judgments.
3. **Pair metrics with counter-metrics.** Never report velocity without stability. If showing deploy frequency, also show change failure rate. If showing PR throughput, also show rework rate.

## Golden Rules

1. **Always get the failing step for failed runs.** "Run X failed" without the step name and error is useless. Drill into step-level status.
2. **Check ALL configured flows, not a sample.** Every flow in scope gets checked.
3. **Include run IDs.** Every run reference includes the run ID so the reader can `debug-run` it directly.
4. **Failed runs first.** Report sections ordered by severity.
5. **Duration context matters.** A 2-hour run is fine if it usually takes 2 hours. Flag runs that are significantly longer than their historical average.
6. **"All clear" is still a report.** Full structure with run counts and completion times even when everything passed.

## Anti-Rationalization Counter-Table

| Excuse | Reality |
|---|---|
| "Run failed but I didn't check which step." | The step name and error message are what the ML engineer needs. Get them. |
| "I checked the main flow, the others are probably fine." | Check ALL configured flows. A failed feature pipeline can block downstream training. |
| "The run is still going, I'll skip it." | Running flows need duration tracking. A stuck run is worse than a failed one — at least failures are visible. |
| "I don't have the typical duration to compare against." | Use recent successful runs from the same lookback period as a baseline. No historical data = note it, don't skip the check. |

## Termination Labels

| Label | Meaning |
|---|---|
| `report_complete` | All flows checked, failures have step-level detail and error messages |
| `report_partial` | Some flows checked but errors prevented full coverage |
| `no_flows_found` | No runs found for configured flows — scope may be wrong |
| `api_error` | Metaflow API unreachable or returning errors |

## Self-Review Checklist

- [ ] All configured flows were checked
- [ ] Failed runs have failing step name and error message
- [ ] Run IDs present for every run referenced
- [ ] Long-running section compares against historical duration
- [ ] Failed section appears before succeeded section
- [ ] Report has date header and flow list noted
- [ ] HTML version uploaded to S3 with commuter link (unless `--no-html` or upload failed with noted fallback)
- [ ] Slack/chat delivery uses TLDR + link, not the full report
